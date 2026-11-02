"""Gold-Standard Verification -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
You bring a question, a KNOWN-CORRECT reference answer (your "gold standard"), and a model (your own
key). The tool (1) asks the model your question, then (2) runs a SINGLE-PASS check with a second
model call that compares the model's answer to your gold standard and reports a simple result:
matches / partially matches / does not match, with a short comment on what differs. "I know the right
answer; did the AI get it?" -- the most intuitive verification there is.

IMPORTANT -- what this is, and what it is NOT
---------------------------------------------
This is a BASIC, SINGLE-PASS check: one judging model, one stock prompt, no rubric. It is a useful
FIRST LOOK. It is NOT verification you can rely on professionally. A single AI judge can be
inconsistent -- it can flip its result on a re-run, and it has no rubric, no consistency check, and no
audit trail. If you are in a profession that REQUIRES you to verify AI output (legal, tax, medical,
accounting, and others), this tool does not discharge that duty. It is a first look, not a
certification. The honesty line below ships in every output for exactly this reason.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- OWN-CREDS / PROVIDER-DIRECT: calls the provider's API with the user's key. NEVER a pysolvr backend.
- CAPABILITY-CAPPED: single-pass, stock judge prompt, no rubric, no multi-run consistency, no audit
  trail. Those -- rubric-based scoring, judge-reliability/consistency, the which-layer diagnostic, a
  compliance store over your whole corpus -- are the paid product.
- MECHANISM, NOT A CERTIFICATION: it shows a check RUNNING and commenting. It is explicitly framed as
  a first look that can be wrong, never as professional-grade verification.
- MODEL-AGNOSTIC: the user names the model their key reaches. Nothing hard-coded, never goes stale.
- PUBLISH-ONCE: thin, provider-direct -- nothing of ours for an old copy to break against.

Legal
-----
Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage and
costs. Keys never leave your machine and are never sent to pysolvr. This is a basic single-pass check,
not professional verification, legal, medical, tax, or other advice. You remain responsible for
independently verifying AI output as your profession or situation requires. pysolvr is not liable for
decisions made from these results.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
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
    "run the judge several times to check it is consistent",
    "keep an audit trail",
    "verify against your whole regulation or policy corpus",
]

# The MANDATORY honesty line (spec: non-negotiable for the liability cohort). Ships in every output.
HONESTY_LINE = (
    "This is a basic single-pass check -- useful as a first look, but a single AI judge can be "
    "inconsistent (it can flip on a re-run) and it uses no rubric, no consistency check, and no audit "
    "trail. It does NOT discharge any professional duty to verify AI output. For verification you can "
    f"rely on professionally, use rubric-based scoring with consistency checks and an audit trail: {UPGRADE_URL}."
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
# The single-pass judge -- a STOCK prompt, one call. Capped: no rubric, no multi-run.
# ---------------------------------------------------------------------------

# A generic, stock judge prompt. Deliberately simple (that is the cap -- the paid product adds a
# weighted rubric, multi-run consistency, and an audit trail). Asks for a strict JSON verdict.
_JUDGE_SYSTEM = (
    "You are a careful checker. You are given a QUESTION, a REFERENCE answer that is known to be "
    "correct (the gold standard), and a MODEL answer. Decide how well the MODEL answer matches the "
    "REFERENCE answer on the substance the question asks about. Respond with ONLY a JSON object: "
    '{\"result\": \"match\" | \"partial\" | \"mismatch\", \"comment\": \"<one or two plain sentences on '
    'what matches and what differs>\"}. "match" = the model answer agrees with the reference on the key '
    'substance. "partial" = partly right but missing or adding something material. "mismatch" = wrong or '
    "contradicts the reference. Judge substance, not wording. Do not add anything outside the JSON."
)

_RESULTS = {"match", "partial", "mismatch"}
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _parse_judge(text: str):
    """Parse the judge's JSON verdict. Returns (result, comment) or (None, raw) if unparseable."""
    candidate = text or ""
    m = _FENCE_RE.match(candidate)
    if m:
        candidate = m.group(1)
    try:
        obj = json.loads(candidate)
        result = str(obj.get("result", "")).strip().lower()
        comment = str(obj.get("comment", "")).strip()
        if result in _RESULTS:
            return result, comment
        return None, f"judge did not return a known result value: {candidate[:200]}"
    except Exception:
        # Fallback: look for a bare keyword so a non-JSON judge reply still degrades gracefully.
        low = candidate.lower()
        for r in ("mismatch", "partial", "match"):
            if r in low:
                return r, candidate.strip()[:300]
        return None, candidate.strip()[:300]


