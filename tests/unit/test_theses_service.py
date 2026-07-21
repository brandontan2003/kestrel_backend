"""
Unit tests for ThesesService.

Strategy: every repository dependency is replaced with an AsyncMock, so
these tests run in milliseconds with no DB, no network, and no FastAPI app.
What we're verifying:
  - the service delegates to the right repo method with the right args
  - ownership checks (user_id mismatch → 404)
  - pagination maths (total_pages ceiling division)
  - create path wires up stock lookup → theses creation → bulk sub-resource creation
"""

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dto.theses import (
    CreateThesesRequest,
    CreateCatalystRequest,
    CreateQuantConditionRequest,
    UpdateThesesRequest,
    QuantConditionRequest,
    CatalystRequest,
)
from app.exception_handler import (
    ThesesNotFoundException,
    StockNotFoundException,
    QuantConditionNotFoundException,
    CatalystNotFoundException,
)
from app.service.theses_service import ThesesService
from common.enums.ThesesEnum import ThesesStatusEnum, QuantModeEnum, CatalystModeEnum


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user_id() -> str:
    return str(uuid.uuid4())


def _make_theses_id() -> str:
    return str(uuid.uuid4())


def _make_stock(ticker: str = "NVDA") -> MagicMock:
    s = MagicMock()
    s.stock_id = str(uuid.uuid4())
    s.ticker = ticker
    return s


def _make_theses(user_id: str, theses_id: str | None = None, ticker: str = "NVDA") -> MagicMock:
    t = MagicMock()
    t.theses_id = theses_id or _make_theses_id()
    t.user_id = user_id
    t.theses_status = ThesesStatusEnum.TRACKING
    t.quant_mode = QuantModeEnum.ANY
    t.catalyst_mode = CatalystModeEnum.ANY
    t.notes = None
    t.stocks_mapping = MagicMock(ticker=ticker)
    t.quant_conditions_mapping = []
    t.catalyst_mapping = []
    return t


def _make_service(
        theses_repo=None,
        stock_repo=None,
        quant_condition_repo=None,
        catalyst_repo=None,
        evaluation_repo=None,
) -> ThesesService:
    return ThesesService(
        theses_repo=theses_repo or AsyncMock(),
        stock_repo=stock_repo or AsyncMock(),
        quant_condition_repo=quant_condition_repo or AsyncMock(),
        catalyst_repo=catalyst_repo or AsyncMock(),
        evaluation_repo=evaluation_repo or AsyncMock(),
    )


# ---------------------------------------------------------------------------
# delete_theses
# ---------------------------------------------------------------------------

class TestDeleteTheses:
    async def test_deletes_when_owner(self):
        user_id = _make_user_id()
        theses = _make_theses(user_id)

        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = theses

        svc = _make_service(theses_repo=theses_repo)
        result = await svc.delete_theses(theses.theses_id, user_id)

        theses_repo.delete_theses.assert_awaited_once_with(theses)
        assert result.status == "SUCCESS"

    async def test_raises_when_theses_not_found(self):
        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = None

        svc = _make_service(theses_repo=theses_repo)

        with pytest.raises(ThesesNotFoundException):
            await svc.delete_theses(_make_theses_id(), _make_user_id())

    async def test_raises_when_wrong_owner(self):
        """Theses exists but belongs to a different user."""
        theses = _make_theses(user_id=_make_user_id())
        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = theses

        svc = _make_service(theses_repo=theses_repo)

        with pytest.raises(ThesesNotFoundException):
            await svc.delete_theses(theses.theses_id, user_id=_make_user_id())  # different caller


# ---------------------------------------------------------------------------
# create_theses
# ---------------------------------------------------------------------------

