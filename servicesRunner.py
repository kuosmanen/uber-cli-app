#help from https://www.geeksforgeeks.org/fastapi-mounting-a-sub-app/

#Here we basically mount the microservices to run on fastapi server.
#In the future this could be expanded or changed to run the microservices on different machines
#and also adding redundancy by cloning machines etc.
#but for now we just run all microservices on one machine.

from fastapi import FastAPI
from authenticationService import app as authenticationApp
from paymentService import app as paymentApp

subApp = FastAPI()

#Including microservices to handle requests to paths, for example "/authentication/login" etc.
subApp.mount("/authentication", authenticationApp)
subApp.mount("/pay", paymentApp)
