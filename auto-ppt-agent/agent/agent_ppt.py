# agent/agent_ppt.py
# ─────────────────────────────────────────────────────────────────────────────
# TRUE MCP AUTONOMOUS AGENT  —  with THEME CUSTOMIZATION
#
# Pipeline (updated):
#   STEP 0  THEME EXTRACTION  — parse user input for theme keyword
#   STEP 1  set_theme()       — apply theme BEFORE create_presentation()
#   STEP 2  PLAN              — flan-t5 generates slide TITLES only
#   STEP 3  create_presentation()
#   FOR each slide:
#       STEP 4  SEARCH        — search_web() via MCP
#       STEP 5  EXTRACT       — parse bullets from search results
#       STEP 6  BUILD         — add_slide() + write_text() via MCP
#   STEP 7  save_presentation()
#
# Role separation (strictly enforced):
#   HFPlanner        → slide TITLES only  (no content)
#   MCP search_web   → ONLY source of factual slide content
#   MCP PPT tools    → create / theme / add / write / save
#   search_extractor → converts raw search JSON → clean bullets (no LLM)
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import json
import logging
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .hf_model import HFPlanner
from .prompt import extract_theme_and_topic        # NEW — returns (theme, topic)
from config.settings import (
    MODEL_NAME,
    FINAL_PPT_PATH,
    PPT_SERVER_SCRIPT,
    SEARCH_SERVER_SCRIPT,
    SEARCH_MAX_RESULTS,
    SEARCH_MIN_BULLETS,
    DEFAULT_NUM_SLIDES,
)
from utils.search_extractor import build_search_query, extract_bullets_from_results

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-20s %(levelname)s  %(message)s",
)
logger = logging.getLogger("Agent")


# ── Helper: call an MCP tool and return parsed JSON dict ────────────────────

async def _call(session: ClientSession, tool: str, args: dict) -> dict:
    """Call an MCP tool, decode the JSON response, and return as dict."""
    logger.info(f"[MCP]  → {tool}({list(args.keys())})")
    result = await session.call_tool(tool, args)
    raw = result.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"result": raw}


# ── Main Agent class ─────────────────────────────────────────────────────────

