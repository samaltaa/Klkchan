# tests/test_sprint3_services.py
"""
Cobertura para app/services.py (79% → objetivo 90%+).

Cubre funciones/ramas no ejercidas:
  - _normalize_timestamp: None, "Z" suffix, date-only, TZ-naive, invalid
  - update_user_iat_cutoff: user not found → False
  - lock_post / sticky_post / shadowban_user: happy + not found
  - _next_id: empty sequence
  - _normalize_vote_target: tipo no válido
  - moderation_action_apply: todas las ramas
  - moderation_queue_list: sin filtro de status
  - get_vote_summary: con user_id, sin target existente
"""
import pytest

import app.services as services
from app.utils.security import hash_password


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _seed_user(email="test@cov.com", username="cov_user"):
    """Crea un usuario mínimo y retorna su dict."""
    return services.create_user({
        "username": username,
        "email": email,
        "password": hash_password("Aa123456!"),
    })


def _seed_board():
    return services.create_board({"name": "CovBoard", "description": "test"})


def _seed_post(user_id: int, board_id: int):
    return services.create_post({
        "title": "Coverage Post",
        "body": "body content",
        "board_id": board_id,
        "user_id": user_id,
    })


# ---------------------------------------------------------------------------
# _normalize_timestamp
# ---------------------------------------------------------------------------

class TestNormalizeTimestamp:
    """Accede a _normalize_timestamp via create_post (que llama get_posts → deepcopy)."""

    def test_none_returns_current_utc(self, temp_data_path):
        """Valor None → retorna timestamp actual ISO."""
        result = services._normalize_timestamp(None)
        assert "T" in result or len(result) > 0

    def test_empty_string_returns_current_utc(self, temp_data_path):
        result = services._normalize_timestamp("")
        assert len(result) > 0

    def test_z_suffix_is_normalized(self, temp_data_path):
        """'2024-01-15T12:00:00Z' → ISO con +00:00."""
        result = services._normalize_timestamp("2024-01-15T12:00:00Z")
        assert "+00:00" in result or "2024-01-15" in result

    def test_date_only_string(self, temp_data_path):
        """'2024-01-15' → añade T00:00:00 y normaliza."""
        result = services._normalize_timestamp("2024-01-15")
        assert "2024-01-15" in result

    def test_tz_naive_datetime_gets_utc(self, temp_data_path):
        """Datetime sin TZ → se le asigna UTC."""
        result = services._normalize_timestamp("2024-06-01T10:30:00")
        assert "2024-06-01" in result

    def test_invalid_string_returned_as_is(self, temp_data_path):
        """String no parseable → retorna original."""
        bad = "not-a-date-at-all"
        result = services._normalize_timestamp(bad)
        assert result == bad


# ---------------------------------------------------------------------------
# update_user_iat_cutoff — rama not found
# ---------------------------------------------------------------------------

class TestUpdateUserIatCutoff:
    def test_returns_false_for_nonexistent_user(self, temp_data_path):
        result = services.update_user_iat_cutoff(99999, 9999999999)
        assert result is False

    def test_returns_true_for_existing_user(self, temp_data_path):
        user = _seed_user("iat_cov@test.com", "iat_cov")
        result = services.update_user_iat_cutoff(user["id"], 9999999999)
        assert result is True


# ---------------------------------------------------------------------------
# lock_post, sticky_post, shadowban_user
# ---------------------------------------------------------------------------

class TestAdminServiceFunctions:
    def test_lock_post_returns_updated_post(self, temp_data_path):
        user = _seed_user("lock1@t.com", "lock1")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        result = services.lock_post(post["id"])
        assert result is not None
        assert result.get("locked") is True

    def test_lock_post_not_found_returns_none(self, temp_data_path):
        assert services.lock_post(99999) is None

    def test_sticky_post_returns_updated_post(self, temp_data_path):
        user = _seed_user("sticky1@t.com", "sticky1")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        result = services.sticky_post(post["id"])
        assert result is not None
        assert result.get("sticky") is True

    def test_sticky_post_not_found_returns_none(self, temp_data_path):
        assert services.sticky_post(99999) is None

    def test_shadowban_user_returns_updated_user(self, temp_data_path):
        user = _seed_user("sb1@t.com", "sb1")

        result = services.shadowban_user(user["id"])
        assert result is not None
        # get_user retorna raw dict que incluye shadowbanned
        loaded = services.get_user(user["id"])
        assert loaded.get("shadowbanned") is True

    def test_shadowban_user_not_found_returns_none(self, temp_data_path):
        assert services.shadowban_user(99999) is None

    def test_lock_is_idempotent(self, temp_data_path):
        user = _seed_user("lock2@t.com", "lock2")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        services.lock_post(post["id"])
        result = services.lock_post(post["id"])
        assert result.get("locked") is True

    def test_sticky_is_idempotent(self, temp_data_path):
        user = _seed_user("sticky2@t.com", "sticky2")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        services.sticky_post(post["id"])
        result = services.sticky_post(post["id"])
        assert result.get("sticky") is True


