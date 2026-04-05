# utils/search_extractor.py
# ─────────────────────────────────────────────────────────────────────────────
# ROLE: EXTRACTOR (Pure rule-based, NO LLM)
#
# Converts DuckDuckGo search results into clean, PPT-safe bullet points.
#
# RULES enforced here:
#   - Max 4 bullets per slide, min 3 preferred
#   - Each bullet: max 15 words (auto-truncated if longer)
#   - NO "[Fallback Knowledge]" prefix on individual bullets
#   - Fallback is a SLIDE-LEVEL decision, logged once — bullets stay clean
#   - No long paragraphs, no raw AI text dumps
# ─────────────────────────────────────────────────────────────────────────────

import re
import logging

logger = logging.getLogger("Extractor")

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_BULLET_WORDS  = 15   # hard cap per bullet (avoids PPT overflow)
MIN_BULLET_WORDS  = 6    # minimum to be considered useful
MAX_BULLETS       = 4    # max bullets per slide
MIN_BULLETS       = 3    # trigger fallback supplement below this

# ── Label prefix pattern — strip any [Tag] or (Tag) at start of bullet ────────
# Catches things like: [Fallback Knowledge], [Source], (Info), etc.
import re as _re
_LABEL_PREFIX_RE = _re.compile(r"^[\[(][^\]\)]{1,40}[\])]\s*", _re.IGNORECASE)


def _strip_label_prefix(text: str) -> str:
    """
    Remove any leading bracketed/parenthesised label from *text*.

    Examples
    --------
    "[Fallback Knowledge] AI is transforming..." → "AI is transforming..."
    "(Source) Climate change affects..."         → "Climate change affects..."
    "Normal bullet point."                        → "Normal bullet point."
    """
    cleaned = _LABEL_PREFIX_RE.sub("", text).strip()
    # Re-capitalise if the prefix was removed
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned if cleaned else text


# ── Fallback templates (clean, no prefix, professional tone) ─────────────────
# Used ONLY when search yields < MIN_BULLETS valid sentences.
# These are slide-position-aware but written as plain professional bullets.
# The agent logs "[FALLBACK]" at slide level — NOT embedded in bullet text.

_FALLBACK_TEMPLATES = [
    # Slide 0 — Introduction
    [
        "{topic} is a transformative field shaping modern technology.",
        "It spans techniques, tools, and frameworks across industries.",
        "Understanding {topic} is essential for professionals today.",
        "This slide introduces the core ideas behind {topic}.",
    ],
    # Slide 1 — Background / History
    [
        "{topic} has evolved significantly over recent decades.",
        "Early research laid foundational principles still used today.",
        "Key milestones shaped the current state of {topic}.",
        "Historical context helps explain why {topic} matters now.",
    ],
    # Slide 2 — Core Concepts
    [
        "Core principles of {topic} focus on efficiency and precision.",
        "Fundamental models define how data and systems interact.",
        "Key terminology includes algorithms, frameworks, and protocols.",
        "Mastering these concepts is critical to applying {topic}.",
    ],
    # Slide 3 — Applications & Benefits
    [
        "{topic} is applied in healthcare, finance, and education.",
        "Organisations use {topic} to improve decisions and cut costs.",
        "Real-world deployments show measurable performance gains.",
        "{topic} enables automation, scalability, and accuracy.",
    ],
    # Slide 4 — Future / Conclusion
    [
        "The future of {topic} is driven by research and investment.",
        "Emerging trends include automation, personalisation, and scale.",
        "Ethical frameworks will guide responsible adoption of {topic}.",
        "{topic} is set to reshape industries in the coming decade.",
    ],
]


def _build_fallback(topic: str, slide_index: int) -> list[str]:
    """
    Return clean fallback bullets for a slide.
    NO prefix is added to individual bullets.
    The calling agent logs fallback usage at slide level.
    """
    idx = min(slide_index, len(_FALLBACK_TEMPLATES) - 1)
    return [
        line.format(topic=topic)
        for line in _FALLBACK_TEMPLATES[idx]
    ]


# ── Bullet processing helpers ─────────────────────────────────────────────────

