from fastapi import FastAPI
from schemas import *
import json
from pathlib import Path

"""
I have created relative file paths because what works on my 
machine might not work on yours, when creating docker images later
this will be the best practice since it keeps the folder 
structure consistent 
"""

BASE_DIR = Path(__file__).resolve().parent.parent #efining parent directory 

DATA_FILE = Path(__file__).resolve().parent / "data" / "data.json" #pointing to the data file and directory 
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
    with open(DATA_FILE, 'w') as f:
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

#endpoints related to boards
@app.get("/")
async def get_data():
    data = load_data()

    return data

@app.post("/postboard")
async def post_board(payload: BoardCreate):
    data = load_data()

    new_board = {
        "name": payload.name,
        "description": payload.name,
    }
    data["boards"].append(new_board)

    save_data(data)
    return data

@app.get("/getboards")
async def get_boards():
    data = load_data()
    return {"boards": data["boards"]}


