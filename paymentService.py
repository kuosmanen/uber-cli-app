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



from fastapi import FastAPI, HTTPException
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



app = FastAPI()
client = MongoClient("mongodb://localhost:27017")
mongoDB = client["uber-cli-database"]
transactionCollection = mongoDB["transactions"]
usersCollection = mongoDB["users"] #this is to check if a user exists

#passenger_id and driver_id is the MongoDB id for the users. this adds a layer of additional security
class PaymentRequest(BaseModel):
    passenger_id: str
    driver_id: str
    amount: float
    cardNumber: str


def validateObjectID(value: str):
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")
    

#the full path is just /pay
@app.post("/")
def pay(req: PaymentRequest):
    try:
        #turning the strings to object_ids to be able to search the database with them
        passenger_oid = validateObjectID(req.passenger_id)
        driver_oid = validateObjectID(req.driver_id)

        #checking if the user exists
        if not usersCollection.find_one({"_id": passenger_oid}):
            raise HTTPException(status_code=404, detail="Pasenger not found")
        if not usersCollection.find_one({"_id": driver_oid}):
            raise HTTPException(status_code=404, detail="Driver not found")
        
        #then continuing with payment
        response = requests.post(PAYMENTURL, json={
            "amount": req.amount,
            "cardNumber": req.cardNumber
        })

        #saving payment to database
        if response.status_code == 200:
            data = response.json()
            transactionCollection.insert_one({
                "passenger_id": req.passenger_id,
                "driver_id": req.driver_id,
                "amount": req.amount,
                "cardNumber": req.cardNumber,
                "transactionID": data.get("transactionID", None)
            })
            return data
        else:
            raise HTTPException(status_code=response.status_code, detail="Payment error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment server not found: {str(e)}")