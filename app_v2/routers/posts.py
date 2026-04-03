from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from app_v2.schemas import PostCreateV2, PostResponseV2, PostListResponseV2
from app_v2.security import require_guest_token, create_guest_token, derive_anon_id, GUEST_TOKEN_EXPIRE_SECONDS
from app_v1.services import get_posts, get_post, create_post

router = APIRouter(prefix="/posts", tags=["Posts"])

def _fmt(p):
    return PostResponseV2(id=p["id"], title=p["title"], body=p["body"], board_id=p.get("board_id", 0), created_at=str(p.get("created_at", "")), votes=p.get("votes", 0), image=p.get("image"), anon_id=p.get("anon_id"), comment_count=len(p.get("comments", [])))

@router.get("", response_model=PostListResponseV2)
def list_posts_v2(board_id: Optional[int] = None, limit: int = Query(50, ge=1, le=100), cursor: Optional[int] = None):
    posts = get_posts()
    if board_id is not None:
        posts = [p for p in posts if p.get("board_id") == board_id]
    if cursor:
        posts = [p for p in posts if p["id"] > cursor]
    posts = posts[:limit]
    return PostListResponseV2(items=[_fmt(p) for p in posts], total=len(posts), next_cursor=posts[-1]["id"] if len(posts) == limit else None)

@router.get("/{post_id}", response_model=PostResponseV2)
def get_post_v2(post_id: int):
    p = get_post(post_id)
    if not p:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    return _fmt(p)

@router.post("", response_model=PostResponseV2, status_code=201)
def create_post_v2(body: PostCreateV2, response: Response, guest: dict = Depends(require_guest_token)):
    p = create_post({"title": body.title, "body": body.body, "board_id": body.board_id, "image": body.image, "user_id": None, "anon_id": derive_anon_id(guest), "votes": 0})
    response.set_cookie(key="guest_token", value=create_guest_token(), httponly=True, secure=False, samesite="lax", max_age=GUEST_TOKEN_EXPIRE_SECONDS)
    return _fmt(p)
