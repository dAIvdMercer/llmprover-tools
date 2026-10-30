"""Model Compare -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
Fires ONE prompt at exactly TWO user-specified models, using the USER'S OWN API keys,
and returns each model's response, token cost, and latency, side by side.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- OWN-CREDS / PROVIDER-DIRECT: calls the provider's API with the user's key. It NEVER
  calls a pysolvr/llmprover backend. Your keys stay on your machine.
- CAPABILITY-CAPPED, NOT QUALITY-CAPPED: it does its one job well and withholds the
  capabilities that ARE the paid product.
- TWO-MODEL CAP: exactly two models, enforced in ONE place (`_enforce_cap`). A head-to-head.
- NO VERDICT: returns responses + cost + latency only. Never a score, winner, or quality hint.
- MODEL-AGNOSTIC: the user names the models their key reaches. Nothing is hard-coded, so the
  tool never goes stale.
- PUBLISH-ONCE: frozen. Cost comes from a static, stamped prices.json snapshot, not a live
  feed, so there is nothing of ours for an old copy to break against.

Legal
-----
Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your
usage and costs. Keys never leave your machine and are never sent to pysolvr. Outputs are
informational, not advice. pysolvr is not liable for decisions made from these results.
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Capability cap -- exactly two models. Enforced in ONE place.
# ---------------------------------------------------------------------------

MODEL_CAP = 2
UPGRADE_URL = "https://llmprover.com"
PRICING_URL = "https://llmprover.com/api-pricing/"
MODELS_HELP_URL = "https://llmprover.com/models/"

# The paid capabilities this free tool withholds, named verbatim for the result line.
PAID_UPGRADE_CAPABILITIES = [
    "Compare 5-20 at once",
    "score which is best",
    "see which layer broke",
    "track drift over time",
]


class ModelCapError(ValueError):
    """Raised when more (or fewer) than two models are supplied."""


def _enforce_cap(models: list[str]) -> list[str]:
    """The single, authoritative capability-cap check. Every shape inherits it."""
    cleaned = [m.strip() for m in models if m and m.strip()]
    if len(cleaned) != MODEL_CAP:
        raise ModelCapError(
            f"Model Compare is a head-to-head: give exactly {MODEL_CAP} models "
            f"(got {len(cleaned)}). "
            f"Compare 5-20 at once, and score which is best, at {UPGRADE_URL}."
        )
    return cleaned


# ---------------------------------------------------------------------------
# Prices -- static, stamped snapshot (stale-data-is-a-backlink principle).
# ---------------------------------------------------------------------------

_PRICES_PATH = Path(__file__).with_name("prices.json")


def load_prices(path: Path = _PRICES_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _cost_usd(model: str, prompt_tokens: int, completion_tokens: int, prices: dict) -> Optional[float]:
    """Cost in USD from the static snapshot. None if the model is not in the snapshot."""
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
# Each returns (text, prompt_tokens, completion_tokens).
# Providers are matched by a simple prefix on the model id the user typed.
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


# provider id -> (matcher(model) -> bool, caller, env var, optional base_url)
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
        f"Could not infer a provider for model '{model}'. Supported prefixes: gpt-/o*, "
        f"claude*, gemini*, grok*, <together org>/<model>, qwen/*. Pass api_keys={{'{model}': 'sk-...'}} "
        f"and the matching provider base manually if your model uses a different id scheme. "
        f"Not sure which models to use? See {MODELS_HELP_URL}"
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
class ModelResult:
    model: str
    response: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_s: Optional[float] = None
    error: Optional[str] = None


@dataclass
class CompareResult:
    prompt: str
    results: list[ModelResult]
    prices_as_of: str
    attribution_line: str
    disclaimer: str = ""
    pricing_url: str = PRICING_URL
    help_url: str = MODELS_HELP_URL


DISCLAIMER = (
    "Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for "
    "your usage and costs. Keys never leave your machine and are never sent to pysolvr. Outputs "
    "are informational, not advice. pysolvr is not liable for decisions made from these results."
)


def build_attribution_line(prices_as_of: str) -> str:
    """The self-attributing result line. Informational, never salesy. Lives in the OUTPUT so it
    survives someone else's UI. Names the withheld paid capabilities + the staleness redirect."""
    caps = ", ".join(PAID_UPGRADE_CAPABILITIES[:-1]) + ", and " + PAID_UPGRADE_CAPABILITIES[-1]
    return (
        f"Head-to-head of 2 models via your own keys. {caps} at {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# The core
# ---------------------------------------------------------------------------


def compare_core(
    prompt: str,
    models: list[str],
    api_keys: Optional[dict] = None,
    prices: Optional[dict] = None,
    max_tokens: int = 1024,
) -> CompareResult:
    """Compare exactly two models on one prompt, provider-direct, with the user's own keys.

    Returns responses + token cost + latency side by side. No quality verdict.

    Parameters
    ----------
    prompt : the single prompt sent to both models.
    models : exactly two model ids (the user names them; model-agnostic).
    api_keys : optional {model_or_ENVVAR: key}. If omitted, keys are read from env vars
               (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY,
               TOGETHER_API_KEY, GROQ_API_KEY). Keys stay on your machine.
    prices : optional pre-loaded prices.json dict (defaults to the bundled snapshot).
    """
    models = _enforce_cap(models)
    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")

    def _run(model: str) -> ModelResult:
        res = ModelResult(model=model)
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
        except Exception as exc:  # noqa: BLE001 -- surface any provider/SDK error per model
            res.error = f"{type(exc).__name__}: {exc}"
        return res

    # Fan the two calls out concurrently (wall-clock latency per model).
    with ThreadPoolExecutor(max_workers=MODEL_CAP) as pool:
        results = list(pool.map(_run, models))

    return CompareResult(
        prompt=prompt,
        results=results,
        prices_as_of=prices_as_of,
        attribution_line=build_attribution_line(prices_as_of),
        disclaimer=DISCLAIMER,
    )


def format_result(result: CompareResult) -> str:
    """Plain-text side-by-side render. The attribution line + disclaimer are part of the output."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"PROMPT: {result.prompt}")
    lines.append("=" * 70)
    for r in result.results:
        lines.append("")
        lines.append(f"--- {r.model} ---")
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
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models to use? {result.help_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
