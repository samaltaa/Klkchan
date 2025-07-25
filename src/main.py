from fastapi import FastAPI
from fastapi import Query
from .routers.users import users_router
from .routers.posts import posts_router
from .routers.test import test_router
from .routers.myupload import upload_router
from .routers import models_docs


app = FastAPI(
    title="KLKCHAN API",
    servers=[{"url": "http://127.0.0.1:8000"}]
)

# Registra routers
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(test_router,prefix='/test')
app.include_router(upload_router, prefix='/upload')
app.include_router(models_docs.router, prefix='/docs')

@app.get("/e_page",)
def page(page: int = Query(1, ge=1, le=20)):
   
    return {"page": page, "size": "size"}


@app.get("/")
async def read_root():
    return {"message": "¡API en marcha!"}


@app.get("/test")
async def test_endpoint():
    "prueba exitosa"
    return {"message": "prueba exitosa"}

