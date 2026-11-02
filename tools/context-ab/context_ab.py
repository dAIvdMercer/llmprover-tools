"""Context A/B Tester -- CLI.

Ask one question of one model two ways, side by side, to see how pasted context changes the answer.
Keys are read from environment variables (never a flag/file). Keys stay on your machine.

Run it with NO arguments and it uses a curated demonstration default: an everyday policy question the
model tends to guess at cold, then answered again with a short policy pasted in. You read the two
answers and see for yourself how the pasted document changed the answer. The tool emits no verdict;
it just shows both answers side by side.

  # run the demonstration default (cold vs with a pasted policy):
  python context_ab.py

  # with vs without context:
  python context_ab.py --model gpt-5 --question "Can I expense a laptop?" \
      --context-file policy.txt

  # context A vs context B:
  python context_ab.py --model gpt-5 --question "What is the refund window?" \
      --mode a-b --context-a-file v1.txt --context-b-file v2.txt

Set the key env var for your model's provider:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from context_ab_core import ModeError, context_ab_core, format_result

# Demonstration default (Step 1b): an everyday policy question the model tends to answer wrong or
# hedge on cold, plus a short policy that settles it. Running cold-vs-with-context shows the user the
# cold answer waver and the grounded answer line up with the pasted rule. The LESSON IS WHAT THE USER
# SEES in the two answers -- the tool never declares which is right (that scored-grounding verdict is
# the paid product). Durable: it is about grounding mechanics, not any model's current quirk. Lives
# in the CLI wrapper defaults, not in context_ab_core.
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_QUESTION = "Can I expense a 1,200 USD laptop without getting approval first?"
DEFAULT_CONTEXT = (
    "Expense policy: Any single purchase over 1,000 USD requires written manager approval in "
    "advance. Purchases of 1,000 USD or less may be expensed without prior approval."
)


def _read(path: str | None, inline: str | None) -> str | None:
    if inline is not None:
        return inline
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Ask one model one question two ways (with/without context, or context A/B). "
                    "With no arguments, runs a curated demonstration default."
    )
    p.add_argument("--model", default=None, help="Model id, e.g. gpt-5 (provider inferred).")
    p.add_argument("--question", default=None, help="The question to ask.")
    p.add_argument("--mode", default="with-without", choices=["with-without", "a-b"],
                   help="with-without (default): cold vs with context. a-b: context A vs B.")
    p.add_argument("--context", help="(with-without) the context text inline.")
    p.add_argument("--context-file", help="(with-without) read context from this file.")
    p.add_argument("--context-a", help="(a-b) context A inline.")
    p.add_argument("--context-a-file", help="(a-b) read context A from this file.")
    p.add_argument("--context-b", help="(a-b) context B inline.")
    p.add_argument("--context-b-file", help="(a-b) read context B from this file.")
    p.add_argument("--max-tokens", type=int, default=1024)
    args = p.parse_args(argv)

    context = _read(args.context_file, args.context)
    context_a = _read(args.context_a_file, args.context_a)
    context_b = _read(args.context_b_file, args.context_b)

    # No model and no question -> run the curated with-vs-without demonstration default so the first
    # run shows the grounding effect instead of erroring on empty input.
    using_demo = args.model is None and args.question is None
    model = args.model if args.model is not None else DEFAULT_MODEL
    question = args.question if args.question is not None else DEFAULT_QUESTION
    mode = args.mode
    if using_demo:
        mode = "with-without"
        if context is None:
            context = DEFAULT_CONTEXT
        print("(no input given -- running the demonstration default: an everyday expense-policy "
              "question asked cold, then with a short policy pasted in. Read both answers and watch "
              "the pasted policy settle it. Pass --model / --question to use your own.)\n")

    try:
        result = context_ab_core(
            question=question,
            model=model,
            mode=mode,
            context=context,
            context_a=context_a,
            context_b=context_b,
            max_tokens=args.max_tokens,
        )
    except ModeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
