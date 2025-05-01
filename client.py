#help from https://www.geeksforgeeks.org/how-to-create-microservices-with-fastapi/

import requests
import json



APIURL = "http://127.0.0.1:8000"



def register(username, password):
    response = requests.post(f"{APIURL}/authentication/register", json={"username": username, "password": password})

    if response.status_code == 200:
        data = response.json()
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
        print("Token:", data["token"])
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

            print("Connected to the server!")

            while True:
                print("Welcome to the service! Choose what you want to do next")
                option = input("\n1 Login\n2 Register\n0 Sign out\nChoose an option: ")

                #Tänne sitten ridematching

        elif option == "2":
            username = input("Enter a new username: ")
            password = input("Enter a password: ")
            #We make sure the user typed the password correctly by asking them to type it again
            passwordAttempt2 = input("Re-enter the password: ")
            if password == passwordAttempt2:
                register(username, password)
            else:
                print("Error: Passwords did not match.")
        

        elif option == "0":
            print("Exiting")
            break


        else:
            print("Invalid option. Please try again.")
            continue




main()