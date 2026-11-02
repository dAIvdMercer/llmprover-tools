"""Right-Size It -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
Run ONE prompt across several models (your own keys), see each model's response and cost, then YOU
mark which responses are "good enough" for your task. The tool does the trivial arithmetic: of the
ones YOU marked acceptable, here is the cheapest, and how much it saves versus the most expensive one
you accepted. The lesson: the cheapest model that is good enough for your task can cost a fraction of
the flagship.

The judgment is ALWAYS YOURS. The tool never decides which answer is good enough -- you do. It only
adds up cost over your selections. That keeps it honest and keeps the automated version (a judge that
scores acceptability across your whole workload, then picks cheapest) as the paid product.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- OWN-CREDS / PROVIDER-DIRECT: calls the provider's API with the user's key. NEVER a pysolvr backend.
- CAPABILITY-CAPPED, NOT QUALITY-CAPPED: it does its one job (run across models, cost-rank your
  acceptable set) genuinely well.
- NO VERDICT: the HUMAN marks which responses are acceptable. The tool NEVER scores quality or says
  which answer is better. It only does cost arithmetic over the human's marks. Automated scoring of
  acceptability across a whole workload, the which-layer diagnostic, and persistence are the paid
  product.
- MODEL-AGNOSTIC: the user names the models their key reaches. Nothing hard-coded, never goes stale.
- PUBLISH-ONCE: thin, provider-direct, static price snapshot -- nothing of ours for an old copy to
  break against.

Legal
-----
Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage and
costs. Keys never leave your machine and are never sent to pysolvr. Outputs are informational, not
advice. pysolvr is not liable for decisions made from these results.
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants + stable links
# ---------------------------------------------------------------------------

UPGRADE_URL = "https://llmprover.pysolvr.com"
PRICING_URL = "https://llmprover.pysolvr.com/api-pricing/"
MODELS_HELP_URL = "https://llmprover.pysolvr.com/models/"
RIGHTSIZE_HELP_URL = "https://llmprover.pysolvr.com/guides/scoring-guide/"

# The paid capabilities this free tool withholds, named plainly for the result line.
PAID_UPGRADE_CAPABILITIES = [
    "score which models clear your quality bar automatically",
    "right-size across your whole workload",
    "see which layer broke",
    "track drift over time",
]

# A run across more than this many models is a paid capability (bulk right-sizing), not a free quick
# look. The cap is on MODEL COUNT, not quality.
MAX_MODELS = 6
MIN_MODELS = 2


class ModelCountError(ValueError):
    """Raised when the number of models is outside the free range (2..MAX_MODELS)."""


# ---------------------------------------------------------------------------
# Prices -- static, stamped snapshot (stale-data-is-a-backlink principle).
# ---------------------------------------------------------------------------

_PRICES_PATH = Path(__file__).with_name("prices.json")


def load_prices(path: Path = _PRICES_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _cost_usd(model: str, prompt_tokens: int, completion_tokens: int, prices: dict) -> Optional[float]:
    entry = prices.get("models", {}).get(model)
    if not entry:
        return None
    return round(
        (prompt_tokens / 1000.0) * entry["input"]
        + (completion_tokens / 1000.0) * entry["output"],
        6,
    )


# ---------------------------------------------------------------------------
# Provider-direct calls -- the user's key, the provider's API, no pysolvr backend.
# Each returns (text, prompt_tokens, completion_tokens). Matched by model-id prefix.
# ---------------------------------------------------------------------------


def _call_openai(model, prompt, api_key, **kw):
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    u = resp.usage
    return resp.choices[0].message.content, u.prompt_tokens, u.completion_tokens


def _call_anthropic(model, prompt, api_key, **kw):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=kw.get("max_tokens", 1024),
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(getattr(b, "text", "") for b in resp.content)
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def _call_openai_compat(model, prompt, api_key, base_url, **kw):
    """Grok / Together / Groq / Gemini (OpenAI-compatible) via the openai SDK + base_url."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    u = resp.usage
    return resp.choices[0].message.content, u.prompt_tokens, u.completion_tokens


_PROVIDERS = [
    ("openai", lambda m: m.startswith(("gpt-", "o1", "o3", "o4", "chatgpt")), _call_openai, "OPENAI_API_KEY", None),
    ("anthropic", lambda m: m.startswith("claude"), _call_anthropic, "ANTHROPIC_API_KEY", None),
    ("google", lambda m: m.startswith("gemini"), _call_openai_compat, "GEMINI_API_KEY",
     "https://generativelanguage.googleapis.com/v1beta/openai/"),
    ("grok", lambda m: m.startswith("grok"), _call_openai_compat, "XAI_API_KEY", "https://api.x.ai/v1"),
    ("together", lambda m: "/" in m and not m.startswith("qwen/"), _call_openai_compat, "TOGETHER_API_KEY",
     "https://api.together.xyz/v1"),
    ("groq", lambda m: m.startswith("qwen/"), _call_openai_compat, "GROQ_API_KEY", "https://api.groq.com/openai/v1"),
]