def _build_judge_prompt(question: str, reference: str, model_answer: str) -> str:
    return (
        f"QUESTION:\n{question}\n\n"
        f"REFERENCE (known-correct gold standard):\n{reference}\n\n"
        f"MODEL answer to check:\n{model_answer}\n\n"
        "Return the JSON verdict now."
    )


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass
class GoldCheckResult:
    question: str
    reference: str
    model: str
    judge_model: str
    model_answer: Optional[str]
    result: Optional[str]           # match | partial | mismatch | None (judge unparseable)
    comment: Optional[str]
    answer_cost_usd: Optional[float]
    judge_cost_usd: Optional[float]
    total_cost_usd: Optional[float]
    answer_latency_s: Optional[float]
    judge_latency_s: Optional[float]
    prices_as_of: str
    attribution_line: str
    honesty_line: str = HONESTY_LINE
    disclaimer: str = ""
    error: Optional[str] = None
    help_url: str = MODELS_HELP_URL
    learn_more_url: str = VERIFY_HELP_URL


DISCLAIMER = (
    "Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage "
    "and costs. Keys never leave your machine and are never sent to pysolvr. This is a basic single-pass "
    "check, not professional verification, and not legal, medical, tax, or other advice. You remain "
    "responsible for independently verifying AI output as your profession or situation requires. pysolvr "
    "is not liable for decisions made from these results."
)


