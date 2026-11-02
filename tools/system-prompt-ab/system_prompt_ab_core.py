"""System-Prompt A/B -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
Hold ONE user prompt fixed and run it at ONE model under TWO (or more) different SYSTEM prompts,
using the USER'S OWN API key, so you can see how the system prompt (the standing instructions /
persona / guardrails) changes the answer, token cost, and latency, side by side. The classic
lesson: a vague, unbounded system prompt tends to cost more tokens and run slower than a tight,
bounded one that gets the same answer. You read the numbers and the answers; the tool draws no
conclusion.

This is "what does my system prompt cost me?" -- measured mechanically. It is NOT a quality score.
It does not say which system prompt is better or which answer is correct. Nothing is sent anywhere
but the provider you call with your own key.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- OWN-CREDS / PROVIDER-DIRECT: calls the provider's API with the user's key. NEVER a pysolvr backend.
- CAPABILITY-CAPPED, NOT QUALITY-CAPPED: it does its one job (system prompts side by side) well.
- NO VERDICT: returns responses + cost + latency only. Never a score, winner, or quality hint.
- MODEL-AGNOSTIC: the user names the model their key reaches. Nothing hard-coded, never goes stale.
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
PROMPT_HELP_URL = "https://llmprover.pysolvr.com/guides/scoring-guide/"

# The paid capabilities this free tool withholds, named plainly for the result line.
PAID_UPGRADE_CAPABILITIES = [
    "score which system prompt answers best",
    "test guardrails across your workload",
    "see which layer broke",
    "track drift over time",
]

# A run with more than this many system prompts is a paid capability (bulk testing), not a free
# quick look. The cap is on COUNT, not quality.
MAX_SYSTEMS = 5


class SystemCountError(ValueError):
    """Raised when the number of system prompts is outside the free range (2..MAX_SYSTEMS)."""


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
# Each takes (model, prompt, system, api_key) and returns (text, prompt_tokens, completion_tokens).
# ---------------------------------------------------------------------------


def _call_openai(model, prompt, system, api_key, **kw):
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=model, messages=messages)
    u = resp.usage
    return resp.choices[0].message.content, u.prompt_tokens, u.completion_tokens


def _call_anthropic(model, prompt, system, api_key, **kw):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    params = {
        "model": model,
        "max_tokens": kw.get("max_tokens", 1024),
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        params["system"] = system
    resp = client.messages.create(**params)
    text = "".join(getattr(b, "text", "") for b in resp.content)
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def _call_openai_compat(model, prompt, system, api_key, base_url, **kw):
    """Grok / Together / Groq / Gemini (OpenAI-compatible) via the openai SDK + base_url."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=model, messages=messages)
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
class SystemResult:
    index: int
    label: str
    system: str
    response: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_s: Optional[float] = None
    error: Optional[str] = None


@dataclass
class SystemPromptABResult:
    model: str
    user_prompt: str
    systems: list  # list[SystemResult]
    prices_as_of: str
    attribution_line: str
    disclaimer: str = ""
    help_url: str = MODELS_HELP_URL
    learn_more_url: str = PROMPT_HELP_URL


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
        f"One prompt run at one model under two or more system prompts via your own keys, with token "
        f"cost and latency side by side. {caps} at {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# The core
# ---------------------------------------------------------------------------


