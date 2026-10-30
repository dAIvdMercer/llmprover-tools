"""Context A/B Tester -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
Ask ONE question of ONE model (your own key) TWO ways, side by side, so you can see how the
context you supply changes the answer. Two modes:

  mode "with-without"  (default): the SAME question answered COLD (no context) vs answered WITH
                        your pasted context. The aha: watch your document make the AI correct.
  mode "a-b"           : the same question answered with CONTEXT A vs CONTEXT B.

The "context" is just text you paste (a policy, a doc, ground-truth) -- it is prepended to your
question as grounding. This is how most people actually use context: paste it in the prompt. No
embeddings, no vector store, no retrieval -- so it is own-key, zero-backend, and publish-once.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- OWN-CREDS / PROVIDER-DIRECT: calls the provider's API with the user's key. NEVER a pysolvr backend.
- CAPABILITY-CAPPED, NOT QUALITY-CAPPED: it does its one job (show both answers) genuinely well.
- NO VERDICT: it shows both answers + cost + latency. It does NOT score which answer is more
  grounded / correct / faithful. That judgment -- scored grounding, the which-layer diagnostic, a
  persistent vector store, retrieval over thousands of docs -- is the paid product.
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
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants + stable links
# ---------------------------------------------------------------------------

UPGRADE_URL = "https://llmprover.com"
PRICING_URL = "https://llmprover.com/api-pricing/"
MODELS_HELP_URL = "https://llmprover.com/models/"
RAG_EVAL_URL = "https://llmprover.com/rag-evaluation/"  # the public twin (F3)

# The paid capabilities this free tool withholds, named plainly for the result line.
PAID_UPGRADE_CAPABILITIES = [
    "Score which answer is actually grounded",
    "see which layer broke",
    "test against a persistent store of thousands of docs",
    "track it over time",
]

VALID_MODES = ("with-without", "a-b")


class ModeError(ValueError):
    """Raised on an unknown mode or missing required context for the mode."""


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


def _build_prompt(question: str, context: Optional[str]) -> str:
    """Grounding is just pasted context prepended to the question (how most people use context)."""
    if not context:
        return question
    return (
        "Use ONLY the following context to answer the question. If the context does not contain "
        "the answer, say so.\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION:\n{question}"
    )


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass
class ArmResult:
    label: str                      # e.g. "Without context" / "With context" / "Context A"
    response: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_s: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ContextABResult:
    mode: str
    model: str
    question: str
    arms: list[ArmResult]
    prices_as_of: str
    attribution_line: str
    disclaimer: str = ""
    help_url: str = MODELS_HELP_URL


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
        f"Context A/B on your own keys. {caps} at {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# The core
# ---------------------------------------------------------------------------


def context_ab_core(
    question: str,
    model: str,
    mode: str = "with-without",
    context: Optional[str] = None,
    context_a: Optional[str] = None,
    context_b: Optional[str] = None,
    api_keys: Optional[dict] = None,
    prices: Optional[dict] = None,
    max_tokens: int = 1024,
) -> ContextABResult:
    """Ask one question of one model two ways, side by side. No verdict.

    mode "with-without": arm 1 = no context, arm 2 = `context`. (Supply `context`.)
    mode "a-b":          arm 1 = `context_a`, arm 2 = `context_b`. (Supply both.)
    """
    if mode not in VALID_MODES:
        raise ModeError(f"mode must be one of {VALID_MODES}, got {mode!r}.")

    if mode == "with-without":
        if not context:
            raise ModeError("mode 'with-without' needs `context` (the document to ground the answer).")
        arms_spec = [("Without context", None), ("With context", context)]
    else:  # a-b
        if not context_a or not context_b:
            raise ModeError("mode 'a-b' needs both `context_a` and `context_b`.")
        arms_spec = [("Context A", context_a), ("Context B", context_b)]

    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")

    def _run(spec) -> ArmResult:
        label, ctx = spec
        res = ArmResult(label=label)
        try:
            # Resolve provider + key inside the arm so a bad model / missing key degrades to a
            # per-arm error (and still renders the result-line) rather than crashing the whole run.
            _pid, caller, env_var, base_url = _resolve_provider(model)
            key = _api_key_for(model, env_var, api_keys)
            prompt = _build_prompt(question, ctx)
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
        except Exception as exc:  # noqa: BLE001 -- surface any provider/SDK/key error per arm
            res.error = f"{type(exc).__name__}: {exc}"
        return res

    with ThreadPoolExecutor(max_workers=2) as pool:
        arms = list(pool.map(_run, arms_spec))

    return ContextABResult(
        mode=mode,
        model=model,
        question=question,
        arms=arms,
        prices_as_of=prices_as_of,
        attribution_line=build_attribution_line(prices_as_of),
        disclaimer=DISCLAIMER,
    )


def format_result(result: ContextABResult) -> str:
    """Plain-text side-by-side render. Attribution line + disclaimer are part of the output."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"MODEL: {result.model}   MODE: {result.mode}")
    lines.append(f"QUESTION: {result.question}")
    lines.append("=" * 70)
    for a in result.arms:
        lines.append("")
        lines.append(f"--- {a.label} ---")
        if a.error:
            lines.append(f"ERROR: {a.error}")
            continue
        cost = f"${a.cost_usd:.6f}" if a.cost_usd is not None else "n/a (model not in price snapshot)"
        lines.append(
            f"tokens: {a.prompt_tokens} in / {a.completion_tokens} out   "
            f"cost: {cost}   latency: {a.latency_s}s"
        )
        lines.append("")
        lines.append(a.response or "")
    lines.append("")
    lines.append("-" * 70)
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models to use? {result.help_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
