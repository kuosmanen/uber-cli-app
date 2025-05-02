#help from https://www.geeksforgeeks.org/socket-programming-python/
#https://realpython.com/api-integration-in-python/
#and https://www.geeksforgeeks.org/multithreading-python-set-1/

import socket
import threading
import requests
import json
from pymongo import MongoClient  # Added: Used for MongoDB user data handling

#List of all clients connected
#the socket is used because every thread gets its own socket
#that's how we identify the client!
#{client_socket: type}
#type 0 is driver, type 1 is passenger
clients = {}

# Rides waiting to be accepted by drivers
pending_rides = {}

# Rides that have been assigned to drivers
assigned_rides = {}

#List of all cities and their clients
#{city: [clientSocket1, clientSocket2,...]}
cities = {}

def client_thread(c, addr):
    clients[c] = {"username": "", "type": "", "city": "", "address": ""}  # Updated: Storing user info for each client
    
    mongo = MongoClient("mongodb://localhost:27017")  # Added: Connection to MongoDB
    db = mongo["uber-cli-database"]
    users = db["users"]

    token_msg = c.recv(1024).decode().strip()
    if not token_msg.startswith("TOKEN:"):
        c.send(b"Authentication failed: token missing")
        c.close()
        return

    token = token_msg.split(":", 1)[1]

    try:
        # Token authentication using external API
        res = requests.post("http://127.0.0.1:8000/authentication/authenticate", json={"token": token})
        if res.status_code != 200:
            c.send(b"Authentication failed: invalid token")
            c.close()
            return

        decoded = requests.get("http://127.0.0.1:8000/authentication/userinfo", headers={"Authorization": f"Bearer {token}"}).json()
        username = decoded["username"]
        accountType = decoded["accountType"]
    except:
        c.send(b"Authentication error")
        c.close()
        return

    user_doc = users.find_one({"username": username})
    if not user_doc:
        c.send(b"Authentication failed: user not found")
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

            if message.startswith("DRIVER_READY:"):
                if clients[c]["type"] != "driver":
                    c.send(b"You are not a driver.")
                    continue
                _, city, address = message.split(":", 2)
                clients[c]["city"] = city
                clients[c]["address"] = address
                if city not in cities:
                    cities[city] = []
                if c not in cities[city]:
                    cities[city].append(c)
                c.send(b"Ready to accept rides!")
                users.update_one(
                    {"username": clients[c]["username"]},
                    {"$set": {"status": "available"}}
                )

            elif message.startswith("REQUEST_RIDE:"):
                if clients[c]["type"] != "passenger":
                    c.send(b"You are not a passenger.")
                    continue
                _, city, address = message.split(":", 2)
                clients[c]["city"] = city
                clients[c]["address"] = address

                eligible_drivers = cities.get(city, [])
                #if there is no available drivers
                if not eligible_drivers:
                    c.send(b"No drivers available in your city.")
                    continue

                for d in eligible_drivers:
                    try:
                        d.send(f"RIDE_REQUEST:{city}:{address}".encode())
                    except:
                        pass
                    
                # Timeout to wait for driver response
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

            elif message.startswith("ACCEPT_RIDE"):
                if clients[c]["type"] != "driver":
                    c.send(b"Only drivers can accept rides.")
                    continue

                accepted = False
                for passenger, ride in pending_rides.items():
                    if passenger in assigned_rides:
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
                    passenger.send(b"Your ride has been completed.")
                    c.send(b"Ride completed. Waiting for next ride...")
                except:
                    pass

                users.update_one(
                    {"username": clients[c]["username"]},
                    {"$set": {"status": "available"}}
                )

        except:
            break
# emptying socket
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
