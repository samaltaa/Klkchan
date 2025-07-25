
from fastapi import APIRouter, HTTPException, Body , status
from ..models import Test
from enum import Enum


test_list = [

{
    "test": "test",
    "status": "Done"
}

]


test_router = APIRouter(
    prefix="/test",
    tags=["test"],
    responses={201: {"description": "test creado exitosamente"}},
)

class statusType(str, Enum):
    Done="Done"
    Pending="Pending"
    
    

@test_router.get("/", status_code=status.HTTP_200_OK)
def get_test(test: str):
    test_list.append(test)
    return {"test": test_list}

@test_router.post("/", status_code=status.HTTP_201_CREATED)
def add_test(test: Test):
    test_list.append(test)

       
  
    return {"test": test_list}

@test_router.put("/index", status_code=status.HTTP_200_OK)
def update(index:int , test:Test):
    test_list[index]={
    
    }

    return {"test": test_list}


@test_router.delete("/", status_code=status.HTTP_200_OK)
def delete(index: int):
    if len(test_list) <= index or index < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Test ID no existe mas")
    del test_list[index]
    return {"test": test_list}


 