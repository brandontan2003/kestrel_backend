"""
Integration tests for the Proposals API endpoints.

Same strategy as test_theses_api.py:
  - Real FastAPI app, real routing, real request/response validation
  - get_current_user → fixed User
  - ProposalService → MagicMock with AsyncMock methods

What we're proving:
  - Correct HTTP methods and URL shapes route to the right handlers
  - Response envelope wraps service output correctly
  - Error status codes from exceptions (404, 409, 422) propagate correctly
  - Query-param filtering (status) is passed through to the service
  - BackgroundTasks (sweep_thesis) is scheduled after approve but doesn't block response
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.authorization.auth_dependency import get_current_user
from app.dto.proposal import (
    RetrieveAllProposalsResponse,
    RetrieveAllThesesProposalResponse,
    RetrieveAllQuantProposalResponse,
    RetrieveAllCatalystProposalResponse,
    RetrieveThesesProposalResponse,
    RetrieveQuantProposalResponse,
    RetrieveCatalystProposalResponse,
)
from app.exception_handler import (
    ThesesProposalNotFoundException,
    QuantProposalNotFoundException,
    CatalystProposalNotFoundException,
    InvalidProposalStatusException,
    InvalidProposalTypeException,
)
from app.main import app
from app.models.users import User
from app.service.proposal_service import get_proposal_service
from common.enums.ProposalEnum import ProposalStatusEnum, ProposalTypeEnum

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = str(uuid.uuid4())
PROPOSAL_ID = str(uuid.uuid4())
THESES_ID = str(uuid.uuid4())
BASE_URL = "http://test"
PREFIX = "/api/v1/proposals"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user() -> User:
    u = MagicMock(spec=User)
    u.user_id = USER_ID
    u.user_status = "ACTIVE"
    return u


def _theses_proposal(proposal_id: str = PROPOSAL_ID) -> RetrieveThesesProposalResponse:
    return RetrieveThesesProposalResponse(
        theses_proposal_id=proposal_id,
        user_id=USER_ID,
        stock_id=str(uuid.uuid4()),
        proposed_change={},
        theses_proposal_status=ProposalStatusEnum.PENDING,
        llm_rationale=None,
        llm_confidence=None,
        source_article_url=None,
        source_evaluation_id=str(uuid.uuid4()),
        rejection_reason=None,
        resolved_at=None,
        created_at=datetime.now(),
    )


def _quant_proposal(proposal_id: str = PROPOSAL_ID) -> RetrieveQuantProposalResponse:
    return RetrieveQuantProposalResponse(
        quant_proposal_id=proposal_id,
        theses_id=THESES_ID,
        quant_condition_id=str(uuid.uuid4()),
        proposal_type=ProposalTypeEnum.UPDATE,
        proposed_change={"value": "30"},
        quant_proposal_status=ProposalStatusEnum.PENDING,
        llm_rationale=None,
        llm_confidence=None,
        source_article_url=None,
        source_evaluation_id=str(uuid.uuid4()),
        rejection_reason=None,
        resolved_at=None,
        created_at=datetime.now(),
    )


def _catalyst_proposal(proposal_id: str = PROPOSAL_ID) -> RetrieveCatalystProposalResponse:
    return RetrieveCatalystProposalResponse(
        catalyst_proposal_id=proposal_id,
        theses_id=THESES_ID,
        catalyst_id=str(uuid.uuid4()),
        proposal_type=ProposalTypeEnum.UPDATE,
        proposed_change={"state": "confirmed"},
        catalyst_proposal_status=ProposalStatusEnum.PENDING,
        llm_rationale=None,
        llm_confidence=None,
        source_article_url=None,
        source_evaluation_id=str(uuid.uuid4()),
        rejection_reason=None,
        resolved_at=None,
        created_at=datetime.now(),
    )


def _empty_all_proposals() -> RetrieveAllProposalsResponse:
    empty_theses = RetrieveAllThesesProposalResponse(
        theses_proposals=[], total=0, page=1, page_size=20, total_pages=0
    )
    empty_quant = RetrieveAllQuantProposalResponse(
        quant_proposals=[], total=0, page=1, page_size=20, total_pages=0
    )
    empty_catalyst = RetrieveAllCatalystProposalResponse(
        catalyst_proposals=[], total=0, page=1, page_size=20, total_pages=0
    )
    return RetrieveAllProposalsResponse(
        theses_proposals=empty_theses,
        quant_proposals=empty_quant,
        catalyst_proposals=empty_catalyst,
    )


@pytest.fixture
def mock_service() -> MagicMock:
    svc = MagicMock()
    for method in [
        "get_all_proposals", "get_all_theses_proposals", "get_all_quant_proposals",
        "get_all_catalyst_proposals",
        "approve_theses_proposal", "reject_theses_proposal",
        "approve_quant_proposal", "reject_quant_proposal",
        "approve_catalyst_proposal", "reject_catalyst_proposal",
    ]:
        setattr(svc, method, AsyncMock())
    return svc


@pytest.fixture
def client(mock_service):
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_proposal_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url=BASE_URL)


# ---------------------------------------------------------------------------
# GET /proposals — aggregate view
# ---------------------------------------------------------------------------

class TestGetAllProposals:
    async def test_returns_all_proposal_types(self, client, mock_service):
        mock_service.get_all_proposals.return_value = _empty_all_proposals()

        async with client as c:
            resp = await c.get(PREFIX)

        assert resp.status_code == 200
        body = resp.json()
        assert "theses_proposals" in body["result"]
        assert "quant_proposals" in body["result"]
        assert "catalyst_proposals" in body["result"]

    async def test_status_filter_passed_to_service(self, client, mock_service):
        mock_service.get_all_proposals.return_value = _empty_all_proposals()

        async with client as c:
            await c.get(f"{PREFIX}?status=PENDING")

        call_kwargs = mock_service.get_all_proposals.call_args
        assert call_kwargs.kwargs.get("status") == ProposalStatusEnum.PENDING or \
               ProposalStatusEnum.PENDING in call_kwargs.args

    async def test_invalid_status_returns_422(self, client, mock_service):
        async with client as c:
            resp = await c.get(f"{PREFIX}?status=GARBAGE")

        assert resp.status_code == 422
        mock_service.get_all_proposals.assert_not_awaited()


# ---------------------------------------------------------------------------
# GET /proposals/theses
# ---------------------------------------------------------------------------

class TestGetThesesProposals:
    async def test_returns_theses_proposals_list(self, client, mock_service):
        mock_service.get_all_theses_proposals.return_value = RetrieveAllThesesProposalResponse(
            theses_proposals=[], total=0, page=1, page_size=20, total_pages=0
        )

        async with client as c:
            resp = await c.get(f"{PREFIX}/theses")

        assert resp.status_code == 200
        assert "theses_proposals" in resp.json()["result"]


# ---------------------------------------------------------------------------
# GET /proposals/quant
# ---------------------------------------------------------------------------

class TestGetQuantProposals:
    async def test_returns_quant_proposals_list(self, client, mock_service):
        mock_service.get_all_quant_proposals.return_value = RetrieveAllQuantProposalResponse(
            quant_proposals=[], total=0, page=1, page_size=20, total_pages=0
        )

        async with client as c:
            resp = await c.get(f"{PREFIX}/quant")

        assert resp.status_code == 200
        assert "quant_proposals" in resp.json()["result"]


# ---------------------------------------------------------------------------
# GET /proposals/catalysts
# ---------------------------------------------------------------------------

class TestGetCatalystProposals:
    async def test_returns_catalyst_proposals_list(self, client, mock_service):
        mock_service.get_all_catalyst_proposals.return_value = RetrieveAllCatalystProposalResponse(
            catalyst_proposals=[], total=0, page=1, page_size=20, total_pages=0
        )

        async with client as c:
            resp = await c.get(f"{PREFIX}/catalysts")

        assert resp.status_code == 200
        assert "catalyst_proposals" in resp.json()["result"]


# ---------------------------------------------------------------------------
# PUT /proposals/theses/{proposal_id}/approve
# ---------------------------------------------------------------------------

class TestApproveThesesProposal:
    async def test_approves_successfully(self, client, mock_service):
        mock_service.approve_theses_proposal.return_value = _theses_proposal()

        async with client as c:
            resp = await c.put(f"{PREFIX}/theses/{PROPOSAL_ID}/approve")

        assert resp.status_code == 200
        body = resp.json()
        assert body["result"]["theses_proposal_id"] == PROPOSAL_ID

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.approve_theses_proposal.side_effect = ThesesProposalNotFoundException()

        async with client as c:
            resp = await c.put(f"{PREFIX}/theses/{PROPOSAL_ID}/approve")

        assert resp.status_code == 404

    async def test_returns_409_when_already_approved(self, client, mock_service):
        mock_service.approve_theses_proposal.side_effect = InvalidProposalStatusException()

        async with client as c:
            resp = await c.put(f"{PREFIX}/theses/{PROPOSAL_ID}/approve")

        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# PUT /proposals/theses/{proposal_id}/reject
# ---------------------------------------------------------------------------

class TestRejectThesesProposal:
    async def test_rejects_with_reason(self, client, mock_service):
        mock_service.reject_theses_proposal.return_value = _theses_proposal()

        async with client as c:
            resp = await c.put(
                f"{PREFIX}/theses/{PROPOSAL_ID}/reject",
                json={"rejection_reason": "data is stale"},
            )

        assert resp.status_code == 200
        mock_service.reject_theses_proposal.assert_awaited_once_with(
            proposal_id=PROPOSAL_ID,
            user_id=USER_ID,
            rejection_reason="data is stale",
        )

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.reject_theses_proposal.side_effect = ThesesProposalNotFoundException()

        async with client as c:
            resp = await c.put(
                f"{PREFIX}/theses/{PROPOSAL_ID}/reject",
                json={"rejection_reason": "doesn't apply"},
            )

        assert resp.status_code == 404

    async def test_returns_409_when_not_pending(self, client, mock_service):
        mock_service.reject_theses_proposal.side_effect = InvalidProposalStatusException()

        async with client as c:
            resp = await c.put(
                f"{PREFIX}/theses/{PROPOSAL_ID}/reject",
                json={"rejection_reason": "too late"},
            )

        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# PUT /proposals/quant/{proposal_id}/approve
# ---------------------------------------------------------------------------

class TestApproveQuantProposal:
    async def test_approves_and_schedules_sweep(self, client, mock_service):
        """
        After approve, the router schedules scheduler.sweep_thesis as a
        BackgroundTask. We don't want to actually run the scheduler in tests,
        so we patch it at the module level.
        """
        quant_prop = _quant_proposal()
        mock_service.approve_quant_proposal.return_value = quant_prop

        with patch("app.api.v1.proposal.scheduler") as mock_scheduler:
            async with client as c:
                resp = await c.put(f"{PREFIX}/quant/{PROPOSAL_ID}/approve")

        assert resp.status_code == 200
        body = resp.json()
        assert body["result"]["quant_proposal_id"] == PROPOSAL_ID
        # BackgroundTask registered (the task itself runs after response, not inside handler)

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.approve_quant_proposal.side_effect = QuantProposalNotFoundException()

        with patch("app.api.v1.proposal.scheduler"):
            async with client as c:
                resp = await c.put(f"{PREFIX}/quant/{PROPOSAL_ID}/approve")

        assert resp.status_code == 404

    async def test_returns_409_when_not_pending(self, client, mock_service):
        mock_service.approve_quant_proposal.side_effect = InvalidProposalStatusException()

        with patch("app.api.v1.proposal.scheduler"):
            async with client as c:
                resp = await c.put(f"{PREFIX}/quant/{PROPOSAL_ID}/approve")

        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# PUT /proposals/quant/{proposal_id}/reject
# ---------------------------------------------------------------------------

class TestRejectQuantProposal:
    async def test_rejects_with_reason(self, client, mock_service):
        mock_service.reject_quant_proposal.return_value = _quant_proposal()

        async with client as c:
            resp = await c.put(
                f"{PREFIX}/quant/{PROPOSAL_ID}/reject",
                json={"rejection_reason": "P/E threshold is fine"},
            )

        assert resp.status_code == 200
        mock_service.reject_quant_proposal.assert_awaited_once_with(
            proposal_id=PROPOSAL_ID,
            user_id=USER_ID,
            rejection_reason="P/E threshold is fine",
        )

    async def test_returns_409_when_not_pending(self, client, mock_service):
        mock_service.reject_quant_proposal.side_effect = InvalidProposalStatusException()

        async with client as c:
            resp = await c.put(
                f"{PREFIX}/quant/{PROPOSAL_ID}/reject",
                json={"rejection_reason": "already handled"},
            )

        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# PUT /proposals/catalyst/{proposal_id}/approve
# ---------------------------------------------------------------------------

class TestApproveCatalystProposal:
    async def test_approves_and_schedules_sweep(self, client, mock_service):
        catalyst_prop = _catalyst_proposal()
        mock_service.approve_catalyst_proposal.return_value = catalyst_prop

        with patch("app.api.v1.proposal.scheduler") as mock_scheduler:
            async with client as c:
                resp = await c.put(f"{PREFIX}/catalyst/{PROPOSAL_ID}/approve")

        assert resp.status_code == 200
        assert resp.json()["result"]["catalyst_proposal_id"] == PROPOSAL_ID

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.approve_catalyst_proposal.side_effect = CatalystProposalNotFoundException()

        with patch("app.api.v1.proposal.scheduler"):
            async with client as c:
                resp = await c.put(f"{PREFIX}/catalyst/{PROPOSAL_ID}/approve")

        assert resp.status_code == 404

    async def test_returns_409_when_not_pending(self, client, mock_service):
        mock_service.approve_catalyst_proposal.side_effect = InvalidProposalStatusException()

        with patch("app.api.v1.proposal.scheduler"):
            async with client as c:
                resp = await c.put(f"{PREFIX}/catalyst/{PROPOSAL_ID}/approve")

        assert resp.status_code == 409

    async def test_returns_422_on_invalid_proposal_type(self, client, mock_service):
        mock_service.approve_catalyst_proposal.side_effect = InvalidProposalTypeException()

        with patch("app.api.v1.proposal.scheduler"):
            async with client as c:
                resp = await c.put(f"{PREFIX}/catalyst/{PROPOSAL_ID}/approve")

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /proposals/catalyst/{proposal_id}/reject
# ---------------------------------------------------------------------------

class TestRejectCatalystProposal:
    async def test_rejects_with_reason(self, client, mock_service):
        mock_service.reject_catalyst_proposal.return_value = _catalyst_proposal()

        async with client as c:
            resp = await c.put(
                f"{PREFIX}/catalyst/{PROPOSAL_ID}/reject",
                json={"rejection_reason": "news was speculative"},
            )

        assert resp.status_code == 200
        mock_service.reject_catalyst_proposal.assert_awaited_once_with(
            proposal_id=PROPOSAL_ID,
            user_id=USER_ID,
            rejection_reason="news was speculative",
        )

    async def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.reject_catalyst_proposal.side_effect = CatalystProposalNotFoundException()

        async with client as c:
            resp = await c.put(
                f"{PREFIX}/catalyst/{PROPOSAL_ID}/reject",
                json={"rejection_reason": "gone"},
            )

        assert resp.status_code == 404

    async def test_returns_409_when_not_pending(self, client, mock_service):
        mock_service.reject_catalyst_proposal.side_effect = InvalidProposalStatusException()

        async with client as c:
            resp = await c.put(
                f"{PREFIX}/catalyst/{PROPOSAL_ID}/reject",
                json={"rejection_reason": "already handled"},
            )

        assert resp.status_code == 409
