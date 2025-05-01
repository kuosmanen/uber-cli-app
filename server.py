#help from https://www.geeksforgeeks.org/socket-programming-python/
#and https://www.geeksforgeeks.org/multithreading-python-set-1/










import socket
import threading

#List of all clients connected
#the socket is used because every thread gets its own socket
#that's how we identify the client!
#{client_socket: type}
#type 0 is driver, type 1 is passenger
chatters = {}

#List of all cities and their clients
#{city: [clientSocket1, clientSocket2,...]}
cities = {"Lappeenranta":[], "Mikkeli":[], "Imatra":[]}

def client_thread(c, addr):
    chatters[c] = 0
    #we set the socket to be the type specified
    
    
    while True:
        try:
            data = c.recv(1024)
            if not data:
                print(f"Client {addr} disconnected.")
                break
            
            message = data.decode()
            print(f"Received from {addr}: {message}")


            #We set the name to the nickname if the user has given one
            #also updating the list of chatters with new nickname
            if message.startswith("NICKNAME "):
                unique = True
                nickname = message[9:]
                if nickname == "Anonymous":
                    c.sendall("SERVER: Your name cannot be Anonymous".encode())
                    continue
                elif nickname == "":
                    c.sendall("SERVER: Please provide a nickname".encode())
                    continue
                for clientSocket, nick in chatters.items():
                    if nick == nickname:
                        unique = False #if the name is not unique we set this flag as false
                        c.sendall("SERVER: That nickname is already taken.".encode())
                        break
                
                if not unique:
                    continue
                #Storing the socket with the nickname
                chatters[c] = nickname
                print(f"Client {addr} set nickname to: {nickname}")
                c.sendall("SERVER: Nickname set successfully".encode())


            elif message.startswith("JOIN "):
                requestedChannel = message[5:]
                if requestedChannel in channels:
                    if c in channels[requestedChannel]:
                        c.sendall(f"SERVER: You are already in channel \"{requestedChannel}\"".encode())
                        continue
                    #Notifying other clients in the channel that the user joined
                    for clientSocket in channels[requestedChannel]:
                        clientSocket.sendall(f"[{requestedChannel}] {chatters[c]} joined the channel".encode())
                    #We add the client to the requested channel
                    channels[requestedChannel].append(c)
                    c.sendall(f"SERVER: Successfully connected to channel \"{requestedChannel}\"".encode())
                else:
                    c.sendall((f"SERVER: \"{requestedChannel}\" is not a valid channel").encode())
            

            elif message.startswith("LEAVE "):
                requestedChannel = message[6:]
                if requestedChannel in channels:
                    #We remove the client from the requested channel if they are in that channel
                    if c in channels[requestedChannel]:
                        channels[requestedChannel].remove(c)
                        c.sendall(f"SERVER: Successfully left channel {requestedChannel}".encode())
                        #Notifying other clients in the channel that the user left
                        for clientSocket in channels[requestedChannel]:
                            clientSocket.sendall(f"[{requestedChannel}] {chatters[c]} left the channel".encode())
                    else:
                        c.sendall(f"SERVER: You are not in channel \"{requestedChannel}\"".encode())
                else:
                    c.sendall((f"SERVER: \"{requestedChannel}\" is not a valid channel").encode())


            elif message.startswith("@"):
                parts = message[1:].split(" ", 1)#everything after @ but before spacebar
                receiver = parts[0] 
                if  not receiver:
                    c.sendall("SERVER: You must include a nickname after the @ symbol".encode())
                    continue
                elif len(parts) < 2 or not parts[1].strip():
                    c.sendall("SERVER: You must include a message after @[user]".encode())
                    continue
                if receiver == "Anonymous":
                    c.sendall("SERVER: The user you want to private message has to have a nickname set".encode())
                    continue

                privateMessage = parts[1] #everything after spacebar

                #finding the recipient socket
                found = False
                for clientSocket, nick in chatters.items():
                    if nick == receiver:
                        found = True
                        #we send the message to the recipient socket
                        clientSocket.sendall(f"Private message from {chatters[c]}: {privateMessage}".encode())
                        c.sendall("SERVER: Private message sent successfully".encode())
                        break
                if not found:
                    c.sendall(f"SERVER: A user with name \"{receiver}\" could not be found".encode())


            elif message == "DISCONNECT":
                #First we tell everyone who disconnected
                for channelName, clientSockets in channels.items():
                    if c in clientSockets: #if the user is in the channel
                        for clientSocket in clientSockets:
                            if clientSocket!= c: #if the user is not the sender itself
                                clientSocket.sendall(f"[{channelName}] {chatters[c]} disconnected".encode())

                #removing the chatter from the chatters dict. and the channels dict.
                chatters.pop(c, None)
                for channel, clients in channels.items():
                    if c in clients:
                        clients.remove(c)
                break


            #This is just sending a normal message
            else:
                #We loop over all the channels the user is in and send the message to everyone in the channels
                senderName = chatters.get(c)
                sentToChannel = False #this is to check if the user is in any channel yet
                for channelName, clientSockets in channels.items():
                    if c in clientSockets: #if the user is in the channel
                        sentToChannel = True
                        for clientSocket in clientSockets:
                            if clientSocket!= c: #if the user is not the sender itself
                                clientSocket.sendall(f"[{channelName}] {senderName}: {message}".encode())
                if not sentToChannel:
                    c.sendall("SERVER: Your message was not sent to anywhere. Use JOIN command to join a channel or privately message someone instead.".encode())
        
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