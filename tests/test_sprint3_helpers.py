# tests/test_sprint3_helpers.py
"""
Cobertura para app/utils/helpers.py (43% → objetivo 100%).

Cubre todas las funciones:
  - normalize_text
  - generate_slug
  - sanitize_html
  - paginate_list
  - normalize_email
"""
import re

import pytest

from app_v1.utils.helpers import (
    generate_slug,
    normalize_email,
    normalize_text,
    paginate_list,
    sanitize_html,
)


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_lowercase(self):
        assert normalize_text("HELLO") == "hello"

    def test_strips_accents(self):
        assert normalize_text("José") == "jose"

    def test_strips_complex_accents(self):
        result = normalize_text("ñoño café")
        assert "n" in result
        assert "caf" in result

    def test_collapses_multiple_spaces(self):
        assert normalize_text("foo   bar") == "foo bar"

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_text("  hello  ") == "hello"

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_already_normalized(self):
        assert normalize_text("hello world") == "hello world"

    def test_unicode_decomposition(self):
        # ü → u (loses umlaut)
        result = normalize_text("über")
        assert result == "uber"


# ---------------------------------------------------------------------------
# generate_slug
# ---------------------------------------------------------------------------

class TestGenerateSlug:
    def test_slug_is_lowercase(self):
        slug = generate_slug("Hello World")
        assert slug == slug.lower()

    def test_slug_has_unique_suffix(self):
        s1 = generate_slug("Same Title")
        s2 = generate_slug("Same Title")
        # Los sufijos deben ser distintos (UUID aleatorio de 6 chars)
        assert s1 != s2

    def test_slug_contains_title_words(self):
        slug = generate_slug("Hola Mundo")
        assert "hola" in slug
        assert "mundo" in slug

    def test_slug_format_with_suffix(self):
        slug = generate_slug("My Post")
        # formato: "my-post-xxxxxx" donde x son hex chars
        parts = slug.rsplit("-", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 6
        assert re.match(r"^[0-9a-f]{6}$", parts[1])

    def test_slug_removes_special_chars(self):
        slug = generate_slug("Hello!!! World???")
        assert "!" not in slug
        assert "?" not in slug

    def test_slug_handles_accents(self):
        slug = generate_slug("Café del Sol")
        assert "!" not in slug
        # accents removed, words joined with hyphens
        assert "-" in slug

    def test_slug_strips_leading_trailing_hyphens(self):
        slug = generate_slug("!!!Title!!!")
        # Should not start or end with hyphen before the unique suffix
        base = slug.rsplit("-", 1)[0]
        assert not base.startswith("-")
        assert not base.endswith("-")


# ---------------------------------------------------------------------------
# sanitize_html
# ---------------------------------------------------------------------------

class TestSanitizeHtml:
    def test_removes_simple_tag(self):
        assert sanitize_html("<b>bold</b>") == "bold"

    def test_removes_script_tag(self):
        result = sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "</script>" not in result
        assert "alert('xss')" not in result  # contenido peligroso también eliminado

    def test_removes_tag_with_attributes(self):
        result = sanitize_html('<a href="http://evil.com">click</a>')
        assert "<a" not in result
        assert "click" in result

    def test_removes_self_closing_tag(self):
        result = sanitize_html("text<br/>more")
        assert "<br" not in result
        assert "text" in result
        assert "more" in result

    def test_plain_text_unchanged(self):
        assert sanitize_html("hello world") == "hello world"

    def test_strips_surrounding_whitespace(self):
        assert sanitize_html("  hello  ") == "hello"

    def test_multiple_nested_tags(self):
        result = sanitize_html("<div><p>text</p></div>")
        assert result == "text"

    def test_empty_string(self):
        assert sanitize_html("") == ""

    def test_img_tag_removed(self):
        result = sanitize_html('<img src="x" onerror="alert(1)">')
        assert "<img" not in result

    def test_style_tag_content_stripped(self):
        result = sanitize_html("<style>body { color: red; }</style>")
        assert "<style>" not in result
        assert "color: red" not in result

    def test_iframe_content_stripped(self):
        result = sanitize_html('<iframe src="evil.com">inner text</iframe>')
        assert "<iframe" not in result
        assert "inner text" not in result

    def test_safe_tag_preserves_content(self):
        assert sanitize_html("<b>bold text</b>") == "bold text"

    def test_mixed_dangerous_and_safe(self):
        result = sanitize_html("hello <script>bad()</script> <b>world</b>")
        assert "bad()" not in result
        assert "world" in result
        assert "hello" in result

    def test_multiline_script_stripped(self):
        result = sanitize_html("<script>\nvar x = 1;\nalert(x);\n</script>rest")
        assert "alert" not in result
        assert "rest" in result


# ---------------------------------------------------------------------------
# paginate_list
# ---------------------------------------------------------------------------

class TestPaginateList:
    def test_first_page(self):
        items = list(range(25))
        result = paginate_list(items, page=1, limit=10)
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["total_items"] == 25
        assert result["total_pages"] == 3
        assert result["data"] == list(range(10))

    def test_second_page(self):
        items = list(range(25))
        result = paginate_list(items, page=2, limit=10)
        assert result["data"] == list(range(10, 20))

    def test_last_partial_page(self):
        items = list(range(25))
        result = paginate_list(items, page=3, limit=10)
        assert result["data"] == list(range(20, 25))

    def test_page_beyond_end_returns_empty(self):
        items = list(range(5))
        result = paginate_list(items, page=10, limit=10)
        assert result["data"] == []

    def test_empty_list(self):
        result = paginate_list([], page=1, limit=10)
        assert result["total_items"] == 0
        assert result["total_pages"] == 0
        assert result["data"] == []

    def test_default_page_and_limit(self):
        items = list(range(5))
        result = paginate_list(items)
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["data"] == items

    def test_exact_fit_one_page(self):
        items = list(range(10))
        result = paginate_list(items, page=1, limit=10)
        assert result["total_pages"] == 1
        assert len(result["data"]) == 10

    def test_limit_larger_than_list(self):
        items = [1, 2, 3]
        result = paginate_list(items, page=1, limit=100)
        assert result["total_pages"] == 1
        assert result["data"] == [1, 2, 3]

    def test_total_pages_ceiling(self):
        # 11 items / 10 per page = 2 pages
        items = list(range(11))
        result = paginate_list(items, page=1, limit=10)
        assert result["total_pages"] == 2


# ---------------------------------------------------------------------------
# normalize_email
# ---------------------------------------------------------------------------

class TestNormalizeEmail:
    def test_lowercases(self):
        assert normalize_email("USER@EXAMPLE.COM") == "user@example.com"

    def test_strips_spaces(self):
        assert normalize_email("  user@example.com  ") == "user@example.com"

    def test_mixed_case_and_spaces(self):
        assert normalize_email("  MeLvin@KLKCHAN.Dev  ") == "melvin@klkchan.dev"

    def test_already_lowercase(self):
        assert normalize_email("user@example.com") == "user@example.com"

    def test_empty_string(self):
        assert normalize_email("") == ""
