"""Gold-Standard Verification -- CLI.

Bring a question, a known-correct reference answer (your gold standard), and a model (your own key).
The tool asks the model, then runs a single-pass check comparing its answer to your gold standard,
and reports matches / partial / mismatch with a short comment. Keys are read from environment
variables (never a flag/file). Keys stay on your machine.

This is a BASIC FIRST-LOOK check, not professional verification. A single AI judge can be
inconsistent. Every run prints that honestly; read it.

Run it with NO arguments and it uses a curated demonstration default so you can watch the check RUN
and comment on a real example. Overwrite the defaults with your own question, gold standard, and model.

  # run the demonstration default (watch the check run):
  python gold_check.py

  # your own:
  python gold_check.py --model gpt-5 \
      --question "What is our refund window?" \
      --reference "Refunds are accepted within 14 days of delivery." \
      --judge-model gpt-5

Set the key env var for your model's provider:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from gold_check_core import gold_check_core, format_result

# Demonstration default (Step 1b; verification-family: show the MECHANISM, never "watch it pass").
# A general-knowledge question whose gold standard is a SPECIFIC, non-obvious value, so the model's
# natural answer tends to differ and the single-pass check visibly flags a difference and comments.
# The point is "watch the check run and say something", not a certified pass. Durable: it is about
# the checking mechanism, not any model's current quirk. Lives in the CLI wrapper defaults.
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_QUESTION = "In how many days must a customer request a refund under our store policy?"
DEFAULT_REFERENCE = (
    "Under our store policy, a customer must request a refund within 14 days of delivery. Requests "
    "after 14 days are not eligible."
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
        description="Check a model's answer against a known-correct reference with a single-pass judge "
                    "(a basic first look, NOT professional verification). With no arguments, runs a "
                    "curated demonstration default."
    )
    p.add_argument("--model", default=None, help="Model to answer the question (provider inferred).")
    p.add_argument("--question", default=None, help="The question to ask the model.")
    p.add_argument("--reference", default=None, help="The known-correct reference answer (gold standard), inline.")
    p.add_argument("--reference-file", default=None, help="Read the gold standard from this file.")
    p.add_argument("--judge-model", default=None, help="Model that does the checking (defaults to --model).")
    p.add_argument("--max-tokens", type=int, default=1024)
    args = p.parse_args(argv)

    reference = _read(args.reference_file, args.reference)

    using_demo = args.model is None and args.question is None and reference is None
    if using_demo:
        model = DEFAULT_MODEL
        question = DEFAULT_QUESTION
        reference = DEFAULT_REFERENCE
        print("(no input given -- running the demonstration default. Watch the single-pass check RUN: "
              "the model answers, then a judge compares that answer to a specific gold standard and "
              "comments on how they differ. This shows the MECHANISM; it is a first look, not a "
              "certified pass. Pass --model / --question / --reference to use your own.)\n")
    else:
        if args.model is None or args.question is None or reference is None:
            print("error: --model, --question, and --reference (or --reference-file) are all required "
                  "(or pass no arguments for the demo default)", file=sys.stderr)
            return 2
        model = args.model
        question = args.question

    result = gold_check_core(
        question=question, reference=reference, model=model,
        judge_model=args.judge_model, max_tokens=args.max_tokens,
    )
    print(format_result(result))
    # Exit 0 even on a mismatch verdict: a mismatch is a normal result, not a tool error. Only a
    # hard model/judge call failure (no answer at all) is surfaced as a non-zero exit.
    return 1 if (result.model_answer is None) else 0


if __name__ == "__main__":
    raise SystemExit(main())
