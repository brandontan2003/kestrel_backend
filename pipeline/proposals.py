"""Thesis-change proposals — the agent's suggested edits to a thesis.

The classifier (llm.py) judges whether the world matched the user's thesis. This
module judges the *thesis itself*: after a sweep, given what the evaluator found
and what the news said, should the thesis be re-worded, re-thresholded, or
pruned? Every suggestion is a proposal only — the user approves or rejects each
one by hand, and the host application persists nothing else.

Same shape as the rest of the package: pure functions over plain dicts, no DB,
no web. The host owns the loop and the persistence; this owns the judgment.

The guards live HERE, in code, after the model call — the prompt asks, the code
enforces (the same split as llm.py's anti-hallucination guards):
  guard 1: `target_id` on an update/remove must be a row the thesis actually has.
  guard 2: a quant `metric` must be one the caller says it can fetch, and the
           `operator` one the caller can compare — otherwise the condition would
           silently never resolve.
  guard 3: an update that changes nothing is dropped (a proposal the user can
           only rubber-stamp is noise).
  guard 4: an `add` that duplicates an existing catalyst is dropped.
  guard 5: a `source_article_index` is resolved to a URL against the articles we
           actually passed in — the model never emits a URL, so it can't invent one.
  guard 6: proposals below MIN_CONFIDENCE are dropped, and at most MAX_PROPOSALS
           survive per sweep (highest confidence first) — a queue nobody reads is
           worse than no queue.

Contract:  suggest(thesis, evaluation, catalyst_states, articles, metrics)
             -> list[Suggestion]
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Iterable, Literal, Any

from pydantic import BaseModel, Field

# The OpenAI call site, prompt loading and prompt versioning are llm.py's — one
# call site for the whole package. Package-private, deliberately reused rather
# than duplicated; llm.py imports the SDK lazily, so this stays import-safe.
from pipeline.llm import _call, _prompt, prompt_version
from pipeline.news import Article

log = logging.getLogger(__name__)

PROPOSE_MODEL = "gpt-5.4"  # judgment about the user's own thesis — worth the reasoning model
PROMPT_NAME = "propose_changes"

# Operators the evaluator can compare (mirrors the host's condition vocabulary).
OPERATORS = frozenset({"<", "<=", ">", ">=", "=="})

# A proposal the user would only rubber-stamp is worse than none: keep the bar
# high and the queue short. Tune against the real approve rate, not by taste.
MIN_CONFIDENCE = 0.5
MAX_PROPOSALS = 3

# The reviewer sees headline + body for each: an untracked material event is only
# spottable from the body ("cuts billions from revenue"), not a terse headline.
MAX_ARTICLES = 30


# --------------------------------------------------------------------------- #
# Output schemas. These ARE the LLM output contract — the API constrains the
# model to them via structured outputs, so no JSON parsing/regex anywhere.
# --------------------------------------------------------------------------- #
class _Proposal(BaseModel):
    """One suggested edit, as the model emits it."""
    target: Literal["quant", "catalyst"]
    action: Literal["add", "update", "remove"]
    target_id: str | None  # the row being changed; null for `add`
    metric: str | None  # quant add/update
    operator: str | None  # quant add/update
    value: float | None  # quant add/update
    description: str | None  # catalyst add/update
    source_article_index: int | None  # index into the articles we supplied
    rationale: str  # 1-2 sentences, shown on the proposal card
    confidence: float = Field(ge=0.0, le=1.0)


class _ProposeOutput(BaseModel):
    proposals: list[_Proposal]


class Suggestion(_Proposal):
    """A proposal that survived the guards, enriched with provenance — what the
    host persists as a row in its proposals table and shows for approval. The
    extra fields are filled by us, never by the model.
    """
    source_article_url: str | None = None
    prompt_version: str
    proposed_at: str  # ISO-8601 UTC, stamped at guard time
    guard_note: str | None = None  # set when a guard rewrote the proposal


# --------------------------------------------------------------------------- #
# Public entry point.
# --------------------------------------------------------------------------- #
def suggest(thesis: dict, evaluation: dict, catalyst_states: dict[str, str] | None = None,
            articles: list[Article] | None = None, metrics: Iterable[str] = ()) -> list[Suggestion]:
    """Review one thesis against the sweep that just ran and suggest edits.

    Args:
        thesis: the same dict `evaluator.evaluate` consumes — `ticker`,
            `quant_mode`, `catalyst_mode`, `quant_conditions`, `catalysts`.
        evaluation: the dict `evaluator.evaluate` returned for it. A
            `quant_detail` list (per-condition live value + pass/fail), if the
            host enriched the result with one, is what makes threshold review
            possible.
        catalyst_states: {catalyst_id: state}. Missing ids read as `unconfirmed`.
        articles: recent articles for the ticker — headline AND body are shown to
            the reviewer, since the materiality of an untracked event lives in the body.
        metrics: the metric names the host can actually fetch. A proposal naming
            anything else is dropped (guard 2). Empty means "don't police it".

    Returns:
        Zero or more Suggestions, highest confidence first. Empty is the common
        and correct answer — see `should_review`. Never raises: a failed review
        is logged and returns [], so one bad thesis can't sink the sweep.
    """
    if not should_review(thesis, evaluation):
        return []

    articles = (articles or [])[:MAX_ARTICLES]
    try:
        raw = _review(thesis, evaluation, catalyst_states or {}, articles, metrics)
    except Exception as exc:
        log.warning("proposal review failed for %s: %s", thesis.get("ticker"), exc)
        return []

    return _apply_guards(raw.proposals, thesis, articles, metrics)


def should_review(thesis: dict, evaluation: dict) -> bool:
    """Is this sweep worth spending a review call on?

    We review a firing thesis too: fresh news can surface a new catalyst worth
    proposing even while the signal holds, so a firing thesis is still worth a
    look rather than skipped. Not_met/incomplete theses may also have wording
    that's the problem. Pure: the host can call it to skip the LLM entirely.
    """
    # Nothing to edit if the thesis has no rows to edit.
    return bool(thesis.get("quant_conditions") or thesis.get("catalysts"))


# --------------------------------------------------------------------------- #
# The review call.
# --------------------------------------------------------------------------- #
def _review(thesis: dict, evaluation: dict, catalyst_states: dict[str, str],
            articles: list[Article], metrics: Iterable[str]) -> _ProposeOutput:
    return _call(
        model=PROPOSE_MODEL,
        system=_prompt(PROMPT_NAME),
        user=_build_user_message(thesis, evaluation, catalyst_states, articles, metrics),
        schema=_ProposeOutput,
        max_tokens=4096,  # room for reasoning tokens + a handful of proposals
        effort="low",  # a focused review, not an essay
    )


def _build_user_message(thesis: dict, evaluation: dict, catalyst_states: dict[str, str],
                        articles: list[Article], metrics: Iterable[str]) -> str:
    """Everything the reviewer is allowed to reason from, as plain text."""
    detail_by_id = {d.get("quant_condition_id"): d for d in evaluation.get("quant_detail", []) or []}

    quant_lines = [
        _format_condition(c, detail_by_id.get(c.get("id")))
        for c in thesis.get("quant_conditions", []) if c.get("enabled", True)
    ] or ["(none)"]

    catalyst_lines = [
        f"- id: {c.get('id')} — \"{c.get('description') or ''}\" "
        f"[state: {catalyst_states.get(c.get('id'), 'unconfirmed')}]"
        for c in thesis.get("catalysts", []) if c.get("enabled", True)
    ] or ["(none)"]

    blocked = evaluation.get("blocked_by") or []
    blocked_lines = [f"- {b}" for b in blocked] or ["(nothing — the thesis is not blocked)"]

    article_lines = [_format_article(i, a) for i, a in enumerate(articles)] or \
                    ["(no recent news for this ticker)"]

    metric_names = ", ".join(sorted(metrics)) or "(unrestricted)"

    return (
        f"""
    TICKER: {thesis.get('ticker', '?')}\n
    QUANT MODE: {thesis.get('quant_mode', 'all')}
    (how the quant conditions combine)\n
    QUANT CONDITIONS:\n {'\n'.join(quant_lines)} \n\n
    CATALYSTS:\n {'\n'.join(catalyst_lines)} \n\n
    LATEST SWEEP:\n
    - status: {evaluation.get('status', '?')}\n
    - reason: {evaluation.get('reason', '')}\n
    - why it isn't firing:\n {'\n'.join(blocked_lines)} \n\n
    FETCHABLE METRICS: {metric_names}\n\n
    RECENT NEWS (headline + body — read the body, that's where materiality is):\n
    {'\n'.join(article_lines)}
    """
    )


def _format_condition(condition: dict, detail: dict | None) -> str:
    """One condition, with the live value the sweep judged it on — the whole
    point of the review is reacting to that number, so it has to be in front of
    the model."""
    line = (f"- id: {condition.get('id')} — {condition.get('metric')} "
            f"{condition.get('operator')} {condition.get('value')}")
    if detail is None:
        return f"{line} [live value: not reported this sweep]"
    value = detail.get("value")
    if value is None:
        return f"{line} [live value: UNAVAILABLE — this condition could not be evaluated]"
    verdict = {True: "passes", False: "fails"}.get(detail.get("passes"), "couldn't evaluate")
    return f"{line} [live value: {value} — {verdict}]"


def _format_article(index: int, a: Article) -> str:
    """Headline AND body. The materiality of a new event — 'cuts billions from
    revenue', 'cancelled', 'SEC charges' — lives in the body, not the one-line
    headline; the reviewer can't spot an untracked event it can't read."""
    body = " ".join((a.summary or "").split())
    if len(body) > 600:
        body = body[:600] + "…"
    date = a.published_at.strftime("%Y-%m-%d") if getattr(a, "published_at", None) else "?"
    head = f"[{index}] ({date}) {a.headline}"
    return f"{head}\n     {body}" if body else f"{head}\n     (headline only)"


# --------------------------------------------------------------------------- #
# The guards — enforce in code what the prompt merely requests.
# --------------------------------------------------------------------------- #
def _apply_guards(proposals: list[_Proposal], thesis: dict, articles: list[Article],
                  metrics: Iterable[str]) -> list[Suggestion]:
    """Drop every proposal the host couldn't safely apply or the user shouldn't
    have to read. Returns the survivors, highest confidence first."""
    metric_names = frozenset(metrics)
    conditions = {c.get("id"): c for c in thesis.get("quant_conditions", []) if c.get("enabled", True)}
    catalysts = {c.get("id"): c for c in thesis.get("catalysts", []) if c.get("enabled", True)}
    existing_descriptions = {_norm(c.get("description") or "") for c in catalysts.values()}

    kept: list[Suggestion] = []
    for p in proposals:
        note = _reject_reason(p, conditions, catalysts, existing_descriptions, metric_names)
        if note is not None:
            log.info("proposal dropped (%s): %s/%s %s", note, p.target, p.action, p.target_id or "")
            continue
        kept.append(_to_suggestion(p, articles))

    kept.sort(key=lambda s: s.confidence, reverse=True)
    if len(kept) > MAX_PROPOSALS:
        log.info("proposal review returned %d — keeping the top %d", len(kept), MAX_PROPOSALS)
    return kept[:MAX_PROPOSALS]


def _reject_reason(p: _Proposal, conditions: dict, catalysts: dict,
                   existing_descriptions: set[str], metric_names: frozenset[str]) -> str | None:
    """Why this proposal can't stand, or None if it survives."""
    # Guard 6: the confidence floor. The prompt asks for calibration; this enforces it.
    if p.confidence < MIN_CONFIDENCE:
        return f"confidence {p.confidence:.2f} below {MIN_CONFIDENCE}"
    if not p.rationale.strip():
        return "no rationale — nothing to show the user"

    known = conditions if p.target == "quant" else catalysts

    # Guard 1: update/remove must name a row the thesis actually has.
    if p.action in ("update", "remove"):
        if not p.target_id:
            return f"{p.action} without a target_id"
        if p.target_id not in known:
            return f"unknown {p.target} id {p.target_id!r}"

    if p.action == "remove":
        return None  # nothing else to validate — the id is the whole payload

    if p.target == "quant":
        return check_quant_proposal(conditions, metric_names, p)

    # target == "catalyst"
    return check_catalyst_proposal(catalysts, existing_descriptions, p)


def check_catalyst_proposal(catalysts: dict, existing_descriptions: set[str], p: _Proposal) -> Any:
    if not (p.description or "").strip():
        return "catalyst proposal without a description"
    if p.action == "update" and _norm(p.description) == _norm(catalysts[p.target_id].get("description") or ""):
        return "update is identical to the current catalyst"
    # Guard 4: don't propose a catalyst the thesis already watches.
    if p.action == "add" and _norm(p.description) in existing_descriptions:
        return "add duplicates an existing catalyst"
    return None


def check_quant_proposal(conditions: dict, metric_names: frozenset[str], p: _Proposal) -> Any:
    # Guard 2: an unfetchable metric or uncomparable operator never resolves.
    if not p.metric:
        return "quant proposal without a metric"
    if metric_names and p.metric not in metric_names:
        return f"unfetchable metric {p.metric!r}"
    if p.operator not in OPERATORS:
        return f"unsupported operator {p.operator!r}"
    if p.value is None or not math.isfinite(p.value):
        return f"non-numeric threshold {p.value!r}"
    # Guard 3: an update that changes nothing wastes a review.
    if p.action == "update" and _is_noop(p, conditions[p.target_id]):
        return "update is identical to the current condition"
    return None


def _is_noop(p: _Proposal, current: dict) -> bool:
    """True if a quant update would leave the condition exactly as it is."""
    try:
        same_value = math.isclose(float(p.value), float(current.get("value")), rel_tol=1e-9)
    except (TypeError, ValueError):
        same_value = False
    return (p.metric == current.get("metric")
            and p.operator == current.get("operator")
            and same_value)


def _to_suggestion(p: _Proposal, articles: list[Article]) -> Suggestion:
    """Stamp provenance onto a surviving proposal."""
    url, note = _resolve_article(p.source_article_index, articles)
    return Suggestion(
        **p.model_dump(),
        source_article_url=url,
        prompt_version=prompt_version(PROMPT_NAME),
        proposed_at=datetime.now(timezone.utc).isoformat(),
        guard_note=note,
    )


def _resolve_article(index: int | None, articles: list[Article]) -> tuple[str | None, str | None]:
    """Guard 5: turn the model's article *index* into a URL ourselves.

    The model never sees or emits a URL, so it cannot cite an article that
    doesn't exist — an out-of-range index just loses the citation (the proposal
    itself may still be sound), which is why this drops the link instead of the
    proposal.
    """
    if index is None:
        return None, None
    if not (0 <= index < len(articles)):
        return None, f"guard: source_article_index {index} out of range — citation dropped"
    return articles[index].url, None


def _norm(text: str) -> str:
    return " ".join(text.lower().split())
