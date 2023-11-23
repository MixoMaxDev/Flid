import hashlib
import random
import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.requests import Request

import uvicorn

from db_wrapper import DBWrapper



app = FastAPI()
db = DBWrapper()


# Auth functions

#login info: username / email + password
#get user by username / email
#hashed password is stored in db
#check if password matches
#return a temporary token
#token is stored in client cookie and server cache
#for every request, check if token is valid for that user

def hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class TokenCache:
    def __init__(self):
        self.tokens = {} #user_id: [token, creation_time]
    
    def _generate_token(self) -> str:
        token_length = 128
        token = ""
        for _ in range(token_length):
            token += chr(random.randint(0, 255))
        
        #hash token
        token: str = hash(token)
        return token
    
    def add_token(self, user_id: int) -> str:
        token = self._generate_token()
        self.tokens[user_id] = [token, int(time.time())]
        return token
    
    def check_token(self, user_id: int, token: str) -> bool:
        if user_id not in self.tokens:
            return False
        
        server_token, creation_time = self.tokens[user_id]
        if token != server_token:
            return False
        elif int(time.time()) - creation_time > 3600: #token expires after 1 hour
            return False
        
        return True #token is the same and not expired

    def delete_token(self, user_id: int) -> None:
        del self.tokens[user_id]

token_cache = TokenCache()

@app.get("/auth/login")
async def login(user_identification: str, password: str) -> JSONResponse:
    if "@" in user_identification:
        user = db.get_user_by_email(user_identification)
    else:
        user = db.get_user_by_username(user_identification)
    
    if user is None:
        return JSONResponse(status_code=404, content={"error": "User does not exist"})
    
    id, username, hashed_password, email = user
    
    if hash(password) != hashed_password:
        return JSONResponse(status_code=401, content={"error": "Incorrect password"})
    else:
        token_cache.add_token(id)

        return JSONResponse(status_code=200, content={"token": token_cache.tokens[id][0], "user_id": id})

@app.get("/auth/logout")
async def logout(user_id: int, token: str) -> JSONResponse:
    if token_cache.check_token(user_id, token):
        token_cache.delete_token(user_id)
        return JSONResponse(status_code=200, content={"success": "Logged out"})
    else:
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})

@app.get("/auth/register")
async def register(username: str, password: str, email: str) -> JSONResponse:
    if db.add_user(username, hash(password), email):
        return JSONResponse(status_code=200, content={"success": "User created"})
    else:
        return JSONResponse(status_code=400, content={"error": "User already exists"})

@app.get("/auth/check")
async def check(user_id: int, token: str) -> JSONResponse:
    if token_cache.check_token(user_id, token):
        return JSONResponse(status_code=200, content={"success": "Token is valid"})
    else:
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})



# user functions

## public functions (no auth)

@app.get("/user/get")
async def get_user(user_id: int) -> JSONResponse:
    user = db.get_user_by_id(user_id)
    if user is None:
        return JSONResponse(status_code=404, content={"error": "User does not exist"})
    else:
        id, username, password, email = user
        return JSONResponse(status_code=200, content={"id": id, "username": username, "email": email})

@app.get("/user/get/all")
async def get_all_users() -> JSONResponse:
    users = db.get_all_users()
    users = [{"id": user[0], "username": user[1], "email": user[3]} for user in users]
    return JSONResponse(status_code=200, content={"users": users})

@app.get("/user/get/num")
async def get_num_users() -> JSONResponse:
    num_users = db.get_num_users()
    return JSONResponse(status_code=200, content={"num_users": num_users})


## private functions (auth)
@app.get("/user/me")
async def get_me(user_id: int, token: str) -> JSONResponse:
    if not token_cache.check_token(user_id, token):
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})
    
    user = db.get_user_by_id(user_id)
    if user is None:
        return JSONResponse(status_code=404, content={"error": "User does not exist"})
    else:
        id, username, password, email = user
        return JSONResponse(status_code=200, content={"id": id, "username": username, "email": email})

