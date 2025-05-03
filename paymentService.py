#This microservice sends payment requests to third-party API
#The API used in this code is just a mock server made with Postman
#but this microservice could be changed to use real payment API
#this is just proof of concept
#The payment is meant to go to the service provider's bank account
#then the service provider pays the drivers, so we log the payments into the database

#Additionally, this service could be made only accessible to the other microservices by,
#for example using a network-level firewall that restricts access from outside

#help from https://learning.postman.com/docs/design-apis/mock-apis/set-up-mock-servers/

#This microservice is designed to be used by the othermicroservices
#the JSON body this microservice takes to the /pay path can be the following
#{
#   "passenger_id": "fasrrgb4u3ith3478gbbg843b"
#   "driver_id": "ufji6arbgi54iu56o456r3ui"
#   "amount": 123,
#   "cardNumber": "42424242424242"
#}
#BEFORE SENDING A REQUEST HERE, TURN OBJECT IDs TO STRINGS
#fastapi and pydantic can't work with MongoDB ObjectIDs so they have to be strings first



from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from pymongo import MongoClient
import requests
from bson import ObjectId #MongoDB uses objectID for the ID and not a string
from bson.errors import InvalidId #for objectID validation

#payment url of this service's provider
PAYMENTURL = "https://0f636854-f90f-4117-b130-ca61d54f75f6.mock.pstmn.io/pay"
#The PostMan mock server always responds with a success message and the same transactionID
#regardless of the amount or cardNumber
#Postman returns this
#{
#    "status": "success",
#    "transactionID": "mock12345"
#}

AUTHENTICATIONURL = "http://127.0.0.1:8000/authentication/authenticate"

app = FastAPI()
client = MongoClient("mongodb://localhost:27017")
mongoDB = client["uber-cli-database"]
transactionCollection = mongoDB["transactions"]
paymentInfoCollection = mongoDB["paymentInfos"]
usersCollection = mongoDB["users"] #this is to check if a user exists

#passenger_id and driver_id is the MongoDB id for the users. this adds a layer of additional security
class PaymentRequest(BaseModel):
    passenger_id: str
    driver_id: str
    amount: float

class CardRequest(BaseModel):
    cardNumber: str


def validateObjectID(value: str):
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")
    
@app.post("/addcard")
def addCard(req: CardRequest, authorization: str = Header(...)):
    #verifying the token so we can add the card
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split(" ", 1)[1]

    try:
        response = requests.post(AUTHENTICATIONURL, json={"token": token})
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Authentication service not reached")
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail= response.json().get("detail"))
    #Now adding the card
    #but first we need the user objectID
    username = response.json().get("username")
    user = usersCollection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    paymentInfoCollection.insert_one({
        "user_id": user["_id"],
        "cardNumber": req.cardNumber
    })
    return {"message": "Card added successfully"}

#This takes a token in the header and returns status 200 if the user has a bank card saved
@app.post("/checkforcard")
def checkForCard(authorization: str = Header(...)):
    #verifying the token so we can respond
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split(" ", 1)[1]

    try:
        response = requests.post(AUTHENTICATIONURL, json={"token": token})
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Authentication service not reached")
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail= response.json().get("detail"))
    #but first we need the user objectID
    username = response.json().get("username")
    user = usersCollection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not paymentInfoCollection.find_one({"user_id": user["_id"]}):
        return {"hasCard": False}
    
    #returning success message to indicate that the user has a bank card
    return {"hasCard": True}

@app.post("/pay")
def pay(req: PaymentRequest):
    try:
        #turning the strings to object_ids to be able to search the database with them
        passenger_oid = validateObjectID(req.passenger_id)
        driver_oid = validateObjectID(req.driver_id)

        #checking if the user exists
        passenger = usersCollection.find_one({"_id": passenger_oid})
        if not passenger:
            raise HTTPException(status_code=404, detail="Pasenger not found")
        driver = usersCollection.find_one({"_id": driver_oid})
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        #Getting the cardNumbers of the passenger and driver
        passengerPaymentInfo = paymentInfoCollection.find_one({"user_id": passenger["_id"]})
        driverPaymentInfo = paymentInfoCollection.find_one({"user_id": driver["_id"]})
        passengerCardNumber = passengerPaymentInfo["cardNumber"]
        driverCardNumber = driverPaymentInfo["cardNumber"]
        #then continuing with payment
        #The passenger pays of course
        response = requests.post(PAYMENTURL, json={
            "amount": req.amount,
            "cardNumber": passengerCardNumber
        })

        #saving payment to database
        if response.status_code == 200:
            data = response.json()
            transactionCollection.insert_one({
                "passenger_id": passenger["_id"],
                "driver_id": driver["_id"],
                "amount": req.amount,
                "passengerCardNumber": passengerCardNumber,
                "driverCardNumber": driverCardNumber,
                "transactionID": data.get("transactionID", None)
            })
            return {"message": "success"}
        else:
            raise HTTPException(status_code=response.status_code, detail="Payment error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment server not found: {str(e)}")