class TestCreateTheses:
    def _request(self, ticker: str = "NVDA") -> CreateThesesRequest:
        return CreateThesesRequest(
            ticker=ticker,
            quant_mode=QuantModeEnum.ANY,
            catalyst_mode=CatalystModeEnum.ANY,
            notes="test thesis",
            quant_conditions=[
                QuantConditionRequest(metric="forward_pe", operator="<", value=Decimal("28"))
            ],
            catalysts=[
                CatalystRequest(state="unconfirmed", description="hyperscaler capex cut")
            ],
        )

    async def test_raises_when_stock_not_found(self):
        stock_repo = AsyncMock()
        stock_repo.get_stock_by_ticker.return_value = None

        svc = _make_service(stock_repo=stock_repo)

        with pytest.raises(StockNotFoundException):
            await svc.create_theses(_make_user_id(), self._request())

    async def test_creates_theses_with_sub_resources(self):
        user_id = _make_user_id()
        stock = _make_stock()

        stock_repo = AsyncMock()
        stock_repo.get_stock_by_ticker.return_value = stock

        theses_id = _make_theses_id()
        created_theses = _make_theses(user_id, theses_id=theses_id)

        theses_repo = AsyncMock()
        # create_theses returns the bare (un-expired) theses; second call after expire returns the full one
        theses_repo.create_theses.return_value = created_theses
        theses_repo.get_theses_by_theses_id.return_value = created_theses

        quant_condition_repo = AsyncMock()
        catalyst_repo = AsyncMock()

        svc = _make_service(
            theses_repo=theses_repo,
            stock_repo=stock_repo,
            quant_condition_repo=quant_condition_repo,
            catalyst_repo=catalyst_repo,
        )

        request = self._request()
        result = await svc.create_theses(user_id, request)

        # Stock lookup used the right ticker
        stock_repo.get_stock_by_ticker.assert_awaited_once_with("NVDA")

        # Theses row created with correct FK
        theses_repo.create_theses.assert_awaited_once_with(
            user_id=user_id,
            stock_id=stock.stock_id,
            quant_mode=QuantModeEnum.ANY,
            catalyst_mode=CatalystModeEnum.ANY,
            notes="test thesis",
        )

        # Sub-resources bulk-created
        quant_condition_repo.bulk_create_quant_condition.assert_awaited_once()
        catalyst_repo.bulk_create_catalysts.assert_awaited_once()

        # Response carries theses_id
        assert result.theses_id == theses_id

    async def test_skips_bulk_create_when_no_sub_resources(self):
        """Empty lists → neither bulk_create should be called."""
        user_id = _make_user_id()
        stock = _make_stock()
        stock_repo = AsyncMock()
        stock_repo.get_stock_by_ticker.return_value = stock

        theses = _make_theses(user_id)
        theses_repo = AsyncMock()
        theses_repo.create_theses.return_value = theses
        theses_repo.get_theses_by_theses_id.return_value = theses

        quant_condition_repo = AsyncMock()
        catalyst_repo = AsyncMock()

        svc = _make_service(
            theses_repo=theses_repo,
            stock_repo=stock_repo,
            quant_condition_repo=quant_condition_repo,
            catalyst_repo=catalyst_repo,
        )

        request = CreateThesesRequest(
            ticker="NVDA",
            quant_mode=QuantModeEnum.ANY,
            catalyst_mode=CatalystModeEnum.ANY,
            quant_conditions=[],
            catalysts=[],
        )
        await svc.create_theses(user_id, request)

        quant_condition_repo.bulk_create_quant_condition.assert_not_awaited()
        catalyst_repo.bulk_create_catalysts.assert_not_awaited()


# ---------------------------------------------------------------------------
# retrieve_all_theses — pagination
# ---------------------------------------------------------------------------

class TestRetrieveAllTheses:
    async def test_pagination_total_pages_ceiling(self):
        """21 items / page_size=20 → total_pages=2 (ceiling division)."""
        user_id = _make_user_id()
        theses_list = [_make_theses(user_id) for _ in range(20)]  # one page of results

        theses_repo = AsyncMock()
        theses_repo.get_all_theses_by_user_id.return_value = (theses_list, 21)

        evaluation_repo = AsyncMock()
        evaluation_repo.get_latest_evaluations_by_user_id.return_value = {}

        svc = _make_service(theses_repo=theses_repo, evaluation_repo=evaluation_repo)
        result = await svc.retrieve_all_theses(user_id, page=1, page_size=20)

        assert result.total == 21
        assert result.total_pages == 2

    async def test_pagination_exact_multiple(self):
        """20 items / page_size=20 → total_pages=1."""
        user_id = _make_user_id()
        theses_list = [_make_theses(user_id) for _ in range(20)]

        theses_repo = AsyncMock()
        theses_repo.get_all_theses_by_user_id.return_value = (theses_list, 20)

        evaluation_repo = AsyncMock()
        evaluation_repo.get_latest_evaluations_by_user_id.return_value = {}

        svc = _make_service(theses_repo=theses_repo, evaluation_repo=evaluation_repo)
        result = await svc.retrieve_all_theses(user_id, page=1, page_size=20)

        assert result.total_pages == 1

    async def test_returns_empty_list_when_no_theses(self):
        theses_repo = AsyncMock()
        theses_repo.get_all_theses_by_user_id.return_value = ([], 0)

        evaluation_repo = AsyncMock()
        evaluation_repo.get_latest_evaluations_by_user_id.return_value = {}

        svc = _make_service(theses_repo=theses_repo, evaluation_repo=evaluation_repo)
        result = await svc.retrieve_all_theses(_make_user_id(), page=1, page_size=20)

        assert result.theses == []
        assert result.total == 0