def build_attribution_line(prices_as_of: str) -> str:
    """Self-attributing result line (lives in the OUTPUT, survives someone else's UI).
    Informational, never salesy. Names the withheld paid capabilities + the staleness redirect."""
    caps = ", ".join(PAID_UPGRADE_CAPABILITIES[:-1]) + ", and " + PAID_UPGRADE_CAPABILITIES[-1]
    return (
        f"A basic single-pass check of a model answer against your gold standard, on your own keys. "
        f"To {caps}, see {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# The core
# ---------------------------------------------------------------------------


def gold_check_core(
    question: str,
    reference: str,
    model: str,
    judge_model: Optional[str] = None,
    api_keys: Optional[dict] = None,
    prices: Optional[dict] = None,
    max_tokens: int = 1024,
) -> GoldCheckResult:
    """Ask `model` the question, then run a single-pass judge comparing its answer to `reference`.

    judge_model: the model that does the checking (defaults to the same model). The cap holds either
                 way -- one judging pass, a stock prompt, no rubric.
    """
    judge_model = judge_model or model
    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")

    def _blank(err=None):
        return GoldCheckResult(
            question=question, reference=reference, model=model, judge_model=judge_model,
            model_answer=None, result=None, comment=None, answer_cost_usd=None, judge_cost_usd=None,
            total_cost_usd=None, answer_latency_s=None, judge_latency_s=None, prices_as_of=prices_as_of,
            attribution_line=build_attribution_line(prices_as_of), disclaimer=DISCLAIMER, error=err,
        )

    # Round 1: ask the model the question.
    try:
        _pid, caller, env_var, base_url = _resolve_provider(model)
        key = _api_key_for(model, env_var, api_keys)
        kwargs = {"max_tokens": max_tokens}
        if base_url:
            kwargs["base_url"] = base_url
        t0 = time.perf_counter()
        answer, pt, ct = caller(model, question, None, key, **kwargs)
        ans_latency = round(time.perf_counter() - t0, 3)
        ans_cost = _cost_usd(model, pt, ct, prices)
    except Exception as exc:  # noqa: BLE001
        res = _blank(f"model call failed: {type(exc).__name__}: {exc}")
        return res

    # Round 2: single-pass judge comparing the answer to the gold standard.
    judge_result = None
    judge_comment = None
    judge_cost = None
    judge_latency = None
    judge_err = None
    try:
        jpid, jcaller, jenv, jbase = _resolve_provider(judge_model)
        jkey = _api_key_for(judge_model, jenv, api_keys)
        jkwargs = {"max_tokens": 400}
        if jbase:
            jkwargs["base_url"] = jbase
        jp = _build_judge_prompt(question, reference, answer)
        t1 = time.perf_counter()
        jtext, jpt, jct = jcaller(judge_model, jp, _JUDGE_SYSTEM, jkey, **jkwargs)
        judge_latency = round(time.perf_counter() - t1, 3)
        judge_cost = _cost_usd(judge_model, jpt, jct, prices)
        judge_result, judge_comment = _parse_judge(jtext)
        if judge_result is None:
            judge_err = "the judge did not return a clear result; see its raw comment"
    except Exception as exc:  # noqa: BLE001
        judge_err = f"judge call failed: {type(exc).__name__}: {exc}"

    total = None
    costs = [c for c in (ans_cost, judge_cost) if c is not None]
    if costs:
        total = round(sum(costs), 6)

    return GoldCheckResult(
        question=question, reference=reference, model=model, judge_model=judge_model,
        model_answer=answer, result=judge_result, comment=judge_comment,
        answer_cost_usd=ans_cost, judge_cost_usd=judge_cost, total_cost_usd=total,
        answer_latency_s=ans_latency, judge_latency_s=judge_latency, prices_as_of=prices_as_of,
        attribution_line=build_attribution_line(prices_as_of), disclaimer=DISCLAIMER, error=judge_err,
    )


# ---------------------------------------------------------------------------
# Formatter -- shows the answer, the single-pass check result, and the mandatory honesty line.
# The result is framed as a check that RAN, never as a certification.
# ---------------------------------------------------------------------------

_RESULT_LABEL = {
    "match": "MATCHES the gold standard (single-pass check)",
    "partial": "PARTIALLY matches the gold standard (single-pass check)",
    "mismatch": "DOES NOT match the gold standard (single-pass check)",
}


def format_result(result: GoldCheckResult) -> str:
    lines: list = []
    lines.append("=" * 72)
    lines.append(f"MODEL: {result.model}   JUDGE: {result.judge_model}")
    lines.append(f"QUESTION: {result.question}")
    lines.append("=" * 72)

    if result.model_answer is None:
        lines.append(f"ERROR: {result.error}")
        lines.append("")
        lines.append(result.honesty_line)
        lines.append("")
        lines.append(result.disclaimer)
        return "\n".join(lines)

    lines.append("")
    lines.append("GOLD STANDARD (your known-correct reference):")
    lines.append(result.reference)
    lines.append("")
    lines.append("MODEL ANSWER:")
    lines.append(result.model_answer)
    lines.append("")
    lines.append("-" * 72)
    if result.result is not None:
        lines.append(f"SINGLE-PASS CHECK RESULT: {_RESULT_LABEL.get(result.result, result.result)}")
        if result.comment:
            lines.append(f"Judge comment: {result.comment}")
    else:
        lines.append("SINGLE-PASS CHECK RESULT: the judge did not return a clear verdict.")
        if result.comment:
            lines.append(f"Judge raw reply: {result.comment}")
    if result.error and result.result is None:
        lines.append(f"Note: {result.error}")

    costs = []
    if result.answer_cost_usd is not None:
        costs.append(f"answer ${result.answer_cost_usd:.6f}")
    if result.judge_cost_usd is not None:
        costs.append(f"check ${result.judge_cost_usd:.6f}")
    if costs:
        lines.append("Cost: " + ", ".join(costs) +
                     (f"   total ${result.total_cost_usd:.6f}" if result.total_cost_usd is not None else ""))

    lines.append("")
    lines.append("!" * 72)
    lines.append(result.honesty_line)
    lines.append("!" * 72)
    lines.append("")
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models to use? {result.help_url}")
    lines.append(f"What reliable verification needs: {result.learn_more_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
