"""
Integration tests for the Theses API endpoints.

These tests spin up the real FastAPI app (no running server, no real DB)
and exercise the full HTTP stack: routing, auth dependency, request
validation, response envelope, and error shape.

What's mocked:
  - get_current_user  → returns a fixed User object, so every test is
    "authenticated". No JWT signing / decoding needed.
  - ThesesService     → replaced per-test with a MagicMock whose methods
    are pre-configured as AsyncMocks.

What's NOT mocked:
  - FastAPI routing and dependency injection
  - Pydantic request/response validation
  - Exception handlers and error-response shape
  - DataResponse / SuccessResponse envelope

This means a mistake in the router (wrong HTTP method, missing path
param, wrong response model) will surface here, not just in unit tests.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import SuccessResponse
from app.dto.theses import (
    CreateThesesResponse,
    RetrieveThesesResponse,
    ThesesResponse,
    RetrieveAllThesesResponse,
    RetrieveAllEvaluationResponse,
)
from app.exception_handler import (
    ThesesNotFoundException,
    StockNotFoundException,
    QuantConditionNotFoundException,
    CatalystNotFoundException,
)
from app.main import app
from app.models.users import User
from app.service.theses_service import get_theses_service
from common.enums.ThesesEnum import ThesesStatusEnum, QuantModeEnum, CatalystModeEnum

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = str(uuid.uuid4())
THESES_ID = str(uuid.uuid4())
CONDITION_ID = str(uuid.uuid4())
CATALYST_ID = str(uuid.uuid4())

BASE_URL = "http://test"
THESES_PREFIX = "/api/v1/theses"


def _make_user() -> User:
    u = MagicMock(spec=User)
    u.user_id = USER_ID
    u.user_status = "ACTIVE"
    return u


def _make_theses_response(theses_id: str = THESES_ID) -> ThesesResponse:
    return ThesesResponse(
        theses_id=theses_id,
        ticker="NVDA",
        theses_status=ThesesStatusEnum.TRACKING,
        quant_mode=QuantModeEnum.ANY,
        catalyst_mode=CatalystModeEnum.ANY,
        notes=None,
        quant_conditions=[],
        catalysts=[],
        latest_evaluation=None,
    )


def _make_retrieve_theses_response(theses_id: str = THESES_ID) -> RetrieveThesesResponse:
    return RetrieveThesesResponse(user_id=USER_ID, theses=_make_theses_response(theses_id))


def _make_create_theses_response(theses_id: str = THESES_ID) -> CreateThesesResponse:
    return CreateThesesResponse(
        theses_id=theses_id,
        ticker="NVDA",
        theses_status=ThesesStatusEnum.TRACKING,
        quant_mode=QuantModeEnum.ANY,
        catalyst_mode=CatalystModeEnum.ANY,
        notes=None,
        quant_conditions=[],
        catalysts=[],
    )


@pytest.fixture
def mock_service() -> MagicMock:
    svc = MagicMock()
    # Make every method an AsyncMock by default so tests can override as needed
    for method in [
        "create_theses", "retrieve_theses_by_theses_id", "retrieve_all_theses",
        "update_theses_by_theses_id", "delete_theses",
        "add_quant_condition", "update_quant_condition", "delete_quant_condition",
        "add_catalyst", "update_catalyst", "delete_catalyst",
        "retrieve_evaluations_by_theses_id",
    ]:
        setattr(svc, method, AsyncMock())
    return svc


@pytest.fixture
def auth_user() -> User:
    return _make_user()


@pytest.fixture
def client(mock_service, auth_user):
    """
    Returns an httpx AsyncClient with:
      - get_current_user overridden to return a fixed user
      - get_theses_service overridden to return mock_service
    """
    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_theses_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url=BASE_URL)


# ---------------------------------------------------------------------------
# POST /theses  — create
# ---------------------------------------------------------------------------

class TestCreateTheses:
    async def test_returns_201_envelope(self, client, mock_service):
        mock_service.create_theses.return_value = _make_create_theses_response()

        payload = {
            "ticker": "NVDA",
            "quant_mode": "ANY",
            "catalyst_mode": "ANY",
            "quant_conditions": [
                {"metric": "forward_pe", "operator": "<", "value": "28"}
            ],
            "catalysts": [
                {"state": "unconfirmed", "description": "hyperscaler capex cut"}
            ],
        }

        async with client as c:
            resp = await c.post(THESES_PREFIX, json=payload)

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "SUCCESS"
        assert body["result"]["theses_id"] == THESES_ID
        assert body["result"]["ticker"] == "NVDA"

    async def test_returns_404_when_stock_not_found(self, client, mock_service):
        mock_service.create_theses.side_effect = StockNotFoundException()

        payload = {
            "ticker": "FAKE",
            "quant_mode": "ANY",
            "catalyst_mode": "ANY",
            "quant_conditions": [],
            "catalysts": [],
        }

        async with client as c:
            resp = await c.post(THESES_PREFIX, json=payload)

        assert resp.status_code == 404
        body = resp.json()
        assert "errors" in body["result"]

    async def test_returns_422_on_invalid_operator(self, client, mock_service):
        payload = {
            "ticker": "NVDA",
            "quant_mode": "ANY",
            "catalyst_mode": "ANY",
            "quant_conditions": [
                {"metric": "forward_pe", "operator": "BETWEEN", "value": "28"}
            ],
            "catalysts": [],
        }

        async with client as c:
            resp = await c.post(THESES_PREFIX, json=payload)

        # Pydantic validator rejects "BETWEEN" — should be 422 before service is even called
        assert resp.status_code == 422
        mock_service.create_theses.assert_not_awaited()

    async def test_returns_422_on_missing_required_fields(self, client, mock_service):
        async with client as c:
            resp = await c.post(THESES_PREFIX, json={})

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /theses/{theses_id}
# ---------------------------------------------------------------------------

class TestGetThesesById:
    async def test_returns_theses(self, client, mock_service):
        mock_service.retrieve_theses_by_theses_id.return_value = _make_retrieve_theses_response()

        async with client as c:
            resp = await c.get(f"{THESES_PREFIX}/{THESES_ID}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["result"]["theses"]["theses_id"] == THESES_ID
        assert body["result"]["user_id"] == USER_ID

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.retrieve_theses_by_theses_id.side_effect = ThesesNotFoundException()

        async with client as c:
            resp = await c.get(f"{THESES_PREFIX}/{THESES_ID}")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /theses  — list
# ---------------------------------------------------------------------------

class TestGetAllTheses:
    async def test_returns_paginated_list(self, client, mock_service):
        mock_service.retrieve_all_theses.return_value = RetrieveAllThesesResponse(
            user_id=USER_ID,
            theses=[_make_theses_response()],
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )

        async with client as c:
            resp = await c.get(THESES_PREFIX)

        assert resp.status_code == 200
        body = resp.json()
        assert body["result"]["total"] == 1
        assert len(body["result"]["theses"]) == 1

    async def test_default_pagination_params_passed_to_service(self, client, mock_service):
        mock_service.retrieve_all_theses.return_value = RetrieveAllThesesResponse(
            user_id=USER_ID, theses=[], total=0, page=1, page_size=20, total_pages=0
        )

        async with client as c:
            await c.get(THESES_PREFIX)

        mock_service.retrieve_all_theses.assert_awaited_once_with(USER_ID, 1, 20)

    async def test_custom_pagination_params(self, client, mock_service):
        mock_service.retrieve_all_theses.return_value = RetrieveAllThesesResponse(
            user_id=USER_ID, theses=[], total=0, page=2, page_size=5, total_pages=0
        )

        async with client as c:
            await c.get(f"{THESES_PREFIX}?page=2&page_size=5")

        mock_service.retrieve_all_theses.assert_awaited_once_with(USER_ID, 2, 5)

    async def test_rejects_page_size_above_cap(self, client, mock_service):
        async with client as c:
            resp = await c.get(f"{THESES_PREFIX}?page_size=101")

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /theses/{theses_id}
# ---------------------------------------------------------------------------

class TestUpdateTheses:
    async def test_updates_successfully(self, client, mock_service):
        mock_service.update_theses_by_theses_id.return_value = _make_retrieve_theses_response()

        async with client as c:
            resp = await c.put(f"{THESES_PREFIX}/{THESES_ID}", json={"notes": "new note"})

        assert resp.status_code == 200
        assert resp.json()["status"] == "SUCCESS"

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.update_theses_by_theses_id.side_effect = ThesesNotFoundException()

        async with client as c:
            resp = await c.put(f"{THESES_PREFIX}/{THESES_ID}", json={"notes": "x"})

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /theses/{theses_id}
# ---------------------------------------------------------------------------

class TestDeleteTheses:
    async def test_deletes_successfully(self, client, mock_service):
        mock_service.delete_theses.return_value = SuccessResponse()

        async with client as c:
            resp = await c.delete(f"{THESES_PREFIX}/{THESES_ID}")

        assert resp.status_code == 200
        assert resp.json()["status"] == "SUCCESS"

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.delete_theses.side_effect = ThesesNotFoundException()

        async with client as c:
            resp = await c.delete(f"{THESES_PREFIX}/{THESES_ID}")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /theses/{theses_id}/quant-condition
# ---------------------------------------------------------------------------

class TestAddQuantCondition:
    async def test_adds_condition(self, client, mock_service):
        mock_service.add_quant_condition.return_value = _make_retrieve_theses_response()

        async with client as c:
            resp = await c.post(
                f"{THESES_PREFIX}/{THESES_ID}/quant-condition",
                json={"metric": "forward_pe", "operator": "<", "value": "28"},
            )

        assert resp.status_code == 200

    async def test_returns_404_when_theses_not_found(self, client, mock_service):
        mock_service.add_quant_condition.side_effect = ThesesNotFoundException()

        async with client as c:
            resp = await c.post(
                f"{THESES_PREFIX}/{THESES_ID}/quant-condition",
                json={"metric": "forward_pe", "operator": "<", "value": "28"},
            )

        assert resp.status_code == 404

    async def test_returns_422_on_invalid_operator(self, client, mock_service):
        async with client as c:
            resp = await c.post(
                f"{THESES_PREFIX}/{THESES_ID}/quant-condition",
                json={"metric": "forward_pe", "operator": "!=", "value": "28"},
            )

        assert resp.status_code == 422
        mock_service.add_quant_condition.assert_not_awaited()


# ---------------------------------------------------------------------------
# DELETE /theses/{theses_id}/quant-condition/{condition_id}
# ---------------------------------------------------------------------------

class TestDeleteQuantCondition:
    async def test_deletes_condition(self, client, mock_service):
        mock_service.delete_quant_condition.return_value = SuccessResponse()

        async with client as c:
            resp = await c.delete(f"{THESES_PREFIX}/{THESES_ID}/quant-condition/{CONDITION_ID}")

        assert resp.status_code == 200

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.delete_quant_condition.side_effect = QuantConditionNotFoundException()

        async with client as c:
            resp = await c.delete(f"{THESES_PREFIX}/{THESES_ID}/quant-condition/{CONDITION_ID}")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /theses/{theses_id}/catalyst
# ---------------------------------------------------------------------------

class TestAddCatalyst:
    async def test_adds_catalyst(self, client, mock_service):
        mock_service.add_catalyst.return_value = _make_retrieve_theses_response()

        async with client as c:
            resp = await c.post(
                f"{THESES_PREFIX}/{THESES_ID}/catalyst",
                json={"state": "unconfirmed", "description": "FDA approval"},
            )

        assert resp.status_code == 200

    async def test_returns_404_when_theses_not_found(self, client, mock_service):
        mock_service.add_catalyst.side_effect = ThesesNotFoundException()

        async with client as c:
            resp = await c.post(
                f"{THESES_PREFIX}/{THESES_ID}/catalyst",
                json={"state": "unconfirmed"},
            )

        assert resp.status_code == 404

    async def test_returns_422_when_state_missing(self, client, mock_service):
        async with client as c:
            resp = await c.post(
                f"{THESES_PREFIX}/{THESES_ID}/catalyst",
                json={"description": "no state field"},
            )

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /theses/{theses_id}/catalyst/{catalyst_id}
# ---------------------------------------------------------------------------

class TestDeleteCatalyst:
    async def test_deletes_catalyst(self, client, mock_service):
        mock_service.delete_catalyst.return_value = SuccessResponse()

        async with client as c:
            resp = await c.delete(f"{THESES_PREFIX}/{THESES_ID}/catalyst/{CATALYST_ID}")

        assert resp.status_code == 200

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.delete_catalyst.side_effect = CatalystNotFoundException()

        async with client as c:
            resp = await c.delete(f"{THESES_PREFIX}/{THESES_ID}/catalyst/{CATALYST_ID}")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /theses/{theses_id}/evaluations
# ---------------------------------------------------------------------------

class TestGetEvaluations:
    async def test_returns_evaluation_list(self, client, mock_service):
        mock_service.retrieve_evaluations_by_theses_id.return_value = RetrieveAllEvaluationResponse(
            theses_id=THESES_ID,
            evaluations=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )

        async with client as c:
            resp = await c.get(f"{THESES_PREFIX}/{THESES_ID}/evaluations")

        assert resp.status_code == 200
        body = resp.json()
        assert body["result"]["theses_id"] == THESES_ID

    async def test_returns_404_when_theses_not_owned(self, client, mock_service):
        mock_service.retrieve_evaluations_by_theses_id.side_effect = ThesesNotFoundException()

        async with client as c:
            resp = await c.get(f"{THESES_PREFIX}/{THESES_ID}/evaluations")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth — 401 without override
# ---------------------------------------------------------------------------

class TestAuth:
    async def test_unauthenticated_request_returns_401(self):
        """Remove the dependency override so the real auth logic runs."""
        app.dependency_overrides.pop(get_current_user, None)
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url=BASE_URL) as c:
            resp = await c.get(f"{THESES_PREFIX}/{THESES_ID}")

        assert resp.status_code == 401
        # Restore for other tests
        app.dependency_overrides[get_current_user] = lambda: _make_user()
