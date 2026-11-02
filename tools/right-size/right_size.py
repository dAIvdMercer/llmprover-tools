"""Right-Size It -- CLI.

Run one prompt across several models (your own keys), read the answers, mark which are good enough,
and the tool tells you the cheapest of the ones YOU accepted, and how much it saves. Keys are read
from environment variables (never a flag/file). Keys stay on your machine.

Run it with NO arguments and it uses a curated demonstration default: a simple everyday task run
across a cheap model, a mid model, and a flagship, with an example "all three acceptable" selection
pre-marked (a simple task even a cheap model handles). You see the cheapest acceptable save a large
share of the cost. The lesson is the cost arithmetic; YOU always decide what is good enough.

  # run the demonstration default (simple task, example marks pre-filled):
  python right_size.py

  # your own: run across your models, then mark the acceptable ones by number:
  python right_size.py --models gpt-4o-mini,gpt-4o,claude-opus-5-5 \
      --prompt "Classify this ticket as billing/technical/other: ..." \
      --acceptable 1,2

If you omit --acceptable, the tool prints the answers and stops so you can read them and re-run with
your picks. The tool never marks acceptability for you.

Set the key env vars for whichever providers your models use:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from right_size_core import (
    ModelCountError,
    cheapest_of_acceptable,
    format_decision,
    format_runs,
    right_size_core,
)

# Demonstration default (Step 1b): a SIMPLE everyday task run across a cheap, a mid, and a flagship
# model, with an example acceptable-set pre-marked. The task is deliberately one even a cheap model
# handles well, so marking all three acceptable is self-evidently reasonable -- and then the cost
# arithmetic shows the cheapest acceptable saving a large share versus the flagship. This demonstrates
# the MECHANIC (you mark, the tool costs) and a durable truth (a cheap model that is good enough can
# cost a fraction of a flagship). The human still owns the quality call; the demo marks are an
# EXAMPLE, clearly labelled. Lives in the CLI wrapper defaults, not in right_size_core.
DEFAULT_MODELS = "gpt-4o-mini,gpt-4o,claude-opus-5-5"
DEFAULT_PROMPT = (
    "Classify this customer message as one of: billing, technical, other. "
    "Reply with only the single word.\n\nMessage: \"My card was charged twice this month.\""
)
DEFAULT_ACCEPTABLE = [1, 2, 3]  # example: a simple task, so all three answers are plausibly fine


def _parse_models(raw):
    return [m.strip() for m in raw.split(",") if m.strip()] if raw else []


def _parse_acceptable(raw):
    if not raw:
        return None
    out = []
    for tok in raw.split(","):
        tok = tok.strip()
        if tok:
            try:
                out.append(int(tok))
            except ValueError:
                raise SystemExit(f"error: --acceptable must be comma-separated run numbers, got '{tok}'")
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Run one prompt across models, mark which answers are good enough, and get the "
                    "cheapest of those (cost arithmetic only, no verdict). With no arguments, runs a "
                    "curated demonstration default."
    )
    p.add_argument("--models", default=None, help="Comma-separated model ids (2 to 6).")
    p.add_argument("--prompt", default=None, help="The prompt to run across the models.")
    p.add_argument("--acceptable", default=None,
                   help="Comma-separated run numbers you judge good enough, e.g. 1,2. Omit to just "
                        "print the answers and stop.")
    p.add_argument("--max-tokens", type=int, default=1024)
    args = p.parse_args(argv)

    using_demo = args.models is None and args.prompt is None
    if using_demo:
        models = _parse_models(DEFAULT_MODELS)
        prompt = DEFAULT_PROMPT
        acceptable = DEFAULT_ACCEPTABLE
        print("(no input given -- running the demonstration default: a simple classify task across a "
              "cheap, a mid, and a flagship model. As an EXAMPLE we mark all three acceptable (a simple "
              "task even a cheap model handles). Watch the cheapest acceptable save most of the cost. "
              "YOU decide what is good enough for your own task. Pass --models / --prompt to use your own.)\n")
    else:
        if args.models is None or args.prompt is None:
            print("error: --models and --prompt are required (or pass no arguments for the demo default)",
                  file=sys.stderr)
            return 2
        models = _parse_models(args.models)
        prompt = args.prompt
        acceptable = _parse_acceptable(args.acceptable)

    try:
        result = right_size_core(prompt=prompt, models=models, max_tokens=args.max_tokens)
    except ModelCountError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_runs(result))

    if acceptable is None:
        print("\n(no --acceptable given: read the answers above, then re-run with "
              "--acceptable <numbers> to see the cheapest of the ones you judge good enough.)")
        return 0

    print()
    decision = cheapest_of_acceptable(result, acceptable)
    print(format_decision(result, decision))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
