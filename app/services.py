# app/services.py
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.helpers import normalize_email

# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "data.json"

EMPTY_STRUCTURE: Dict[str, Any] = {
    "users": [],
    "posts": [],
    "boards": [],
    "comments": [],
    "replies": [],
    "votes": [],
    "subscriptions": [],
    "tags": [],
    "attachments": [],
    "moderation": {
        "reports": [],
        "actions": [],
    },
}


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_timestamp(value: Optional[str]) -> str:
    if not value:
        return _now_utc_iso()
    if isinstance(value, str):
        candidate = value.strip()
        try:
            # Support "Z" suffix and date-only strings
            cleaned = candidate.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
        except ValueError:
            try:
                dt = datetime.fromisoformat(candidate + "T00:00:00")
            except ValueError:
                return candidate
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return _now_utc_iso()


def _ensure_data_file() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        DATA_PATH.write_text(
            json.dumps(EMPTY_STRUCTURE, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )


def load_data() -> Dict[str, Any]:
    """Load the JSON document, self-healing the file when corrupted."""
    _ensure_data_file()
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        DATA_PATH.write_text(
            json.dumps(EMPTY_STRUCTURE, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
        return json.loads(json.dumps(EMPTY_STRUCTURE))


def save_data(data: Dict[str, Any]) -> None:
    _ensure_data_file()
    tmp = DATA_PATH.with_name(DATA_PATH.stem + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    tmp.replace(DATA_PATH)


# ---------------------------------------------------------------------------
# User services
# ---------------------------------------------------------------------------
def get_users() -> List[Dict[str, Any]]:
    data = load_data()
    return data["users"]


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    data = load_data()
    return next((u for u in data["users"] if u.get("id") == user_id), None)


get_user_by_id = get_user


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    data = load_data()
    target = normalize_email(email)
    return next(
        (
            u
            for u in data["users"]
            if normalize_email(u.get("email", "")) == target
        ),
        None,
    )


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    data = load_data()
    return next((u for u in data["users"] if u.get("username") == username), None)


def create_user(user: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("username", "email", "password"):
        if not user.get(key):
            raise ValueError(f"Missing field: {key}")

    data = load_data()
    user_copy = deepcopy(user)
    if user_copy.get("email"):
        user_copy["email"] = normalize_email(user_copy["email"])

    user_copy["id"] = _next_id(data["users"])
    user_copy.setdefault("posts", [])
    user_copy.setdefault("roles", ["user"])
    user_copy.setdefault("is_active", True)
    user_copy.setdefault("created_at", _now_utc_iso())

    data["users"].append(user_copy)
    save_data(data)
    return user_copy


def update_user(user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = load_data()
    allowed = {"username", "email", "display_name", "bio"}

    for user in data["users"]:
        if user.get("id") == user_id:
            safe_updates = {
                key: value
                for key, value in updates.items()
                if value is not None and key in allowed
            }

            if "email" in safe_updates:
                new_email = normalize_email(safe_updates["email"])
                if normalize_email(user.get("email", "")) != new_email:
                    if any(
                        normalize_email(other.get("email", "")) == new_email
                        for other in data["users"]
                        if other.get("id") != user_id
                    ):
                        raise ValueError("Email already in use")
                    safe_updates["email"] = new_email

            user.update(safe_updates)
            user["updated_at"] = _now_utc_iso()
            save_data(data)
            return user
    return None


def update_user_roles(user_id: int, roles: List[str]) -> Optional[Dict[str, Any]]:
    """Replace the roles list for a user. Always keeps 'user' as base role."""
    data = load_data()
    safe_roles = list({r for r in roles if r in {"user", "mod", "admin"}} | {"user"})
    for user in data["users"]:
        if user.get("id") == user_id:
            user["roles"] = safe_roles
            user["updated_at"] = _now_utc_iso()
            save_data(data)
            return user
    return None


def update_user_password(user_id: int, new_hashed: str) -> bool:
    data = load_data()
    for user in data["users"]:
        if user.get("id") == user_id:
            user["password"] = new_hashed
            user["updated_at"] = _now_utc_iso()
            save_data(data)
            return True
    return False


def delete_user(user_id: int) -> bool:
    data = load_data()
    initial = len(data["users"])
    data["users"] = [u for u in data["users"] if u.get("id") != user_id]
    if len(data["users"]) != initial:
        # Collect IDs before removing
        post_ids = {p.get("id") for p in data["posts"] if p.get("user_id") == user_id}
        comment_ids = {c.get("id") for c in data["comments"] if c.get("user_id") == user_id}
        data["posts"] = [p for p in data["posts"] if p.get("user_id") != user_id]
        data["comments"] = [c for c in data["comments"] if c.get("user_id") != user_id]
        # Cascade: remove votes by the user and votes on their content
        data["votes"] = [
            v for v in data.get("votes", [])
            if not (
                v.get("user_id") == user_id
                or (v.get("target_type") == "post" and v.get("target_id") in post_ids)
                or (v.get("target_type") == "comment" and v.get("target_id") in comment_ids)
            )
        ]
        save_data(data)
        return True
    return False


# ---------------------------------------------------------------------------
# Board services
# ---------------------------------------------------------------------------
def list_boards() -> List[Dict[str, Any]]:
    data = load_data()
    boards: List[Dict[str, Any]] = []
    posts = data.get("posts", [])
    for entry in data.get("boards", []):
        board = deepcopy(entry)
        board['created_at'] = _normalize_timestamp(board.get('created_at'))
        if board.get('updated_at'):
            board['updated_at'] = _normalize_timestamp(board.get('updated_at'))
        board.setdefault('description', '')
        board["post_count"] = sum(1 for post in posts if post.get('board_id') == board.get('id'))
        boards.append(board)
    boards.sort(key=lambda b: b.get("id", 0))
    return boards


def get_board(board_id: int) -> Optional[Dict[str, Any]]:
    return next((b for b in list_boards() if b.get("id") == board_id), None)


def create_board(board: Dict[str, Any]) -> Dict[str, Any]:
    data = load_data()
    board_copy = deepcopy(board)
    board_copy["id"] = _next_id(data["boards"])
    board_copy.setdefault("name", "")
    board_copy.setdefault("created_at", _now_utc_iso())
    board_copy.setdefault("description", "")
    data.setdefault("boards", []).append(board_copy)
    save_data(data)
    return board_copy


def update_board(board_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = load_data()
    allowed = {"name", "description"}
    for board in data.get("boards", []):
        if board.get("id") == board_id:
            safe_updates = {
                key: value
                for key, value in updates.items()
                if value is not None and key in allowed
            }
            if not safe_updates:
                return board
            board.update(safe_updates)
            board["updated_at"] = _now_utc_iso()
            save_data(data)
            return board
    return None


def delete_board(board_id: int) -> bool:
    data = load_data()
    before = len(data.get("boards", []))
    data["boards"] = [b for b in data.get("boards", []) if b.get("id") != board_id]
    if len(data["boards"]) != before:
        # Cascade posts and comments for this board
        board_post_ids = {p.get("id") for p in data.get("posts", []) if p.get("board_id") == board_id}
        comment_ids = {c.get("id") for c in data.get("comments", []) if c.get("post_id") in board_post_ids}
        data["posts"] = [p for p in data.get("posts", []) if p.get("board_id") != board_id]
        data["comments"] = [c for c in data.get("comments", []) if c.get("post_id") not in board_post_ids]
        # Cascade: remove votes on board posts and their comments
        data["votes"] = [
            v for v in data.get("votes", [])
            if not (
                (v.get("target_type") == "post" and v.get("target_id") in board_post_ids)
                or (v.get("target_type") == "comment" and v.get("target_id") in comment_ids)
            )
        ]
        save_data(data)
        return True
    return False


# ---------------------------------------------------------------------------
# Comment helpers
# ---------------------------------------------------------------------------
def _build_comment(raw: Dict[str, Any]) -> Dict[str, Any]:
    comment = deepcopy(raw)
    comment["created_at"] = _normalize_timestamp(comment.get("created_at"))
    if comment.get("updated_at"):
        comment["updated_at"] = _normalize_timestamp(comment.get("updated_at"))
    comment.setdefault("votes", 0)
    return comment


def get_comments() -> List[Dict[str, Any]]:
    data = load_data()
    comments = [_build_comment(c) for c in data.get("comments", [])]
    comments.sort(key=lambda c: c.get("id", 0))
    return comments


def get_comments_for_post(post_id: int) -> List[Dict[str, Any]]:
    return [c for c in get_comments() if c.get("post_id") == post_id]


def create_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    if not comment.get("user_id"):
        raise ValueError("user_id is required")
    if not comment.get("post_id"):
        raise ValueError("post_id is required")

    data = load_data()
    comment_copy = deepcopy(comment)
    comment_copy["id"] = _next_id(data.get("comments", []))
    comment_copy.setdefault("votes", 0)
    comment_copy["created_at"] = _now_utc_iso()
    data.setdefault("comments", []).append(comment_copy)
    save_data(data)
    return _build_comment(comment_copy)


def delete_comment(comment_id: int) -> bool:
    data = load_data()
    before = len(data.get("comments", []))
    data["comments"] = [c for c in data.get("comments", []) if c.get("id") != comment_id]
    if len(data["comments"]) != before:
        # Cascade: remove votes on this comment
        data["votes"] = [
            v for v in data.get("votes", [])
            if not (v.get("target_type") == "comment" and v.get("target_id") == comment_id)
        ]
        save_data(data)
        return True
    return False


# ---------------------------------------------------------------------------
# Post services
# ---------------------------------------------------------------------------
def _group_comments_by_post(comments: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for comment in comments:
        grouped.setdefault(comment.get("post_id"), []).append(comment)
    for bucket in grouped.values():
        bucket.sort(key=lambda c: c.get("id", 0))
    return grouped


def get_posts() -> List[Dict[str, Any]]:
    data = load_data()
    comments = [_build_comment(c) for c in data.get("comments", [])]
    comments_by_post = _group_comments_by_post(comments)

    posts: List[Dict[str, Any]] = []
    for entry in data.get("posts", []):
        post = deepcopy(entry)
        post["created_at"] = _normalize_timestamp(post.get("created_at"))
        if post.get("updated_at"):
            post["updated_at"] = _normalize_timestamp(post.get("updated_at"))
        post.setdefault("votes", 0)
        post.setdefault("score", post.get("votes", 0))
        post.setdefault("tags", [])
        post.setdefault("attachments", [])
        post_comments = comments_by_post.get(post.get("id"), [])
        post["comment_count"] = len(post_comments)
        post["comments"] = post_comments
        posts.append(post)

    posts.sort(key=lambda p: p.get("id", 0))
    return posts


def get_post(post_id: int) -> Optional[Dict[str, Any]]:
    return next((post for post in get_posts() if post.get("id") == post_id), None)


def create_post(post: Dict[str, Any]) -> Dict[str, Any]:
    if not post.get("user_id"):
        raise ValueError("user_id is required")
    if not post.get("board_id"):
        raise ValueError("board_id is required")

    data = load_data()
    post_copy = deepcopy(post)
    post_copy["id"] = _next_id(data.get("posts", []))
    post_copy["created_at"] = _now_utc_iso()
    post_copy.setdefault("votes", 0)
    post_copy.setdefault("score", 0)
    post_copy.setdefault("attachments", [])
    post_copy.setdefault("tags", [])
    post_copy.pop("comments", None)
    post_copy.pop("comment_count", None)

    data.setdefault("posts", []).append(post_copy)

    for user in data.get("users", []):
        if user.get("id") == post_copy["user_id"]:
            user.setdefault("posts", [])
            if post_copy["id"] not in user["posts"]:
                user["posts"].append(post_copy["id"])
            break

    save_data(data)
    created = get_post(post_copy["id"])
    return created if created else post_copy


def update_post(post_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = load_data()
    allowed = {"title", "body", "board_id", "tags"}
    for post in data.get("posts", []):
        if post.get("id") == post_id:
            safe_updates = {
                key: value
                for key, value in updates.items()
                if value is not None and key in allowed
            }
            if not safe_updates:
                return get_post(post_id)
            post.update(safe_updates)
            post["updated_at"] = _now_utc_iso()
            save_data(data)
            return get_post(post_id)
    return None


def delete_post(post_id: int) -> bool:
    data = load_data()
    before = len(data.get("posts", []))
    data["posts"] = [p for p in data.get("posts", []) if p.get("id") != post_id]
    if len(data.get("posts", [])) != before:
        # Collect comment IDs before removing them
        comment_ids = {c.get("id") for c in data.get("comments", []) if c.get("post_id") == post_id}
        data["comments"] = [c for c in data.get("comments", []) if c.get("post_id") != post_id]
        # Cascade: remove votes on the post and its comments
        data["votes"] = [
            v for v in data.get("votes", [])
            if not (
                (v.get("target_type") == "post" and v.get("target_id") == post_id)
                or (v.get("target_type") == "comment" and v.get("target_id") in comment_ids)
            )
        ]
        for user in data.get("users", []):
            if post_id in user.get("posts", []):
                user["posts"].remove(post_id)
        save_data(data)
        return True
    return False


# ---------------------------------------------------------------------------
# Vote services
# ---------------------------------------------------------------------------


def _normalize_vote_target(target_type: str) -> str:
    value = target_type.lower()
    if value not in {'post', 'comment'}:
        raise ValueError('unsupported target_type')
    return value


def _aggregate_vote_stats(votes: list[dict], target_type: str, target_id: int) -> tuple[int, int, int]:
    filtered = [v for v in votes if v.get('target_type') == target_type and v.get('target_id') == target_id]
    upvotes = sum(1 for v in filtered if v.get('value') == 1)
    downvotes = sum(1 for v in filtered if v.get('value') == -1)
    score = upvotes - downvotes
    return score, upvotes, downvotes


def apply_vote(user_id: int, target_type: str, target_id: int, value: int) -> dict:
    if value not in (-1, 0, 1):
        raise ValueError('value must be -1, 0, or 1')
    normalized_type = _normalize_vote_target(target_type)

    data = load_data()
    entity = _get_entity(data, normalized_type, target_id)
    if entity is None:
        raise ValueError('target_not_found')

    votes = data.setdefault('votes', [])
    existing = next(
        (
            v
            for v in votes
            if v.get('user_id') == user_id
            and v.get('target_type') == normalized_type
            and v.get('target_id') == target_id
        ),
        None,
    )

    if value == 0:
        if existing:
            votes.remove(existing)
    else:
        timestamp = _now_utc_iso()
        if existing:
            existing['value'] = value
            existing['updated_at'] = timestamp
        else:
            votes.append(
                {
                    'id': _next_id(votes),
                    'user_id': user_id,
                    'target_type': normalized_type,
                    'target_id': target_id,
                    'value': value,
                    'created_at': timestamp,
                    'updated_at': timestamp,
                }
            )

    score, upvotes, downvotes = _aggregate_vote_stats(votes, normalized_type, target_id)
    entity['votes'] = score
    entity['score'] = score
    save_data(data)
    return {
        'target_type': normalized_type,
        'target_id': target_id,
        'value': value,
        'score': score,
        'upvotes': upvotes,
        'downvotes': downvotes,
    }


def get_vote_summary(target_type: str, target_id: int, *, user_id: Optional[int] = None) -> Optional[dict]:
    normalized_type = _normalize_vote_target(target_type)
    data = load_data()
    entity = _get_entity(data, normalized_type, target_id)
    if entity is None:
        return None

    votes = data.get('votes', [])
    score, upvotes, downvotes = _aggregate_vote_stats(votes, normalized_type, target_id)
    user_vote = None
    if user_id is not None:
        match = next(
            (
                v
                for v in votes
                if v.get('user_id') == user_id
                and v.get('target_type') == normalized_type
                and v.get('target_id') == target_id
            ),
            None,
        )
        if match:
            user_vote = match.get('value')

    return {
        'target_type': normalized_type,
        'target_id': target_id,
        'score': score,
        'upvotes': upvotes,
        'downvotes': downvotes,
        'user_vote': user_vote,
    }


# ---------------------------------------------------------------------------
# Moderation helpers (reports, actions)
# ---------------------------------------------------------------------------
def _ensure_moderation_root(data: Dict[str, Any]) -> None:
    data.setdefault("moderation", {})
    data["moderation"].setdefault("reports", [])
    data["moderation"].setdefault("actions", [])


def _next_id(sequence: List[Dict[str, Any]], key: str = "id") -> int:
    return max((item.get(key, 0) for item in sequence), default=0) + 1


def _get_entity(data: Dict[str, Any], target_type: str, target_id: int) -> Optional[Dict[str, Any]]:
    kind = target_type.lower()
    if kind == "user":
        return next((u for u in data.get("users", []) if u.get("id") == target_id), None)
    if kind == "post":
        return next((p for p in data.get("posts", []) if p.get("id") == target_id), None)
    if kind == "comment":
        return next((c for c in data.get("comments", []) if c.get("id") == target_id), None)
    return None


def moderation_report_create(
    reporter_id: int,
    target_type: str,
    target_id: int,
    reason: str = "",
) -> Dict[str, Any]:
    data = load_data()
    _ensure_moderation_root(data)

    report = {
        "id": _next_id(data["moderation"]["reports"]),
        "created_at": _now_utc_iso(),
        "reporter_id": reporter_id,
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason or "",
        "status": "pending",
        "invalid_target": _get_entity(data, target_type, target_id) is None,
    }
    data["moderation"]["reports"].append(report)
    save_data(data)
    return report


def moderation_queue_list(status: Optional[str] = "pending") -> List[Dict[str, Any]]:
    data = load_data()
    _ensure_moderation_root(data)
    reports = data["moderation"]["reports"]
    if status:
        return [r for r in reports if r.get("status") == status]
    return reports


def moderation_action_apply(
    moderator_id: int,
    target_type: str,
    target_id: int,
    action: str,
    reason: str = "",
    report_id: Optional[int] = None,
) -> Dict[str, Any]:
    act = action.lower()
    data = load_data()
    _ensure_moderation_root(data)

    entity = _get_entity(data, target_type, target_id)

    valid_actions = {"remove", "approve", "lock", "sticky", "ban_user", "shadowban"}
    if act not in valid_actions:
        result: Dict[str, Any] = {"applied": False, "error": "unknown_action"}
    elif act != "approve" and entity is None:
        result = {"applied": False, "error": "target_not_found"}
    else:
        if act == "remove":
            entity["removed"] = True
            if target_type == "post":
                entity["locked"] = True
        elif act == "approve":
            pass
        elif act == "lock":
            if target_type != "post":
                result = {"applied": False, "error": "lock_only_for_posts"}
                _log_moderation_action(data, moderator_id, target_type, target_id, act, reason, False, result["error"], report_id)
                save_data(data)
                return result
            entity["locked"] = True
        elif act == "sticky":
            if target_type != "post":
                result = {"applied": False, "error": "sticky_only_for_posts"}
                _log_moderation_action(data, moderator_id, target_type, target_id, act, reason, False, result["error"], report_id)
                save_data(data)
                return result
            entity["sticky"] = True
        elif act == "ban_user":
            if target_type != "user":
                result = {"applied": False, "error": "ban_only_for_users"}
                _log_moderation_action(data, moderator_id, target_type, target_id, act, reason, False, result["error"], report_id)
                save_data(data)
                return result
            entity["banned"] = True
        elif act == "shadowban":
            if target_type != "user":
                result = {"applied": False, "error": "shadowban_only_for_users"}
                _log_moderation_action(data, moderator_id, target_type, target_id, act, reason, False, result["error"], report_id)
                save_data(data)
                return result
            entity["shadowbanned"] = True

        result = {"applied": True}

        if report_id is not None:
            for report in data["moderation"]["reports"]:
                if report.get("id") == report_id:
                    report["status"] = "closed"
                    report["closed_at"] = _now_utc_iso()
                    report["closed_by"] = moderator_id
                    report["resolution"] = act
                    break

    _log_moderation_action(
        data,
        moderator_id,
        target_type,
        target_id,
        act,
        reason,
        result.get("applied", False),
        result.get("error"),
        report_id,
    )
    save_data(data)
    return result


def _log_moderation_action(
    data: Dict[str, Any],
    moderator_id: int,
    target_type: str,
    target_id: int,
    action: str,
    reason: str,
    applied: bool,
    error: Optional[str],
    report_id: Optional[int],
) -> None:
    entry = {
        "id": _next_id(data["moderation"]["actions"]),
        "ts": _now_utc_iso(),
        "moderator_id": moderator_id,
        "target_type": target_type,
        "target_id": target_id,
        "action": action,
        "reason": reason or "",
        "applied": applied,
        "error": error,
        "report_id": report_id,
    }
    data["moderation"]["actions"].append(entry)
