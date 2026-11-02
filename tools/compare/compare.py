"""Model Compare -- CLI.

Universal baseline run path. Keys are read from environment variables (never a flag,
never a file). Your keys stay on your machine and are never sent to pysolvr.

Run it with NO arguments and it uses a curated demonstration default: a small, cheap model vs a
large flagship on one everyday question, so the first run shows the responses with their token cost
and latency side by side. Overwrite the defaults freely with your own models and prompt.

    # run the demonstration default (cheap vs flagship on an everyday question):
    python compare.py

    # your own head-to-head:
    python compare.py --models gpt-5,claude-opus-5-5 --prompt "Explain CRDTs in one sentence."

Set the key env vars for whichever providers your two models use:
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY,
    TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from compare_core import ModelCapError, compare_core, format_result

# Demonstration default (Step 1b): a cheap model vs a flagship on one everyday question. The lesson
# is mechanical and durable -- the responses land side by side with their token cost and latency, so
# the price/speed gap between a small and a large model is visible at a glance. No verdict: the user
# reads both answers and decides. Lives in the CLI wrapper defaults, not in compare_core.
DEFAULT_MODELS = "gpt-4o-mini,claude-opus-5-5"
DEFAULT_PROMPT = "Write a friendly two-sentence reply apologizing to a customer for a late delivery."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare two LLMs head-to-head on your own prompt, with your own keys. "
                    "With no arguments, runs a curated demonstration default."
    )
    parser.add_argument(
        "--models",
        default=None,
        help=f"Exactly two model ids, comma-separated. e.g. gpt-5,claude-opus-5-5 "
             f"(default demo: {DEFAULT_MODELS}).",
    )
    parser.add_argument("--prompt", default=None, help="The prompt to send to both models.")
    parser.add_argument(
        "--max-tokens", type=int, default=1024, help="Max completion tokens (default 1024)."
    )
    args = parser.parse_args(argv)

    # No models and no prompt -> run the curated demonstration default so the first run is
    # instructive instead of erroring on empty input.
    using_demo = args.models is None and args.prompt is None
    models_raw = args.models if args.models is not None else DEFAULT_MODELS
    prompt = args.prompt if args.prompt is not None else DEFAULT_PROMPT

    if using_demo:
        print(f"(no input given -- running the demonstration default: {models_raw} on an everyday "
              "question. Pass --models / --prompt to use your own.)\n")

    models = [m for m in models_raw.split(",")]
    try:
        result = compare_core(prompt, models, max_tokens=args.max_tokens)
    except ModelCapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
