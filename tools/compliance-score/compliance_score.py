"""Compliance Scoring -- CLI.

Paste your reference documentation (the rules / standard / policy) and your own draft (a clause,
policy, marketing claim, filing). The tool runs a single lightweight pass that reads your draft
against your reference and reports, per point, whether the reference supports it, is silent on it, or
contradicts it, plus a coarse count. It is a READ to help your review, never a compliance
certification. Keys are read from environment variables (never a flag/file).

This is a basic first-look read, not a certification. A single pass can be inconsistent. Every run
prints that honestly; read it.

Run it with NO arguments and it uses a curated demonstration default so you can watch the read RUN on
a real reference and draft. Overwrite the defaults with your own.

  # run the demonstration default (watch the compliance read run):
  python compliance_score.py

  # your own (paste inline or from files):
  python compliance_score.py --model gpt-5 \
      --reference-file policy.txt --draft-file my_clause.txt

Set the key env var for your model's provider:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from compliance_score_core import compliance_score_core, format_result

# Demonstration default (Step 1b; verification-family: show the MECHANISM, never "watch it pass").
# A short reference (a refund policy) and a draft (a returns notice) crafted so the read reliably
# surfaces a MIX: a supported point, a point not in the reference, and a point that contradicts it.
# The point is to watch the read break the draft into points and flag each -- the mechanism working,
# not a certified pass. Durable: it is about the reading mechanism over fixed text, not a model quirk.
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_REFERENCE = (
    "Refund Policy. Customers may request a refund within 14 days of delivery. Approved refunds are "
    "issued to the original payment method. Shipping charges are non-refundable."
)
DEFAULT_DRAFT = (
    "Returns notice: You can request a refund within 14 days of delivery. Refunds are given as store "
    "credit. We also refund your original shipping cost, and we offer free return shipping on all orders."
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
        description="Read your own draft against your reference documentation (a review aid, NOT a "
                    "compliance certification). With no arguments, runs a curated demonstration default."
    )
    p.add_argument("--model", default=None, help="Model that does the read (provider inferred).")
    p.add_argument("--reference", default=None, help="The reference rules / standard, inline.")
    p.add_argument("--reference-file", default=None, help="Read the reference from this file.")
    p.add_argument("--draft", default=None, help="Your draft (own work product), inline.")
    p.add_argument("--draft-file", default=None, help="Read the draft from this file.")
    p.add_argument("--max-tokens", type=int, default=700)
    args = p.parse_args(argv)

    reference = _read(args.reference_file, args.reference)
    draft = _read(args.draft_file, args.draft)

    using_demo = args.model is None and reference is None and draft is None
    if using_demo:
        model = DEFAULT_MODEL
        reference = DEFAULT_REFERENCE
        draft = DEFAULT_DRAFT
        print("(no input given -- running the demonstration default. Watch the read RUN: it breaks a "
              "sample returns-notice draft into points and checks each against a sample refund policy, "
              "flagging what is supported, what is not in the policy, and what contradicts it. This "
              "shows the MECHANISM; it is a review aid, not a certification. Pass --model / --reference "
              "/ --draft to use your own.)\n")
    else:
        if args.model is None or reference is None or draft is None:
            print("error: --model, --reference (or --reference-file), and --draft (or --draft-file) are "
                  "all required (or pass no arguments for the demo default)", file=sys.stderr)
            return 2
        model = args.model

    result = compliance_score_core(
        reference=reference, draft=draft, judge_model=model, max_tokens=args.max_tokens,
    )
    print(format_result(result))
    return 1 if (result.error and not result.points) else 0


if __name__ == "__main__":
    raise SystemExit(main())
