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
    
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo["uber-cli-database"]
    users = db["users"]

    tokenMessage = c.recv(1024).decode().strip()
    if not tokenMessage.startswith("TOKEN:"):
        c.send(b"Authentication failed: token missing")
        c.close()
        return

    token = tokenMessage.split(":", 1)[1]

    try:
        #Token authentication using authentication microservice API
        res = requests.post(AUTHENTICATIONURL, json={"token": token})
        if res.status_code != 200:
            errorMesage = res.json().get("detail")
            c.send(errorMesage.encode())
            c.close()
            return

        decoded = requests.get(USERINFOURL, headers={"Authorization": f"Bearer {token}"}).json()
        username = decoded["username"]
        accountType = decoded["accountType"]
    except:
        c.send(b"Authentication error")
        c.close()
        return

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

            #driver setting their location indicating that they're ready to drive
            if message.startswith("DRIVER_READY:"):
                if clients[c]["type"] != "driver":
                    c.send(b"You're not a driver.")
                    continue

                #getting the city and address from the driver's request
                _, city, address = message.split(":", 2)
                clients[c]["city"] = city
                clients[c]["address"] = address
                #Initializing a list to store drivers' sockets for that city if there isn't one
                if city not in cities:
                    cities[city] = []
                #adding the driver to the list of drivers in the city
                if c not in cities[city]:
                    cities[city].append(c)

                #responding to confirm success
                c.send(b"Ready to accept rides!")
                #filtering out this user in the database and then adding the correct status for them
                users.update_one(
                    {"username": clients[c]["username"]},
                    {"$set": {"status": "available"}}
                )

            elif message.startswith("REQUEST_RIDE:"):
                if clients[c]["type"] != "passenger":
                    c.send(b"Drivers cannot request rides.")
                    continue

                #getting the city and address from the passenger's request
                _, city, address, destination = message.split(":", 3)
                clients[c]["city"] = city
                clients[c]["address"] = address
                clients[c]["destination"] = destination

                #getting the list of available drivers in passenger's city
                eligible_drivers = cities.get(city, [])
                #if there is no available drivers
                if not eligible_drivers:
                    c.send(b"No drivers available in your city.")
                    continue

                for d in eligible_drivers:
                    try:
                        d.send(f"Ride request in {city} from {address} to {destination}".encode())
                    except:
                        pass
                    
                # Timeout to wait for driver response
                def timeout():
                    #if passenger hasn't gotten a ride when timeout happens, the pending ride is deleted
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
                #this code part ends here but the timeout function is still going
                #after 30sec it runs the timeout() function

            elif message.startswith("ACCEPT_RIDE"):
                if clients[c]["type"] != "driver":
                    c.send(b"Only drivers can accept rides.")
                    continue

                accepted = False
                #passenger is the passenger's socket and ride is the ride info: city, address, responses, timer
                for passenger, ride in pending_rides.items():
                    if passenger in assigned_rides:
                        c.send(b"This ride was already accepted by someone.")
                        continue
                    if ride["city"].lower() == clients[c]["city"].lower():
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

            elif message.startswith("RIDE_COMPLETE"):
                if clients[c]["type"] != "driver":
                    c.send(b"Only drivers can complete rides.")
                    continue
                
                #Getting the passenger socket from assignedrides using the driver's socket
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

                    #Now payment processing for passenger
                    #We get the driver and passenger info from the database
                    driverRecord = users.find_one({"username": clients[c]["username"]})
                    passengerRecord = users.find_one({"username": clients[passenger]["username"]})

                    #then their object IDs to send to payment microservice
                    if driverRecord and passengerRecord:
                        driver_id = str(driverRecord["_id"])
                        passenger_id = str(passengerRecord["_id"])
                    
                    paymentData = {
                        "passenger_id": passenger_id,
                        "driver_id": driver_id,
                        "amount": 10,
                    }

                    try:
                        response = requests.post(PAYMENTURL, json= paymentData)
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

                users.update_one(
                    {"username": clients[c]["username"]},
                    {"$set": {"status": "available"}}
                )

        except:
            break
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