# ---------------------------------------------------------------------------
# retrieve_theses_by_theses_id
# ---------------------------------------------------------------------------

class TestRetrieveThesesById:
    async def test_returns_theses_for_owner(self):
        user_id = _make_user_id()
        theses = _make_theses(user_id)

        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = theses

        evaluation_repo = AsyncMock()
        evaluation_repo.get_latest_evaluation.return_value = None

        svc = _make_service(theses_repo=theses_repo, evaluation_repo=evaluation_repo)
        result = await svc.retrieve_theses_by_theses_id(theses.theses_id, user_id)

        assert result.theses.theses_id == theses.theses_id
        assert result.user_id == user_id

    async def test_raises_not_found_for_wrong_user(self):
        theses = _make_theses(user_id=_make_user_id())
        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = theses

        svc = _make_service(theses_repo=theses_repo)

        with pytest.raises(ThesesNotFoundException):
            await svc.retrieve_theses_by_theses_id(theses.theses_id, user_id=_make_user_id())


# ---------------------------------------------------------------------------
# update_theses_by_theses_id
# ---------------------------------------------------------------------------

class TestUpdateTheses:
    async def test_updates_successfully(self):
        user_id = _make_user_id()
        theses = _make_theses(user_id)

        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = theses
        theses_repo.update_theses.return_value = theses

        evaluation_repo = AsyncMock()
        evaluation_repo.get_latest_evaluation.return_value = None

        svc = _make_service(theses_repo=theses_repo, evaluation_repo=evaluation_repo)
        payload = UpdateThesesRequest(notes="updated note")
        result = await svc.update_theses_by_theses_id(theses.theses_id, user_id, payload)

        theses_repo.update_theses.assert_awaited_once_with(theses, payload)
        assert result.user_id == user_id

    async def test_raises_not_found_for_wrong_user(self):
        theses = _make_theses(user_id=_make_user_id())
        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = theses

        svc = _make_service(theses_repo=theses_repo)

        with pytest.raises(ThesesNotFoundException):
            await svc.update_theses_by_theses_id(
                theses.theses_id, _make_user_id(), UpdateThesesRequest()
            )


# ---------------------------------------------------------------------------
# add_quant_condition
# ---------------------------------------------------------------------------

class TestAddQuantCondition:
    async def test_adds_condition_and_returns_updated_theses(self):
        user_id = _make_user_id()
        theses = _make_theses(user_id)

        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = theses

        evaluation_repo = AsyncMock()
        evaluation_repo.get_latest_evaluation.return_value = None

        quant_condition_repo = AsyncMock()

        svc = _make_service(
            theses_repo=theses_repo,
            quant_condition_repo=quant_condition_repo,
            evaluation_repo=evaluation_repo,
        )

        request = CreateQuantConditionRequest(metric="forward_pe", operator="<", value=Decimal("28"))
        await svc.add_quant_condition(theses.theses_id, user_id, request)

        quant_condition_repo.create_quant_condition.assert_awaited_once_with(
            theses_id=theses.theses_id,
            metric="forward_pe",
            operator="<",
            value=Decimal("28"),
        )

    async def test_raises_when_theses_not_found(self):
        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = None

        svc = _make_service(theses_repo=theses_repo)

        with pytest.raises(ThesesNotFoundException):
            await svc.add_quant_condition(
                _make_theses_id(), _make_user_id(),
                CreateQuantConditionRequest(metric="forward_pe", operator="<", value=Decimal("28"))
            )


# ---------------------------------------------------------------------------
# delete_quant_condition
# ---------------------------------------------------------------------------

