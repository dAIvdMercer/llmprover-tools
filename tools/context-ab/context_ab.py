"""Context A/B Tester -- CLI.

Ask one question of one model two ways, side by side, to see how pasted context changes the answer.
Keys are read from environment variables (never a flag/file). Keys stay on your machine.

  # with vs without context (default):
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


def _read(path: str | None, inline: str | None) -> str | None:
    if inline is not None:
        return inline
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Ask one model one question two ways (with/without context, or context A/B)."
    )
    p.add_argument("--model", required=True, help="Model id, e.g. gpt-5 (provider inferred).")
    p.add_argument("--question", required=True, help="The question to ask.")
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

    try:
        result = context_ab_core(
            question=args.question,
            model=args.model,
            mode=args.mode,
            context=_read(args.context_file, args.context),
            context_a=_read(args.context_a_file, args.context_a),
            context_b=_read(args.context_b_file, args.context_b),
            max_tokens=args.max_tokens,
        )
    except ModeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
