# mcp_servers/web_search_server.py
# ─────────────────────────────────────────────────────────────────────────────
# ROLE: TRUTH SOURCE (MCP Search Tool)
#
# Provides the `search_web` MCP tool which performs real DuckDuckGo searches.
# This is the ONLY authorised source of factual content in the agent pipeline.
# The PPT agent calls this tool once per slide to gather real web data.
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Search-Server")

mcp = FastMCP("Search-Server")


def _ddg_search(query: str, max_results: int) -> list[dict]:
    """
    Run a real DuckDuckGo search and return structured results.
    Each result: {"title": str, "snippet": str, "url": str}
    """
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body",  ""),
                    "url":     r.get("href",  ""),
                })
        return results
    except ImportError:
        logger.error("duckduckgo_search not installed. Run: pip install duckduckgo-search")
        return []
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo and return real results as JSON.

    Parameters
    ----------
    query       : Optimised search query (built by the agent per slide).
    max_results : Maximum number of results to return (default 5).

    Returns
    -------
    JSON string: list of {"title", "snippet", "url"} objects.
    An empty list [] is returned (not an error) if search yields nothing.
    """
    logger.info(f"[SEARCH] search_web called — query: {query!r}")
    results = _ddg_search(query, max_results)
    logger.info(f"[SEARCH] Returned {len(results)} results for: {query!r}")
    return json.dumps(results, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
