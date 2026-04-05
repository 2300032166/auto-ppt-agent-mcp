# agent/prompt.py
# ─────────────────────────────────────────────────────────────────────────────
# Role: PLANNER support only.
# The LLM (flan-t5) is strictly a Planner — it generates slide titles and nothing else.
# All slide content comes from MCP search_web tool results (see search_extractor.py).
#
# Also exposes:
#   extract_theme_and_topic(raw) → (theme_name, clean_topic)
#   for the updated agent pipeline.
# ─────────────────────────────────────────────────────────────────────────────

import re
import sys
import os

# Make themes importable when this module is loaded standalone
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from themes.theme_config import parse_theme_from_input, DEFAULT_THEME_NAME

# ── Slide title planning prompt ───────────────────────────────────────────────
# Tuned for flan-t5-base instruction-following behaviour.
TITLE_PLANNING_PROMPT = (
    "List exactly {n} slide titles for a PowerPoint presentation on: {topic}. "
    "Follow this structure: Introduction, Background, Key Concepts, "
    "Applications and Benefits, Future Outlook and Conclusion. "
    "Return only the titles separated by commas, nothing else."
)

# ── Topic extraction ──────────────────────────────────────────────────────────
# Strips instructional prefixes from user input so the actual subject is clean:
#   "Create a 5-slide presentation on Quantum Computing" → "Quantum Computing"

_TOPIC_STRIP_PATTERNS = [
    r"create\s+a?\s*\d*[\s-]*slides?\s+presentation\s+on\s+(.+)",
    r"(?:make|build|generate|create)\s+a\s+presentation\s+(?:about|on)\s+(.+)",
    r"presentation\s+(?:about|on)\s+(.+)",
    r"slides?\s+(?:about|on)\s+(.+)",
    r"topic[:\s]+(.+)",
]

# ── Theme noise words to strip from topic string ──────────────────────────────
# e.g. "AI with dark theme" → "AI"
_THEME_NOISE_RE = re.compile(
    r"\b(?:with\s+)?(?:dark|academic|creative|minimal|professional|colorful|colourful)"
    r"(?:\s+(?:theme|style|mode|look))?\b",
    re.IGNORECASE,
)
_AUDIENCE_NOISE_RE = re.compile(
    r"\b(?:for\s+)?(?:school|business|technical|students?|professionals?)\b"
    r"(?:\s+(?:audience|style))?",
    re.IGNORECASE,
)


def extract_topic(raw: str) -> str:
    """
    Extract the real subject from an instruction-style user input.

    Also strips theme/audience noise so it doesn't pollute the actual topic.

    Examples
    --------
    "Create a 5-slide presentation on Quantum Computing" → "Quantum Computing"
    "Artificial Intelligence in Healthcare"              → "Artificial Intelligence in Healthcare"
    "Create PPT on AI with dark theme"                   → "AI"
    """
    cleaned = raw.strip().rstrip(".!")

    # Try structured patterns first
    for pattern in _TOPIC_STRIP_PATTERNS:
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            topic = m.group(1).strip().rstrip(".!")
            if topic:
                # Strip theme/audience noise from the extracted portion
                topic = _THEME_NOISE_RE.sub("", topic).strip()
                topic = _AUDIENCE_NOISE_RE.sub("", topic).strip()
                topic = re.sub(r"\s{2,}", " ", topic).strip().rstrip(",.")
                if topic:
                    return topic

    # Fallback: strip noise from the full string
    topic = _THEME_NOISE_RE.sub("", cleaned).strip()
    topic = _AUDIENCE_NOISE_RE.sub("", topic).strip()
    topic = re.sub(r"\s{2,}", " ", topic).strip().rstrip(",.")
    return topic or cleaned


def extract_theme_and_topic(raw: str) -> tuple[str, str]:
    """
    Parse the raw user input and return:
        (theme_name, clean_topic)

    theme_name is always a valid preset name (never None).

    Examples
    --------
    "Create PPT on AI with dark theme"          → ("dark",         "AI")
    "Make 5 slides on solar system"             → ("professional", "solar system")
    "academic style on quantum computing"        → ("academic",     "quantum computing")
    "Create a presentation on Machine Learning" → ("professional", "Machine Learning")
    """
    theme_name  = parse_theme_from_input(raw)
    clean_topic = extract_topic(raw)
    return theme_name, clean_topic


# ── Fallback titles (used ONLY when flan-t5 title generation fails) ───────────
def build_fallback_titles(topic: str, n: int = 5) -> list[str]:
    """Return n presentation-ready slide titles derived from the topic."""
    base = [
        f"Introduction to {topic}",
        f"Background and History of {topic}",
        f"Core Concepts of {topic}",
        f"Applications and Benefits of {topic}",
        f"Future of {topic} and Conclusion",
    ]
    # Extend with generic labels if more than 5 slides are requested
    extras = [f"Deep Dive into {topic} — Part {i}" for i in range(1, n + 1)]
    return (base + extras)[:n]
