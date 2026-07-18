from fastapi import APIRouter, Depends, Query

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import DataResponse
from app.dto.error import ErrorResponse
from app.dto.proposal import (
    RetrieveAllThesesProposalResponse, RetrieveAllQuantProposalResponse, RetrieveAllCatalystProposalResponse,
    RetrieveAllProposalsResponse, RetrieveQuantProposalResponse, RejectProposalRequest, RetrieveThesesProposalResponse,
    RetrieveCatalystProposalResponse,
)
from app.enums.ErrorEnum import ErrorEnum
from app.models import User
from app.service.proposal_service import get_proposal_service, ProposalService
from common.enums.ProposalEnum import ProposalStatusEnum

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.get("", response_model=DataResponse[RetrieveAllProposalsResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_all_proposals(
        status: ProposalStatusEnum | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100), current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    all_proposals = await service.get_all_proposals(user_id=current_user.user_id, status=status, page=page,
                                                    page_size=page_size)
    return DataResponse(result=all_proposals)


@router.get("/theses", response_model=DataResponse[RetrieveAllThesesProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_all_theses_proposal(
        status: ProposalStatusEnum | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100), current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    theses_proposals = await service.get_all_theses_proposals(
        user_id=current_user.user_id, theses_proposal_status=status, page=page, page_size=page_size)
    return DataResponse(result=theses_proposals)


@router.get("/quant", response_model=DataResponse[RetrieveAllQuantProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_all_quant_proposals(
        status: ProposalStatusEnum | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100), current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    quant_proposals = await service.get_all_quant_proposals(
        user_id=current_user.user_id, quant_proposal_status=status, page=page, page_size=page_size)
    return DataResponse(result=quant_proposals)


@router.get("/catalysts", response_model=DataResponse[RetrieveAllCatalystProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_all_catalyst_proposals(
        status: ProposalStatusEnum | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100), current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    catalyst_proposals = await service.get_all_catalyst_proposals(
        user_id=current_user.user_id, catalyst_proposal_status=status, page=page, page_size=page_size)
    return DataResponse(result=catalyst_proposals)


# Theses Proposal
@router.put("/theses/{proposal_id}/approve", response_model=DataResponse[RetrieveThesesProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.THESES_PROPOSAL_NOT_FOUND.error_code},
                       409: {"model": ErrorResponse, "description": ErrorEnum.INVALID_PROPOSAL_STATUS.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def approve_theses_proposal(
        proposal_id: str, current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    proposal = await service.approve_theses_proposal(proposal_id=proposal_id, user_id=current_user.user_id)
    return DataResponse(result=proposal)


@router.put("/theses/{proposal_id}/reject", response_model=DataResponse[RetrieveThesesProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.THESES_PROPOSAL_NOT_FOUND.error_code},
                       409: {"model": ErrorResponse, "description": ErrorEnum.INVALID_PROPOSAL_STATUS.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def reject_theses_proposal(
        proposal_id: str, payload: RejectProposalRequest, current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    proposal = await service.reject_theses_proposal(
        proposal_id=proposal_id,
        user_id=current_user.user_id,
        rejection_reason=payload.rejection_reason,
    )
    return DataResponse(result=proposal)


# Quant Proposal
@router.put("/quant/{proposal_id}/approve", response_model=DataResponse[RetrieveQuantProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.QUANT_PROPOSAL_NOT_FOUND.error_code},
                       409: {"model": ErrorResponse, "description": ErrorEnum.INVALID_PROPOSAL_STATUS.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.INVALID_PROPOSAL_TYPE.error_code}
                       })
async def approve_quant_proposal(
        proposal_id: str, current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    proposal = await service.approve_quant_proposal(proposal_id=proposal_id, user_id=current_user.user_id)
    return DataResponse(result=proposal)


@router.put("/quant/{proposal_id}/reject", response_model=DataResponse[RetrieveQuantProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.QUANT_PROPOSAL_NOT_FOUND.error_code},
                       409: {"model": ErrorResponse, "description": ErrorEnum.INVALID_PROPOSAL_STATUS.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def reject_quant_proposal(
        proposal_id: str, payload: RejectProposalRequest, current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    proposal = await service.reject_quant_proposal(
        proposal_id=proposal_id,
        user_id=current_user.user_id,
        rejection_reason=payload.rejection_reason,
    )
    return DataResponse(result=proposal)


# Catalyst Proposal
@router.put("/catalyst/{proposal_id}/approve", response_model=DataResponse[RetrieveCatalystProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.CATALYST_PROPOSAL_NOT_FOUND.error_code},
                       409: {"model": ErrorResponse, "description": ErrorEnum.INVALID_PROPOSAL_STATUS.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.INVALID_PROPOSAL_TYPE.error_code}
                       })
async def approve_catalyst_proposal(
        proposal_id: str, current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    proposal = await service.approve_catalyst_proposal(proposal_id=proposal_id, user_id=current_user.user_id)
    return DataResponse(result=proposal)


@router.put("/catalyst/{proposal_id}/reject", response_model=DataResponse[RetrieveCatalystProposalResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.CATALYST_PROPOSAL_NOT_FOUND.error_code},
                       409: {"model": ErrorResponse, "description": ErrorEnum.INVALID_PROPOSAL_STATUS.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def reject_catalyst_proposal(
        proposal_id: str, payload: RejectProposalRequest, current_user: User = Depends(get_current_user),
        service: ProposalService = Depends(get_proposal_service)):
    proposal = await service.reject_catalyst_proposal(
        proposal_id=proposal_id,
        user_id=current_user.user_id,
        rejection_reason=payload.rejection_reason,
    )
    return DataResponse(result=proposal)
