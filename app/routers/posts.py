from fastapi import APIRouter, HTTPException, status
from app.schemas.schemas import Post, PostCreate, PostUpdate
from app.services import get_posts, get_post, create_post, update_post, delete_post
from app.utils.banned_words import has_banned_words

if has_banned_words(payload.title, lang_hint="es") or has_banned_words(payload.content, lang_hint="es"):
    raise HTTPException(status_code=400, detail="Contenido con palabras no permitidas.")

posts_router = APIRouter(prefix="/posts", tags=["Posts"])

@posts_router.get("/", response_model=list[Post])
def read_posts():
    return get_posts()

@posts_router.post("/", response_model=Post, status_code=status.HTTP_201_CREATED)
def create_new_post(post: PostCreate):
    new_post = create_post(post.dict())
    return new_post

@posts_router.get("/{post_id}", response_model=Post)
def read_post(post_id: int):
    post = get_post(post_id)
    if not post:
        raise HTTPException(404, "Post no encontrado")
    return post

@posts_router.put("/{post_id}", response_model=Post)
def update_existing_post(post_id: int, post: PostUpdate):
    updated = update_post(post_id, post.dict())
    if not updated:
        raise HTTPException(404, "Post no encontrado")
    return updated

@posts_router.delete("/{post_id}")
def delete_existing_post(post_id: int):
    success = delete_post(post_id)
    if not success:
        raise HTTPException(404, "Post no encontrado")
    return {"message": "Post eliminado"}


