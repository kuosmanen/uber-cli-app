#help from https://www.geeksforgeeks.org/socket-programming-python/
#https://realpython.com/api-integration-in-python/
#and https://www.geeksforgeeks.org/multithreading-python-set-1/

import socket
import threading
import requests
from pymongo import MongoClient

AUTHENTICATIONURL = "http://127.0.0.1:8000/authentication/authenticate"
USERINFOURL = "http://127.0.0.1:8000/authentication/userinfo"
PAYMENTURL = "http://127.0.0.1:8000/payment/pay"

#List of all clients connected
#the socket is used because every thread gets its own socket
#that's how we identify the client!
#{client_socket: username, type, city, address}

clients = {}

# Rides waiting to be accepted by drivers
pending_rides = {}

# Rides that have been assigned to drivers
assigned_rides = {}

#List of all cities and their clients
#{city: [clientSocket1, clientSocket2,...]}
cities = {}

def client_thread(c, addr):
    clients[c] = {"username": "", "type": "", "city": "", "address": ""}

    # MongoDB database for user data
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo["uber-cli-database"]
    users = db["users"]

    tokenMessage = c.recv(1024).decode().strip()
    if not tokenMessage.startswith("TOKEN:"):
        c.send(b"Authentication failed: token missing")
        c.close()
        return

# Extract the token from the incoming authentication message
token = tokenMessage.split(":", 1)[1]

try:
    # Authenticate the token using the authentication microservice
    res = requests.post(AUTHENTICATIONURL, json={"token": token})
    if res.status_code != 200:
        errorMesage = res.json().get("detail")
        c.send(errorMesage.encode())
        c.close()
        return

    # Retrieve user information using the valid token
    decoded = requests.get(USERINFOURL, headers={"Authorization": f"Bearer {token}"}).json()
    username = decoded["username"]
    accountType = decoded["accountType"]
except:
    # Authentication or user info fetch failed
    c.send(b"Authentication error")
    c.close()
    return

# Store the authenticated user's info in the clients dictionary
clients[c]["username"] = username
clients[c]["type"] = accountType
c.send(f"Authenticated as {username} ({accountType})".encode())