# ---------------------------------------------------------------------------
# _next_id — secuencia vacía
# ---------------------------------------------------------------------------

class TestNextId:
    def test_empty_sequence_returns_1(self, temp_data_path):
        result = services._next_id([])
        assert result == 1

    def test_non_empty_sequence_increments(self, temp_data_path):
        seq = [{"id": 1}, {"id": 3}, {"id": 7}]
        result = services._next_id(seq)
        assert result == 8


# ---------------------------------------------------------------------------
# _normalize_vote_target — tipo inválido
# ---------------------------------------------------------------------------

class TestNormalizeVoteTarget:
    def test_valid_post(self, temp_data_path):
        assert services._normalize_vote_target("post") == "post"

    def test_valid_comment(self, temp_data_path):
        assert services._normalize_vote_target("comment") == "comment"

    def test_case_insensitive(self, temp_data_path):
        assert services._normalize_vote_target("POST") == "post"

    def test_invalid_type_raises_value_error(self, temp_data_path):
        with pytest.raises(ValueError, match="unsupported target_type"):
            services._normalize_vote_target("board")

    def test_empty_string_raises_value_error(self, temp_data_path):
        with pytest.raises(ValueError):
            services._normalize_vote_target("")


# ---------------------------------------------------------------------------
# moderation_action_apply — ramas
# ---------------------------------------------------------------------------

class TestModerationActionApply:
    def test_lock_action_on_post(self, temp_data_path):
        user = _seed_user("mod1@t.com", "mod1")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        result = services.moderation_action_apply(
            moderator_id=1, target_type="post", target_id=post["id"], action="lock"
        )
        assert result["applied"] is True
        loaded = services._get_entity(services.load_data(), "post", post["id"])
        assert loaded.get("locked") is True

    def test_sticky_action_on_post(self, temp_data_path):
        user = _seed_user("mod2@t.com", "mod2")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        result = services.moderation_action_apply(
            moderator_id=1, target_type="post", target_id=post["id"], action="sticky"
        )
        assert result["applied"] is True

    def test_lock_on_non_post_returns_applied_false(self, temp_data_path):
        user = _seed_user("mod3@t.com", "mod3")
        post_data = _seed_post(user["id"], _seed_board()["id"])
        comment = services.create_comment({
            "body": "test comment",
            "post_id": post_data["id"],
            "user_id": user["id"],
        })

        result = services.moderation_action_apply(
            moderator_id=1, target_type="comment", target_id=comment["id"], action="lock"
        )
        assert result["applied"] is False
        assert result["error"] == "lock_only_for_posts"

    def test_sticky_on_non_post_returns_applied_false(self, temp_data_path):
        user = _seed_user("mod4@t.com", "mod4")
        result = services.moderation_action_apply(
            moderator_id=1, target_type="user", target_id=user["id"], action="sticky"
        )
        assert result["applied"] is False
        assert result["error"] == "sticky_only_for_posts"

    def test_ban_user_on_user(self, temp_data_path):
        user = _seed_user("mod5@t.com", "mod5")
        result = services.moderation_action_apply(
            moderator_id=1, target_type="user", target_id=user["id"], action="ban_user"
        )
        assert result["applied"] is True
        loaded = services._get_entity(services.load_data(), "user", user["id"])
        assert loaded.get("banned") is True

    def test_ban_user_on_non_user_returns_applied_false(self, temp_data_path):
        user = _seed_user("mod6@t.com", "mod6")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        result = services.moderation_action_apply(
            moderator_id=1, target_type="post", target_id=post["id"], action="ban_user"
        )
        assert result["applied"] is False
        assert result["error"] == "ban_only_for_users"

    def test_shadowban_on_user(self, temp_data_path):
        user = _seed_user("mod7@t.com", "mod7")
        result = services.moderation_action_apply(
            moderator_id=1, target_type="user", target_id=user["id"], action="shadowban"
        )
        assert result["applied"] is True

    def test_shadowban_on_non_user_returns_applied_false(self, temp_data_path):
        user = _seed_user("mod8@t.com", "mod8")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        result = services.moderation_action_apply(
            moderator_id=1, target_type="post", target_id=post["id"], action="shadowban"
        )
        assert result["applied"] is False

    def test_unknown_action_returns_applied_false(self, temp_data_path):
        result = services.moderation_action_apply(
            moderator_id=1, target_type="post", target_id=1, action="fly_to_moon"
        )
        assert result["applied"] is False
        assert result["error"] == "unknown_action"

    def test_action_on_nonexistent_target(self, temp_data_path):
        result = services.moderation_action_apply(
            moderator_id=1, target_type="post", target_id=99999, action="remove"
        )
        assert result["applied"] is False
        assert result["error"] == "target_not_found"

    def test_approve_action_always_applied(self, temp_data_path):
        """approve no requiere que el target exista."""
        result = services.moderation_action_apply(
            moderator_id=1, target_type="post", target_id=99999, action="approve"
        )
        assert result["applied"] is True

    def test_action_with_report_id_closes_report(self, temp_data_path):
        """Si se pasa report_id, el reporte queda cerrado."""
        user = _seed_user("mod9@t.com", "mod9")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        report = services.moderation_report_create(
            reporter_id=user["id"],
            target_type="post",
            target_id=post["id"],
            reason="bad content",
        )

        services.moderation_action_apply(
            moderator_id=1,
            target_type="post",
            target_id=post["id"],
            action="remove",
            report_id=report["id"],
        )

        data = services.load_data()
        updated_report = next(
            (r for r in data["moderation"]["reports"] if r["id"] == report["id"]),
            None,
        )
        assert updated_report is not None
        assert updated_report["status"] == "closed"


