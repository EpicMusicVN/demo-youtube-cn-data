"""Regex patterns and constants for competitor-metrics computation.

Centralised here so the metric modules stay focused on logic. All patterns are
pre-compiled and case-insensitive.
"""
import re

# --- Sponsor / paid-content detection (matched against video descriptions) ---
# ``\bpaid\b`` avoids false positives like "unpaid".
SPONSOR_RE = re.compile(r"sponsor|partner|ad:|code:|promo|affiliate|\bpaid\b|kollab", re.I)

# --- Title-formula detection (matched against video titles) ---
HOWTO_RE = re.compile(r"^\s*how to\b", re.I)
WHY_RE = re.compile(r"^\s*why\b", re.I)
LISTICLE_RE = re.compile(
    r"\b\d+\s+(ways?|steps?|things?|tips?|reasons?|facts?|ideas?)\b|^\s*top\s+\d+", re.I
)
NUMBER_START_RE = re.compile(r"^\s*\d+")

# --- Revenue-stream detection (matched against video descriptions) ---
REVENUE_PATTERNS = {
    "merch": re.compile(r"merch|teespring|redbubble|/shop\b", re.I),
    "course": re.compile(r"course|udemy|teachable|gumroad|skool", re.I),
    "discord": re.compile(r"discord\.gg", re.I),
    "newsletter": re.compile(r"substack|newsletter", re.I),
    "membership": re.compile(r"patreon|/join\b|membership", re.I),
    "affiliate": re.compile(r"amzn\.to|amazon.*associate|affiliate", re.I),
}
