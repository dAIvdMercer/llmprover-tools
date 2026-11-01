"""Variance Tester -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
Ask ONE model the SAME prompt N times (your own key) and see how much the answer moves. Run them
at one temperature, or sweep a few, and look at the spread: the responses side by side, their
token cost and latency, and a MECHANICAL similarity measure (how much the wordings overlap). The
aha most people have not seen: ask the same thing five times and get five different answers.

This is "how consistent is this model, really?" -- measured honestly. It is NOT a quality score.
The tool does not say which answer is better, or whether any of them is correct. It shows you the
spread so you can decide whether this model is stable enough for your use.

The mechanical similarity is a plain token-overlap (Jaccard) number: 1.00 = identical wording,
0.00 = no shared words. It is arithmetic over the text, not a judgment. Nothing is sent anywhere
but the provider you call with your own key.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- OWN-CREDS / PROVIDER-DIRECT: calls the provider's API with the user's key. NEVER a pysolvr backend.
- CAPABILITY-CAPPED, NOT QUALITY-CAPPED: it does its one job (show the spread) genuinely well.
- NO VERDICT: it shows the responses + cost + latency + a mechanical similarity number. It does NOT
  score which answer is better, whether any is correct, or whether the model is "good enough". That
  judgment -- scored consistency, rubric-based scoring, the which-layer diagnostic, drift tracking
  over time, agent integration -- is the paid product.
- MODEL-AGNOSTIC: the user names the model their key reaches. Nothing hard-coded, never goes stale.
- PUBLISH-ONCE: thin, provider-direct, static price snapshot -- nothing of ours for an old copy to
  break against.

Legal
-----
Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage
and costs. Keys never leave your machine and are never sent to pysolvr. Outputs are informational,
not advice. pysolvr is not liable for decisions made from these results.
"""

from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants + stable links
# ---------------------------------------------------------------------------

UPGRADE_URL = "https://llmprover.com"
PRICING_URL = "https://llmprover.com/api-pricing/"
MODELS_HELP_URL = "https://llmprover.com/models/"
SCORING_HELP_URL = "https://llmprover.com/guides/scoring-guide/"  # the knowledge-gap content link

# The paid capabilities this free tool withholds, named plainly for the result line.
PAID_UPGRADE_CAPABILITIES = [
    "Score consistency across runs",
    "catch verdict flips with a reliability-checked judge",
    "see which layer broke",
    "track drift over time",
]

# A run with more than this many calls is a paid capability (bulk/scheduled reliability testing),
# not a free quick look. The cap is on CALL COUNT, not quality.
MAX_RUNS = 10


class RunCountError(ValueError):
    """Raised when the requested run count exceeds the free capability cap."""


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
# temperature is passed through where the provider supports it; omitted when None.
# ---------------------------------------------------------------------------


def _call_openai(model, prompt, api_key, temperature=None, **kw):
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    params = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if temperature is not None:
        params["temperature"] = temperature
    resp = client.chat.completions.create(**params)
    u = resp.usage
    return resp.choices[0].message.content, u.prompt_tokens, u.completion_tokens


