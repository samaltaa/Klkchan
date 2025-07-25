from fastapi import APIRouter,File
import shutil
from typing import List

upload_router = APIRouter()


@upload_router.post("/file")
async def upload_file(file: bytes = File(..., description="Sube un archivo")):
    return {"filename": "uploaded_file", "size": len(file)}

from fastapi import UploadFile

@upload_router.post("/uploadfile1")
def upload_file1(file: UploadFile = File(...)):
    return {"filename": file.filename,
             "content_type": file.content_type, 
             "size": len(file.file.read())}


@upload_router.post("/uploadfile2")
def upload_file1(file: UploadFile ):

    with open("img/image.png", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
      

    return {
        "filename": file.filename,
    
    }


@upload_router.post("/uploadfile3")
async def upload_file3(files: List[UploadFile] ):
    filenames = []
    for file in files:
        with open(f"img/{file.filename}", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        filenames.append(file.filename)
    return {"filenames": filenames}