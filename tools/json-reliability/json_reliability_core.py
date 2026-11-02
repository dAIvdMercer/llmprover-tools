"""JSON / Structured-Output Reliability -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
Fire the SAME request at ONE model N times (your own key) and measure how reliably it returns valid,
schema-matching JSON. You get, per run: did it parse as JSON, did it match your schema, and the raw
text; and an aggregate SCHEMA PASS RATE (e.g. "7 of 10 runs produced valid matching JSON"). The
thing agent and tool builders keep getting burned by: a model that returns good JSON most of the
time still breaks a pipeline on the run that does not.

This is "how reliably does this model produce the structured output my code depends on?" -- measured
mechanically. It is NOT a quality score. It does not say the JSON is correct, well-designed, or
better than another model's. It counts parses and schema matches. Nothing is sent anywhere but the
provider you call with your own key.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- OWN-CREDS / PROVIDER-DIRECT: calls the provider's API with the user's key. NEVER a pysolvr backend.
- CAPABILITY-CAPPED, NOT QUALITY-CAPPED: it does its one job (measure parse + schema reliability) well.
- NO VERDICT: it reports pass/fail counts and a pass rate. It does NOT score whether the JSON content
  is correct, whether the schema is well-designed, or which model is better. Scored reliability, the
  which-layer diagnostic, drift tracking, and silent-model-swap canaries are the paid product.
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
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants + stable links
# ---------------------------------------------------------------------------

UPGRADE_URL = "https://llmprover.pysolvr.com"
PRICING_URL = "https://llmprover.pysolvr.com/api-pricing/"
MODELS_HELP_URL = "https://llmprover.pysolvr.com/models/"
RELIABILITY_HELP_URL = "https://llmprover.pysolvr.com/guides/scoring-guide/"

# The paid capabilities this free tool withholds, named plainly for the result line.
PAID_UPGRADE_CAPABILITIES = [
    "score structured-output reliability across your workload",
    "catch a silent model swap with a canary",
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
# JSON extraction + schema validation -- mechanical checks, NOT a quality judgment.
# ---------------------------------------------------------------------------

# Strips a ```json ... ``` (or bare ```) fence if the model wrapped its output in one. Many models
# do this even when asked for raw JSON, so stripping it is part of a fair parse check, not leniency
# about correctness.
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _strip_fence(text: str) -> str:
    m = _FENCE_RE.match(text or "")
    return m.group(1) if m else (text or "")


def _try_parse_json(text: str):
    """Return (parsed_obj, None) on success or (None, error_message). Mechanical: did it parse?"""
    candidate = _strip_fence(text)
    try:
        return json.loads(candidate), None
    except Exception as exc:  # noqa: BLE001
        return None, f"not valid JSON: {type(exc).__name__}: {exc}"


def _validate_schema(obj, schema: Optional[dict]):
    """Return (ok, error_message). Uses jsonschema if available; else a structural fallback that
    checks declared `required` keys and top-level `type`. Mechanical pass/fail, never a verdict on
    whether the content is correct."""
    if not schema:
        return True, None
    try:
        import jsonschema  # type: ignore

        try:
            jsonschema.validate(instance=obj, schema=schema)
            return True, None
        except jsonschema.ValidationError as exc:
            return False, f"schema mismatch: {exc.message}"
    except ImportError:
        # Fallback: no jsonschema installed. Do a minimal structural check so the tool still runs.
        return _fallback_schema_check(obj, schema)


def _fallback_schema_check(obj, schema: dict):
    """Minimal structural check when jsonschema is not installed: top-level type + required keys."""
    expected_type = schema.get("type")
    _JSON_TYPES = {
        "object": dict, "array": list, "string": str,
        "number": (int, float), "integer": int, "boolean": bool, "null": type(None),
    }
    if expected_type and expected_type in _JSON_TYPES:
        if not isinstance(obj, _JSON_TYPES[expected_type]):
            return False, f"schema mismatch (fallback check): top level is not a JSON {expected_type}"
    if schema.get("type", "object") == "object" and isinstance(obj, dict):
        missing = [k for k in schema.get("required", []) if k not in obj]
        if missing:
            return False, f"schema mismatch (fallback check): missing required key(s): {', '.join(missing)}"
    return True, None


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    index: int
    response: Optional[str] = None
    parsed_ok: bool = False
    schema_ok: bool = False
    detail: Optional[str] = None  # error message when a check failed
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_s: Optional[float] = None
    error: Optional[str] = None  # provider/key error (the call itself failed)

    @property
    def passed(self) -> bool:
        return self.parsed_ok and self.schema_ok and self.error is None


@dataclass
class ReliabilityResult:
    model: str
    prompt: str
    system: Optional[str]
    has_schema: bool
    runs: list  # list[RunResult]
    pass_count: int
    total_runs: int
    total_cost_usd: Optional[float]
    prices_as_of: str
    attribution_line: str
    label: Optional[str] = None  # optional label for this batch (used by the demo default)
    disclaimer: str = ""
    help_url: str = MODELS_HELP_URL
    learn_more_url: str = RELIABILITY_HELP_URL

    @property
    def pass_rate(self) -> float:
        return round(self.pass_count / self.total_runs, 4) if self.total_runs else 0.0


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
        f"Structured-output reliability measured by schema pass rate via your own keys. "
        f"{caps} at {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# The core
# ---------------------------------------------------------------------------


def json_reliability_core(
    prompt: str,
    model: str,
    runs: int = 5,
    schema: Optional[dict] = None,
    system: Optional[str] = None,
    label: Optional[str] = None,
    api_keys: Optional[dict] = None,
    prices: Optional[dict] = None,
    max_tokens: int = 1024,
) -> ReliabilityResult:
    """Fire the same request N times and measure the schema pass rate. No verdict.

    prompt:  the user request (should ask for JSON output).
    runs:    how many times to fire it (capped at MAX_RUNS).
    schema:  optional JSON Schema (dict). When given, each response must parse AND validate to pass.
             When None, a response passes if it merely parses as JSON.
    system:  optional system prompt (this is where a 'loose' vs 'strict' instruction lives -- the
             demo default varies THIS, holding the user prompt constant).
    label:   optional human label for this batch (e.g. "loose instruction"), used in the output.
    """
    if runs < 1:
        raise RunCountError("Need at least 1 run.")
    if runs > MAX_RUNS:
        raise RunCountError(
            f"This free tool runs a request up to {MAX_RUNS} times (a quick reliability look). "
            f"Requested {runs}. Bulk and scheduled reliability testing, scored reliability, and "
            f"silent-model-swap canaries are the paid product at {UPGRADE_URL}."
        )

    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")

    def _run(index: int) -> RunResult:
        res = RunResult(index=index)
        try:
            _pid, caller, env_var, base_url = _resolve_provider(model)
            key = _api_key_for(model, env_var, api_keys)
            kwargs = {"max_tokens": max_tokens}
            if base_url:
                kwargs["base_url"] = base_url
            t0 = time.perf_counter()
            text, pt, ct = caller(model, prompt, system, key, **kwargs)
            res.latency_s = round(time.perf_counter() - t0, 3)
            res.response = text
            res.prompt_tokens = pt
            res.completion_tokens = ct
            res.cost_usd = _cost_usd(model, pt, ct, prices)
            parsed, parse_err = _try_parse_json(text)
            if parse_err:
                res.parsed_ok = False
                res.detail = parse_err
            else:
                res.parsed_ok = True
                ok, schema_err = _validate_schema(parsed, schema)
                res.schema_ok = ok
                if not ok:
                    res.detail = schema_err
        except Exception as exc:  # noqa: BLE001 -- surface any provider/SDK/key error per run
            res.error = f"{type(exc).__name__}: {exc}"
        return res

    with ThreadPoolExecutor(max_workers=min(runs, 5)) as pool:
        results = list(pool.map(_run, range(runs)))
    results.sort(key=lambda r: r.index)

    pass_count = sum(1 for r in results if r.passed)
    costs = [r.cost_usd for r in results if r.cost_usd is not None]
    total_cost = round(sum(costs), 6) if costs else None

    return ReliabilityResult(
        model=model,
        prompt=prompt,
        system=system,
        has_schema=schema is not None,
        runs=results,
        pass_count=pass_count,
        total_runs=len(results),
        total_cost_usd=total_cost,
        prices_as_of=prices_as_of,
        attribution_line=build_attribution_line(prices_as_of),
        label=label,
        disclaimer=DISCLAIMER,
    )


# ---------------------------------------------------------------------------
# Formatters -- the pass rate + per-run checks are the output. No verdict.
# ---------------------------------------------------------------------------


def _format_run_line(r: RunResult) -> str:
    if r.error:
        return f"--- Run {r.index + 1}: CALL FAILED -- {r.error}"
    parse = "parsed" if r.parsed_ok else "NOT JSON"
    schema = "schema OK" if r.schema_ok else ("schema FAIL" if r.parsed_ok else "schema n/a")
    status = "PASS" if r.passed else "FAIL"
    cost = f"${r.cost_usd:.6f}" if r.cost_usd is not None else "n/a"
    line = f"--- Run {r.index + 1}: {status}  ({parse}, {schema})  cost {cost}  {r.latency_s}s"
    if r.detail and not r.passed:
        line += f"\n      {r.detail}"
    return line


def format_result(result: ReliabilityResult) -> str:
    """Plain-text render of ONE batch. Attribution line + disclaimer are part of the output."""
    lines: list = []
    lines.append("=" * 72)
    head = f"MODEL: {result.model}   RUNS: {result.total_runs}"
    if result.label:
        head = f"[{result.label}]  " + head
    lines.append(head)
    lines.append(f"SCHEMA: {'yes (parse + schema match required)' if result.has_schema else 'no (parse-only check)'}")
    lines.append("=" * 72)
    for r in result.runs:
        lines.append(_format_run_line(r))
    lines.append("-" * 72)
    lines.append(
        f"SCHEMA PASS RATE: {result.pass_count} of {result.total_runs} runs produced valid "
        f"{'matching ' if result.has_schema else ''}JSON  ({result.pass_rate:.0%}). "
        f"This is a mechanical count, not a quality score."
    )
    if result.total_cost_usd is not None:
        lines.append(f"Total cost this batch: ${result.total_cost_usd:.6f}")
    lines.append("")
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models to use? {result.help_url}")
    lines.append(f"Why reliability needs more than one pass: {result.learn_more_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)


def format_comparison(batches: list) -> str:
    """Render SEVERAL batches side by side (used by the loose-vs-strict demo default). Shows each
    batch's runs + pass rate, then a mechanical summary of the pass rates. NO verdict: it reports
    the numbers and lets the reader see that the stricter instruction parsed more reliably."""
    if not batches:
        return "(no batches to show)"
    lines: list = []
    for b in batches:
        lines.append(format_result(b))
        lines.append("")
    lines.append("=" * 72)
    lines.append("SUMMARY (pass rates side by side -- mechanical counts, not a quality verdict):")
    for b in batches:
        tag = b.label or b.model
        lines.append(f"  {tag:<28} {b.pass_count}/{b.total_runs}  ({b.pass_rate:.0%})")
    lines.append("=" * 72)
    return "\n".join(lines)
