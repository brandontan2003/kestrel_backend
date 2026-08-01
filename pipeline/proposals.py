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
  guard 6: proposals below their confidence floor are dropped, and the queue is
           quota'd PER KIND — refinements and discoveries never compete for the
           same slot (discovery is honestly less certain, so a global
           confidence sort would evict it every time).
  guard 7: a quant update that would flip a failing condition to passing on the
           very value the sweep just judged is a rubber stamp, not a thesis —
           dropped. ("Don't weaken the thesis into always firing", enforced.)
  guard 8: a catalyst `add` must cite the article that motivates it — discovery
           without grounding is speculation, and the prompt's rule 3 is now code.
  guard 9: a quant `add` on a metric the thesis already conditions on is dropped
           (redundant under ALL, contradictory under ANY).

Contract:  suggest(thesis, evaluation, catalyst_states, articles, metrics,
                   quant_history) -> list[Suggestion]
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Iterable, Literal

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
_OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
}

# A proposal the user would only rubber-stamp is worse than none: keep the bar
# high and the queue short. Refinement (editing what the user wrote) demands
# more certainty than discovery (surfacing an event they haven't seen) — a
# dismissed discovery costs one click, a missed one costs the alert. Separate
# floors, separate quotas, so the two kinds never compete for a slot.
# Tune against the real approve rate, not by taste.
MIN_CONFIDENCE_REFINEMENT = 0.55
MIN_CONFIDENCE_DISCOVERY = 0.45
MAX_REFINEMENTS = 2
MAX_DISCOVERIES = 2

# The reviewer sees headline + body for each: an untracked material event is only
# spottable from the body ("cuts billions from revenue"), not a terse headline.
# Selection is NEWEST-first (see suggest) — when the cap binds, it must be old
# news that loses, not this morning's story.
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


def _is_discovery(p: _Proposal) -> bool:
    """Discovery = surfacing an untracked event as a new catalyst. Everything
    else (threshold fixes, re-wording, pruning — and quant adds, which refine
    the quant side) is refinement of what the user already wrote."""
    return p.target == "catalyst" and p.action == "add"


# --------------------------------------------------------------------------- #
# Public entry point.
# --------------------------------------------------------------------------- #
def suggest(thesis: dict, evaluation: dict, catalyst_states: dict[str, str] | None = None,
            articles: list[Article] | None = None, metrics: Iterable[str] = (),
            quant_history: dict[str, dict] | None = None) -> list[Suggestion]:
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
        quant_history: optional {condition_id: {"sweeps", "resolved", "min",
            "max"}} summarizing past sweeps — what turns "unavailable every
            time" and "no plausible path" from guesses into facts the model
            can cite.

    Returns:
        Zero or more Suggestions — refinements first, then discoveries, each
        group highest-confidence first. Empty is the common and correct answer —
        see `should_review`. Never raises: a failed review is logged and returns
        [], so one bad thesis can't sink the sweep.
    """
    if not should_review(thesis, evaluation):
        return []

    # Newest-first before the cap binds: fetch() returns oldest-first (the state
    # machine needs chronology), so a plain [:MAX_ARTICLES] would keep exactly
    # the articles every previous sweep already saw and drop this morning's
    # story — the one discovery exists for. Body presence only breaks ties.
    articles = sorted(articles or [],
                      key=lambda a: (a.published_at, a.has_body),
                      reverse=True)[:MAX_ARTICLES]
    try:
        raw = _review(thesis, evaluation, catalyst_states or {}, articles, metrics,
                      quant_history or {})
    except Exception as exc:
        # A crashed review and a quiet one must not look alike in the logs —
        # "the feature does nothing" has hidden behind this line before.
        log.error("proposal review FAILED for %s (returning no proposals): %s",
                  thesis.get("ticker"), exc)
        return []

    return _apply_guards(raw.proposals, thesis, articles, metrics, evaluation)


def should_review(thesis: dict, evaluation: dict) -> bool:
    """Is this sweep worth spending a review call on?

    We review a firing thesis too: fresh news can surface a new catalyst worth
    proposing even while the signal holds, so a firing thesis is still worth a
    look rather than skipped. Not_met/incomplete theses may also have wording
    that's the problem. Pure: the host can call it to skip the LLM entirely
    (the scheduler adds its own change-gate on top — nothing new since the
    last sweep means nothing new to review).
    """
    # Nothing to edit if the thesis has no rows to edit.
    return bool(thesis.get("quant_conditions") or thesis.get("catalysts"))


# --------------------------------------------------------------------------- #
# The review call.
# --------------------------------------------------------------------------- #
def _review(thesis: dict, evaluation: dict, catalyst_states: dict[str, str],
            articles: list[Article], metrics: Iterable[str],
            quant_history: dict[str, dict]) -> _ProposeOutput:
    return _call(
        model=PROPOSE_MODEL,
        system=_prompt(PROMPT_NAME),
        user=_build_user_message(thesis, evaluation, catalyst_states, articles, metrics,
                                 quant_history),
        schema=_ProposeOutput,
        # Reasoning tokens + output share this budget; 30 article bodies make a
        # big prompt, and a truncated response parses to None and silently
        # drops EVERY proposal (same lesson as llm.py's Pass-1 budget).
        max_tokens=8192,
        effort="low",  # a focused review, not an essay
    )


def _build_user_message(thesis: dict, evaluation: dict, catalyst_states: dict[str, str],
                        articles: list[Article], metrics: Iterable[str],
                        quant_history: dict[str, dict]) -> str:
    """Everything the reviewer is allowed to reason from, as plain text."""
    detail_by_id = {d.get("quant_condition_id"): d for d in evaluation.get("quant_detail", []) or []}

    quant_lines = [
        _format_condition(c, detail_by_id.get(c.get("id")), quant_history.get(c.get("id")))
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
        RECENT NEWS (newest first; headline + body — read the body, that's where materiality is):\n
        {'\n'.join(article_lines)}
        """
    )


