"""Unit tests for the competitor-metrics engine.

Run from the project root:  python3 -m unittest discover tests
Uses stdlib ``unittest`` only — no extra dependency, runs offline.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_inspector.competitor_metrics import compute_competitor_metrics  # noqa: E402


def make_video(**overrides):
    """Build a formatted-video dict (shape from video_utils.format_video)."""
    base = {
        "title": "Untitled",
        "url": "https://youtu.be/x",
        "publishedAt": "2026-05-01T08:00:00Z",
        "views": "1000",
        "likes": "50",
        "comments": "5",
        "durationSeconds": 600,
        "tags": [],
        "description": "",
        "hasPaidProductPlacement": False,
    }
    base.update(overrides)
    return base


class TestEdgeCases(unittest.TestCase):
    def test_empty_videos(self):
        m = compute_competitor_metrics({}, [])
        self.assertEqual(m["videoSampleSize"], 0)
        self.assertEqual(m["profile"]["ageText"], "-")
        self.assertEqual(m["cadence"]["consistencyLabel"], "-")
        self.assertEqual(m["format"]["shortsRatio"], 0.0)
        self.assertEqual(m["engagement"]["avgViewsLatest"], 0)
        self.assertEqual(m["seo"]["topTags"], [])

    def test_none_inputs(self):
        m = compute_competitor_metrics(None, None)  # must not raise
        self.assertEqual(m["videoSampleSize"], 0)

    def test_zero_division(self):
        channel = {"statistics": {"viewCount": "0", "subscriberCount": "0", "videoCount": "0"}}
        videos = [make_video(views="0", likes="0", comments="0")]
        m = compute_competitor_metrics(channel, videos)
        self.assertEqual(m["profile"]["avgViewsLifetime"], 0)
        self.assertEqual(m["profile"]["viewsToSubRatio"], 0.0)
        self.assertEqual(m["engagement"]["likeRate"], 0.0)

    def test_missing_and_null_fields(self):
        videos = [
            {"title": None, "views": None, "publishedAt": None},  # everything missing
            make_video(description=None, tags=None),
        ]
        m = compute_competitor_metrics({}, videos)  # must not raise
        self.assertEqual(m["videoSampleSize"], 2)
        self.assertEqual(m["seo"]["avgTagsPerVideo"], 0.0)

    def test_string_typed_counts(self):
        videos = [make_video(views="2000", likes="100", comments="10")]
        m = compute_competitor_metrics({}, videos)
        self.assertEqual(m["engagement"]["avgViewsLatest"], 2000)
        self.assertEqual(m["engagement"]["likeRate"], 5.0)


class TestProfile(unittest.TestCase):
    def test_lifetime_and_ratio(self):
        channel = {
            "publishedAt": "2024-05-01T00:00:00Z",
            "statistics": {"viewCount": "1000000", "subscriberCount": "10000", "videoCount": "100"},
        }
        videos = [make_video(views="2000") for _ in range(10)]
        profile = compute_competitor_metrics(channel, videos)["profile"]
        self.assertEqual(profile["avgViewsLifetime"], 10000)  # 1_000_000 / 100
        self.assertEqual(profile["viewsToSubRatio"], 20.0)    # 2000 / 10000 * 100
        self.assertEqual(profile["viewsToSubLabel"], "engaged")
        self.assertIn("y", profile["ageText"])


class TestCadence(unittest.TestCase):
    def test_even_cadence(self):
        # 10 uploads exactly one day apart at 08:00 UTC -> 17:00 KST.
        videos = [make_video(publishedAt=f"2026-05-{d:02d}T08:00:00Z") for d in range(1, 11)]
        cadence = compute_competitor_metrics({}, videos)["cadence"]
        self.assertEqual(cadence["avgDaysBetween"], 1.0)
        self.assertEqual(cadence["consistencyLabel"], "Rất đều")
        self.assertEqual(cadence["peakHoursKST"][0]["hour"], 17)
        self.assertIn(cadence["peakDayLabel"], ["T2", "T3", "T4", "T5", "T6", "T7", "CN"])

    def test_irregular_cadence(self):
        # Alternating 1-day / 19-day gaps -> high stddev -> "Không đều".
        dates = ["2026-05-01", "2026-05-02", "2026-05-21", "2026-05-22"]
        videos = [make_video(publishedAt=f"{d}T00:00:00Z") for d in dates]
        cadence = compute_competitor_metrics({}, videos)["cadence"]
        self.assertEqual(cadence["consistencyLabel"], "Không đều")


class TestFormat(unittest.TestCase):
    def test_shorts_and_formulas(self):
        videos = (
            [make_video(durationSeconds=30, title="How to win at life") for _ in range(4)]
            + [make_video(durationSeconds=600, title="5 ways to grow fast") for _ in range(6)]
        )
        fmt = compute_competitor_metrics({}, videos)["format"]
        self.assertEqual(fmt["shortsRatio"], 40.0)
        self.assertEqual(fmt["shortsCount"], 4)
        self.assertEqual(fmt["longformCount"], 6)
        self.assertEqual(fmt["avgDurationMin"], 10.0)
        self.assertEqual(fmt["titleFormulas"]["howTo"], 4)
        self.assertEqual(fmt["titleFormulas"]["listicle"], 6)
        self.assertEqual(fmt["titleFormulas"]["numberStart"], 6)


class TestEngagement(unittest.TestCase):
    def test_breakout_and_underperform(self):
        videos = [make_video(views="100") for _ in range(9)] + [make_video(views="10000")]
        eng = compute_competitor_metrics({}, videos)["engagement"]
        self.assertEqual(eng["avgViewsLatest"], 1090)  # (9*100 + 10000) / 10
        self.assertEqual(len(eng["breakoutVideos"]), 1)
        self.assertEqual(eng["breakoutVideos"][0]["views"], 10000)
        self.assertEqual(len(eng["underperformVideos"]), 3)  # capped at 3


class TestSeo(unittest.TestCase):
    def test_tags_sponsor_revenue(self):
        videos = [
            make_video(tags=["kpop", "music"], description="Use code SAVE10 — sponsored by X"),
            make_video(tags=["kpop"], description="Join our discord.gg/abc community"),
            make_video(tags=["kpop", "dance"], description="plain description"),
        ]
        seo = compute_competitor_metrics({}, videos)["seo"]
        self.assertEqual(seo["topTags"][0]["tag"], "kpop")
        self.assertEqual(seo["topTags"][0]["count"], 3)
        self.assertGreater(seo["sponsorRate"], 0)
        self.assertTrue(seo["hasSponsor"])
        self.assertTrue(seo["revenueStreams"]["discord"])
        self.assertFalse(seo["revenueStreams"]["course"])

    def test_paid_placement_count(self):
        videos = [make_video(hasPaidProductPlacement=True), make_video()]
        seo = compute_competitor_metrics({}, videos)["seo"]
        self.assertEqual(seo["paidPlacementCount"], 1)


if __name__ == "__main__":
    unittest.main()
