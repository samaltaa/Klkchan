from fastapi import APIRouter, Depends, HTTPException, Response, status
from app_v2.schemas import CommentCreateV2, CommentResponseV2
from app_v2.security import require_guest_token, create_guest_token, derive_anon_id, GUEST_TOKEN_EXPIRE_SECONDS
from app_v1.services import get_comments_for_post, create_comment, get_post

router = APIRouter(prefix="/comments", tags=["Comments"])

def _fmt(c):
    return CommentResponseV2(id=c["id"], body=c["body"], post_id=c.get("post_id", 0), parent_comment_id=c.get("parent_comment_id"), created_at=str(c.get("created_at", "")), votes=c.get("votes", 0), anon_id=c.get("anon_id"), replies=[_fmt(r) for r in c.get("replies", [])])

@router.get("/{post_id}", response_model=list[CommentResponseV2])
def get_comments_v2(post_id: int):
    if not get_post(post_id):
        raise HTTPException(status_code=404, detail="Post no encontrado")
    return [_fmt(c) for c in get_comments_for_post(post_id)]

@router.post("", response_model=CommentResponseV2, status_code=201)
def create_comment_v2(body: CommentCreateV2, response: Response, guest: dict = Depends(require_guest_token)):
    if not get_post(body.post_id):
        raise HTTPException(status_code=404, detail="Post no encontrado")
    c = create_comment({"body": body.body, "post_id": body.post_id, "parent_comment_id": body.parent_comment_id, "user_id": None, "anon_id": derive_anon_id(guest), "votes": 0})
    response.set_cookie(key="guest_token", value=create_guest_token(), httponly=True, secure=False, samesite="lax", max_age=GUEST_TOKEN_EXPIRE_SECONDS)
    return _fmt(c)
