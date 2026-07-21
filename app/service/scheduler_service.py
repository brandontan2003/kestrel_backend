"""The orchestrator — the one component the three repos were missing.

The ML package owns the *judgment*; this service owns the *loop*. Once per
interval, for every tracked thesis, it runs the four-call ML sequence from the
Kestrel-ML README and persists what comes back:

    news.fetch  ->  llm.classify_batch  ->  catalysts.apply  ->  evaluator.evaluate

It is deliberately import-safe: the ML sub-imports (openai/yfinance) are lazy, so
this module loads even without API keys — the loop only needs them when it runs.

Runs as an asyncio background task off the FastAPI lifespan (see app/main.py),
gated by SCHEDULER_ENABLED so dev/test processes stay quiet by default.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logger import logger
from app.database_registry import get_sessionmaker
from app.dto.alert import CreateAlertRequest
from app.enums.WebSocketEnum import WebSocketEventTypeEnum
from app.models import Theses, Evaluation
from app.repository.alert_repository import AlertRepository
from app.repository.catalyst_proposal_repository import CatalystProposalRepository
from app.repository.catalyst_repository import CatalystRepository
from app.repository.evaluation_repository import EvaluationRepository
from app.repository.quant_proposal_repository import QuantProposalRepository
from app.repository.theses_repository import ThesesRepository
from app.service import ml_adapter, quant_service
from app.service.proposal_generator import ProposalGenerator
from app.service.telegram_service import TelegramService, get_telegram_service
from app.websocket.connection_manager import manager
from common.enums.ThesesEnum import ThesesStatusEnum
from common.enums.AlertsEnum import AlertChannelsEnum
from pipeline import catalysts, evaluator, llm, news

# Verdicts whose article never confirms anything don't need persisting as evidence
# unless they bear on the catalyst; the state machine still returns a transition.
_NO_PROMPT = "no_classification"


class SchedulerService:
    def __init__(self, telegram_service: TelegramService) -> None:
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()
        self._telegram_service = telegram_service

    # ----- lifecycle -------------------------------------------------------- #
    def start(self) -> None:
        if not settings.SCHEDULER_ENABLED:
            logger.info("scheduler disabled (SCHEDULER_ENABLED=false) — not starting")
            return
        if self._task is not None:
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._loop(), name="kestrel-scheduler")
        logger.info("scheduler started: every %ss, lookback %sh",
                    settings.SCHEDULER_INTERVAL_SECONDS, settings.SCHEDULER_LOOKBACK_HOURS)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stopping.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("scheduler stopped")

    async def _loop(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.run_once()
            except Exception:  # a bad cycle must never kill the loop
                logger.exception("scheduler cycle failed")
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=settings.SCHEDULER_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass  # interval elapsed → next cycle

    # ----- one poll cycle over all theses ----------------------------------- #
    async def run_once(self) -> None:
        session_maker = get_sessionmaker()
        async with session_maker() as session:
            theses_repo = ThesesRepository(session)
            theses = await theses_repo.get_all_theses_by_status(ThesesStatusEnum.TRACKING)
            logger.info("scheduler cycle: %d tracking theses", len(theses))

        # Process each thesis in its own session so one failure/rollback is isolated.
        for thesis in theses:
            try:
                async with session_maker() as session:
                    await self._process_thesis(session, thesis.theses_id)
                    await session.commit()
            except Exception:
                logger.exception("scheduler: thesis %s failed", thesis.theses_id)

    async def _process_thesis(self, session, theses_id: str) -> None:
        theses_repo = ThesesRepository(session)
        catalyst_repo = CatalystRepository(session)
        eval_repo = EvaluationRepository(session)

        thesis = await theses_repo.get_theses_by_theses_id(theses_id)
        if thesis is None:
            return

        ticker = thesis.stocks_mapping.ticker
        quant_conditions = ml_adapter.enabled_quant_conditions(thesis)
        catalyst_rows = ml_adapter.enabled_catalysts(thesis)
        by_id = {c.catalyst_id: c for c in catalyst_rows}

        prompt_version = _NO_PROMPT
        # Populated below for a catalyst thesis (classification). A quant-only
        # thesis fetches none here; the reviewer fetches its own in
        # _generate_proposals so it can still DISCOVER a new catalyst from the news.
        articles: list = []

        # 1–3. News → classify → apply state machine (only if there are catalysts to judge)
        if catalyst_rows:
            since = datetime.now(timezone.utc) - timedelta(hours=settings.SCHEDULER_LOOKBACK_HOURS)
            articles = news.fetch(ticker, since=since)

            # Dedup across polls: drop articles already recorded on any catalyst's evidence.
            seen: set[str] = set()
            for c in catalyst_rows:
                seen |= ml_adapter.evidence_article_ids(c)
            fresh = [a for a in articles if a.id not in seen]
            logger.info("thesis %s (%s): %d articles, %d fresh", theses_id, ticker, len(articles), len(fresh))

            if fresh:
                verdicts = llm.classify_batch(fresh, ml_adapter.catalyst_defs_for_classify(catalyst_rows))
                for v in verdicts:
                    catalyst = by_id.get(v.catalyst_id)
                    if catalyst is None:
                        continue
                    current = ml_adapter.normalize_state(catalyst.state)
                    transition = catalysts.apply(current, v)
                    await catalyst_repo.record_verdict(
                        catalyst, transition.new_state.value,
                        ml_adapter.verdict_to_evidence(v), transition.changed,
                    )
                    prompt_version = v.prompt_version

        # 4. Quant + catalyst states → signal
        metric_values = quant_service.fetch_metrics(ticker) if quant_conditions else {}
        quant_results = quant_service.evaluate_conditions(quant_conditions, metric_values)
        catalyst_states = {c.catalyst_id: ml_adapter.normalize_state(c.state) for c in catalyst_rows}
        thesis_dict = ml_adapter.build_thesis_dict(thesis, quant_conditions, catalyst_rows)
        result = evaluator.evaluate(thesis_dict, quant_results, catalyst_states)
        # Enrich (not mutate the vendored evaluator): persist the per-condition
        # values so the UI shows live metric readings instead of "—".
        result["quant_detail"] = ml_adapter.quant_detail(quant_conditions, quant_results)

        # Detect a signal that just flipped true, for the notify hook.
        previous = await eval_repo.get_latest_evaluation(theses_id)
        was_firing = bool(previous.signal) if previous is not None else False

        if prompt_version == _NO_PROMPT and previous is not None:
            prompt_version = previous.prompt_version  # keep column meaningful across quiet cycles

        evaluation = await eval_repo.create_evaluation(
            theses_id=theses_id,
            evaluation_status=result["status"],
            prompt_version=prompt_version,
            results=result,
            signal=result["signal"],
            reason=result["reason"]
        )

        # 5. Review the thesis itself against what the sweep found, and queue any
        # suggested edits for the user to approve.
        await self._generate_proposals(session, theses_id, thesis_dict, result,
                                       evaluation.evaluation_id, catalyst_states, articles)

        if result["signal"] and not was_firing:
            await self._on_signal_fired(thesis, evaluation, session)

    async def _generate_proposals(self, session, theses_id: str, thesis_dict: dict, result: dict,
                                  evaluation_id: str, catalyst_states: dict, articles: list) -> None:
        """Best-effort: the sweep's own work is what matters, so a failed review
        is logged and dropped rather than allowed to roll back the evaluation."""
        if not settings.PROPOSALS_ENABLED:
            return

        # Discovery needs news. A catalyst thesis already fetched it above; a
        # quant-only thesis did not — so fetch it here whenever we don't already
        # have articles, including when the signal is firing. A firing thesis can
        # still surface fresh events worth proposing on, so we spend the call.
        # Without this, a quant-only thesis — the common case — could never be
        # told about a material event worth adding a catalyst for.
        if not articles:
            try:
                since = datetime.now(timezone.utc) - timedelta(hours=settings.SCHEDULER_LOOKBACK_HOURS)
                articles = news.fetch(thesis_dict["ticker"], since=since)
                logger.info("thesis %s (%s): reviewer fetched %d articles for discovery",
                            theses_id, thesis_dict.get("ticker"), len(articles))
            except Exception:
                logger.warning("scheduler: reviewer news fetch failed for %s", thesis_dict.get("ticker"))

        try:
            generator = ProposalGenerator(QuantProposalRepository(session), CatalystProposalRepository(session))
            await generator.generate(
                theses_id=theses_id,
                thesis_dict=thesis_dict,
                evaluation=result,
                evaluation_id=evaluation_id,
                catalyst_states=catalyst_states,
                articles=articles,
            )
        except Exception:
            logger.exception("scheduler: proposal generation failed for thesis %s", theses_id)

    async def sweep_thesis(self, theses_id: str) -> None:
        """Re-evaluate one thesis right now, in its own session — the on-demand
        counterpart to run_once (e.g. straight after a proposal is approved, so the
        dashboard reflects the new conditions without waiting for the next cycle)."""
        session_maker = get_sessionmaker()
        try:
            async with session_maker() as session:
                await self._process_thesis(session, theses_id)
                await session.commit()
        except Exception:
            logger.exception("sweep_thesis: thesis %s failed", theses_id)

    async def _on_signal_fired(self, thesis: Theses, evaluation: Evaluation, session: AsyncSession) -> None:
        """A thesis's signal just went true. Best-effort live push to the owner.

        Phase 2 proper still owns: persisting an Alert row + the frontend
        consuming this event. The outbound WS infra already exists, so we use it.
        """
        thesis_id = thesis.theses_id
        ticker = thesis.stocks_mapping.ticker

        evaluation_id = evaluation.evaluation_id
        reason = evaluation.reason

        logger.info("SIGNAL fired for thesis %s (%s): %s", thesis_id, ticker, reason)
        alert_repo = AlertRepository(session)

        chat_id = thesis.users_mapping.telegram_chat_id
        user_id = thesis.user_id
        if chat_id:
            build_request = CreateAlertRequest(
                evaluation_id=evaluation_id,
                user_id=user_id,
                channels_sent=AlertChannelsEnum.TELEGRAM
            )
            alert = await alert_repo.create_alert(build_request)

            text = f"🟢 Signal firing: *{ticker}*\n{reason}"
            await self._telegram_service.send_notification_on_telegram(alert, chat_id, text, user_id)

        try:
            await manager.push_to_user(
                user_id,
                WebSocketEventTypeEnum.ALERT,
                {"theses_id": thesis_id, "ticker": ticker, "reason": reason,
                 "evaluated_at": evaluation.created_at},
            )
        except Exception:
            logger.warning("scheduler: WS push failed for user %s", user_id)


scheduler = SchedulerService(telegram_service=Depends(get_telegram_service))
