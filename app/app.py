from fastapi import FastAPI
from fastapi import Query
from .routers.users import users_router
from .routers.posts import posts_router
from .routers.test import test_router
from .routers.myupload import upload_router
from .routers import models_docs