def _split_into_sentences(text: str) -> list[str]:
    """Split a multi-sentence paragraph into individual sentences."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _is_valid_sentence(s: str) -> bool:
    """Return True only if *s* qualifies as a usable slide bullet."""
    s = s.strip()
    words = s.split()
    if len(words) < MIN_BULLET_WORDS:
        return False
    if re.match(r"^https?://", s):                          # raw URL
        return False
    if re.match(r"^\d{1,2}[/-]\d{1,2}", s):                # date fragment
        return False
    if re.search(r"\bclick here\b|\bread more\b|\bsee also\b|\bcookie\b", s, re.I):
        return False
    if re.search(r"\bcopyright\b|\ball rights reserved\b", s, re.I):
        return False
    if not _is_english(s):                                   # reject non-English text
        return False
    return True


def _shorten_bullet(s: str, max_words: int = MAX_BULLET_WORDS) -> str:
    """
    Truncate *s* to at most *max_words* words.
    Appends '.' if the truncated sentence doesn't end with punctuation.
    Auto-compression rule: trim at the last comma or semicolon within limit
    to keep the bullet grammatically clean.
    """
    words = s.split()
    if len(words) <= max_words:
        return s  # already short enough

    # Try to split at a natural boundary (comma/semicolon) within word limit
    candidate = " ".join(words[:max_words])
    # Walk back to find last comma or semicolon for a clean cut
    for i in range(max_words - 1, max_words // 2, -1):
        w = words[i]
        if w.endswith(",") or w.endswith(";"):
            candidate = " ".join(words[:i])
            break

    candidate = candidate.rstrip(",;: ")
    if not candidate.endswith((".","!","?")):
        candidate += "."
    return candidate


def _clean_and_shorten(s: str) -> str:
    """Normalise whitespace, capitalise, ensure period, then shorten."""
    s = re.sub(r"\s+", " ", s).strip()
    s = s[0].upper() + s[1:] if s else s
    if s and s[-1] not in ".!?":
        s += "."
    return _shorten_bullet(s)


# ── Generic slide-structure words — meaningless in a search query ──────────────
# Titles like "Future of AI and Conclusion" include words that return
# grammar/writing sites instead of factual content about the topic.
_SLIDE_STOP_WORDS = re.compile(
    r"\b(introduction|conclusion|overview|background|history|future|outlook|summary|review|key concepts?|deep dive|part \d+)\b",
    re.IGNORECASE,
)

# ── Non-Latin character detector ────────────────────────────────────────────
# Rejects Chinese, Japanese, Korean, Arabic, etc. characters in bullets.
# A bullet is "non-English" if more than 10% of its chars are non-ASCII.
_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")


def _is_english(text: str, threshold: float = 0.10) -> bool:
    """
    Return True if the sentence is predominantly Latin/English.
    Rejects text where non-ASCII characters exceed *threshold* ratio.
    """
    if not text:
        return False
    non_ascii_count = len(_NON_ASCII_RE.findall(text))
    return (non_ascii_count / len(text)) < threshold


# ── Query builder ─────────────────────────────────────────────────────────────────

def build_search_query(topic: str, slide_title: str) -> str:
    """
    Build an optimised DuckDuckGo query per slide.

    Strategy:
    - Strip generic slide-structure words from the title (Introduction,
      Conclusion, Background, etc.) which produce off-topic search hits.
    - Always anchor the query to the *topic* so results stay on-subject.
    - Format: "{cleaned_title} {topic} key facts"
    """
    # Remove generic words from the slide title
    clean_title = _SLIDE_STOP_WORDS.sub("", slide_title)
    clean_title = re.sub(r"\s{2,}", " ", clean_title).strip().strip("-—,")

    # If nothing meaningful remains in the title, search by topic only
    if not clean_title or len(clean_title.split()) < 2:
        return f"{topic} key facts overview"

    return f"{clean_title} {topic} key facts"


# ── Main public function ──────────────────────────────────────────────────────

def extract_bullets_from_results(
    results: list[dict],
    topic: str,
    slide_title: str,
    slide_index: int = 0,
    max_bullets: int = MAX_BULLETS,
    min_bullets: int = MIN_BULLETS,
) -> list[str]:
    """
    Convert DuckDuckGo search results into PPT-safe bullet points.

    Guarantees
    ----------
    - Between min_bullets and max_bullets bullets returned
    - Each bullet is at most MAX_BULLET_WORDS words
    - NO prefix labels embedded in bullet text
    - Fallback bullets are clean professional sentences (slide-level log only)

    Parameters
    ----------
    results     : list of {"title", "snippet", "url"} from search_web MCP tool
    topic       : cleaned topic string (e.g. "Quantum Computing")
    slide_title : this slide's title
    slide_index : 0-indexed position (used to pick the right fallback set)
    max_bullets : cap on bullets returned (default 4)
    min_bullets : minimum before supplementing with fallback (default 3)
    """

    # ── Full fallback: no search results at all ───────────────────────────────
    if not results:
        logger.warning(f"[EXTRACTOR][FALLBACK] '{slide_title}' — no search results.")
        fb = _build_fallback(topic, slide_index)
        return [_strip_label_prefix(_clean_and_shorten(b)) for b in fb[:max_bullets]]

    # ── Collect and join all snippet text ─────────────────────────────────────
    all_text = " ".join(
        (r.get("snippet") or r.get("title") or "")
        for r in results
    ).strip()

    if not all_text:
        logger.warning(f"[EXTRACTOR][FALLBACK] '{slide_title}' — empty snippets.")
        fb = _build_fallback(topic, slide_index)
        return [_strip_label_prefix(_clean_and_shorten(b)) for b in fb[:max_bullets]]

    # ── Extract sentences from search snippets ────────────────────────────────
    sentences = _split_into_sentences(all_text)
    bullets: list[str] = []
    seen: set[str] = set()

    for raw_s in sentences:
        if not _is_valid_sentence(raw_s):
            continue
        cleaned = _clean_and_shorten(raw_s)
        cleaned = _strip_label_prefix(cleaned)     # remove any [Tag] prefix
        # Deduplication: skip near-duplicates using first 35 chars as key
        key = cleaned[:35].lower()
        if key in seen:
            continue
        seen.add(key)
        bullets.append(cleaned)
        if len(bullets) >= max_bullets:
            break

    # ── Supplement with fallback if search bullets are insufficient ───────────
    if len(bullets) < min_bullets:
        logger.warning(
            f"[EXTRACTOR][FALLBACK] '{slide_title}' — only {len(bullets)} "
            f"search bullet(s); supplementing with fallback."
        )
        fb = _build_fallback(topic, slide_index)
        fb_cleaned = [_strip_label_prefix(_clean_and_shorten(b)) for b in fb]
        needed = max_bullets - len(bullets)
        bullets.extend(fb_cleaned[:needed])

    logger.info(
        f"[EXTRACTOR] '{slide_title}': {len(bullets)} bullet(s) "
        f"(max {MAX_BULLET_WORDS} words each)."
    )
    return bullets[:max_bullets]