def _call_anthropic(model, prompt, api_key, temperature=None, **kw):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    params = {
        "model": model,
        "max_tokens": kw.get("max_tokens", 1024),
        "messages": [{"role": "user", "content": prompt}],
    }
    if temperature is not None:
        params["temperature"] = temperature
    resp = client.messages.create(**params)
    text = "".join(getattr(b, "text", "") for b in resp.content)
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def _call_openai_compat(model, prompt, api_key, base_url, temperature=None, **kw):
    """Grok / Together / Groq / Gemini (OpenAI-compatible) via the openai SDK + base_url."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    params = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if temperature is not None:
        params["temperature"] = temperature
    resp = client.chat.completions.create(**params)
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
# Mechanical similarity -- arithmetic over the text, NOT a quality judgment.
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    union = ta | tb
    if not union:
        return 1.0
    return round(len(ta & tb) / len(union), 4)


def _pairwise_similarity(texts: list[str]) -> dict:
    """Mechanical overlap summary across the responses. No quality score.

    Returns mean / min / max pairwise Jaccard token overlap, plus whether every response was
    byte-identical. 1.0 = identical wording, 0.0 = no shared words.
    """
    clean = [t for t in texts if t]
    if len(clean) == 0:
        return {"pairs": 0, "mean": None, "min": None, "max": None, "all_identical": False, "responses": 0}
    if len(clean) < 2:
        return {"pairs": 0, "mean": None, "min": None, "max": None, "all_identical": True, "responses": len(clean)}
    sims = [_jaccard(a, b) for a, b in combinations(clean, 2)]
    return {
        "pairs": len(sims),
        "mean": round(sum(sims) / len(sims), 4),
        "min": min(sims),
        "max": max(sims),
        "all_identical": len(set(clean)) == 1,
        "responses": len(clean),
    }


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    index: int
    temperature: Optional[float] = None
    response: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_s: Optional[float] = None
    error: Optional[str] = None


@dataclass
class VarianceResult:
    model: str
    prompt: str
    runs: list[RunResult]
    similarity: dict
    total_cost_usd: Optional[float]
    prices_as_of: str
    attribution_line: str
    disclaimer: str = ""
    help_url: str = MODELS_HELP_URL
    learn_more_url: str = SCORING_HELP_URL
    temperatures: list = field(default_factory=list)


DISCLAIMER = (
    "Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your "
    "usage and costs. Keys never leave your machine and are never sent to pysolvr. Outputs are "
    "informational, not advice. pysolvr is not liable for decisions made from these results."
)


def build_attribution_line(prices_as_of: str) -> str:
    """Self-attributing result line (lives in the OUTPUT, survives someone else's UI).
    Informational, never salesy. Names the withheld paid capabilities + the staleness redirect."""
    caps = ", ".join(PAID_UPGRADE_CAPABILITIES[:-1]) + ", and " + PAID_UPGRADE_CAPABILITIES[-1]
    return (
        f"Same prompt run multiple times via your own keys, with a mechanical consistency read. "
        f"{caps} at {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# The core
# ---------------------------------------------------------------------------


def variance_core(
    prompt: str,
    model: str,
    runs: int = 5,
    temperatures: Optional[list] = None,
    api_keys: Optional[dict] = None,
    prices: Optional[dict] = None,
    max_tokens: int = 1024,
) -> VarianceResult:
    """Run the same prompt N times at one model and report the spread. No verdict.

    runs:         how many times to fire the prompt (capped at MAX_RUNS). Ignored if
                  `temperatures` is given (then one run per temperature).
    temperatures: optional list of temperatures to sweep; one run each, in order. When set, this
                  defines the run count (and is still capped at MAX_RUNS). When None, `runs`
                  identical calls are made at the provider default temperature.
    """
    if temperatures:
        call_specs = [(i, float(t)) for i, t in enumerate(temperatures)]
    else:
        call_specs = [(i, None) for i in range(runs)]

    if len(call_specs) < 1:
        raise RunCountError("Need at least 1 run.")
    if len(call_specs) > MAX_RUNS:
        raise RunCountError(
            f"This free tool runs a prompt up to {MAX_RUNS} times (a quick consistency look). "
            f"Requested {len(call_specs)}. Bulk and scheduled reliability testing, scored "
            f"consistency, and drift tracking over time are the paid product at {UPGRADE_URL}."
        )

    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")

    def _run(spec) -> RunResult:
        index, temperature = spec
        res = RunResult(index=index, temperature=temperature)
        try:
            # Resolve provider + key inside the call so a bad model / missing key degrades to a
            # per-run error (and still renders the result-line) rather than crashing the whole run.
            _pid, caller, env_var, base_url = _resolve_provider(model)
            key = _api_key_for(model, env_var, api_keys)
            kwargs = {"max_tokens": max_tokens, "temperature": temperature}
            if base_url:
                kwargs["base_url"] = base_url
            t0 = time.perf_counter()
            text, pt, ct = caller(model, prompt, key, **kwargs)
            res.latency_s = round(time.perf_counter() - t0, 3)
            res.response = text
            res.prompt_tokens = pt
            res.completion_tokens = ct
            res.cost_usd = _cost_usd(model, pt, ct, prices)
        except Exception as exc:  # noqa: BLE001 -- surface any provider/SDK/key error per run
            res.error = f"{type(exc).__name__}: {exc}"
        return res

    with ThreadPoolExecutor(max_workers=min(len(call_specs), 5)) as pool:
        results = list(pool.map(_run, call_specs))
    results.sort(key=lambda r: r.index)

    similarity = _pairwise_similarity([r.response for r in results if r.response])
    costs = [r.cost_usd for r in results if r.cost_usd is not None]
    total_cost = round(sum(costs), 6) if costs else None

    return VarianceResult(
        model=model,
        prompt=prompt,
        runs=results,
        similarity=similarity,
        total_cost_usd=total_cost,
        prices_as_of=prices_as_of,
        attribution_line=build_attribution_line(prices_as_of),
        disclaimer=DISCLAIMER,
        temperatures=list(temperatures) if temperatures else [],
    )


def _similarity_phrase(sim: dict) -> str:
    """Plain-English framing of the mechanical number. Measurement, not mockery, not a verdict."""
    if sim.get("responses", 0) == 0:
        return "No responses returned, so there is nothing to measure (check the per-run errors above)."
    if sim.get("responses", 0) < 2:
        return "Only one response returned, so there is no spread to measure. Run it more times."
    if sim.get("all_identical"):
        return "Every response was identical."
    mean = sim.get("mean")
    if mean is None:
        return "Not enough responses to measure spread."
    return (
        f"Mean wording overlap {mean:.2f} (min {sim['min']:.2f}, max {sim['max']:.2f}) across "
        f"{sim['pairs']} pair(s). 1.00 means identical wording, 0.00 means no shared words. "
        f"This is mechanical overlap, not a quality score."
    )


def format_result(result: VarianceResult) -> str:
    """Plain-text render. Attribution line + disclaimer are part of the output."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"MODEL: {result.model}   RUNS: {len(result.runs)}")
    if result.temperatures:
        lines.append(f"TEMPERATURES: {', '.join(str(t) for t in result.temperatures)}")
    lines.append(f"PROMPT: {result.prompt}")
    lines.append("=" * 70)
    for r in result.runs:
        lines.append("")
        temp = f" temp={r.temperature}" if r.temperature is not None else ""
        lines.append(f"--- Run {r.index + 1}{temp} ---")
        if r.error:
            lines.append(f"ERROR: {r.error}")
            continue
        cost = f"${r.cost_usd:.6f}" if r.cost_usd is not None else "n/a (model not in price snapshot)"
        lines.append(
            f"tokens: {r.prompt_tokens} in / {r.completion_tokens} out   "
            f"cost: {cost}   latency: {r.latency_s}s"
        )
        lines.append("")
        lines.append(r.response or "")
    lines.append("")
    lines.append("-" * 70)
    lines.append("CONSISTENCY (mechanical): " + _similarity_phrase(result.similarity))
    if result.total_cost_usd is not None:
        lines.append(f"Total cost this run: ${result.total_cost_usd:.6f}")
    lines.append("")
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models to use? {result.help_url}")
    lines.append(f"Why a single pass can be unreliable: {result.learn_more_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