while True:
    try:
        data = c.recv(1024)
        if not data:
            break

        message = data.decode().strip()
        print(message)

        # Driver signals they are ready to accept rides
        if message.startswith("DRIVER_READY:"):
            if clients[c]["type"] != "driver":
                c.send(b"You're not a driver.")
                continue

            # Extract city and address from message
            _, city, address = message.split(":", 2)
            clients[c]["city"] = city
            clients[c]["address"] = address

            # Add driver to the city-specific driver pool
            if city not in cities:
                cities[city] = []
            if c not in cities[city]:
                cities[city].append(c)

            # Confirm driver is ready and update DB
            c.send(b"Ready to accept rides!")
            users.update_one(
                {"username": clients[c]["username"]},
                {"$set": {"status": "available"}}
            )

        # Passenger requests a ride
        elif message.startswith("REQUEST_RIDE:"):
            if clients[c]["type"] != "passenger":
                c.send(b"Drivers cannot request rides.")
                continue

            # Extract passenger info
            _, city, address, destination = message.split(":", 3)
            clients[c]["city"] = city
            clients[c]["address"] = address
            clients[c]["destination"] = destination

            eligible_drivers = cities.get(city, [])

            if not eligible_drivers:
                c.send(b"No drivers available in your city.")
                continue

            # Notify all available drivers in the city about the request
            for d in eligible_drivers:
                try:
                    d.send(f"Ride request in {city} from {address} to {destination}".encode())
                except:
                    pass

            # Set a timeout for driver responses
            def timeout():
                if c not in assigned_rides:
                    c.send(b"No driver accepted your ride request in time.")
                del pending_rides[c]

            timer = threading.Timer(30.0, timeout)
            timer.start()
            pending_rides[c] = {
                "city": city,
                "address": address,
                "responses": [],
                "timer": timer
            }

            c.send(b"Ride request sent. Waiting for driver...")

        # Driver accepts a ride
        elif message.startswith("ACCEPT_RIDE"):
            if clients[c]["type"] != "driver":
                c.send(b"Only drivers can accept rides.")
                continue

            accepted = False

            for passenger, ride in pending_rides.items():
                if passenger in assigned_rides:
                    c.send(b"This ride was already accepted by someone.")
                    continue
                if ride["city"].lower() == clients[c]["city"].lower():
                    # Assign driver and cancel ride timeout
                    assigned_rides[passenger] = c
                    ride["timer"].cancel()

                    users.update_one(
                        {"username": clients[c]["username"]},
                        {"$set": {"status": "on_ride"}}
                    )

                    try:
                        passenger.send(f"Ride accepted. Driver location: {clients[c]['address']}".encode())
                        c.send(f"You accepted the ride. Passenger location: {clients[passenger]['address']}".encode())
                    except:
                        pass

                    accepted = True
                    break

            if not accepted:
                c.send(b"Ride request not accepted. Ready to accept rides!")

        # Driver marks the ride as completed
        elif message.startswith("RIDE_COMPLETE"):
            if clients[c]["type"] != "driver":
                c.send(b"Only drivers can complete rides.")
                continue

            # Find the associated passenger
            passenger = None
            for p, d in assigned_rides.items():
                if d == c:
                    passenger = p
                    break

            if not passenger:
                c.send(b"No active ride to complete.")
                continue

            del assigned_rides[passenger]

            try:
                passenger.send(b"Your ride has been completed. Proceeding to pay automatically...")
                c.send(b"Ride completed. Waiting for payment...")

                # Get database records for payment processing
                driverRecord = users.find_one({"username": clients[c]["username"]})
                passengerRecord = users.find_one({"username": clients[passenger]["username"]})

                if driverRecord and passengerRecord:
                    driver_id = str(driverRecord["_id"])
                    passenger_id = str(passengerRecord["_id"])

                # Call payment microservice
                paymentData = {
                    "passenger_id": passenger_id,
                    "driver_id": driver_id,
                    "amount": 10,
                }

                try:
                    response = requests.post(PAYMENTURL, json=paymentData)
                    if response.status_code == 200:
                        c.send(b"Payment processed successfully.")
                        passenger.send(b"Payment successful. Thank you!")
                    else:
                        errorMessage = res.json().get("detail")
                        c.send(f"Payment service failed: {errorMessage}. Please contact support.".encode())
                        passenger.send(f"Payment failed: {errorMessage}. Please contact support.".encode())
                except Exception as e:
                    c.send(b"Payment service unreachable.")
                    passenger.send(b"Payment service unreachable.")
            except:
                pass

            # Set driver status back to available
            users.update_one(
                {"username": clients[c]["username"]},
                {"$set": {"status": "available"}}
            )

    except:
        break  # Socket error or disconnect
#emptying socket
    if c in clients:
        city = clients[c].get("city", "")
        if city in cities and c in cities[city]:
            cities[city].remove(c)
        del clients[c]
    for p, d in list(assigned_rides.items()):
        if d == c or p == c:
            del assigned_rides[p]
    if c in pending_rides:
        try:
            pending_rides[c]["timer"].cancel()
        except:
            pass
        del pending_rides[c]
    c.close()
    print(f"Socket closed for {c}")

def start_server():
    s = socket.socket()		 
    print ("Socket successfully created")

    port = 123			

    #empty string because we want to listen for connections
    s.bind(("", port))		 
    print ("socket binded to %s" %(port)) 

    #we put the socket into listening mode
    s.listen()	 
    print ("The socket is listening") 

    #looping forever for connections
    while True: 
        c, addr = s.accept() #accept method waits for incoming connection
        #c is the client socket object, addr is the address of the client

        #creating a new thread for handling the client request
        thread = threading.Thread(target=client_thread, args=(c, addr))
        thread.start()
        print ("Client thread started for", addr)


start_server()
