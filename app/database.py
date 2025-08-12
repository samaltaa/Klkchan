from fastapi import FastAPI, HTTPException, Body 
from databases import Database 
from sqlalchemy import * 
#from models import [models here]
#schemas import [schemas]
from datetime import date 
import os 
#from helpers import [helper functions]

DATABASE_URL = ""
database = Database(DATABASE_URL)

app = FastAPI()

@app.on_event("startup")
async def startup():
    engine = create_engine(DATABASE_URL)
    #metadata.create_all(engine) uncomment when metadata is imported from models
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/health")
async def health():
    await database.execute("SELECT 1")
    return {"status": "ok"}
