"""Turns the ML reviewer's suggestions into pending proposal rows.

This is the missing half of the proposals feature: the tables, the approve/reject
endpoints and the review page all existed, but nothing ever *wrote* a proposal,
so the queue was permanently empty. The scheduler calls this at the end of each
sweep, right after the evaluation lands.

The split is the same one the rest of the integration uses: `pipeline.proposals`
owns the judgment (what's worth suggesting, and the guards on it), this owns the
persistence (what a suggestion looks like as a row, and whether it's new).

`proposed_change` is the one JSON column both sides of the feature read, so it
carries two kinds of key:
  * the **apply** keys the approve path feeds back into the repos on approval
    (`metric`/`operator`/`value`, `state`/`description`);
  * the **display** keys the proposal card renders (`ticker`, `currentValue`,
    `liveValue`, ...) — a proposal has to be legible weeks later, and the row it
    describes may have changed or been deleted by then.
"""
from __future__ import annotations

from app.core.logger import logger
from app.repository.alert_repository import AlertRepository
from app.repository.catalyst_proposal_repository import CatalystProposalRepository
from app.repository.quant_proposal_repository import QuantProposalRepository
from app.repository.user_repository import UserRepository
from app.service import quant_service
from app.service.telegram_service import TelegramService
from common.enums.CatalystEnum import CatalystState
from common.enums.ProposalEnum import ProposalTypeEnum
from pipeline import proposals

# The ML guards police `metric` against this — anything else is unfetchable, so
# the condition could only ever evaluate to "incomplete".
FETCHABLE_METRICS = tuple(quant_service.METRIC_MAP)

_ACTION_TO_TYPE = {
    "add": ProposalTypeEnum.ADD,
    "update": ProposalTypeEnum.UPDATE,
    "remove": ProposalTypeEnum.REMOVE,
}


def _format_quant_proposal(change: dict) -> str:
    ticker = change.get("ticker", "")
    metric = change.get("currentMetric") or change.get("metric", "")
    current_op = change.get("currentOperator", "")
    current_val = change.get("currentValue", "")
    new_op = change.get("operator", "")
    new_val = change.get("value", "")
    rationale = change.get("rationale", "")
    live = change.get("liveValue")

    if new_val:
        change_line = f"{metric} {current_op} {current_val}  →  {metric} {new_op} {new_val}"
    else:
        change_line = f"Remove {metric} {current_op} {current_val}"

    live_line = f"Live value: {live}\n" if live is not None else ""
    rationale_line = f"{rationale}\n" if rationale else ""

    return (f"""
         💡New proposal for *{ticker}*\n
         \n
         {change_line}\n
         {live_line}\n
         {rationale_line}\n
         \n👉 Review → https://kestrel-rose.vercel.app/proposals""")


def _format_catalyst_proposal(change: dict) -> str:
    ticker = change.get("ticker", "")
    description = change.get("description", "")
    current = change.get("currentDescription", "")
    rationale = change.get("rationale", "")

    if current and description:
        change_line = f"\"{current}\"\n→  \"{description}\""
    elif description:
        change_line = f"Add: \"{description}\""
    else:
        change_line = f"Remove: \"{current}\""

    rationale_line = f"{rationale}\n" if rationale else ""

    return (f"""
         💡New proposal for *{ticker}*\n
         \n
         {change_line}\n
         {rationale_line}\n
         \n👉 Review → https://kestrel-rose.vercel.app/proposals""")


