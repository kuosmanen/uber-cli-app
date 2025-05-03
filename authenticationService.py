#This microservice authenticates users at login and sends back a JWT



from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
#pydantic is used for clean input validation, very good
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from pymongo import MongoClient
from fastapi import Header

#https://www.geeksforgeeks.org/authentication-and-authorization-with-fastapi/

app = FastAPI()
context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "132456789" #.env variable will be used here in production
client = MongoClient("mongodb://localhost:27017") #same for this: .env
mongoDB = client["uber-cli-database"]
usersCollection = mongoDB["users"]


#these are so that fastapi takes the token as JSON request body and not as a query parameter
class User(BaseModel):
    username: str
    password: str
    accountType: str
#accountType can be either passenger or driver

#login doesn't require you to specify your account type
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenData(BaseModel):
    token: str


def createToken(data: dict):
    #Copying original so it isn't changed
    copiedData = data.copy()
    #Token expiry 15min
    expire= datetime.now() + timedelta(minutes=15)
    copiedData["exp"] = expire

    #generating token
    token = jwt.encode(copiedData, SECRET_KEY, algorithm="HS256")
    return token




#This can be called by other microservices for them to authenticate different actions
#such as ordering a car ride.
@app.post("/authenticate")
def verifyToken(data: TokenData):
    try:
        decrypted = jwt.decode(data.token, SECRET_KEY, algorithms=["HS256"]) #algorithms is OK, but not algorithm, that does not work here!
        username = decrypted.get("username")
        #if there's no username, then we send an error
        if not username:
            raise HTTPException(status_code=403, detail="Invalid credentials")
        else:
            return {"message": "success"}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token is expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Couldn't validate credentials")


@app.post("/register")
def register(user: User):
    if usersCollection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    hashedPassword = context.hash(user.password)
    usersCollection.insert_one({
        "username": user.username,
        "password": hashedPassword,
        "accountType": user.accountType,
        "status": None
    })
    return {"message": "Registered"}

@app.post("/login")
def login(user: LoginRequest):
    storedUser = usersCollection.find_one({"username": user.username})

    #cheching if the username is in the database and
    #if the password doesn't match the stored password, then we raise exception
    if not storedUser or not context.verify(user.password, storedUser["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
         #otherwise we send back the token
        token = createToken(data={"username": user.username})
        return {"token": token}


@app.get("/userinfo")
def get_user_info(Authorization: str = Header(...)):
    token = Authorization.replace("Bearer ", "")
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = decoded.get("username")
        user = usersCollection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"username": username, "accountType": user["accountType"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token is expired")
    except Exception as e:
        raise HTTPException(status_code=403, detail="Invalid token")
