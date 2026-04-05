import os

# ── Base Directories ──────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Hugging Face Settings (Planner only) ─────────────────────────────────────
MODEL_NAME = "google/flan-t5-base"

# ── MCP Server Scripts ────────────────────────────────────────────────────────
PPT_SERVER_SCRIPT    = os.path.join(BASE_DIR, "mcp_servers", "ppt_server.py")
SEARCH_SERVER_SCRIPT = os.path.join(BASE_DIR, "mcp_servers", "web_search_server.py")

# ── Search Settings ───────────────────────────────────────────────────────────
SEARCH_MAX_RESULTS   = 5     # DuckDuckGo results fetched per slide query
SEARCH_MIN_BULLETS   = 2     # If fewer valid bullets extracted → use fallback

# ── Presentation Settings ─────────────────────────────────────────────────────
DEFAULT_FILENAME  = "final.pptx"
FINAL_PPT_PATH    = os.path.join(OUTPUT_DIR, DEFAULT_FILENAME)
DEFAULT_NUM_SLIDES = 5