def _resolve_provider(model: str):
    for pid, matches, caller, env_var, base_url in _PROVIDERS:
        if matches(model):
            return pid, caller, env_var, base_url
    raise ValueError(
        f"Could not infer a provider for model '{model}'. Supported prefixes: gpt-/o*, claude*, "
        f"gemini*, grok*, <together org>/<model>, qwen/*. Not sure which models to use? {MODELS_HELP_URL}"
    )


def _api_key_for(model: str, env_var: str, api_keys: Optional[dict]) -> str:
    if api_keys:
        if model in api_keys:
            return api_keys[model]
        if env_var in api_keys:
            return api_keys[env_var]
    key = os.environ.get(env_var)
    if not key:
        raise RuntimeError(
            f"No API key for model '{model}'. Set the {env_var} environment variable, or pass "
            f"api_keys={{'{model}': '<key>'}}. Your key stays on your machine and is never sent to pysolvr."
        )
    return key


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass
class ModelRun:
    index: int
    model: str
    response: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_s: Optional[float] = None
    error: Optional[str] = None


@dataclass
class RightSizeResult:
    prompt: str
    runs: list  # list[ModelRun], in the model order given
    prices_as_of: str
    attribution_line: str
    disclaimer: str = ""
    help_url: str = MODELS_HELP_URL
    learn_more_url: str = RIGHTSIZE_HELP_URL


DISCLAIMER = (
    "Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your "
    "usage and costs. Keys never leave your machine and are never sent to pysolvr. You decide which "
    "answers are good enough; the tool only adds up cost. Outputs are informational, not advice. "
    "pysolvr is not liable for decisions made from these results."
)