def system_prompt_ab_core(
    model: str,
    user_prompt: str,
    systems: list,
    labels: Optional[list] = None,
    api_keys: Optional[dict] = None,
    prices: Optional[dict] = None,
    max_tokens: int = 1024,
) -> SystemPromptABResult:
    """Run ONE user prompt at ONE model under 2..MAX_SYSTEMS system prompts. No verdict.

    model:       one model id (the user names it; model-agnostic).
    user_prompt: the single user message, held constant across all system prompts.
    systems:     2..MAX_SYSTEMS system-prompt strings, run concurrently.
    labels:      optional human labels per system prompt (e.g. "vague", "tight").
    """
    if not (user_prompt and user_prompt.strip()):
        raise SystemCountError("Give a user prompt to run under each system prompt.")
    cleaned = [s for s in systems if s is not None and str(s).strip()]
    if len(cleaned) < 2:
        raise SystemCountError(
            "System-Prompt A/B is a side-by-side: give at least 2 system prompts. "
            f"Score which answers best, and test guardrails across your workload, at {UPGRADE_URL}."
        )
    if len(cleaned) > MAX_SYSTEMS:
        raise SystemCountError(
            f"This free tool compares up to {MAX_SYSTEMS} system prompts at once (a quick look). "
            f"Requested {len(cleaned)}. Bulk testing, scored quality, and drift tracking over time "
            f"are the paid product at {UPGRADE_URL}."
        )

    if labels and len(labels) == len(cleaned):
        use_labels = list(labels)
    else:
        use_labels = [f"System {i + 1}" for i in range(len(cleaned))]

    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")

    def _run(spec) -> SystemResult:
        index, label, system = spec
        res = SystemResult(index=index, label=label, system=system)
        try:
            _pid, caller, env_var, base_url = _resolve_provider(model)
            key = _api_key_for(model, env_var, api_keys)
            kwargs = {"max_tokens": max_tokens}
            if base_url:
                kwargs["base_url"] = base_url
            t0 = time.perf_counter()
            text, pt, ct = caller(model, user_prompt, system, key, **kwargs)
            res.latency_s = round(time.perf_counter() - t0, 3)
            res.response = text
            res.prompt_tokens = pt
            res.completion_tokens = ct
            res.total_tokens = (pt or 0) + (ct or 0)
            res.cost_usd = _cost_usd(model, pt, ct, prices)
        except Exception as exc:  # noqa: BLE001 -- surface any provider/SDK/key error per system
            res.error = f"{type(exc).__name__}: {exc}"
        return res

    specs = [(i, use_labels[i], cleaned[i]) for i in range(len(cleaned))]
    with ThreadPoolExecutor(max_workers=min(len(specs), 5)) as pool:
        results = list(pool.map(_run, specs))
    results.sort(key=lambda r: r.index)

    return SystemPromptABResult(
        model=model,
        user_prompt=user_prompt,
        systems=results,
        prices_as_of=prices_as_of,
        attribution_line=build_attribution_line(prices_as_of),
        disclaimer=DISCLAIMER,
    )


# ---------------------------------------------------------------------------
# Formatter -- responses + cost + latency + a mechanical delta. No verdict.
# ---------------------------------------------------------------------------


def _truncate(text: str, limit: int = 300) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " ..."


def _delta_summary(results: list) -> Optional[str]:
    """Mechanical comparison of the lightest vs heaviest system prompt by token count + cost. This
    is arithmetic over token usage, NOT a statement about which system prompt is better."""
    priced = [r for r in results if r.error is None and r.total_tokens is not None]
    if len(priced) < 2:
        return None
    cheapest = min(priced, key=lambda r: r.total_tokens)
    dearest = max(priced, key=lambda r: r.total_tokens)
    if cheapest.index == dearest.index or dearest.total_tokens == 0 or cheapest.total_tokens == 0:
        return None
    tok_factor = dearest.total_tokens / cheapest.total_tokens
    light = f"Lightest: [{cheapest.label}] {cheapest.total_tokens} tokens"
    if cheapest.cost_usd is not None:
        light += f" (${cheapest.cost_usd:.6f})"
    heavy = f"Heaviest: [{dearest.label}] {dearest.total_tokens} tokens"
    if dearest.cost_usd is not None:
        heavy += f" (${dearest.cost_usd:.6f})"
    tail = f"The heaviest system prompt used {tok_factor:.1f}x the tokens of the lightest"
    if cheapest.cost_usd is not None and dearest.cost_usd and cheapest.cost_usd > 0:
        tail += f" and cost {dearest.cost_usd / cheapest.cost_usd:.1f}x as much"
    tail += ". Token and cost counts only, not a judgment of which answer is better."
    return f"{light}   {heavy}\n{tail}"


def format_result(result: SystemPromptABResult) -> str:
    """Plain-text side-by-side render. Attribution line + disclaimer are part of the output."""
    lines: list = []
    lines.append("=" * 72)
    lines.append(f"MODEL: {result.model}   SYSTEM PROMPTS: {len(result.systems)}")
    lines.append(f"USER PROMPT (held constant): {result.user_prompt}")
    lines.append("=" * 72)
    for r in result.systems:
        lines.append("")
        lines.append(f"--- [{r.label}] ---")
        lines.append(f"SYSTEM PROMPT: {_truncate(r.system)}")
        if r.error:
            lines.append(f"ERROR: {r.error}")
            continue
        cost = f"${r.cost_usd:.6f}" if r.cost_usd is not None else "n/a (model not in price snapshot)"
        lines.append(
            f"tokens: {r.prompt_tokens} in / {r.completion_tokens} out "
            f"({r.total_tokens} total)   cost: {cost}   latency: {r.latency_s}s"
        )
        lines.append("")
        lines.append(r.response or "")
    summary = _delta_summary(result.systems)
    lines.append("")
    lines.append("-" * 72)
    if summary:
        lines.append(summary)
        lines.append("")
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models to use? {result.help_url}")
    lines.append(f"How the system prompt drives cost: {result.learn_more_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
