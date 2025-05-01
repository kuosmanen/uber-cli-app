import requests

SERVER = "http://localhost:8001"

def register(username, password):
    r = requests.post(f"{SERVER}/register", json={"username": username, "password": password})
    print(r.json())

def login(username, password):
    if (response = requests.post(f"{SERVER}/login", json={"username": username, "password": password})) ==
    return True

# Example usage
register("alice", "pass123")
login("alice", "pass123")







print("Welcome to the ride service!\nFirst, login to the server")
nickname = None
ip = None
thread = None

#Main loop to handle user inputs

def main():
    while True:
        option = input("\n1 Login\n2 Register\n0 Exit program\nChoose an option: ")
        
        if option == "1":
            username = input("Enter your username: ")
            password = input("Enter your password: ")

            try: 
                s.connect((ip, PORT))
                #When we connect to theserver, we can start listening to incoming messages in a separate thread
                #the deamon=True makes the thread exit when the main program exits
                if not thread:
                    thread = threading.Thread(target=listen_for_messages, daemon=True)
                    thread.start()
                print("Connected to the server!")
                print("The commands are the following:")
                print("\"NICKNAME (new_nickname)\" to change your nickname")
                print("You cannot receive private messages if you don't have a nickname!")
                print("Available channels are: general, cats and movies")
                print("\"JOIN (channel_name)\" to join a channel")
                print("Then just type a message to send it to everyone your joined channel(s)")
                print("\"LEAVE (channel_name)\" to leave a channel")
                print("To private message someone, start the message with \"@username message\"")
                print("\"DISCONNECT\" to disconnect from the server")
                print()
                while True:
                    message = input("")
                    if message == "DISCONNECT":
                        s.sendall(message.encode())
                        s.close()
                        print("Disconnected from the server.")
                        thread = None
                        break
                    
                    try:
                        s.sendall(message.encode())
                    except (socket.error, OSError):
                        print("Connection lost.")
                        thread = None
                        break  #Exiting loop if sending fails
                
            except  socket.error:
                print("Invalid IP address")
                continue

        elif option == "0":
            print("Exiting")
            s.close()
            break

        else:
            print("Invalid option. Please try again.")
            continue




main()