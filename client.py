#help from https://www.geeksforgeeks.org/how-to-create-microservices-with-fastapi/

import requests
import socket

APIURL = "http://127.0.0.1:8000"

TOKEN = None

def register(username, password, accountType):
    #accountType is either passenger or driver
    response = requests.post(f"{APIURL}/authentication/register", json={"username": username, "password": password, "accountType": accountType})
    data = response.json()
    
    if response.status_code == 200:
        print(data.get("message"))
        return True
    else:
        print("Registration failed:", data.get("detail"))
        return False

def login(username, password):
    response = requests.post(f"{APIURL}/authentication/login", json={"username": username, "password": password})
    data = response.json()

    if response.status_code == 200:
        print("Logged in")
        return data["token"]
    else:
        print("Login failed:", data.get("detail"))
        return False
    
def addBankCard(cardNumber):
    response = requests.post(f"{APIURL}/payment/addcard", json={"cardNumber": cardNumber}, headers={"Authorization": f"Bearer {TOKEN}"})
    data = response.json()

    if response.status_code == 200:
        data = response.json()
        print(data.get("message"))
    else:
        errorMessage = response.json().get("detail")
        print(f"Failed to add card: {errorMessage}")



#Main loop to handle user inputs
def main():
    print("Welcome to the ride service!\nFirst, login to the server")
    while True:
        option = input("\n1 Login\n2 Register\n3 Add Payment option\n4 Use the ride service\n0 Exit program\nChoose an option: ")


        if option == "1":
            global TOKEN
            username = input("Enter your username: ")
            password = input("Enter your password: ")

            TOKEN = login(username, password)


        elif option == "2":
            username = input("Enter a new username: ")
            password = input("Enter a password: ")
            #We make sure the user typed the password correctly by asking them to type it again
            passwordAttempt2 = input("Re-enter the password: ")
            if password == passwordAttempt2:
                #next we ask if they want to be a passenger or driver
                accountType = None
                while accountType != "1" and accountType != "2":
                    accountType = input("Type 1 if you want to be a passenger, type 2 if you want to be a driver: ")
                    if accountType == "1":
                            accountType = "passenger"
                    elif accountType == "2":
                        accountType = "driver"
                    else:
                        print("Input was not 1 or 2. Try again...")
                        continue
                    register(username, password, accountType)
                    break
            else:
                print("Error: Passwords did not match.")
        
        elif option == "3":
            #Adding a bank card
            if not TOKEN:
                print("You have to log in first!")
                continue
            print("Add you bank card number so you can pay for rides.")
            cardNumber = input("Bank card number: ")
            addBankCard(cardNumber)
        
        elif option == "4":
            if not TOKEN:
                print("You have to log in first!")
                continue

            #Checking for valid payment info aka. bank card for both driver and passenger
            response = requests.post(f"{APIURL}/payment/checkforcard", headers={"Authorization": f"Bearer {TOKEN}"})
            data = response.json()

            if response.status_code != 200:
                errorMessage = data.get("detail")
                print(f"Error: {errorMessage}")
                continue
            if data.get("hasCard") == False:
                print("You need to add a bank card first!")
                continue



            #Starting socket connection and authentication with token
            s = socket.socket()
            s.connect(("127.0.0.1", 123))
            s.send(f"TOKEN:{TOKEN}".encode())
            response = s.recv(1024).decode()
            if "fail" in response.lower():
                print("Socket authentication failed.")
                s.close()
                continue
            print(response)

            #Fetching user type to determine client behavior
            userinfo = requests.get(f"{APIURL}/authentication/userinfo", headers={"Authorization": f"Bearer {TOKEN}"})
            accountType = userinfo.json()["accountType"]

            if accountType == "driver":
                #driver starting to listen for requests
                print("Welcome, driver! Start receving ride requests by entering your location.")
                city = input("Enter your current city: ")
                address = input("Enter your current street address: ")
                s.send(f"DRIVER_READY:{city}:{address}".encode())
                print("Waiting for ride requests...\n")
                while True:
                    msg = s.recv(1024).decode()
                    if not msg.strip():
                        continue
                    print(">>>", msg)
                    if "Ride request" in msg:
                        accept = input("Accept the ride? (yes/no): ").strip().lower()
                        if accept == "yes":
                            s.send(b"ACCEPT_RIDE")  #Driver accepts ride
                        else:
                            print("Ride request not accepted. Ready to accept rides!")
                    elif "Passenger location" in msg:
                        print("You are now driving to the passenger...")
                        input("Press Enter when the ride is complete.")
                        s.send(b"RIDE_COMPLETE")  #completing the ride
                        #receiving last messages
                        msg = s.recv(1024).decode() #waiting for payment msg
                        print(">>>", msg)
                        msg = s.recv(1024).decode() #success, fail or 404
                        print(">>>", msg)
                        break

            elif accountType == "passenger":
                #Passenger requesting a ride
                print("Welcome, passenger! Request a ride by entering your location.")
                #asking ride info from passenger
                city = input("Enter your city: ")
                address = input("Enter your current street address: ")
                destination = input("Enter your destination address: ")
                #sending info to server
                s.send(f"REQUEST_RIDE:{city}:{address}:{destination}".encode())
                print("Ride request sent. Waiting 30 seconds for response...\n")
                #checking if ride is accepted
                while True:
                    msg = s.recv(1024).decode()
                    if not msg.strip():
                        continue
                    print(">>>", msg)
                    if "no driver accepted" in msg.lower() or "no drivers available" in msg.lower():
                        print("Returning to main menu...")
                        s.close()
                        break
                    if "payment" in msg.lower():
                        if not msg.strip():
                            print("Unexpected error during payment. Contact support.")
                        break
        

        elif option == "0":
            print("Exiting")
            break


        else:
            print("Invalid option. Please try again.")
            continue

main()
