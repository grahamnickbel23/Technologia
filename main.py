# main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/home")
def home():
    return {"message": "FastAPI is running!"}