class PPTAgent:
    """
    Autonomous MCP agent for generating themed PowerPoint presentations.

    Parameters
    ----------
    raw_topic  : User-provided input (may include theme keywords).
    num_slides : Number of content slides to generate (default 5).
    theme      : Optional theme override; if None it is auto-detected from
                 raw_topic.  Pass an explicit value in manual / API mode.
    """

    def __init__(
        self,
        raw_topic: str,
        num_slides: int = DEFAULT_NUM_SLIDES,
        theme: str | None = None,
        output_name: str | None = None,
    ):
        # ── STEP 0: THEME EXTRACTION ─────────────────────────────────────────
        detected_theme, clean_topic = extract_theme_and_topic(raw_topic)

        # Explicit override takes priority; fall back to auto-detected
        self.theme_name  = theme.strip().lower() if theme else detected_theme
        self.topic       = clean_topic
        self.num_slides  = num_slides
        self.output_name = output_name or os.path.basename(FINAL_PPT_PATH)
        self.planner     = HFPlanner(MODEL_NAME)

        logger.info(f"[AGENT] Raw input  : '{raw_topic}'")
        logger.info(f"[AGENT] Topic      : '{self.topic}'")
        logger.info(f"[AGENT] Theme      : '{self.theme_name}'")
        logger.info(f"[AGENT] Slides     : {self.num_slides}")
        logger.info(f"[AGENT] Output file: '{self.output_name}'")

        # MCP server parameters
        self._ppt_params = StdioServerParameters(
            command="python",
            args=[PPT_SERVER_SCRIPT],
            env=os.environ.copy(),
        )
        self._search_params = StdioServerParameters(
            command="python",
            args=[SEARCH_SERVER_SCRIPT],
            env=os.environ.copy(),
        )

    # ── Stage 2: PLAN ────────────────────────────────────────────────────────

    def _plan(self) -> list[str]:
        """Use flan-t5 ONLY to produce slide titles. No content generated."""
        logger.info("[STAGE 2] PLAN — generating slide titles via LLM")
        titles = self.planner.plan_slide_titles(self.topic, self.num_slides)
        for i, t in enumerate(titles, 1):
            logger.info(f"  Title {i}: {t}")
        return titles

    # ── Stage 4: SEARCH (MCP tool) ───────────────────────────────────────────

    async def _search(
        self, search_session: ClientSession, slide_title: str, slide_index: int
    ) -> list[str]:
        """
        MANDATORY: call search_web MCP tool for every slide.
        No slide may receive content without a search call.
        """
        query = build_search_query(self.topic, slide_title)
        logger.info(f"[STAGE 4] SEARCH — slide {slide_index+1}: {query!r}")

        raw = await search_session.call_tool(
            "search_web", {"query": query, "max_results": SEARCH_MAX_RESULTS}
        )
        raw_text = raw.content[0].text

        try:
            results = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("[SEARCH] Bad JSON from search_web — will use fallback.")
            results = []

        # ── Stage 5: EXTRACT ─────────────────────────────────────────────────
        logger.info(f"[STAGE 5] EXTRACT — {len(results)} result(s) for '{slide_title}'")
        bullets = extract_bullets_from_results(
            results=results,
            topic=self.topic,
            slide_title=slide_title,
            slide_index=slide_index,
            max_bullets=4,
            min_bullets=SEARCH_MIN_BULLETS,
        )
        return bullets

    # ── Stage 6: BUILD SLIDE (MCP tools) ────────────────────────────────────

    async def _build_slide(
        self,
        ppt_session: ClientSession,
        slide_title: str,
        bullets: list[str],
        slide_num: int,
    ) -> None:
        """Call add_slide then write_text MCP tools to render one themed slide."""
        logger.info(f"[STAGE 6] BUILD  — slide {slide_num}: '{slide_title}'")

        add_result  = await _call(ppt_session, "add_slide", {"title": slide_title})
        slide_index = add_result.get("slide_index", slide_num)

        await _call(
            ppt_session,
            "write_text",
            {"slide_index": slide_index, "points": bullets},
        )
        logger.info(
            f"[BUILD]  Slide {slide_num} complete "
            f"({len(bullets)} bullet(s), idx={slide_index})"
        )

    # ── Master run ───────────────────────────────────────────────────────────

    async def run(self) -> str:
        """
        Execute the full themed agent loop:

            STEP 0  (done in __init__)  — theme extracted from raw input
            STEP 1  set_theme()         — theme applied to PPT server state
            STEP 2  PLAN (LLM)          — slide titles
            STEP 3  create_presentation()
            STEP 4-6  ×N               — SEARCH → EXTRACT → BUILD per slide
            STEP 7  save_presentation()

        Returns the path to the saved .pptx file.
        """
        # ── STEP 2: PLAN (LLM, outside MCP) ──────────────────────────────────
        slide_titles = self._plan()

        # ── Open two concurrent MCP sessions ────────────────────────────────
        async with stdio_client(self._ppt_params) as (ppt_r, ppt_w):
            async with ClientSession(ppt_r, ppt_w) as ppt_session:
                await ppt_session.initialize()
                logger.info("[AGENT] Connected to PPT MCP server.")

                async with stdio_client(self._search_params) as (s_r, s_w):
                    async with ClientSession(s_r, s_w) as search_session:
                        await search_session.initialize()
                        logger.info("[AGENT] Connected to Search MCP server.")

                        # ── STEP 1: SET THEME (BEFORE create_presentation) ──
                        logger.info(f"[STAGE 1] SET THEME → '{self.theme_name}'")
                        theme_result = await _call(
                            ppt_session,
                            "set_theme",
                            {"theme_name": self.theme_name},
                        )
                        print(f"\n  ✔ Theme applied: {theme_result.get('result', '')}")

                        # ── STEP 3: CREATE PRESENTATION ─────────────────────
                        await _call(
                            ppt_session,
                            "create_presentation",
                            {"title": self.topic},
                        )

                        # ── STEP 4-6: Agentic loop — one iteration per slide
                        for i, title in enumerate(slide_titles):
                            print(f"\n── Slide {i+1}/{self.num_slides}: {title}")

                            # SEARCH + EXTRACT
                            bullets = await self._search(search_session, title, i)
                            print(f"   ✔ {len(bullets)} bullet(s) extracted from web")

                            # BUILD
                            await self._build_slide(ppt_session, title, bullets, i + 1)
                            print(f"   ✔ Slide built via MCP tools")

                        # ── STEP 7: SAVE ────────────────────────────────────
                        logger.info(f"[STAGE 7] SAVE — saving as '{self.output_name}'")
                        await _call(
                            ppt_session,
                            "save_presentation",
                            {"filename": self.output_name},
                        )

        import os as _os
        final_path = _os.path.join(_os.path.dirname(FINAL_PPT_PATH), self.output_name)
        logger.info(f"[AGENT] Done. File: {final_path}")
        return final_path


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else "Artificial Intelligence in Healthcare"
    agent = PPTAgent(raw)
    asyncio.run(agent.run())
