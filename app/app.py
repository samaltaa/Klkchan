from fastapi import FastAPI
from schemas import *
import json
import pathlib as path

"""
I have created relative file paths because what works on my 
machine might not work on yours, when creating docker images later
this will be the best practice since it keeps the folder 
structure consistent 
"""

BASE_DIR = path(__file__).resolve().parent.parent #efining parent directory 

DATA_FILE = path(__file__).resolve().parent / "data" / "data.json" #pointing to the data file and directory 
DATA_FILE.parent.mkdir(exist_ok=True)

app = FastAPI()

#function for getting the data from the json file 
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
        return {"boards":[], "users": [], "posts": [], "comments": [], "replies": []}

#function for saving data in the json file
def save_data(data):
    with open(DATA_FILE, 'W') as f:
        json.dump(data, f, indent=2)

@app.on_event("startup")
async def startup():
    # Initialize JSON file if it doesn't exist
    if not DATA_FILE.exists():
        initial_data = {"boards":[], "users": [], "posts": [], "comments": [], "replies": []}
        save_data(initial_data)

@app.get("/health")
async def health():
    return {"status": "ok"}

#endpoints

