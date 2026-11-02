"""Cost Table -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
You tell it how many input and output tokens a typical run of your workload uses (and, optionally,
how many of those runs you expect per month). It prints what that workload would cost on every model
in a dated price snapshot, cheapest first, as a plain table: cost per run and projected monthly cost.
"What does this workload cost on each provider?" -- a finance question, answered with arithmetic.

This is the take-home twin of the live pricing table at llmprover.pysolvr.com/api-pricing/. It is
pure arithmetic over a static, dated price snapshot and the token counts you supply. It makes NO
calls to any provider and needs NO API key -- nothing is sent anywhere.

What it is NOT
--------------
It does NOT recommend a model. It will not tell you which model is cheapest-that-is-still-good-enough
for your task, because that needs a quality judgment (scored runs against a bar), and that judgment --
right-sizing across your real workload, the which-layer diagnostic, drift over time -- is the paid
product. This tool does the cost arithmetic only. The cheapest row is the cheapest row, not a
recommendation.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- CAPABILITY-CAPPED, NOT QUALITY-CAPPED: it does its one job (cost across models) genuinely well.
- NO VERDICT / NO RECOMMENDATION: it ranks by cost only. It does not say which model is good enough.
  That -- scored right-sizing across your workload, the diagnostic, drift -- is the paid product.
- MODEL-AGNOSTIC: it costs every model in the snapshot (or a subset you name). Nothing hard-coded.
- STATIC PRICE SNAPSHOT: prices come from a dated prices.json, never a live feed, so an old copy has
  nothing of ours to break against. A model not in the snapshot is reported as such, never guessed.
- PUBLISH-ONCE: pure arithmetic, no backend, no key. The only thing that can stale is the snapshot,
  which is dated and redirects to the live table.

Legal
-----
Free tool, provided as-is, no warranty. Prices are a dated snapshot and drift; verify against the
provider and the live table before relying on them. Outputs are informational, not advice. pysolvr
is not liable for decisions made from these results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants + stable links
# ---------------------------------------------------------------------------

UPGRADE_URL = "https://llmprover.pysolvr.com"
PRICING_URL = "https://llmprover.pysolvr.com/api-pricing/"
MODELS_HELP_URL = "https://llmprover.pysolvr.com/models/"
RIGHTSIZE_HELP_URL = "https://llmprover.pysolvr.com/guides/scoring-guide/"  # the knowledge-gap link

# The paid capabilities this free tool withholds, named plainly for the result line.
PAID_UPGRADE_CAPABILITIES = [
    "find the cheapest model that still passes your quality bar",
    "score it across your real workload",
    "track price and quality drift over time",
]


class TokenCountError(ValueError):
    """Raised when the supplied token counts or volume are invalid."""


# ---------------------------------------------------------------------------
# Prices -- static, stamped snapshot (stale-data-is-a-backlink principle).
# ---------------------------------------------------------------------------

_PRICES_PATH = Path(__file__).with_name("prices.json")


def load_prices(path: Path = _PRICES_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _cost_per_run(input_tokens: int, output_tokens: int, entry: dict) -> float:
    return round(
        (input_tokens / 1000.0) * entry["input"]
        + (output_tokens / 1000.0) * entry["output"],
        6,
    )


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass
class ModelCost:
    model: str
    input_price_per_1k: float
    output_price_per_1k: float
    cost_per_run: float
    cost_per_month: Optional[float] = None  # None when no monthly volume given


@dataclass
class CostTableResult:
    input_tokens: int
    output_tokens: int
    runs_per_month: Optional[int]
    rows: list  # list[ModelCost], cheapest first
    unpriced_models: list  # model ids present in the snapshot request but missing a price entry
    prices_as_of: str
    attribution_line: str
    disclaimer: str = ""
    help_url: str = MODELS_HELP_URL
    learn_more_url: str = RIGHTSIZE_HELP_URL
    unit: str = "USD per 1K tokens"


DISCLAIMER = (
    "Free tool, provided as-is, no warranty. Prices are a dated snapshot and drift. Verify against "
    "the provider and the live table before relying on them. This tool does cost arithmetic only. It "
    "does not recommend a model. Outputs are informational, not advice. pysolvr is not liable for "
    "decisions made from these results."
)


def build_attribution_line(prices_as_of: str) -> str:
    """Self-attributing result line (lives in the OUTPUT, survives someone else's UI).
    Informational, never salesy. Names the withheld paid capabilities + the staleness redirect."""
    caps = ", ".join(PAID_UPGRADE_CAPABILITIES[:-1]) + ", and " + PAID_UPGRADE_CAPABILITIES[-1]
    return (
        f"Workload cost compared across models, cheapest first. This is cost arithmetic only, not a "
        f"recommendation. To {caps}, see {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# The core
# ---------------------------------------------------------------------------


def cost_table_core(
    input_tokens: int,
    output_tokens: int,
    runs_per_month: Optional[int] = None,
    models: Optional[list] = None,
    prices: Optional[dict] = None,
) -> CostTableResult:
    """Compute the cost of one workload run across models. No recommendation, no verdict.

    input_tokens:   tokens in a typical run's prompt/input.
    output_tokens:  tokens in a typical run's completion/output.
    runs_per_month: optional expected runs per month; when given, each row also carries a projected
                    monthly cost. When None, only per-run cost is shown.
    models:         optional subset of model ids to cost. When None, every model in the snapshot is
                    costed. An id not found in the snapshot is reported in `unpriced_models`.
    """
    if input_tokens < 0 or output_tokens < 0:
        raise TokenCountError("Token counts must be zero or positive whole numbers.")
    if input_tokens == 0 and output_tokens == 0:
        raise TokenCountError(
            "Both token counts are zero, so every cost would be zero. Enter the input and output "
            "token counts for a typical run of your workload (a rough estimate is fine)."
        )
    if runs_per_month is not None and runs_per_month < 0:
        raise TokenCountError("Runs per month must be zero or a positive whole number.")

    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")
    snapshot = prices.get("models", {})

    requested = models if models else list(snapshot.keys())
    rows: list = []
    unpriced: list = []
    for model in requested:
        entry = snapshot.get(model)
        if not entry:
            unpriced.append(model)
            continue
        per_run = _cost_per_run(input_tokens, output_tokens, entry)
        per_month = round(per_run * runs_per_month, 4) if runs_per_month else None
        rows.append(
            ModelCost(
                model=model,
                input_price_per_1k=entry["input"],
                output_price_per_1k=entry["output"],
                cost_per_run=per_run,
                cost_per_month=per_month,
            )
        )

    rows.sort(key=lambda r: r.cost_per_run)

    return CostTableResult(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        runs_per_month=runs_per_month,
        rows=rows,
        unpriced_models=unpriced,
        prices_as_of=prices_as_of,
        attribution_line=build_attribution_line(prices_as_of),
        disclaimer=DISCLAIMER,
    )


def format_result(result: CostTableResult) -> str:
    """Plain-text render. Attribution line + disclaimer are part of the output."""
    lines: list = []
    lines.append("=" * 74)
    header = f"WORKLOAD: {result.input_tokens} input tokens / {result.output_tokens} output tokens per run"
    if result.runs_per_month:
        header += f"   x {result.runs_per_month} runs/month"
    lines.append(header)
    lines.append("=" * 74)
    lines.append("")

    if not result.rows:
        lines.append("No models from the price snapshot matched your request.")
    else:
        if result.runs_per_month:
            lines.append(f"{'MODEL':<34}{'COST/RUN':>14}{'COST/MONTH':>16}")
            lines.append("-" * 74)
            for r in result.rows:
                lines.append(f"{r.model:<34}{'$' + format(r.cost_per_run, '.6f'):>14}{'$' + format(r.cost_per_month, '.2f'):>16}")
        else:
            lines.append(f"{'MODEL':<34}{'COST/RUN':>14}")
            lines.append("-" * 48)
            for r in result.rows:
                lines.append(f"{r.model:<34}{'$' + format(r.cost_per_run, '.6f'):>14}")
        lines.append("")
        cheapest = result.rows[0]
        dearest = result.rows[-1]
        if cheapest.cost_per_run > 0 and cheapest is not dearest:
            factor = dearest.cost_per_run / cheapest.cost_per_run
            lines.append(
                f"Cheapest priced: {cheapest.model} (${cheapest.cost_per_run:.6f}/run). "
                f"Most expensive: {dearest.model} (${dearest.cost_per_run:.6f}/run), {factor:.1f}x more. "
                f"Cost only -- not a judgment of which is good enough for your task."
            )

    if result.unpriced_models:
        lines.append("")
        lines.append(
            "Not in the price snapshot (no cost shown): "
            + ", ".join(result.unpriced_models)
            + f". Add them to prices.json locally, or see the live table: {PRICING_URL}"
        )

    lines.append("")
    lines.append("-" * 74)
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models exist or what they cost? {result.help_url}")
    lines.append(f"Paying for more quality than you need? How right-sizing works: {result.learn_more_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
