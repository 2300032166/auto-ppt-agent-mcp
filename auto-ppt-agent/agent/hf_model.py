# agent/hf_model.py
# ─────────────────────────────────────────────────────────────────────────────
# ROLE: PLANNER ONLY
#
# This module is STRICTLY responsible for generating slide *titles*.
# It does NOT generate slide content, bullet points, or any factual text.
# All factual content is sourced exclusively via the MCP search_web tool.
# ─────────────────────────────────────────────────────────────────────────────

import re
import logging
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
from .prompt import TITLE_PLANNING_PROMPT, build_fallback_titles, extract_topic

logger = logging.getLogger("Planner")


class HFPlanner:
    """
    Hugging Face flan-t5 wrapper used EXCLUSIVELY as a slide title planner.

    Responsibilities
    ----------------
    - Receive a cleaned topic string
    - Return a list of N slide titles (strings only)

    Forbidden
    ---------
    - Generating bullet points
    - Generating slide body content
    - Any factual knowledge production
    """

    def __init__(self, model_name: str = "google/flan-t5-base"):
        logger.info(f"[PLANNER] Loading model: {model_name}")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.model.to(self.device)
        logger.info(f"[PLANNER] Model ready on {self.device}.")

    def _run(self, prompt: str, max_new_tokens: int = 120) -> str | None:
        """Low-level model inference — returns raw decoded string."""
        try:
            inputs = self.tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=256
            ).to(self.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                num_beams=4,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        except Exception as e:
            logger.error(f"[PLANNER] Inference error: {e}")
            return None

    def plan_slide_titles(self, topic: str, n: int = 5) -> list[str]:
        """
        Generate exactly *n* slide titles for *topic*.

        Parameters
        ----------
        topic : str   Clean subject string (already processed by extract_topic)
        n     : int   Number of slides requested (default 5)

        Returns
        -------
        list[str]  Exactly n title strings
        """
        prompt = TITLE_PLANNING_PROMPT.format(topic=topic, n=n)
        logger.info(f"[PLANNER] Generating {n} titles for: '{topic}'")
        raw = self._run(prompt, max_new_tokens=120)
        logger.debug(f"[PLANNER] Raw output: {raw!r}")

        if not raw:
            logger.warning("[PLANNER] Empty output — using fallback titles.")
            return build_fallback_titles(topic, n)

        # Parse comma- or newline-separated titles
        parts = re.split(r"[,\n]+", raw)
        titles = []
        for p in parts:
            p = re.sub(r"^\d+[.)]\s*", "", p.strip().strip("\"'")).strip()
            if p and len(p) > 3:
                titles.append(p)

        if len(titles) < 2:
            logger.warning(f"[PLANNER] Only {len(titles)} usable titles — using fallbacks.")
            return build_fallback_titles(topic, n)

        # Pad with fallbacks if under n, trim if over
        fallbacks = build_fallback_titles(topic, n)
        while len(titles) < n:
            titles.append(fallbacks[len(titles)])
        return titles[:n]


# ── Backwards-compatibility shim (remove after full migration) ────────────────
class HFModel(HFPlanner):
    """Deprecated alias kept so run_agent.py import doesn't break during migration."""
    def generate_slide_titles(self, topic: str) -> list[str]:
        return self.plan_slide_titles(topic)
