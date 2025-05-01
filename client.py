import requests
import json

APIURL = "http://127.0.0.1:8001"



def register(username, password):
    r = requests.post(f"{APIURL}/register", json={"username": username, "password": password})
    print(r.json())

def login(username, password):
    response = requests.post(f"{APIURL}/login", json={"username": username, "password": password})

    if response.status_code == 200:
        data = response.json()
        print("Logged in")
        print("Token:", data["token"])
        return data["token"]
    else:
        print("Login failed:", response.text)
        return None









print("Welcome to the ride service!\nFirst, login to the server")
nickname = None
#Main loop to handle user inputs

def main():
    while True:
        option = input("\n1 Login\n2 Register\n0 Exit program\nChoose an option: ")
        
        if option == "1":
            username = input("Enter your username: ")
            password = input("Enter your password: ")

            if login(username, password) == None:
                continue

            print("Connected to the server!")

            while True:
                print()
                
            
        elif option == "0":
            print("Exiting")
            break

        else:
            print("Invalid option. Please try again.")
            continue




main()