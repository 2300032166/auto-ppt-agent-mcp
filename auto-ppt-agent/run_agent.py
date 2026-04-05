# run_agent.py - Entry point for the True MCP Auto-PPT Agent (with Theme + Output name support)
# -*- coding: utf-8 -*-
import sys, io
# Force UTF-8 stdout so Unicode chars don't crash on Windows cp1252
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


import asyncio
import sys
import argparse
import logging

from agent.agent_ppt import PPTAgent
from utils.helpers import ensure_directory
from config.settings import OUTPUT_DIR, DEFAULT_NUM_SLIDES
from themes.theme_config import THEME_PRESETS, DEFAULT_THEME_NAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-20s %(levelname)s  %(message)s",
)
logger = logging.getLogger("Main")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Auto-PPT: True MCP Agent — generates themed PowerPoint from web search data.\n\n"
            "Theme can be specified via --theme flag OR embedded in the topic string, e.g.:\n"
            "  python run_agent.py \"Create PPT on AI with dark theme\"\n"
            "  python run_agent.py \"Solar System\" --theme academic\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "topic",
        nargs="*",
        help='Presentation topic, e.g. "Quantum Computing"',
    )
    parser.add_argument(
        "--slides", "-s",
        type=int,
        default=DEFAULT_NUM_SLIDES,
        help=f"Number of slides to generate (default: {DEFAULT_NUM_SLIDES})",
    )
    parser.add_argument(
        "--theme", "-t",
        type=str,
        default=None,
        choices=list(THEME_PRESETS.keys()),
        metavar="THEME",
        help=(
            f"Presentation theme. Choices: {', '.join(THEME_PRESETS.keys())}. "
            f"Default: auto-detected from topic (falls back to '{DEFAULT_THEME_NAME}')"
        ),
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        metavar="FILENAME",
        help=(
            "Output filename for the saved presentation. "
            "Must end with .pptx (e.g. 'my_topic.pptx'). "
            "Defaults to 'final.pptx' if not specified."
        ),
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    # Resolve topic: CLI arg > interactive prompt
    if args.topic:
        topic = " ".join(args.topic)
    else:
        topic = input("Enter the topic for your presentation: ").strip()

    if not topic:
        print("Error: No topic provided.")
        sys.exit(1)

    num_slides  = args.slides
    theme_flag  = args.theme        # None = auto-detect from topic string
    output_flag = args.output       # None = use default 'final.pptx'

    # Sanitise output filename
    if output_flag:
        output_flag = output_flag.strip()
        if not output_flag.lower().endswith(".pptx"):
            output_flag += ".pptx"
    else:
        output_flag = "final.pptx"

    ensure_directory(OUTPUT_DIR)

    print("\n" + "=" * 60)
    print(f"  Auto-PPT  |  True MCP Agent  (with Theme Engine)")
    print(f"  Input     : {topic}")
    print(f"  Slides    : {num_slides}")
    print(f"  Theme     : {theme_flag or 'auto-detect from input'}")
    print(f"  Output    : {output_flag}")
    print("=" * 60)
    print("\n[ARCHITECTURE]")
    print("  Planner : flan-t5 (titles ONLY)")
    print("  Search  : MCP search_web (DuckDuckGo, real data)")
    print("  Theme   : set_theme() → applied before create_presentation()")
    print("  Builder : MCP PPT tools (add_slide, write_text, save)")
    print()

    # Pass theme=None → agent auto-detects from topic;
    # Pass theme="dark" etc. → explicit override
    agent = PPTAgent(
        raw_topic   = topic,
        num_slides  = num_slides,
        theme       = theme_flag,
        output_name = output_flag,
    )

    try:
        output_path = await agent.run()
        print("\n" + "=" * 60)
        print(f"  [OK] Presentation generated successfully!")
        print(f"  Theme : '{agent.theme_name}'")
        print(f"  File  : {output_path}")
        print("=" * 60 + "\n")
    except Exception as e:
        logger.error(f"Agent failed: {e}", exc_info=True)
        print("\nAn error occurred. Check logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(0)