class TestDeleteQuantCondition:
    async def test_deletes_condition(self):
        user_id = _make_user_id()
        condition = MagicMock()
        condition_id = str(uuid.uuid4())

        quant_condition_repo = AsyncMock()
        quant_condition_repo.get_quant_condition_by_id_and_user.return_value = condition

        svc = _make_service(quant_condition_repo=quant_condition_repo)
        result = await svc.delete_quant_condition(_make_theses_id(), condition_id, user_id)

        quant_condition_repo.delete_quant_condition.assert_awaited_once_with(condition)
        assert result.status == "SUCCESS"

    async def test_raises_when_condition_not_found(self):
        quant_condition_repo = AsyncMock()
        quant_condition_repo.get_quant_condition_by_id_and_user.return_value = None

        svc = _make_service(quant_condition_repo=quant_condition_repo)

        with pytest.raises(QuantConditionNotFoundException):
            await svc.delete_quant_condition(_make_theses_id(), str(uuid.uuid4()), _make_user_id())


# ---------------------------------------------------------------------------
# add_catalyst
# ---------------------------------------------------------------------------

class TestAddCatalyst:
    async def test_adds_catalyst(self):
        user_id = _make_user_id()
        theses = _make_theses(user_id)

        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = theses

        evaluation_repo = AsyncMock()
        evaluation_repo.get_latest_evaluation.return_value = None

        catalyst_repo = AsyncMock()

        svc = _make_service(
            theses_repo=theses_repo,
            catalyst_repo=catalyst_repo,
            evaluation_repo=evaluation_repo,
        )

        request = CreateCatalystRequest(state="unconfirmed", description="FDA approval")
        await svc.add_catalyst(theses.theses_id, user_id, request)

        catalyst_repo.create_catalyst.assert_awaited_once_with(
            theses_id=theses.theses_id,
            state="unconfirmed",
            description="FDA approval",
            evidence=None,
        )

    async def test_raises_when_theses_not_found(self):
        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id.return_value = None

        svc = _make_service(theses_repo=theses_repo)

        with pytest.raises(ThesesNotFoundException):
            await svc.add_catalyst(
                _make_theses_id(), _make_user_id(),
                CreateCatalystRequest(state="unconfirmed")
            )


# ---------------------------------------------------------------------------
# delete_catalyst
# ---------------------------------------------------------------------------

class TestDeleteCatalyst:
    async def test_deletes_catalyst(self):
        user_id = _make_user_id()
        catalyst = MagicMock()
        catalyst_id = str(uuid.uuid4())

        catalyst_repo = AsyncMock()
        catalyst_repo.get_catalyst_by_id_and_user.return_value = catalyst

        svc = _make_service(catalyst_repo=catalyst_repo)
        result = await svc.delete_catalyst(_make_theses_id(), catalyst_id, user_id)

        catalyst_repo.delete_catalyst.assert_awaited_once_with(catalyst)
        assert result.status == "SUCCESS"

    async def test_raises_when_catalyst_not_found(self):
        catalyst_repo = AsyncMock()
        catalyst_repo.get_catalyst_by_id_and_user.return_value = None

        svc = _make_service(catalyst_repo=catalyst_repo)

        with pytest.raises(CatalystNotFoundException):
            await svc.delete_catalyst(_make_theses_id(), str(uuid.uuid4()), _make_user_id())


# ---------------------------------------------------------------------------
# retrieve_evaluations_by_theses_id
# ---------------------------------------------------------------------------

class TestRetrieveEvaluations:
    async def test_raises_when_theses_not_owned_by_user(self):
        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id_and_user_id.return_value = None

        svc = _make_service(theses_repo=theses_repo)

        with pytest.raises(ThesesNotFoundException):
            await svc.retrieve_evaluations_by_theses_id(_make_theses_id(), _make_user_id(), 1, 20)

    async def test_returns_evaluations_with_correct_pagination(self):
        user_id = _make_user_id()
        theses_id = _make_theses_id()

        theses_repo = AsyncMock()
        theses_repo.get_theses_by_theses_id_and_user_id.return_value = _make_theses(user_id, theses_id)

        fake_eval = MagicMock()
        fake_eval.__dict__ = {
            "evaluation_id": str(uuid.uuid4()),
            "theses_id": theses_id,
            "evaluation_status": "Some Status",
            "signal": True,
            "reason": "met conditions",
            "prompt_version": "prompt_version",
            "results": {},
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        evaluation_repo = AsyncMock()
        evaluation_repo.get_all_evaluation_by_theses_id.return_value = ([fake_eval], 1)

        svc = _make_service(theses_repo=theses_repo, evaluation_repo=evaluation_repo)
        result = await svc.retrieve_evaluations_by_theses_id(theses_id, user_id, page=1, page_size=20)

        assert result.total == 1
        assert result.total_pages == 1
        assert result.theses_id == theses_id