@app.get("/user/me/change/password")
async def change_password(user_id: int, token: str, new_password: str) -> JSONResponse:
    if not token_cache.check_token(user_id, token):
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})
    
    db.change_password(user_id, hash(new_password))
    return JSONResponse(status_code=200, content={"success": "Password changed"})

@app.get("/user/me/change/email")
async def change_email(user_id: int, token: str, new_email: str) -> JSONResponse:
    if not token_cache.check_token(user_id, token):
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})
    
    db.change_email(user_id, new_email)
    return JSONResponse(status_code=200, content={"success": "Email changed"})

@app.get("/user/me/delete")
async def delete_user(user_id: int, token: str) -> JSONResponse:
    if not token_cache.check_token(user_id, token):
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})
    
    db.delete_user(user_id)
    return JSONResponse(status_code=200, content={"success": "User deleted"})

@app.get("/user/me/transactions")
async def get_transactions(user_id: int, token: str) -> JSONResponse:
    if not token_cache.check_token(user_id, token):
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})
    
    owes = db.get_owes_by_sender_id(user_id)
    owed = db.get_owes_by_receiver_id(user_id)
    
    total_sum = 0
    for owe in owes:
        total_sum += owe[2]
    for owe in owed:
        total_sum -= owe[2]
    
    return JSONResponse(status_code=200, content={"owes": owes, "owed": owed, "total_sum": total_sum})

@app.get("/user/me/settle")
async def settle(user_id: int, token: str) -> JSONResponse:
    if not token_cache.check_token(user_id, token):
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})
    
    #get all transactions
    #calculate the sum for each user we owe / owe us
    #if the sum is negative, we owe them
    #if the sum is positive, they owe us
    
    owes = db.get_owes_by_sender_id(user_id)
    owed = db.get_owes_by_receiver_id(user_id)
    
    user_dict = {} #user_id: sum
    
    for owe in owes:
        id, sender_id, receiver_id, amount, description = owe
        if receiver_id not in user_dict:
            user_dict[receiver_id] = 0
        user_dict[receiver_id] += amount
    
    for owe in owed:
        id, sender_id, receiver_id, amount, description = owe
        if sender_id not in user_dict:
            user_dict[sender_id] = 0
        user_dict[sender_id] -= amount
    
    owes = {}
    owed = {}
    
    for user_id, user_sum in user_dict.items():
        if user_sum < 0:
            owes[user_id] = user_sum
        elif user_sum > 0:
            owed[user_id] = user_sum
    
    return JSONResponse(status_code=200, content={"owes": owes, "owed": owed})

# owes functions

## public functions (no auth)

@app.get("/owes/get/num")
async def get_num_owes() -> JSONResponse:
    num_owes = db.get_num_owes()
    return JSONResponse(status_code=200, content={"num_owes": num_owes})

@app.get("/owes/get/sum")
async def get_sum_owes() -> JSONResponse:
    sum_owes = db.get_sum_owes()
    return JSONResponse(status_code=200, content={"sum_owes": sum_owes})


## private functions (auth)

@app.get("/owes/add")
async def add_owe(user_id: int, token: str, receiver_id: int, amount: float, description: str) -> JSONResponse:
    if not token_cache.check_token(user_id, token):
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})
    
    db.add_owe(user_id, receiver_id, amount, description)
    return JSONResponse(status_code=200, content={"success": "Owe added"})

@app.get("/owes/delete")
async def delete_owe(user_id: int, token: str, owe_id: int) -> JSONResponse:
    if not token_cache.check_token(user_id, token):
        return JSONResponse(status_code=401, content={"error": "Token is not valid"})
    
    db.delete_owe(owe_id)
    return JSONResponse(status_code=200, content={"success": "Owe deleted"})


#html
@app.get("/")
async def login_page() -> HTMLResponse:
    return HTMLResponse(content=open("login.html").read(), status_code=200)

@app.get("/home")
async def home_page() -> HTMLResponse:
    return HTMLResponse(content=open("home.html").read(), status_code=200)



uvicorn.run(app, host="127.0.0.1", port=80)