def _format_condition(condition: dict, detail: dict | None, history: dict | None) -> str:
    """One condition, with the live value the sweep judged it on — the whole
    point of the review is reacting to that number, so it has to be in front of
    the model — plus the sweep history when the host supplies one, so "never
    resolves" and "no plausible path" are read off facts, not guessed."""
    line = (f"- id: {condition.get('id')} — {condition.get('metric')} "
            f"{condition.get('operator')} {condition.get('value')}")
    if detail is None:
        line += " [live value: not reported this sweep]"
    else:
        value = detail.get("value")
        if value is None:
            line += " [live value: UNAVAILABLE — this condition could not be evaluated]"
        else:
            passes = detail.get("passes")
            verdict = "couldn't evaluate" if passes is None else ("passes" if passes else "fails")
            line += f" [live value: {value} — {verdict}]"

    if history and history.get("sweeps"):
        sweeps, resolved = history["sweeps"], history.get("resolved", 0)
        if resolved:
            line += (f"\n    [history: resolved {resolved}/{sweeps} recent sweeps, "
                     f"value range {history.get('min')}–{history.get('max')}]")
        else:
            line += f"\n    [history: resolved 0/{sweeps} recent sweeps — never produces a value]"
    return line


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
                  metrics: Iterable[str], evaluation: dict) -> list[Suggestion]:
    """Drop every proposal the host couldn't safely apply or the user shouldn't
    have to read. Returns the survivors — refinements then discoveries, each
    group highest-confidence first, quota'd separately (guard 6)."""
    metric_names = frozenset(metrics)
    conditions = {c.get("id"): c for c in thesis.get("quant_conditions", []) if c.get("enabled", True)}
    catalysts = {c.get("id"): c for c in thesis.get("catalysts", []) if c.get("enabled", True)}
    existing_descriptions = {_norm(c.get("description") or "") for c in catalysts.values()}
    # The value each condition was actually judged on this sweep (guard 7).
    live_values = {d.get("quant_condition_id"): d.get("value")
                   for d in evaluation.get("quant_detail", []) or []}

    kept: list[Suggestion] = []
    for p in proposals:
        note = _reject_reason(p, conditions, catalysts, existing_descriptions, metric_names,
                              live_values, len(articles))
        if note is not None:
            log.info("proposal dropped (%s): %s/%s %s", note, p.target, p.action, p.target_id or "")
            continue
        kept.append(_to_suggestion(p, articles))

    refinements = sorted((s for s in kept if not _is_discovery(s)),
                         key=lambda s: s.confidence, reverse=True)
    discoveries = sorted((s for s in kept if _is_discovery(s)),
                         key=lambda s: s.confidence, reverse=True)
    if len(refinements) > MAX_REFINEMENTS or len(discoveries) > MAX_DISCOVERIES:
        log.info("proposal review returned %d refinements / %d discoveries — keeping %d / %d",
                 len(refinements), len(discoveries), MAX_REFINEMENTS, MAX_DISCOVERIES)
    return refinements[:MAX_REFINEMENTS] + discoveries[:MAX_DISCOVERIES]


