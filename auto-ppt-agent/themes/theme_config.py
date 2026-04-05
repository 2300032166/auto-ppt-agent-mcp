# themes/theme_config.py
# ─────────────────────────────────────────────────────────────────────────────
# All predefined theme presets for the Auto-PPT system.
# Each theme defines colors, fonts, and size presets that are applied globally.
# ─────────────────────────────────────────────────────────────────────────────

from dataclasses import dataclass, field
from typing import Tuple

# RGB colour type alias
RGB = Tuple[int, int, int]


@dataclass
class ThemeConfig:
    """
    Full theme specification for a presentation.

    Colours are (R, G, B) tuples (0-255).
    Sizes are in PowerPoint Points (Pt).
    """
    name: str

    # ── Background ────────────────────────────────────────────────────────────
    background_color: RGB = (255, 255, 255)   # slide background

    # ── Title slide ───────────────────────────────────────────────────────────
    title_color: RGB       = (31, 73, 125)    # title slide title text
    subtitle_color: RGB    = (89, 89, 89)     # title slide subtitle text

    # ── Content slides ────────────────────────────────────────────────────────
    slide_title_color: RGB = (31, 73, 125)    # slide heading text
    body_color: RGB        = (50, 50, 50)     # bullet text

    # ── Fonts ─────────────────────────────────────────────────────────────────
    font_family: str       = "Calibri"
    title_size: int        = 32              # Pt — title slide title
    slide_title_size: int  = 28              # Pt — content slide heading
    body_size: int         = 18              # Pt — bullet points

    # ── Accent bar (thin rect under slide title) ──────────────────────────────
    accent_color: RGB      = (31, 73, 125)


# ── Preset Registry ───────────────────────────────────────────────────────────

THEME_PRESETS: dict[str, ThemeConfig] = {

    # White background, blue headers — corporate / business
    "professional": ThemeConfig(
        name               = "professional",
        background_color   = (255, 255, 255),
        title_color        = (31, 73, 125),
        subtitle_color     = (89, 89, 89),
        slide_title_color  = (31, 73, 125),
        body_color         = (50, 50, 50),
        font_family        = "Calibri",
        title_size         = 36,
        slide_title_size   = 28,
        body_size          = 18,
        accent_color       = (31, 73, 125),
    ),

    # Dark background, white / light text
    "dark": ThemeConfig(
        name               = "dark",
        background_color   = (30, 30, 30),
        title_color        = (255, 255, 255),
        subtitle_color     = (200, 200, 200),
        slide_title_color  = (100, 181, 246),   # light-blue heading
        body_color         = (224, 224, 224),
        font_family        = "Calibri",
        title_size         = 36,
        slide_title_size   = 28,
        body_size          = 18,
        accent_color       = (100, 181, 246),
    ),

    # Classic serif look — universities, research
    "academic": ThemeConfig(
        name               = "academic",
        background_color   = (252, 251, 245),   # off-white / parchment
        title_color        = (60, 40, 20),
        subtitle_color     = (100, 80, 60),
        slide_title_color  = (80, 50, 20),
        body_color         = (60, 40, 20),
        font_family        = "Georgia",
        title_size         = 34,
        slide_title_size   = 26,
        body_size          = 17,
        accent_color       = (139, 90, 43),
    ),

    # Vibrant, gradient-inspired — marketing, creative
    "creative": ThemeConfig(
        name               = "creative",
        background_color   = (245, 240, 255),   # very light lavender
        title_color        = (98, 0, 234),      # purple
        subtitle_color     = (0, 150, 136),     # teal
        slide_title_color  = (98, 0, 234),
        body_color         = (40, 40, 60),
        font_family        = "Trebuchet MS",
        title_size         = 36,
        slide_title_size   = 28,
        body_size          = 18,
        accent_color       = (0, 200, 83),      # vivid green accent bar
    ),

    # Ultra-clean white, single accent line
    "minimal": ThemeConfig(
        name               = "minimal",
        background_color   = (255, 255, 255),
        title_color        = (30, 30, 30),
        subtitle_color     = (120, 120, 120),
        slide_title_color  = (30, 30, 30),
        body_color         = (80, 80, 80),
        font_family        = "Arial",
        title_size         = 34,
        slide_title_size   = 26,
        body_size          = 17,
        accent_color       = (255, 87, 34),     # coral accent bar
    ),
}

DEFAULT_THEME_NAME = "professional"


def get_theme(name: str) -> ThemeConfig:
    """
    Return a ThemeConfig for *name*.

    Falls back to 'professional' (with a warning) for unknown names.
    """
    import logging
    logger = logging.getLogger("ThemeConfig")

    key = (name or "").strip().lower()
    if key not in THEME_PRESETS:
        logger.warning(
            f"[THEME] Unknown theme '{name}'. Falling back to 'professional'."
        )
        key = DEFAULT_THEME_NAME
    theme = THEME_PRESETS[key]
    logger.info(f"[THEME] Loaded preset: '{theme.name}'")
    return theme


def parse_theme_from_input(raw_input: str) -> str:
    """
    Scan the user's raw input string for a recognised theme keyword.

    Returns the matched theme name, or DEFAULT_THEME_NAME if none found.

    Examples
    --------
    "Create PPT on AI with dark theme"     → "dark"
    "Make 5 slides on solar system"        → "professional"
    "academic style on quantum computing"  → "academic"
    """
    import re
    text = raw_input.lower()

    # Ordered from most specific to most general
    patterns = [
        (r"\bdark\b",         "dark"),
        (r"\bacademic\b",     "academic"),
        (r"\bcreative\b",     "creative"),
        (r"\bminimal\b",      "minimal"),
        (r"\bprofessional\b", "professional"),
        # Audience-based heuristics
        (r"\bschool\b",       "academic"),
        (r"\bbusiness\b",     "professional"),
        (r"\btechnical\b",    "minimal"),
        (r"\bcolorful\b",     "creative"),
        (r"\bcolourful\b",    "creative"),
    ]

    for pattern, theme_name in patterns:
        if re.search(pattern, text):
            return theme_name

    return DEFAULT_THEME_NAME
