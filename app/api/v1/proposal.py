from fastapi import APIRouter, Depends, Query

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import DataResponse
from app.dto.error import ErrorResponse
from app.dto.proposal import (
    RetrieveAllThesesProposalResponse, RetrieveAllQuantProposalResponse, RetrieveAllCatalystProposalResponse,
    RetrieveAllProposalsResponse,
)
from app.enums.ErrorEnum import ErrorEnum
from app.enums.ProposalEnum import ProposalStatusEnum
from app.models import User
from app.service.proposal_service import get_proposal_service, ProposalService

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.get("", response_model=DataResponse[RetrieveAllProposalsResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_all_proposals(
        status: ProposalStatusEnum | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100), current_user: User = Depends(get_current_user),
        proposal_service: ProposalService = Depends(get_proposal_service)):
    all_proposals = await proposal_service.get_all_proposals(user_id=current_user.user_id, status=status, page=page,
                                                             page_size=page_size)
    return DataResponse(result=all_proposals)


@router.get("/theses", response_model=DataResponse[RetrieveAllThesesProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_all_theses_proposal(
        status: ProposalStatusEnum | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100), current_user: User = Depends(get_current_user),
        proposal_service: ProposalService = Depends(get_proposal_service)):
    theses_proposals = await proposal_service.get_all_theses_proposals(
        user_id=current_user.user_id, theses_proposal_status=status, page=page, page_size=page_size)
    return DataResponse(result=theses_proposals)


@router.get("/quant", response_model=DataResponse[RetrieveAllQuantProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_all_quant_proposals(
        status: ProposalStatusEnum | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100), current_user: User = Depends(get_current_user),
        proposal_service: ProposalService = Depends(get_proposal_service)):
    quant_proposals = await proposal_service.get_all_quant_proposals(
        user_id=current_user.user_id, quant_proposal_status=status, page=page, page_size=page_size)
    return DataResponse(result=quant_proposals)


@router.get("/catalysts", response_model=DataResponse[RetrieveAllCatalystProposalResponse])
async def retrieve_all_catalyst_proposals(
        status: ProposalStatusEnum | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100), current_user: User = Depends(get_current_user),
        proposal_service: ProposalService = Depends(get_proposal_service)):
    catalyst_proposals = await proposal_service.get_all_catalyst_proposals(
        user_id=current_user.user_id, catalyst_proposal_status=status, page=page, page_size=page_size)
    return DataResponse(result=catalyst_proposals)
