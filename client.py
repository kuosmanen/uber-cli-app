#help from https://www.geeksforgeeks.org/how-to-create-microservices-with-fastapi/

import requests



APIURL = "http://127.0.0.1:8000"



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








#Main loop to handle user inputs
def main():
    print("Welcome to the ride service!\nFirst, login to the server")
    while True:
        option = input("\n1 Login\n2 Register\n0 Exit program\nChoose an option: ")


        if option == "1":
            username = input("Enter your username: ")
            password = input("Enter your password: ")

            token = login(username, password)
            if not token:
                continue

            print("Welcome to the service! Choose what you want to do next")
            while True:
                option = input("\n1 Login\n2 Register\n0 Sign out\nChoose an option: ")

                #Tänne sitten ridematching

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
        

        elif option == "0":
            print("Exiting")
            break


        else:
            print("Invalid option. Please try again.")
            continue




main()