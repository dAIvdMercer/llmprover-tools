"""Cost Table -- CLI.

Tell it the input and output token counts for a typical run of your workload (and, optionally, how
many runs per month) and it prints what that workload costs on every model in a dated price
snapshot, cheapest first. Pure arithmetic: it makes NO provider calls and needs NO API key.

Run it with NO arguments and it uses a curated demonstration default (a realistic 1,500-input /
500-output-token workload at 100,000 runs/month) so the first run is instructive out of the box: you
see the same workload span from tens of dollars a month to thousands, purely by model choice.
Overwrite the defaults freely with your own numbers.

  # run the demonstration default (realistic workload + monthly projection):
  python cost_table.py

  # cost one run across every model in the snapshot:
  python cost_table.py --input-tokens 1200 --output-tokens 400

  # project a monthly bill at 50,000 runs/month:
  python cost_table.py --input-tokens 1200 --output-tokens 400 --runs-per-month 50000

  # only cost specific models:
  python cost_table.py --input-tokens 1200 --output-tokens 400 --models gpt-4o-mini,claude-haiku-5-5

It does NOT recommend a model -- it ranks by cost only. Choosing the cheapest model that is still
good enough for your task needs a quality judgment, which is the paid product.
"""

from __future__ import annotations

import argparse
import sys

from cost_table_core import TokenCountError, cost_table_core, format_result

# Demonstration default (Step 1b): a realistic workload pre-filled so a no-argument run is
# instructive out of the box. The lesson is pure arithmetic -- the same workload costs vastly
# different amounts across models -- which never ages in a publish-once artifact. These live in the
# CLI wrapper defaults, not in cost_table_core; the user overwrites them with any flag.
DEFAULT_INPUT_TOKENS = 1500
DEFAULT_OUTPUT_TOKENS = 500
DEFAULT_RUNS_PER_MONTH = 100000


def _parse_models(raw):
    if not raw:
        return None
    return [m.strip() for m in raw.split(",") if m.strip()]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Cost one workload run across models from a dated price snapshot "
                    "(cost arithmetic only, no recommendation). With no arguments, runs a curated "
                    "demonstration default."
    )
    p.add_argument("--input-tokens", type=int, default=None,
                   help=f"Input/prompt tokens in a typical run (default demo: {DEFAULT_INPUT_TOKENS}).")
    p.add_argument("--output-tokens", type=int, default=None,
                   help=f"Output/completion tokens in a typical run (default demo: {DEFAULT_OUTPUT_TOKENS}).")
    p.add_argument("--runs-per-month", type=int, default=None,
                   help="Expected runs per month; when set, also shows projected monthly cost "
                        f"(default demo: {DEFAULT_RUNS_PER_MONTH}).")
    p.add_argument("--models", default=None,
                   help="Optional comma-separated model ids to cost. Default: every model in the snapshot.")
    args = p.parse_args(argv)

    # If the user gave neither token count, run the curated demonstration default so the first run
    # teaches the lesson (the bill swings wildly by model) instead of erroring on an empty box.
    using_demo = args.input_tokens is None and args.output_tokens is None
    input_tokens = args.input_tokens if args.input_tokens is not None else DEFAULT_INPUT_TOKENS
    output_tokens = args.output_tokens if args.output_tokens is not None else DEFAULT_OUTPUT_TOKENS
    runs_per_month = args.runs_per_month
    if using_demo and runs_per_month is None:
        runs_per_month = DEFAULT_RUNS_PER_MONTH

    if using_demo:
        print("(no workload given -- running the demonstration default: a realistic "
              f"{input_tokens}-input / {output_tokens}-output-token workload at {runs_per_month} "
              "runs/month. Pass --input-tokens / --output-tokens to use your own.)\n")

    try:
        result = cost_table_core(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            runs_per_month=runs_per_month,
            models=_parse_models(args.models),
        )
    except TokenCountError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
