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

from app.config import settings
from app.core.logger import logger
from app.database_registry import get_sessionmaker
from app.models import Theses
from app.repository.catalyst_repository import CatalystRepository
from app.repository.evaluation_repository import EvaluationRepository
from app.repository.theses_repository import ThesesRepository
from app.service import ml_adapter, quant_service
from app.websocket.connection_manager import manager
from common.enums.ThesesEnum import ThesesStatusEnum
from pipeline import catalysts, evaluator, llm, news

# Verdicts whose article never confirms anything don't need persisting as evidence
# unless they bear on the catalyst; the state machine still returns a transition.
_NO_PROMPT = "no_classification"


class SchedulerService:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

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

        await eval_repo.create_evaluation(
            theses_id=theses_id,
            evaluation_status=result["status"],
            prompt_version=prompt_version,
            results=result,
            signal=result["signal"],
            reason=result["reason"],
        )

        if result["signal"] and not was_firing:
            await self._on_signal_fired(thesis, result)

    async def _on_signal_fired(self, thesis: Theses, result: dict) -> None:
        """A thesis's signal just went true. Best-effort live push to the owner.

        Phase 2 proper still owns: persisting an Alert row + the frontend
        consuming this event. The outbound WS infra already exists, so we use it.
        """
        logger.info("SIGNAL fired for thesis %s (%s): %s",
                    thesis.theses_id, result.get("ticker"), result.get("reason"))
        try:
            await manager.push_to_user(
                thesis.user_id,
                "signal",
                {"theses_id": thesis.theses_id, "ticker": result.get("ticker"),
                 "reason": result.get("reason"), "evaluated_at": result.get("evaluated_at")},
            )
        except Exception:
            logger.warning("scheduler: WS push failed for user %s", thesis.user_id)


scheduler = SchedulerService()
