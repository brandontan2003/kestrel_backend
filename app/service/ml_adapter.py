"""Adapter between backend ORM models and the vendored ML `pipeline` package.

The two sides disagree on casing and shape:

  * backend enums are UPPERCASE (`ANY`, `NONE_REQUIRED`); the ML evaluator wants
    lowercase (`any`, `none_required`) and lowercase catalyst states.
  * backend rows are SQLAlchemy models; the pipeline wants plain dicts.

Everything that translates one to the other lives here, so the scheduler reads
as the clean four-call sequence the ML README describes.
"""
from __future__ import annotations

from app.models import Catalyst, QuantCondition, Theses
from common.enums.CatalystEnum import CatalystState
from common.enums.ThesesEnum import CatalystModeEnum, QuantModeEnum

_DEFAULT_CATALYST_STATE = CatalystState.UNCONFIRMED.value


def normalize_state(state: str | None) -> str:
    """Backend catalyst state -> ML lowercase state string (defensive)."""
    return (state or _DEFAULT_CATALYST_STATE).strip().lower()


def enabled_quant_conditions(thesis: Theses) -> list[QuantCondition]:
    """Ordered, enabled quant rows — the single source of order for BOTH the
    thesis dict and `quant_service.evaluate_conditions`, so they align 1:1."""
    return [q for q in thesis.quant_conditions_mapping if q.enabled]


def enabled_catalysts(thesis: Theses) -> list[Catalyst]:
    return [c for c in thesis.catalyst_mapping if c.enabled]


def build_thesis_dict(thesis: Theses, quant_conditions: list[QuantCondition],
                      catalysts: list[Catalyst]) -> dict:
    """Assemble the `thesis` dict `evaluator.evaluate` expects.

    `quant_conditions` is passed in (not re-read) so its order is identical to
    the one used to build `quant_results` — the evaluator aligns them by index.
    """
    return {
        "ticker": thesis.stocks_mapping.ticker,
        # Passed through in the backend's native UPPERCASE — the evaluator
        # normalizes casing itself. Round-tripped through the enum so an unknown
        # mode fails here rather than reaching the evaluator.
        "quant_mode": QuantModeEnum(thesis.quant_mode).value,
        "catalyst_mode": CatalystModeEnum(thesis.catalyst_mode).value,
        "quant_conditions": [
            {
                "id": q.quant_condition_id,
                "metric": q.metric,
                "operator": q.operator,
                "value": float(q.value),
                "enabled": True,
            }
            for q in quant_conditions
        ],
        "catalysts": [
            {"id": c.catalyst_id, "description": c.description, "enabled": True}
            for c in catalysts
        ],
    }


def quant_detail(quant_conditions: list[QuantCondition], quant_results: list[dict]) -> list[dict]:
    """Per-condition breakdown to persist alongside the evaluation.

    The vendored evaluator only returns a summary `quant_ok`; this pairs each
    condition with the live value + pass/fail it was judged on, so the UI can
    show the actual metric value instead of a dash. Aligned by position (same
    order the thesis dict + quant_results were built from).
    """
    return [
        {
            "quant_condition_id": q.quant_condition_id,
            "metric": q.metric,
            "operator": q.operator,
            "threshold": float(q.value),
            "value": r.get("value"),
            "passes": r.get("passes"),
        }
        for q, r in zip(quant_conditions, quant_results)
    ]


def quant_history_summary(evaluations) -> dict[str, dict]:
    """Compress past evaluations' `quant_detail` into per-condition stats for
    the proposal reviewer: {condition_id: {"sweeps", "resolved", "min", "max"}}.

    This is what lets the reviewer say "resolved 0/10 — never resolves" or
    "range 18.7–19.4, nowhere near the threshold" from facts instead of a
    single reading. Tolerant of old rows without `quant_detail` (pre-enrichment
    sweeps just don't count toward the stats).
    """
    stats: dict[str, dict] = {}
    for ev in evaluations:
        results = ev.results if isinstance(ev.results, dict) else {}
        for d in results.get("quant_detail") or []:
            if not isinstance(d, dict):
                continue
            cid = d.get("quant_condition_id")
            if not cid:
                continue
            s = stats.setdefault(cid, {"sweeps": 0, "resolved": 0, "min": None, "max": None})
            s["sweeps"] += 1
            value = d.get("value")
            if value is None:
                continue
            s["resolved"] += 1
            s["min"] = value if s["min"] is None else min(s["min"], value)
            s["max"] = value if s["max"] is None else max(s["max"], value)
    return stats


def catalyst_defs_for_classify(catalysts: list[Catalyst]) -> list[dict]:
    """The `catalysts` arg for `llm.classify_batch` — only id + description."""
    return [{"id": c.catalyst_id, "description": c.description or ""} for c in catalysts]


def verdict_to_evidence(verdict) -> dict:
    """A `CatalystVerdict` -> the JSON dict persisted onto `Catalyst.evidence`.

    `.model_dump()` already matches the README's evidence shape; wrapped here so
    the pydantic dependency stays inside the adapter.
    """
    return verdict.model_dump()


def evidence_article_ids(catalyst: Catalyst) -> set[str]:
    """article_ids already recorded on a catalyst's evidence — the per-thesis
    dedup set so we don't re-classify the same article across polls."""
    evidence = catalyst.evidence or []
    if not isinstance(evidence, list):
        return set()
    return {e.get("article_id") for e in evidence if isinstance(e, dict) and e.get("article_id")}