def _reject_reason(p: _Proposal, conditions: dict, catalysts: dict,
                   existing_descriptions: set[str], metric_names: frozenset[str],
                   live_values: dict, n_articles: int) -> str | None:
    """Why this proposal can't stand, or None if it survives."""
    # Guard 6: the confidence floor. The prompt asks for calibration; this enforces it.
    floor = MIN_CONFIDENCE_DISCOVERY if _is_discovery(p) else MIN_CONFIDENCE_REFINEMENT
    if p.confidence < floor:
        return f"confidence {p.confidence:.2f} below {floor}"
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
        return _check_quant_proposal(p, conditions, metric_names, live_values)

    return _check_catalyst_proposal(p, catalysts, existing_descriptions, n_articles)


def _check_quant_proposal(p: _Proposal, conditions: dict, metric_names: frozenset[str],
                          live_values: dict) -> str | None:
    # Guard 2: an unfetchable metric or uncomparable operator never resolves.
    if not p.metric:
        return "quant proposal without a metric"
    if metric_names and p.metric not in metric_names:
        return f"unfetchable metric {p.metric!r}"
    if p.operator not in OPERATORS:
        return f"unsupported operator {p.operator!r}"
    if p.value is None or not math.isfinite(p.value):
        return f"non-numeric threshold {p.value!r}"

    if p.action == "add":
        # Guard 9: one condition per metric. A second threshold on the same
        # metric is redundant under ALL and contradictory under ANY — and a
        # disjoint pair (>40 alongside <30) would silently make the thesis
        # unsatisfiable forever.
        if any(c.get("metric") == p.metric for c in conditions.values()):
            return f"thesis already has a condition on {p.metric!r}"
        return None

    # action == "update" — guard 1 upstream guarantees the id resolves; the
    # .get() keeps the type checker honest about it.
    current = conditions.get(p.target_id or "")
    if current is None:
        return f"unknown quant id {p.target_id!r}"
    # Guard 3: an update that changes nothing wastes a review.
    if _is_noop(p, current):
        return "update is identical to the current condition"
    # Guard 7: the one rule whose violation costs the user money, not attention.
    if _weakens_into_firing(p, current, live_values.get(p.target_id)):
        return "update would flip a failing condition to passing on today's value — rubber stamp"
    return None


def _check_catalyst_proposal(p: _Proposal, catalysts: dict, existing_descriptions: set[str],
                             n_articles: int) -> str | None:
    desc = _norm(p.description or "")
    if not desc:
        return "catalyst proposal without a description"
    if p.action == "update":
        current = catalysts.get(p.target_id or "") or {}
        if desc == _norm(current.get("description") or ""):
            return "update is identical to the current catalyst"
    if p.action == "add":
        # Guard 4: don't propose a catalyst the thesis already watches.
        if desc in existing_descriptions:
            return "add duplicates an existing catalyst"
        # Guard 8: discovery must be grounded in an article we actually supplied
        # (prompt rule 3, enforced). Updates/removes may cite one; an add MUST.
        if p.source_article_index is None:
            return "catalyst add without a motivating article"
        if not (0 <= p.source_article_index < n_articles):
            return f"catalyst add cites article {p.source_article_index}, which doesn't exist"
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


def _weakens_into_firing(p: _Proposal, current: dict, live_value) -> bool:
    """True if the update's whole effect is moving the goalposts to where the
    ball already is: the condition FAILS on the value the sweep just judged,
    and the proposed condition PASSES on that same value.

    Metric changes are exempt — `live_value` was measured for the current
    metric, so it says nothing about a different one (guard 2 already vets
    fetchability). No live value, no verdict: never triggers on unknowns.
    """
    if live_value is None or p.metric != current.get("metric"):
        return False
    current_op = _OPS.get(current.get("operator") or "")
    proposed_op = _OPS.get(p.operator or "")
    current_value = current.get("value")
    if current_op is None or proposed_op is None or current_value is None or p.value is None:
        return False
    try:
        live = float(live_value)
        was_passing = bool(current_op(live, float(current_value)))
        now_passing = bool(proposed_op(live, float(p.value)))
    except (TypeError, ValueError):
        return False
    return now_passing and not was_passing


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
    proposal. (For a catalyst `add` an invalid index is fatal instead — guard 8
    rejects it before we get here, because there the article IS the evidence.)
    """
    if index is None:
        return None, None
    if not (0 <= index < len(articles)):
        return None, f"guard: source_article_index {index} out of range — citation dropped"
    return articles[index].url, None


def _norm(text: str) -> str:
    return " ".join(text.lower().split())
