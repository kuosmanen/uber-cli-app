#help from https://www.geeksforgeeks.org/socket-programming-python/
#https://realpython.com/api-integration-in-python/
#and https://www.geeksforgeeks.org/multithreading-python-set-1/







import socket
import threading
import requests
import json

#List of all clients connected
#the socket is used because every thread gets its own socket
#that's how we identify the client!
#{client_socket: type}
#type 0 is driver, type 1 is passenger
clients = {}

#List of all cities and their clients
#{city: [clientSocket1, clientSocket2,...]}
cities = {"Lappeenranta":[], "Mikkeli":[], "Imatra":[]}

def client_thread(c, addr):
    clients[c] = 0
    #we set the socket to be the type specified
    
    
    while True:
        try:
            data = c.recv(1024)
            if not data:
                print(f"Client {addr} disconnected.")
                break
            
            message = data.decode()
            print(f"Received from {addr}: {message}")

            
        except Exception as e:
            print("An error occurred:", str(e))
            break

    c.close()
    print(f"Connection closed for {addr}")




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