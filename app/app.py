from fastapi import FastAPI, HTTPException, Depends, Form, File, UploadFile
from sqlalchemy.orm import Session
from datetime import date
from passlib.context import CryptContext
from typing import Optional

from database import get_db, init_db
from image_utils import validate_and_encode_image
from models import Board as BoardModel, User as UserModel, Post as PostModel, Comment as CommentModel, Reply as ReplyModel
from schemas import (
    BoardCreate, Board,
    UserCreate, UserUpdate, User,
    PostUpdate, Post,
    CommentCreate, Comment,
    ReplyCreate, Reply,
)
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


# Board endpoints

@app.post("/postboard", response_model=Board)
async def post_board(payload: BoardCreate, db: Session = Depends(get_db)):
    board = BoardModel(name=payload.name, description=payload.description)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


@app.get("/getboards", response_model=list[Board])
async def get_boards(db: Session = Depends(get_db)):
    return db.query(BoardModel).all()


# Post endpoints

@app.get("/getposts", response_model=list[Post])
async def get_posts(db: Session = Depends(get_db)):
    return db.query(PostModel).all()


@app.get("/boards/{board_id}/posts", response_model=list[Post])
async def get_posts_by_board(board_id: int, db: Session = Depends(get_db)):
    if not db.query(BoardModel).filter(BoardModel.id == board_id).first():
        raise HTTPException(status_code=404, detail="Board not found")
    return db.query(PostModel).filter(PostModel.board_id == board_id).all()


@app.post("/posts", response_model=Post)
async def create_post(
    title: Optional[str] = Form(None),
    body: str = Form(...),
    board_id: int = Form(...),
    user_id: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
    ):
    
    if not db.query(BoardModel).filter(BoardModel.id == board_id).first():
        raise HTTPException(status_code=404, detail="Board not found")

    # Only validate user if one was provided (logged-in users)
    if user_id and not db.query(UserModel).filter(UserModel.id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    
    image_url = None
    if image and image.filename:
        image_url = await validate_and_encode_image(image)

    post = PostModel(
        title=title,
        body=body,
        board_id=board_id,
        user_id=user_id,  # None = anonymous
        image_url=image_url,
        created_at=date.today(),
        votes=0,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@app.patch("/posts/{post_id}", response_model=Post)
async def update_post(post_id: int, payload: PostUpdate, db: Session = Depends(get_db)):
    post = db.query(PostModel).filter(PostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)
    return post


@app.delete("/posts/{post_id}")
async def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(PostModel).filter(PostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return {"detail": "Post deleted"}


# Comment endpoints

@app.post("/comments", response_model=Comment)
async def create_comment(
    body: str = Form(...),
    post_id: int = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)):

    if not db.query(PostModel).filter(PostModel.id == post_id).first():
        raise HTTPException(status_code=404, detail="Post not found")
    
    image_url = None
    if image and image.filename:
        image_url = await validate_and_encode_image(image)

    comment = CommentModel(
        body=body,
        post_id=post_id,
        created_at=date.today(),
        votes=0,
        user_id=None,  # TODO: replace with authenticated user id
        image_url=image_url
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@app.get("/posts/{post_id}/comments", response_model=list[Comment])
async def get_comments_by_post(post_id: int, db: Session = Depends(get_db)):
    if not db.query(PostModel).filter(PostModel.id == post_id).first():
        raise HTTPException(status_code=404, detail="Post not found")
    return db.query(CommentModel).filter(CommentModel.post_id == post_id).all()


# Reply endpoints

@app.post("/replies", response_model=Reply)
async def create_reply(
    body: str = Form(...),
    comment_id: int = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)):

    if not db.query(CommentModel).filter(CommentModel.id == comment_id).first():
        raise HTTPException(status_code=404, detail="Comment not found")
    
    image_url = None
    if image and image.filename:
        image_url = await validate_and_encode_image(image)

    reply = ReplyModel(
        body=body,
        comment_id=comment_id,
        created_at=date.today(),
        votes=0,
        user_id=None,  # TODO: replace with authenticated user id
        image_url=image_url
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply


@app.get("/comments/{comment_id}/replies", response_model=list[Reply])
async def get_replies_by_comment(comment_id: int, db: Session = Depends(get_db)):
    if not db.query(CommentModel).filter(CommentModel.id == comment_id).first():
        raise HTTPException(status_code=404, detail="Comment not found")
    return db.query(ReplyModel).filter(ReplyModel.comment_id == comment_id).all()


# User endpoints

@app.post("/users", response_model=User)
async def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserModel).filter(UserModel.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = pwd_context.hash(payload.password)
    user = UserModel(
        username=payload.username,
        email=payload.email,
        password=hashed_pw,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users", response_model=list[User])
async def get_users(db: Session = Depends(get_db)):
    return db.query(UserModel).all()


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.patch("/users/{user_id}", response_model=User)
async def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = payload.model_dump(exclude_unset=True)
    if "password" in updates:
        updates["password"] = pwd_context.hash(updates["password"])

    for field, value in updates.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}
