from fastapi import APIRouter, HTTPException, status
from ..schemas import Post, PostCreate, PostUpdate

posts: list[Post] = []

posts_router = APIRouter(prefix="/posts", tags=["posts"])

@posts_router.get("/", response_model=list[Post])
def read_posts():
    return posts

@posts_router.post("/", response_model=Post, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate):
    new_id = len(posts) + 1
    new_post = Post(id=new_id, **post.dict())
    posts.append(new_post)
    return new_post

@posts_router.get("/{post_id}", response_model=Post)
def get_post(post_id: int):
    for p in posts:
        if p.id == post_id:
            return p
    raise HTTPException(404, "Post no encontrado")

@posts_router.put("/{post_id}", response_model=Post)
def update_post(post_id: int, post: PostUpdate):
    for idx, p in enumerate(posts):
        if p.id == post_id:
            updated = Post(id=post_id, **post.dict())
            posts[idx] = updated
            return updated
    raise HTTPException(404, "Post no encontrado")

@posts_router.delete("/{post_id}", response_model=Post)
def delete_post(post_id: int):
    for idx, p in enumerate(posts):
        if p.id == post_id:
            return posts.pop(idx)
    raise HTTPException(404, "Post no encontrado")
