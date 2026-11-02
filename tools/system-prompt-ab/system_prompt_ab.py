"""System-Prompt A/B -- CLI.

Hold one user prompt fixed and run it at one model under two (or more) different system prompts, to
see how the system prompt changes the answer, token cost, and latency, side by side. Keys are read
from environment variables (never a flag/file). Keys stay on your machine.

Run it with NO arguments and it uses a curated demonstration default: a vague, unbounded system
prompt vs a tight, bounded one, with the same user question. You see the vague one use more tokens
and cost more for the same answer. The lesson is the token and cost numbers, never a verdict.

  # run the demonstration default (vague vs tight system prompt):
  python system_prompt_ab.py

  # your own: one question under two system prompts:
  python system_prompt_ab.py --model gpt-5 \
      --prompt "How do I reset my password?" \
      --system "You are a helpful assistant." \
      --system "You are a support agent. Answer in at most 3 short steps. No preamble."

Set the key env var for your model's provider:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from system_prompt_ab_core import SystemCountError, format_result, system_prompt_ab_core

# Demonstration default (Step 1b, FLAGSHIP): the same user question under a vague, unbounded system
# prompt vs a tight, bounded one. The vague system prompt tends to produce a longer, costlier answer;
# the tight one answers the same thing in fewer tokens. The lesson is entirely in token cost +
# latency (the safest cap), it is a durable truth about instruction discipline (not a model quirk),
# and the tool emits no verdict. These live in the CLI wrapper defaults, not in the core.
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_PROMPT = "How do I reset my password?"
DEFAULT_SYSTEMS = [
    "You are a helpful assistant.",
    ("You are a support agent. Answer in at most 3 short numbered steps. No preamble, no sign-off, "
     "no extra explanation."),
]
DEFAULT_LABELS = ["vague / unbounded", "tight / bounded"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Run one prompt at one model under two or more system prompts, side by side "
                    "(token cost + latency, no verdict). With no arguments, runs a demonstration default."
    )
    p.add_argument("--model", default=None, help="Model id, e.g. gpt-5 (provider inferred).")
    p.add_argument("--prompt", default=None, help="The user prompt, held constant across system prompts.")
    p.add_argument("--system", action="append", default=None,
                   help="A system prompt. Repeat --system for each one (2 to 5).")
    p.add_argument("--label", action="append", default=None,
                   help="Optional label per system prompt, in the same order as --system.")
    p.add_argument("--max-tokens", type=int, default=1024)
    args = p.parse_args(argv)

    # No model, no prompt, no systems -> run the flagship vague-vs-tight demonstration default.
    using_demo = args.model is None and args.prompt is None and not args.system
    if using_demo:
        model = DEFAULT_MODEL
        user_prompt = DEFAULT_PROMPT
        systems = DEFAULT_SYSTEMS
        labels = DEFAULT_LABELS
        print("(no input given -- running the demonstration default: the same question under a vague, "
              "unbounded system prompt vs a tight, bounded one. Watch the vague one use more tokens "
              "and cost more. Pass --model / --prompt / --system to use your own.)\n")
    else:
        if args.model is None or args.prompt is None:
            print("error: --model and --prompt are required (or pass no arguments for the demo default)",
                  file=sys.stderr)
            return 2
        if not args.system or len(args.system) < 2:
            print("error: give at least two --system values (or pass no arguments for the demo default)",
                  file=sys.stderr)
            return 2
        model = args.model
        user_prompt = args.prompt
        systems = args.system
        labels = args.label

    try:
        result = system_prompt_ab_core(
            model=model, user_prompt=user_prompt, systems=systems, labels=labels,
            max_tokens=args.max_tokens,
        )
    except SystemCountError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