class ProposalGenerator:
    def __init__(self, quant_proposal_repo: QuantProposalRepository, catalyst_proposal_repo: CatalystProposalRepository,
                 user_repo: UserRepository, alert_repo: AlertRepository):
        self._quant_repo = quant_proposal_repo
        self._catalyst_repo = catalyst_proposal_repo
        self._user_repo = user_repo
        self._alert_repo = alert_repo

    async def generate(self, *, theses_id: str, thesis_dict: dict, evaluation: dict, evaluation_id: str,
                       catalyst_states: dict[str, str], articles: list | None = None) -> int:
        """Review one swept thesis and persist whatever survives as PENDING rows.

        Args:
            thesis_dict: the dict the evaluator consumed (`ml_adapter.build_thesis_dict`).
            evaluation: the dict the evaluator returned, enriched with `quant_detail`.
            evaluation_id: the row just persisted — every proposal is provenanced
                back to the sweep that motivated it (`source_evaluation_id`).
            catalyst_states / articles: the same values the sweep judged on.

        Returns:
            How many proposals were created. Never raises — a thesis whose review
            fails just gets no proposals, exactly like a thesis with nothing to say.
        """
        suggestions = proposals.suggest(
            thesis=thesis_dict,
            evaluation=evaluation,
            catalyst_states=catalyst_states,
            articles=articles or [],
            metrics=FETCHABLE_METRICS,
        )
        if not suggestions:
            return 0

        pending_quant = await self._quant_repo.get_pending_by_theses_id(theses_id)
        pending_catalyst = await self._catalyst_repo.get_pending_by_theses_id(theses_id)

        created = 0
        for s in suggestions:
            try:
                if s.target == "quant":
                    made = await self._persist_quant(theses_id, s, thesis_dict, evaluation,
                                                     evaluation_id, pending_quant)
                else:
                    made = await self._persist_catalyst(theses_id, s, thesis_dict,
                                                        evaluation_id, pending_catalyst)
                created += int(made)
            except Exception:
                # One malformed suggestion must not cost the thesis its evaluation:
                # the sweep's own transaction is already carrying the sweep's work.
                logger.exception("proposal generator: failed to persist %s/%s on thesis %s",
                                 s.target, s.action, theses_id)

        logger.info("thesis %s: %d/%d proposals created", theses_id, created, len(suggestions))
        return created

    # ----- quant ------------------------------------------------------------ #
    async def _persist_quant(self, theses_id: str, s, thesis_dict: dict, evaluation: dict,
                             evaluation_id: str, pending: list) -> bool:
        current = _condition_by_id(thesis_dict).get(s.target_id, {})
        change = {
            "ticker": thesis_dict.get("ticker"),
            "rationale": s.rationale,
            # display: what the row looks like today, so the card reads on its own
            "currentMetric": current.get("metric"),
            "currentOperator": current.get("operator"),
            "currentValue": current.get("value"),
            "liveValue": _live_value(evaluation, s.target_id),
        }
        if s.action != "remove":
            # apply keys — `enabled` is deliberately absent: this proposal changes
            # the threshold, and the repo skips the fields it isn't given.
            change |= {"metric": s.metric, "operator": s.operator, "value": s.value,
                       "suggestedValue": s.value}

        if _duplicate_quant(s, change, pending):
            logger.info("thesis %s: skipping duplicate quant %s already pending", theses_id, s.action)
            return False

        quant_proposal = await self._quant_repo.create_quant_proposal(
            theses_id=theses_id,
            quant_condition_id=s.target_id,  # NULL for an ADD
            proposal_type=_ACTION_TO_TYPE[s.action],
            proposed_change=change,
            llm_rationale=s.rationale,
            llm_confidence=s.confidence,
            source_article_url=s.source_article_url,
            source_evaluation_id=evaluation_id,
        )
        telegram_service = TelegramService(user_repo=self._user_repo, alert_repo=self._alert_repo)

        theses = quant_proposal.theses_mapping
        user_id = theses.user_id
        chat_id = theses.users_mapping.telegram_chat_id
        if chat_id:
            telegram_message = _format_quant_proposal(quant_proposal.proposed_change)
            await telegram_service.send_proposal_on_telegram(chat_id, telegram_message, user_id)

        return True

    # ----- catalyst --------------------------------------------------------- #
    async def _persist_catalyst(self, theses_id: str, s, thesis_dict: dict,
                                evaluation_id: str, pending: list) -> bool:
        current = _catalyst_by_id(thesis_dict).get(s.target_id, {})
        change = {
            "ticker": thesis_dict.get("ticker"),
            "rationale": s.rationale,
            "currentDescription": current.get("description"),
        }
        if s.action == "add":
            # A proposed catalyst starts unconfirmed like any other — approving it
            # queues it for the classifier, it doesn't assert the event happened.
            change |= {"state": CatalystState.UNCONFIRMED.value, "description": s.description,
                       "evidence": None}
        elif s.action == "update":
            # No `state` key: re-wording a catalyst must not silently reset the
            # state (and its evidence trail) that news already established.
            change |= {"description": s.description}

        if _duplicate_catalyst(s, pending):
            logger.info("thesis %s: skipping duplicate catalyst %s already pending", theses_id, s.action)
            return False

        catalyst_proposal = await self._catalyst_repo.create_catalyst_proposal(
            theses_id=theses_id,
            catalyst_id=s.target_id,  # NULL for an ADD
            proposal_type=_ACTION_TO_TYPE[s.action],
            proposed_change=change,
            llm_rationale=s.rationale,
            llm_confidence=s.confidence,
            source_article_url=s.source_article_url,
            source_evaluation_id=evaluation_id,
        )

        telegram_service = TelegramService(user_repo=self._user_repo, alert_repo=self._alert_repo)

        theses = catalyst_proposal.theses_mapping
        user_id = theses.user_id
        chat_id = theses.users_mapping.telegram_chat_id
        if chat_id:
            telegram_message = _format_catalyst_proposal(catalyst_proposal.proposed_change)
            await telegram_service.send_proposal_on_telegram(chat_id, telegram_message, user_id)

        return True


# --------------------------------------------------------------------------- #
# Dedup — the reviewer sees the same unchanged thesis every sweep, so without
# this an unapproved suggestion would be re-queued hourly until the user acted.
# --------------------------------------------------------------------------- #
def _duplicate_quant(s, change: dict, pending: list) -> bool:
    kind = _ACTION_TO_TYPE[s.action]
    for p in pending:
        if p.proposal_type != kind or p.quant_condition_id != s.target_id:
            continue
        existing = p.proposed_change or {}
        if s.action == "remove":
            return True  # same row, same ask — nothing else distinguishes them
        if (existing.get("metric") == change.get("metric")
                and existing.get("operator") == change.get("operator")
                and _same_number(existing.get("value"), change.get("value"))):
            return True
    return False


def _duplicate_catalyst(s, pending: list) -> bool:
    kind = _ACTION_TO_TYPE[s.action]
    for p in pending:
        if p.proposal_type != kind or p.catalyst_id != s.target_id:
            continue
        existing = p.proposed_change or {}
        if s.action == "remove":
            return True
        if _norm(existing.get("description")) == _norm(s.description):
            return True
    return False


def _same_number(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return a == b


def _norm(text: str | None) -> str:
    return " ".join((text or "").lower().split())


def _condition_by_id(thesis_dict: dict) -> dict[str, dict]:
    return {c.get("id"): c for c in thesis_dict.get("quant_conditions", [])}


def _catalyst_by_id(thesis_dict: dict) -> dict[str, dict]:
    return {c.get("id"): c for c in thesis_dict.get("catalysts", [])}


def _live_value(evaluation: dict, condition_id: str | None):
    """The metric reading the sweep judged this condition on — the number the
    rationale is reacting to, pinned into the row so the card can show it even
    after later sweeps have moved on."""
    for d in evaluation.get("quant_detail") or []:
        if d.get("quant_condition_id") == condition_id:
            return d.get("value")
    return None
