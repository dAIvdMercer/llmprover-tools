"""Compliance Scoring -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
You paste your REFERENCE documentation (the rules / standard / policy you must meet) and your DRAFT
(a clause, a policy, a marketing claim, a filing -- your OWN work product, whether or not AI wrote
it). The tool runs a single lightweight pass that reads your draft against your reference and reports:
which points in the draft are supported by the reference, which are NOT found in it, and where the
draft appears to CONTRADICT it, with a coarse mechanical count ("3 of 4 checked points traced to your
reference"). It is a review aid, a read to help you check your own work, NOT a compliance
certification.

Unlike the verification tools, this does not run any model to generate an answer. It scores an
artifact you ALREADY HAVE against documentation you supply. Useful even if no AI was involved: "does
my draft comply with these rules?"

IMPORTANT -- a read, NOT a certification
----------------------------------------
This COMMENTS on how your draft lines up with your reference; it never CERTIFIES compliance. It will
never tell you a draft is "compliant" or "approved". It is a single lightweight pass that can be
inconsistent and can miss things. It is a first look to guide YOUR review, not a substitute for it,
and it does not discharge any professional duty. The honesty line ships in every output.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- OWN-CREDS / PROVIDER-DIRECT: calls the provider's API with the user's key. NEVER a pysolvr backend.
  Reference + draft are pasted text in the prompt. No embeddings, no vector store, no retrieval.
- CAPABILITY-CAPPED: ONE lightweight judge, a basic prompt, QUALITATIVE commentary + a coarse count.
  It NEVER emits a compliance certification. Rubric-WEIGHTED scoring, the which-layer diagnostic,
  multi-run consistency, a compliance store over your whole corpus, and an audit trail are the paid
  product.
- INSTRUMENT, NOT ADVISOR: it helps your review; you own your compliance. (Same stance free and paid.)
- MODEL-AGNOSTIC: the user names the model their key reaches. Nothing hard-coded, never goes stale.
- PUBLISH-ONCE: thin, provider-direct -- nothing of ours for an old copy to break against.

Legal
-----
Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage and
costs. Keys never leave your machine and are never sent to pysolvr. This is a basic single-pass read,
not a compliance certification, and not legal, medical, tax, or other advice. You remain responsible
for your own compliance and for verifying this read as your profession or situation requires. pysolvr
is not liable for decisions made from these results.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants + stable links
# ---------------------------------------------------------------------------

UPGRADE_URL = "https://llmprover.pysolvr.com"
PRICING_URL = "https://llmprover.pysolvr.com/api-pricing/"
MODELS_HELP_URL = "https://llmprover.pysolvr.com/models/"
VERIFY_HELP_URL = "https://llmprover.pysolvr.com/guides/scoring-guide/"

# The paid capabilities this free tool withholds, named plainly for the result line.
PAID_UPGRADE_CAPABILITIES = [
    "score against a weighted rubric",
    "run the check several times to confirm it is consistent",
    "see which requirement each point meets or misses",
    "check your draft against your whole regulation or policy corpus",
    "keep an audit trail",
]

# The MANDATORY honesty line (spec: non-negotiable for the liability cohort). Ships in every output.
HONESTY_LINE = (
    "This is a basic single-pass READ to help you review your own draft -- not a compliance "
    "certification. A single lightweight check can be inconsistent (it can change on a re-run) and can "
    "miss things. It uses no weighted rubric, no consistency check, and no audit trail, and it does "
    "NOT certify compliance or discharge any professional duty. You own your compliance; this is an "
    f"instrument to assist your review. For compliance checking you can rely on, see {UPGRADE_URL}."
)


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
# The single-pass read -- basic prompt, one call. Comment + a coarse count, NEVER a certification.
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = (
    "You help someone review their OWN draft against reference documentation (rules, a standard, a "
    "policy). You are given the REFERENCE and the DRAFT. Break the draft into its key checkable points "
    "and, for each, say whether the REFERENCE supports it, does not mention it, or contradicts it. Do "
    "NOT decide whether the draft is 'compliant' or 'approved' -- that is not your job and not "
    "something a single read can establish. Judge only against the reference text provided. Respond "
    "with ONLY a JSON object: {\"points\": [{\"point\": \"<a claim/requirement in the draft>\", "
    "\"status\": \"supported\" | \"not_in_reference\" | \"contradicts\", \"detail\": \"<short note, "
    "cite the part of the reference>\"}], \"note\": \"<one or two plain sentences for the reviewer>\"}. "
    "Keep points concise and material. This is a read to help a human review, not a verdict or a "
    "certification."
)

_STATUSES = {"supported", "not_in_reference", "contradicts"}
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _build_judge_prompt(reference: str, draft: str) -> str:
    return (
        f"REFERENCE (the rules / standard / policy to check against):\n{reference}\n\n"
        f"DRAFT (the user's own work product to review):\n{draft}\n\n"
        "Return the JSON read now."
    )


def _parse_judge(text: str):
    """Parse the per-point read. Returns (points, note, raw). points is a list of dicts with
    point/status/detail; raw is set (and points empty) if unparseable. Never raises."""
    candidate = text or ""
    m = _FENCE_RE.match(candidate)
    if m:
        candidate = m.group(1)
    try:
        obj = json.loads(candidate)
        points = []
        for p in obj.get("points", []):
            status = str(p.get("status", "")).strip().lower()
            if status not in _STATUSES:
                status = "unknown"
            points.append({
                "point": str(p.get("point", "")).strip(),
                "status": status,
                "detail": str(p.get("detail", "")).strip(),
            })
        note = str(obj.get("note", "")).strip()
        return points, note, None
    except Exception:
        return [], "", (text or "").strip()[:400]


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass
class ComplianceResult:
    reference: str
    draft: str
    judge_model: str
    points: list = field(default_factory=list)  # list of {point, status, detail}
    note: str = ""
    judge_raw: Optional[str] = None
    supported_count: int = 0
    total_points: int = 0
    cost_usd: Optional[float] = None
    prices_as_of: str = "unknown"
    attribution_line: str = ""
    honesty_line: str = HONESTY_LINE
    disclaimer: str = ""
    error: Optional[str] = None
    help_url: str = MODELS_HELP_URL
    learn_more_url: str = VERIFY_HELP_URL


DISCLAIMER = (
    "Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage "
    "and costs. Keys never leave your machine and are never sent to pysolvr. This is a basic "
    "single-pass read, not a compliance certification, and not legal, medical, tax, or other advice. "
    "You remain responsible for your own compliance and for verifying this read as your profession or "
    "situation requires. pysolvr is not liable for decisions made from these results."
)


def build_attribution_line(prices_as_of: str) -> str:
    """Self-attributing result line (lives in the OUTPUT, survives someone else's UI).
    Informational, never salesy. Names the withheld paid capabilities + the staleness redirect."""
    caps = ", ".join(PAID_UPGRADE_CAPABILITIES[:-1]) + ", and " + PAID_UPGRADE_CAPABILITIES[-1]
    return (
        f"A basic single-pass read of your own draft against your pasted reference, on your own keys. A "
        f"read to help your review, not a certification. To {caps}, see {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# The core
# ---------------------------------------------------------------------------


def compliance_score_core(
    reference: str,
    draft: str,
    judge_model: str,
    api_keys: Optional[dict] = None,
    prices: Optional[dict] = None,
    max_tokens: int = 700,
) -> ComplianceResult:
    """Run a single-pass read of `draft` against `reference`. Per-point commentary + a coarse count.
    No model-answer round -- this scores an artifact the user already has. Never a certification."""
    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")

    def _shell(**kw):
        base = dict(reference=reference, draft=draft, judge_model=judge_model,
                    prices_as_of=prices_as_of,
                    attribution_line=build_attribution_line(prices_as_of), disclaimer=DISCLAIMER)
        base.update(kw)
        return ComplianceResult(**base)

    try:
        pid, caller, env_var, base_url = _resolve_provider(judge_model)
        key = _api_key_for(judge_model, env_var, api_keys)
        kwargs = {"max_tokens": max_tokens}
        if base_url:
            kwargs["base_url"] = base_url
        jp = _build_judge_prompt(reference, draft)
        text, pt, ct = caller(judge_model, jp, _JUDGE_SYSTEM, key, **kwargs)
        cost = _cost_usd(judge_model, pt, ct, prices)
    except Exception as exc:  # noqa: BLE001
        return _shell(error=f"check call failed: {type(exc).__name__}: {exc}")

    points, note, raw = _parse_judge(text)
    supported = sum(1 for p in points if p["status"] == "supported")
    err = None
    if not points and raw:
        err = "the read could not be parsed into points; see its raw reply"

    return _shell(
        points=points, note=note, judge_raw=raw, supported_count=supported,
        total_points=len(points), cost_usd=cost, error=err,
    )


# ---------------------------------------------------------------------------
# Formatter -- per-point read + a coarse count + the mandatory honesty line.
# Framed as notes to help a human review, never a compliance certification.
# ---------------------------------------------------------------------------

_STATUS_MARK = {
    "supported": "supported by your reference",
    "not_in_reference": "NOT found in your reference",
    "contradicts": "appears to CONTRADICT your reference",
    "unknown": "unclear",
}


def format_result(result: ComplianceResult) -> str:
    lines: list = []
    lines.append("=" * 72)
    lines.append(f"COMPLIANCE READ (reader model: {result.judge_model})")
    lines.append("=" * 72)
    lines.append("")
    lines.append("REFERENCE (your rules / standard):")
    lines.append(result.reference.strip())
    lines.append("")
    lines.append("DRAFT (your own work product):")
    lines.append(result.draft.strip())
    lines.append("")
    lines.append("-" * 72)

    if result.error and not result.points:
        lines.append(f"The read could not be completed as structured points.")
        if result.judge_raw:
            lines.append(f"Raw reply: {result.judge_raw}")
        if result.error:
            lines.append(f"Note: {result.error}")
    else:
        lines.append("PER-POINT READ (notes to help your review -- not a verdict, not a certification):")
        for i, p in enumerate(result.points, 1):
            lines.append(f"  {i}. [{_STATUS_MARK.get(p['status'], p['status'])}] {p['point']}")
            if p["detail"]:
                lines.append(f"      {p['detail']}")
        if result.total_points:
            not_supported = result.total_points - result.supported_count
            lines.append("")
            lines.append(
                f"COARSE COUNT: {result.supported_count} of {result.total_points} checked points traced "
                f"to your reference; {not_supported} did not (not found or contradicting). This is a "
                f"mechanical count of this one read, not a compliance score or a pass/fail."
            )
        if result.note:
            lines.append(f"Reviewer note: {result.note}")

    if result.cost_usd is not None:
        lines.append(f"Cost: ${result.cost_usd:.6f}")

    lines.append("")
    lines.append("!" * 72)
    lines.append(result.honesty_line)
    lines.append("!" * 72)
    lines.append("")
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models to use? {result.help_url}")
    lines.append(f"What reliable compliance checking needs: {result.learn_more_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
