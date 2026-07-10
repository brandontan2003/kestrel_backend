from fastapi.params import Depends

from app.dto.proposal import RetrieveAllThesesProposalResponse, RetrieveThesesProposalResponse, \
    RetrieveAllQuantProposalResponse, RetrieveQuantProposalResponse, RetrieveAllCatalystProposalResponse, \
    RetrieveCatalystProposalResponse, RetrieveAllProposalsResponse
from app.enums.ProposalEnum import ProposalStatusEnum
from app.repository.catalyst_proposal_repository import CatalystProposalRepository, get_catalyst_proposal_repository
from app.repository.catalyst_repository import CatalystRepository, get_catalyst_repository
from app.repository.quant_condition_repository import QuantConditionRepository, get_quant_condition_repository
from app.repository.quant_proposal_repository import QuantProposalRepository, get_quant_proposal_repository
from app.repository.theses_proposal_repository import ThesesProposalRepository, get_theses_proposal_repository
from app.repository.theses_repository import ThesesRepository, get_theses_repository


class ProposalService:
    def __init__(self, theses_repository: ThesesRepository, theses_proposal_repository: ThesesProposalRepository,
                 quant_condition_repository: QuantConditionRepository,
                 quant_proposal_repository: QuantProposalRepository, catalyst_repository: CatalystRepository,
                 catalyst_proposal_repository: CatalystProposalRepository):
        self._theses_repo = theses_repository
        self._theses_proposal_repo = theses_proposal_repository
        self._quant_condition_repo = quant_condition_repository
        self._quant_proposal_repo = quant_proposal_repository
        self._catalyst_repo = catalyst_repository
        self._catalyst_proposal_repo = catalyst_proposal_repository

    async def get_all_proposals(self, user_id: str, status: ProposalStatusEnum | None, page: int,
                                page_size: int) -> RetrieveAllProposalsResponse:
        theses = await self.get_all_theses_proposals(user_id, status, page, page_size)
        quant = await self.get_all_quant_proposals(user_id, status, page, page_size)
        catalyst = await self.get_all_catalyst_proposals(user_id, status, page, page_size)

        return RetrieveAllProposalsResponse(theses_proposals=theses, quant_proposals=quant, catalyst_proposals=catalyst)

    async def get_all_theses_proposals(self, user_id: str, theses_proposal_status: ProposalStatusEnum | None, page: int,
                                       page_size: int) -> RetrieveAllThesesProposalResponse:
        theses_proposals, total = await self._theses_proposal_repo.get_all_theses_proposal_by_user(
            user_id, page, page_size, theses_proposal_status)
        result = [RetrieveThesesProposalResponse(**theses_proposal.__dict__) for theses_proposal in theses_proposals]

        return RetrieveAllThesesProposalResponse(theses_proposals=result, total=total, page=page, page_size=page_size,
                                                 total_pages=-(-total // page_size))

    async def get_all_quant_proposals(self, user_id: str, quant_proposal_status: ProposalStatusEnum | None, page: int,
                                      page_size: int) -> RetrieveAllQuantProposalResponse:
        quant_proposals, total = await self._quant_proposal_repo.get_all_quant_proposal_by_user(
            user_id, page, page_size, quant_proposal_status)
        result = [RetrieveQuantProposalResponse(**quant_proposal.__dict__) for quant_proposal in quant_proposals]

        return RetrieveAllQuantProposalResponse(quant_proposals=result, total=total, page=page, page_size=page_size,
                                                total_pages=-(-total // page_size))

    async def get_all_catalyst_proposals(self, user_id: str, catalyst_proposal_status: str | None, page: int,
                                         page_size: int) -> RetrieveAllCatalystProposalResponse:
        catalyst_proposals, total = await self._catalyst_proposal_repo.get_all_catalyst_proposal_by_user(
            user_id, page, page_size, catalyst_proposal_status)
        result = [RetrieveCatalystProposalResponse(**catalyst_proposal.__dict__) for catalyst_proposal in
                  catalyst_proposals]

        return RetrieveAllCatalystProposalResponse(catalyst_proposals=result, total=total, page=page,
                                                   page_size=page_size, total_pages=-(-total // page_size))


async def get_proposal_service(theses_repo: ThesesRepository = Depends(get_theses_repository),
                               theses_proposal_repo: ThesesProposalRepository = Depends(get_theses_proposal_repository),
                               quant_condition_repo: QuantConditionRepository = Depends(get_quant_condition_repository),
                               quant_proposal_repo: QuantProposalRepository = Depends(get_quant_proposal_repository),
                               catalyst_repo: CatalystRepository = Depends(get_catalyst_repository),
                               catalyst_proposal_repo: CatalystProposalRepository = Depends(
                                   get_catalyst_proposal_repository)) -> ProposalService:
    return ProposalService(theses_repo, theses_proposal_repo, quant_condition_repo, quant_proposal_repo, catalyst_repo,
                           catalyst_proposal_repo)
