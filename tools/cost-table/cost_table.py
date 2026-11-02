"""Cost Table -- CLI.

Tell it the input and output token counts for a typical run of your workload (and, optionally, how
many runs per month) and it prints what that workload costs on every model in a dated price
snapshot, cheapest first. Pure arithmetic: it makes NO provider calls and needs NO API key.

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


def _parse_models(raw):
    if not raw:
        return None
    return [m.strip() for m in raw.split(",") if m.strip()]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Cost one workload run across models from a dated price snapshot "
                    "(cost arithmetic only, no recommendation)."
    )
    p.add_argument("--input-tokens", type=int, required=True,
                   help="Input/prompt tokens in a typical run (a rough estimate is fine).")
    p.add_argument("--output-tokens", type=int, required=True,
                   help="Output/completion tokens in a typical run.")
    p.add_argument("--runs-per-month", type=int, default=None,
                   help="Optional expected runs per month. When set, also shows projected monthly cost.")
    p.add_argument("--models", default=None,
                   help="Optional comma-separated model ids to cost. Default: every model in the snapshot.")
    args = p.parse_args(argv)

    try:
        result = cost_table_core(
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens,
            runs_per_month=args.runs_per_month,
            models=_parse_models(args.models),
        )
    except TokenCountError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
