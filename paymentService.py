#This microservice sends payment requests to third-party API
#The API used in this code is just a mock server made with Postman
#but this microservice could be changed to use real payment API
#this is just proof of concept

#This microservice is designed to be used by the othermicroservices
#the JSON body this microservice takes to the /pay path can be the following
#{
#   "amount": 123
#   "cardNumber": "42424242424242"
#}

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
import requests


PAYMENTURL = "https://0f636854-f90f-4117-b130-ca61d54f75f6.mock.pstmn.io/pay"
#The PostMan mock server always responds with a success message and the same transactionID
#regardless of the amount and cardNumber

app = FastAPI()
client = MongoClient("mongodb://localhost:27017")
mongoDB = client["authentication"]
paymentCollection = mongoDB["paymentInfo"]


class PaymentRequest(BaseModel):
    amount: float
    cardNumber: str

#the full path is just /pay
@app.post("/")
def pay(req: PaymentRequest):
    try:
        response = requests.post(PAYMENTURL, json={
            "amount": req.amount,
            "cardNumber": req.cardNumber
        })

        if response.status_code == 200:
            data = response.json()
            paymentCollection.insert_one({
                "amount": req.amount,
                "cardNumber": req.cardNumber,
                "status": data.get("status"),
                "transactionID": data.get("transactionID", None)
            })
            return data
        else:
            raise HTTPException(status_code=response.status_code, detail="Payment error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment server not found: {str(e)}")