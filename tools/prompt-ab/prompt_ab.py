"""Prompt A/B Diff -- CLI.

Fire two (or more) prompts at one model and see each response, token cost, and latency, side by
side. Keys are read from environment variables (never a flag/file). Keys stay on your machine.

Run it with NO arguments and it uses a curated demonstration default: a rambling, unbounded ask vs a
tight, structured ask for the same thing. You see the rambling one use more tokens, cost more, and
run slower, for the same answer. The lesson is the token and cost numbers, never a verdict.

  # run the demonstration default (rambling vs tight):
  python prompt_ab.py

  # your own two prompts at one model:
  python prompt_ab.py --model gpt-5 \
      --prompt "Summarize this in 3 bullets: ..." \
      --prompt "TL;DR in 3 bullets: ..."

Set the key env var for your model's provider:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from prompt_ab_core import PromptCountError, format_result, prompt_ab_core

# Demonstration default (Step 1b, FLAGSHIP): the same task asked two ways -- a rambling, unbounded
# prompt vs a tight, structured one. The rambling prompt tends to use more tokens, cost more, and
# run slower for the same answer. The lesson is entirely in token cost + latency (the safest cap),
# it is a durable arithmetic truth (more words in and out = more cost, not a model quirk), and the
# tool emits no verdict. These live in the CLI wrapper defaults, not in prompt_ab_core.
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_PROMPTS = [
    (
        "I was wondering if you could possibly help me out here, I have this situation where I need "
        "to let a customer know that their order is going to be a little bit late, and I want to be "
        "really nice and warm and apologetic about it, maybe explain that we care a lot, and just "
        "generally make them feel good even though it's late, so could you write something for me "
        "that does all of that in a friendly tone? Thanks so much, really appreciate it."
    ),
    "Write a friendly two-sentence apology to a customer for a late order.",
]
DEFAULT_LABELS = ["rambling / unbounded", "tight / structured"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Run two or more prompts at one model, side by side (token cost + latency, no "
                    "verdict). With no arguments, runs a curated demonstration default."
    )
    p.add_argument("--model", default=None, help="Model id, e.g. gpt-5 (provider inferred).")
    p.add_argument("--prompt", action="append", default=None,
                   help="A prompt. Repeat --prompt for each one (2 to 5).")
    p.add_argument("--label", action="append", default=None,
                   help="Optional label per prompt, in the same order as --prompt.")
    p.add_argument("--max-tokens", type=int, default=1024)
    args = p.parse_args(argv)

    # No model and no prompts -> run the flagship rambling-vs-tight demonstration default.
    using_demo = args.model is None and not args.prompt
    if using_demo:
        model = DEFAULT_MODEL
        prompts = DEFAULT_PROMPTS
        labels = DEFAULT_LABELS
        print("(no input given -- running the demonstration default: a rambling, unbounded ask vs a "
              "tight, structured ask for the same thing. Watch the rambling one use more tokens, "
              "cost more, and run slower. Pass --model / --prompt to use your own.)\n")
    else:
        if args.model is None:
            print("error: --model is required (or pass no arguments to run the demo default)", file=sys.stderr)
            return 2
        if not args.prompt or len(args.prompt) < 2:
            print("error: give at least two --prompt values (or pass no arguments for the demo default)",
                  file=sys.stderr)
            return 2
        model = args.model
        prompts = args.prompt
        labels = args.label

    try:
        result = prompt_ab_core(
            model=model, prompts=prompts, labels=labels, max_tokens=args.max_tokens,
        )
    except PromptCountError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
