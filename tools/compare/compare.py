"""Model Compare -- CLI.

Universal baseline run path. Keys are read from environment variables (never a flag,
never a file). Your keys stay on your machine and are never sent to pysolvr.

    python compare.py --models gpt-5,claude-opus-5-5 --prompt "Explain CRDTs in one sentence."

Set the key env vars for whichever providers your two models use:
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY,
    TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from compare_core import ModelCapError, compare_core, format_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare two LLMs head-to-head on your own prompt, with your own keys."
    )
    parser.add_argument(
        "--models",
        required=True,
        help="Exactly two model ids, comma-separated. e.g. gpt-5,claude-opus-5-5",
    )
    parser.add_argument("--prompt", required=True, help="The prompt to send to both models.")
    parser.add_argument(
        "--max-tokens", type=int, default=1024, help="Max completion tokens (default 1024)."
    )
    args = parser.parse_args(argv)

    models = [m for m in args.models.split(",")]
    try:
        result = compare_core(args.prompt, models, max_tokens=args.max_tokens)
    except ModelCapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
