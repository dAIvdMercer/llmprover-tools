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

Run it with NO arguments and it uses a curated demonstration default: the same open-ended prompt run
at temperature 0 vs temperature 1, so the first run shows how the temperature dial changes the
wording spread (the mechanical consistency number). Overwrite the defaults freely.

  # run the demonstration default (temp 0 vs temp 1):
  python variance.py

Set the key env var for your model's provider:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from variance_core import RunCountError, TemperatureError, format_result, variance_core

# Demonstration default (Step 1b): one open-ended prompt (room to vary) run at temperature 0 vs
# temperature 1. The mechanical consistency read (wording overlap) shows the temp-0 pair far more
# alike than the temp-1 pair -- the lesson is entirely in the numbers, never a verdict, and it is a
# durable truth about the temperature dial (not a model quirk). Lives in the CLI wrapper defaults.
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_PROMPT = "Give me a one-sentence tagline for a new coffee shop."
DEFAULT_TEMPERATURES = "0,0,1,1"  # two runs at temp 0, two at temp 1 -- spread visible within each


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
        description="Run one prompt at one model N times and report the spread (no quality verdict). "
                    "With no arguments, runs a curated demonstration default."
    )
    p.add_argument("--model", default=None, help="Model id, e.g. gpt-5 (provider inferred).")
    p.add_argument("--prompt", help="The prompt to run, inline.")
    p.add_argument("--prompt-file", help="Read the prompt from this file.")
    p.add_argument("--runs", type=int, default=5, help="How many times to run (default 5, max 10).")
    p.add_argument("--temperatures", help="Comma-separated temperatures to sweep (one run each), "
                                          "range 0-2, e.g. 0,0.5,1.0. Overrides --runs.")
    p.add_argument("--max-tokens", type=int, default=1024)
    args = p.parse_args(argv)

    # No model and no prompt -> run the curated demonstration default (temp 0 vs temp 1) so the first
    # run teaches the temperature lesson instead of erroring on empty input.
    using_demo = args.model is None and args.prompt is None and args.prompt_file is None
    if using_demo:
        model = DEFAULT_MODEL
        prompt = DEFAULT_PROMPT
        temperatures = _parse_temps(DEFAULT_TEMPERATURES)
        print("(no input given -- running the demonstration default: one open-ended prompt at "
              "temperature 0 (x2) vs temperature 1 (x2). Watch the wording overlap stay high at "
              "temp 0 and drop at temp 1. Pass --model / --prompt to use your own.)\n")
    else:
        if args.model is None:
            raise SystemExit("error: --model is required (or pass no arguments to run the demo default)")
        model = args.model
        prompt = _read_prompt(args.prompt_file, args.prompt)
        temperatures = _parse_temps(args.temperatures)

    try:
        result = variance_core(
            prompt=prompt,
            model=model,
            runs=args.runs,
            temperatures=temperatures,
            max_tokens=args.max_tokens,
        )
    except (RunCountError, TemperatureError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
