"""Unit tests for the YouTube comment fetcher.

Run from the project root:  python3 -m unittest discover tests
Covers only the offline helpers — no network calls.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yt_inspector.comments as comments_mod  # noqa: E402
from yt_inspector.comments import (  # noqa: E402
    _format_comment,
    _friendly_error,
    fetch_comments,
    resolve_video_id,
)


def _make_thread(idx, author=None, text=None, replies=0):
    """Build a commentThreads.list API item for tests."""
    return {
        "snippet": {
            "totalReplyCount": replies,
            "topLevelComment": {
                "snippet": {
                    "authorDisplayName": f"user{idx}" if author is None else author,
                    "textOriginal": f"comment {idx}" if text is None else text,
                    "likeCount": idx,
                    "publishedAt": "2026-05-01T00:00:00Z",
                }
            },
        },
        "replies": {"comments": []},
    }


class TestResolveVideoId(unittest.TestCase):
    def test_watch_url(self):
        self.assertEqual(
            resolve_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_short_youtu_be_url(self):
        self.assertEqual(resolve_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_shorts_url(self):
        self.assertEqual(
            resolve_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_bare_id(self):
        self.assertEqual(resolve_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_watch_url_with_extra_params(self):
        self.assertEqual(
            resolve_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s"),
            "dQw4w9WgXcQ",
        )

    def test_invalid_inputs(self):
        for value in ["", None, "not a url", "https://www.youtube.com/@channel"]:
            self.assertIsNone(resolve_video_id(value))


class TestFormatComment(unittest.TestCase):
    def test_prefers_text_original(self):
        snippet = {
            "authorDisplayName": "Jane",
            "textOriginal": "raw text",
            "textDisplay": "<b>html</b>",
            "likeCount": 12,
            "publishedAt": "2026-05-01T00:00:00Z",
        }
        result = _format_comment(snippet)
        self.assertEqual(result["author"], "Jane")
        self.assertEqual(result["text"], "raw text")
        self.assertEqual(result["likes"], 12)

    def test_missing_fields_default_safely(self):
        result = _format_comment({})
        self.assertIsNone(result["author"])
        self.assertEqual(result["text"], "")
        self.assertEqual(result["likes"], 0)


class TestFriendlyError(unittest.TestCase):
    def test_comments_disabled(self):
        self.assertIn("disabled", _friendly_error("HTTP 403 error: commentsDisabled"))

    def test_video_not_found(self):
        self.assertIn("not found", _friendly_error("HTTP 404 error: videoNotFound").lower())

    def test_quota_exceeded(self):
        self.assertIn("quota", _friendly_error("HTTP 403 error: quotaExceeded").lower())

    def test_unknown_error_fails_closed(self):
        # Unrecognised errors must NOT leak the raw API body to the client.
        raw = 'HTTP 500 error: {"error": {"message": "internal project detail"}}'
        result = _friendly_error(raw)
        self.assertNotIn("project detail", result)
        self.assertIn("Could not fetch comments", result)


class TestFetchCommentsPagination(unittest.TestCase):
    def setUp(self):
        self._real_api_get = comments_mod.api_get
        self._real_load_dotenv = comments_mod.load_dotenv
        comments_mod.load_dotenv = lambda *a, **k: None  # skip .env I/O

    def tearDown(self):
        comments_mod.api_get = self._real_api_get
        comments_mod.load_dotenv = self._real_load_dotenv

    def _stub(self, pages):
        """Make api_get return successive ``pages`` (list of API responses)."""
        calls = []

        def fake(path, params):
            calls.append(params)
            return pages[len(calls) - 1]

        comments_mod.api_get = fake
        return calls

    def test_paginates_across_pages(self):
        pages = [
            {"items": [_make_thread(i) for i in range(100)], "nextPageToken": "p2"},
            {"items": [_make_thread(i) for i in range(100)], "nextPageToken": None},
        ]
        calls = self._stub(pages)
        result = fetch_comments("dQw4w9WgXcQ", max_results=150)
        self.assertEqual(result["count"], 150)
        self.assertEqual(len(calls), 2)
        self.assertTrue(result["truncated"])  # capped at 150

    def test_stops_when_no_next_token(self):
        pages = [{"items": [_make_thread(i) for i in range(30)], "nextPageToken": None}]
        self._stub(pages)
        result = fetch_comments("dQw4w9WgXcQ", max_results=200)
        self.assertEqual(result["count"], 30)
        self.assertFalse(result["truncated"])  # exhausted, not capped

    def test_page_cap_stops_empty_token_loop(self):
        # API keeps returning a token but no items — must not loop forever.
        endless = {"items": [], "nextPageToken": "always"}
        comments_mod.api_get = lambda path, params: endless
        result = fetch_comments("dQw4w9WgXcQ", max_results=100)
        self.assertEqual(result["count"], 0)

    def test_skips_ghost_comments(self):
        pages = [{
            "items": [
                _make_thread(1),
                _make_thread(2, author="", text="   "),  # ghost — skipped
                _make_thread(3),
            ],
            "nextPageToken": None,
        }]
        self._stub(pages)
        result = fetch_comments("dQw4w9WgXcQ", max_results=100)
        self.assertEqual(result["count"], 2)

    def test_invalid_video_id_raises(self):
        with self.assertRaises(RuntimeError):
            fetch_comments("not-a-video", max_results=50)


if __name__ == "__main__":
    unittest.main()
