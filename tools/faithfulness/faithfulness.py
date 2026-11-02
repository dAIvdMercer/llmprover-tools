"""Context-Faithfulness Check -- CLI.

Paste a source (a policy, regulation clause, contract section, any ground-truth) and ask a question.
The tool has the model answer using that source, then runs one lightweight pass that reads the answer
against the source and comments on faithfulness: does every claim trace to the source, did it add
anything the source does not say, does it contradict the source. It is a READ to help your review,
never a compliance verdict. Keys are read from environment variables (never a flag/file).

This is a basic first-look read, not professional verification. A single pass can be inconsistent.
Every run prints that honestly; read it.

Run it with NO arguments and it uses a curated demonstration default so you can watch the read RUN on
a real source and answer. Overwrite the defaults with your own source, question, and model.

  # run the demonstration default (watch the faithfulness read run):
  python faithfulness.py

  # your own (paste source inline or from a file):
  python faithfulness.py --model gpt-5 \
      --question "Can an employee carry unused leave into next year?" \
      --source-file leave_policy.txt

Set the key env var for your model's provider:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from faithfulness_core import faithfulness_core, format_result

# Demonstration default (Step 1b; verification-family: show the MECHANISM, never "watch it pass").
# A short source stating specific rules, and a question whose natural answer tends to ADD a detail the
# source does not state (carryover), so the read visibly flags an unsupported addition. The point is
# "watch the read run and surface something", not a certified pass. Durable: it is about the
# faithfulness-reading mechanism, not any model's current quirk. Lives in the CLI wrapper defaults.
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_QUESTION = "Can an employee carry unused annual leave into the next year, and how is leave paid out on exit?"
DEFAULT_SOURCE = (
    "Annual Leave Policy. Full-time employees receive 20 days of paid annual leave per calendar year. "
    "Leave is booked at least two weeks in advance and approved by the employee's manager."
)


def _read(path, inline):
    if inline is not None:
        return inline
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Read an AI answer for faithfulness to a pasted source (a review aid, NOT a "
                    "compliance verdict). With no arguments, runs a curated demonstration default."
    )
    p.add_argument("--model", default=None, help="Model to answer the question (provider inferred).")
    p.add_argument("--question", default=None, help="The question to ask, answered using your source.")
    p.add_argument("--source", default=None, help="The source / ground-truth text, inline.")
    p.add_argument("--source-file", default=None, help="Read the source from this file.")
    p.add_argument("--judge-model", default=None, help="Model that does the faithfulness read (defaults to --model).")
    p.add_argument("--max-tokens", type=int, default=1024)
    args = p.parse_args(argv)

    source = _read(args.source_file, args.source)

    using_demo = args.model is None and args.question is None and source is None
    if using_demo:
        model = DEFAULT_MODEL
        question = DEFAULT_QUESTION
        source = DEFAULT_SOURCE
        print("(no input given -- running the demonstration default. Watch the faithfulness read RUN: "
              "the model answers using a short pasted policy, then a single pass reads that answer "
              "against the policy and flags anything it added or contradicted. This shows the "
              "MECHANISM; it is a review aid, not a certified pass. Pass --model / --question / "
              "--source to use your own.)\n")
    else:
        if args.model is None or args.question is None or source is None:
            print("error: --model, --question, and --source (or --source-file) are all required "
                  "(or pass no arguments for the demo default)", file=sys.stderr)
            return 2
        model = args.model
        question = args.question

    result = faithfulness_core(
        source=source, question=question, model=model,
        judge_model=args.judge_model, max_tokens=args.max_tokens,
    )
    print(format_result(result))
    return 1 if (result.answer is None) else 0


if __name__ == "__main__":
    raise SystemExit(main())
