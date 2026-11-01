"""Variance Tester -- CLI.

Ask one model the same prompt N times and see how much the answer moves: the responses, their
cost and latency, and a mechanical consistency (wording-overlap) read. No quality verdict.
Keys are read from environment variables (never a flag/file). Keys stay on your machine.

  # run the same prompt 5 times (default):
  python variance.py --model gpt-5 --prompt "Name one risk of deploying this model."

  # run it 8 times:
  python variance.py --model gpt-5 --prompt "..." --runs 8

  # sweep temperatures (one run each):
  python variance.py --model gpt-5 --prompt "..." --temperatures 0,0.5,1.0

  # read the prompt from a file:
  python variance.py --model claude-sonnet-5-5 --prompt-file prompt.txt

Set the key env var for your model's provider:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from variance_core import RunCountError, format_result, variance_core


def _read_prompt(path: str | None, inline: str | None) -> str:
    if inline is not None:
        return inline
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    raise SystemExit("error: provide --prompt or --prompt-file")


def _parse_temps(raw: str | None) -> list | None:
    if not raw:
        return None
    try:
        return [float(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise SystemExit("error: --temperatures must be a comma-separated list of numbers, e.g. 0,0.5,1.0")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run one prompt at one model N times and report the spread (no quality verdict)."
    )
    p.add_argument("--model", required=True, help="Model id, e.g. gpt-5 (provider inferred).")
    p.add_argument("--prompt", help="The prompt to run, inline.")
    p.add_argument("--prompt-file", help="Read the prompt from this file.")
    p.add_argument("--runs", type=int, default=5, help="How many times to run (default 5, max 10).")
    p.add_argument("--temperatures", help="Comma-separated temperatures to sweep (one run each), e.g. 0,0.5,1.0.")
    p.add_argument("--max-tokens", type=int, default=1024)
    args = p.parse_args(argv)

    prompt = _read_prompt(args.prompt_file, args.prompt)

    try:
        result = variance_core(
            prompt=prompt,
            model=args.model,
            runs=args.runs,
            temperatures=_parse_temps(args.temperatures),
            max_tokens=args.max_tokens,
        )
    except RunCountError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