def build_attribution_line(prices_as_of: str) -> str:
    """Self-attributing result line (lives in the OUTPUT, survives someone else's UI).
    Informational, never salesy. Names the withheld paid capabilities + the staleness redirect."""
    caps = ", ".join(PAID_UPGRADE_CAPABILITIES[:-1]) + ", and " + PAID_UPGRADE_CAPABILITIES[-1]
    return (
        f"One prompt run across models on your own keys. You mark which answers are good enough; the "
        f"tool finds the cheapest of those. To {caps}, see {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# Step 1: run the prompt across the models (provider-direct).
# ---------------------------------------------------------------------------


def right_size_core(
    prompt: str,
    models: list,
    api_keys: Optional[dict] = None,
    prices: Optional[dict] = None,
    max_tokens: int = 1024,
) -> RightSizeResult:
    """Run ONE prompt across 2..MAX_MODELS models, returning each response + cost. No verdict.

    This is step 1 (gather). The user then marks which responses are acceptable and calls
    cheapest_of_acceptable() -- step 2 (the cost arithmetic). The tool never marks acceptability.
    """
    cleaned = [m.strip() for m in models if m and m.strip()]
    if len(cleaned) < MIN_MODELS:
        raise ModelCountError(
            f"Right-Size It compares at least {MIN_MODELS} models so you can pick the cheapest that "
            f"is good enough. Got {len(cleaned)}."
        )
    if len(cleaned) > MAX_MODELS:
        raise ModelCountError(
            f"This free tool runs across up to {MAX_MODELS} models (a quick by-hand right-sizing). "
            f"Requested {len(cleaned)}. Automated right-sizing across 20+ models and your whole "
            f"workload is the paid product at {UPGRADE_URL}."
        )

    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")

    def _run(spec) -> ModelRun:
        index, model = spec
        res = ModelRun(index=index, model=model)
        try:
            _pid, caller, env_var, base_url = _resolve_provider(model)
            key = _api_key_for(model, env_var, api_keys)
            kwargs = {"max_tokens": max_tokens}
            if base_url:
                kwargs["base_url"] = base_url
            t0 = time.perf_counter()
            text, pt, ct = caller(model, prompt, key, **kwargs)
            res.latency_s = round(time.perf_counter() - t0, 3)
            res.response = text
            res.prompt_tokens = pt
            res.completion_tokens = ct
            res.cost_usd = _cost_usd(model, pt, ct, prices)
        except Exception as exc:  # noqa: BLE001 -- surface any provider/SDK/key error per model
            res.error = f"{type(exc).__name__}: {exc}"
        return res

    specs = [(i, cleaned[i]) for i in range(len(cleaned))]
    with ThreadPoolExecutor(max_workers=min(len(specs), MAX_MODELS)) as pool:
        results = list(pool.map(_run, specs))
    results.sort(key=lambda r: r.index)

    return RightSizeResult(
        prompt=prompt,
        runs=results,
        prices_as_of=prices_as_of,
        attribution_line=build_attribution_line(prices_as_of),
        disclaimer=DISCLAIMER,
    )


# ---------------------------------------------------------------------------
# Step 2: the cost arithmetic over the human's acceptable marks. No verdict.
# ---------------------------------------------------------------------------


@dataclass
class CheapestOfAcceptable:
    accepted_indices: list
    accepted_models: list
    cheapest: Optional[ModelRun]
    dearest_accepted: Optional[ModelRun]
    savings_usd: Optional[float]
    savings_pct: Optional[float]
    note: Optional[str] = None


def cheapest_of_acceptable(result: RightSizeResult, accepted_indices: list) -> CheapestOfAcceptable:
    """Of the runs the USER marked acceptable, find the cheapest and how much it saves vs the most
    expensive one they accepted. Pure arithmetic over the human's selection -- NO quality judgment.
    accepted_indices are 1-based (as shown in the printed run list)."""
    by_index = {r.index + 1: r for r in result.runs}
    accepted = []
    for i in accepted_indices:
        r = by_index.get(i)
        if r is None:
            continue
        if r.error is not None or r.cost_usd is None:
            # Can't cost-rank a failed call or an unpriced model; skip it from the arithmetic.
            continue
        accepted.append(r)

    if not accepted:
        return CheapestOfAcceptable(
            accepted_indices=list(accepted_indices), accepted_models=[], cheapest=None,
            dearest_accepted=None, savings_usd=None, savings_pct=None,
            note="No acceptable runs with a known cost to compare. Mark at least one priced run as acceptable.",
        )

    cheapest = min(accepted, key=lambda r: r.cost_usd)
    dearest = max(accepted, key=lambda r: r.cost_usd)
    savings_usd = round(dearest.cost_usd - cheapest.cost_usd, 6)
    savings_pct = round((savings_usd / dearest.cost_usd) * 100, 1) if dearest.cost_usd > 0 else 0.0
    return CheapestOfAcceptable(
        accepted_indices=list(accepted_indices),
        accepted_models=[r.model for r in accepted],
        cheapest=cheapest,
        dearest_accepted=dearest,
        savings_usd=savings_usd,
        savings_pct=savings_pct,
    )


# ---------------------------------------------------------------------------
# Formatters -- responses + cost, then the cheapest-of-acceptable arithmetic. No verdict.
# ---------------------------------------------------------------------------


def format_runs(result: RightSizeResult) -> str:
    """Step 1 render: each model's response + cost, numbered so the user can mark acceptable ones."""
    lines: list = []
    lines.append("=" * 72)
    lines.append(f"PROMPT: {result.prompt}")
    lines.append("=" * 72)
    for r in result.runs:
        lines.append("")
        n = r.index + 1
        lines.append(f"--- [{n}] {r.model} ---")
        if r.error:
            lines.append(f"ERROR: {r.error}")
            continue
        cost = f"${r.cost_usd:.6f}" if r.cost_usd is not None else "n/a (model not in price snapshot)"
        lines.append(f"cost: {cost}   latency: {r.latency_s}s   "
                     f"tokens: {r.prompt_tokens} in / {r.completion_tokens} out")
        lines.append("")
        lines.append(r.response or "")
    lines.append("")
    lines.append("-" * 72)
    lines.append("Read the answers above and decide which ones are GOOD ENOUGH for your task. The tool")
    lines.append("does not judge quality -- you do. Then it finds the cheapest of the ones you marked.")
    return "\n".join(lines)


def format_decision(result: RightSizeResult, decision: CheapestOfAcceptable) -> str:
    """Step 2 render: the cost arithmetic over the human's acceptable marks + result-line + disclaimer."""
    lines: list = []
    lines.append("=" * 72)
    if decision.note:
        lines.append(decision.note)
    else:
        accepted = ", ".join(f"[{i}]" for i in decision.accepted_indices)
        lines.append(f"YOU MARKED ACCEPTABLE: {accepted}  ({', '.join(decision.accepted_models)})")
        c = decision.cheapest
        d = decision.dearest_accepted
        lines.append(f"CHEAPEST ACCEPTABLE: {c.model} at ${c.cost_usd:.6f} for this run.")
        if d and d.model != c.model and d.cost_usd and d.cost_usd > 0:
            lines.append(
                f"Most expensive you accepted: {d.model} at ${d.cost_usd:.6f}. "
                f"Picking the cheapest acceptable saves ${decision.savings_usd:.6f} per run "
                f"({decision.savings_pct:.0f}% less) for an answer you already called good enough."
            )
        else:
            lines.append("Only one acceptable priced model, so there is nothing cheaper to compare against yet.")
        lines.append("This is cost arithmetic over YOUR choices, not a judgment of which answer is better.")
    lines.append("=" * 72)
    lines.append("")
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models to use? {result.help_url}")
    lines.append(f"How right-sizing works: {result.learn_more_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