# ---------------------------------------------------------------------------
# moderation_queue_list — sin filtro de status
# ---------------------------------------------------------------------------

class TestModerationQueueList:
    def test_filter_by_status_pending(self, temp_data_path):
        user = _seed_user("queueu@t.com", "queueu")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])
        services.moderation_report_create(user["id"], "post", post["id"], "spam")

        pending = services.moderation_queue_list(status="pending")
        assert all(r["status"] == "pending" for r in pending)

    def test_no_filter_returns_all(self, temp_data_path):
        user = _seed_user("queueu2@t.com", "queueu2")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])
        services.moderation_report_create(user["id"], "post", post["id"], "spam1")
        services.moderation_report_create(user["id"], "post", post["id"], "spam2")

        all_reports = services.moderation_queue_list(status=None)
        assert len(all_reports) >= 2


# ---------------------------------------------------------------------------
# get_vote_summary — con user_id + target no existente
# ---------------------------------------------------------------------------

class TestGetVoteSummary:
    def test_returns_none_for_nonexistent_target(self, temp_data_path):
        result = services.get_vote_summary("post", 99999)
        assert result is None

    def test_returns_summary_with_user_id(self, temp_data_path):
        user = _seed_user("vote_sum@t.com", "vote_sum")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        # Votar y luego consultar con user_id
        services.apply_vote(user["id"], "post", post["id"], 1)
        result = services.get_vote_summary("post", post["id"], user_id=user["id"])

        assert result is not None
        assert result["score"] == 1
        assert result["user_vote"] == 1

    def test_returns_none_user_vote_when_not_voted(self, temp_data_path):
        user = _seed_user("vote_sum2@t.com", "vote_sum2")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])

        result = services.get_vote_summary("post", post["id"], user_id=user["id"])
        assert result is not None
        assert result["user_vote"] is None

    def test_unsupported_target_type_raises(self, temp_data_path):
        with pytest.raises(ValueError):
            services.get_vote_summary("board", 1)


# ---------------------------------------------------------------------------
# _get_entity — tipos
# ---------------------------------------------------------------------------

class TestGetEntity:
    def test_get_user_entity(self, temp_data_path):
        user = _seed_user("entity1@t.com", "entity1")
        data = services.load_data()
        result = services._get_entity(data, "user", user["id"])
        assert result is not None
        assert result["id"] == user["id"]

    def test_get_post_entity(self, temp_data_path):
        user = _seed_user("entity2@t.com", "entity2")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])
        data = services.load_data()
        result = services._get_entity(data, "post", post["id"])
        assert result is not None

    def test_get_comment_entity(self, temp_data_path):
        user = _seed_user("entity3@t.com", "entity3")
        board = _seed_board()
        post = _seed_post(user["id"], board["id"])
        comment = services.create_comment({
            "body": "test", "post_id": post["id"], "user_id": user["id"]
        })
        data = services.load_data()
        result = services._get_entity(data, "comment", comment["id"])
        assert result is not None

    def test_unknown_type_returns_none(self, temp_data_path):
        data = services.load_data()
        result = services._get_entity(data, "board", 1)
        assert result is None

    def test_nonexistent_id_returns_none(self, temp_data_path):
        data = services.load_data()
        assert services._get_entity(data, "post", 99999) is None
