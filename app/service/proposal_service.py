from fastapi.params import Depends

from app.dto.proposal import RetrieveAllThesesProposalResponse, RetrieveThesesProposalResponse, \
    RetrieveAllQuantProposalResponse, RetrieveQuantProposalResponse, RetrieveAllCatalystProposalResponse, \
    RetrieveCatalystProposalResponse, RetrieveAllProposalsResponse
from app.dto.theses import UpdateQuantConditionRequest, UpdateCatalystRequest
from common.enums.CatalystEnum import CatalystState
from common.enums.ProposalEnum import ProposalStatusEnum, ProposalTypeEnum
from app.exception_handler import QuantProposalNotFoundException, InvalidProposalStatusException, \
    QuantConditionNotFoundException, InvalidProposalTypeException, ThesesProposalNotFoundException, \
    CatalystProposalNotFoundException, CatalystNotFoundException
from app.repository.catalyst_proposal_repository import CatalystProposalRepository, get_catalyst_proposal_repository
from app.repository.catalyst_repository import CatalystRepository, get_catalyst_repository
from app.repository.quant_condition_repository import QuantConditionRepository, get_quant_condition_repository
from app.repository.quant_proposal_repository import QuantProposalRepository, get_quant_proposal_repository
from app.repository.theses_proposal_repository import ThesesProposalRepository, get_theses_proposal_repository
from app.repository.theses_repository import ThesesRepository, get_theses_repository
from common.enums.ProposalEnum import ProposalStatusEnum, ProposalTypeEnum


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

    # Theses proposals
    async def approve_theses_proposal(self, proposal_id: str, user_id: str) -> RetrieveThesesProposalResponse:
        proposal = await self._theses_proposal_repo.get_by_theses_proposal_id_and_user_id(proposal_id, user_id)
        if proposal is None:
            raise ThesesProposalNotFoundException()
        self._check_status(proposal.theses_proposal_status)

        change = proposal.proposed_change
        theses = await self._theses_repo.create_theses(
            user_id=user_id,
            stock_id=proposal.stock_id,
            quant_mode=change.get("quant_mode"),
            catalyst_mode=change.get("catalyst_mode"),
            notes=change.get("notes")
        )
        theses_id = theses.theses_id
        await self._quant_condition_repo.bulk_create_quant_condition(theses_id, change.get("quant_conditions"))
        await self._catalyst_repo.bulk_create_catalysts(theses_id, change.get("catalysts"))

        updated_theses_proposal = await self._theses_proposal_repo.approve_theses_proposal(proposal)
        return RetrieveThesesProposalResponse(**updated_theses_proposal.__dict__)

    async def reject_theses_proposal(self, proposal_id: str, user_id: str,
                                     rejection_reason: str) -> RetrieveThesesProposalResponse:
        proposal = await self._theses_proposal_repo.get_by_theses_proposal_id_and_user_id(proposal_id, user_id)
        if proposal is None:
            raise ThesesProposalNotFoundException()
        self._check_status(proposal.theses_proposal_status)

        updated_theses_proposal = await self._theses_proposal_repo.reject_theses_proposal(proposal, rejection_reason)
        return RetrieveThesesProposalResponse(**updated_theses_proposal.__dict__)

    # Quant proposals
    async def approve_quant_proposal(self, proposal_id: str, user_id: str) -> RetrieveQuantProposalResponse:
        proposal = await self._quant_proposal_repo.get_by_quant_proposal_id_and_user_id(proposal_id, user_id)
        if proposal is None:
            raise QuantProposalNotFoundException()
        self._check_status(proposal.quant_proposal_status)

        change = proposal.proposed_change
        proposal_type = proposal.proposal_type

        if proposal_type == ProposalTypeEnum.ADD:
            await self._quant_condition_repo.create_quant_condition(
                theses_id=proposal.theses_id,
                metric=change["metric"],
                operator=change["operator"],
                value=change["value"],
            )

        else:
            condition = await self._quant_condition_repo.get_quant_condition_by_id_and_user(
                proposal.quant_condition_id, proposal.theses_id, user_id)
            if condition is None:
                raise QuantConditionNotFoundException()

            if proposal_type == ProposalTypeEnum.UPDATE:
                # `.get()`, not `[...]`: a partial proposed_change is a partial
                # update (the repo skips None fields), not a KeyError.
                request = UpdateQuantConditionRequest(metric=change.get("metric"), operator=change.get("operator"),
                                                      value=change.get("value"), enabled=change.get("enabled"))
                await self._quant_condition_repo.update_quant_condition(condition, request)
                await self._quant_proposal_repo.supersede_pending_updates(
                    quant_condition_id=proposal.quant_condition_id,
                    approved_proposal_id=proposal_id
                )
            elif proposal_type == ProposalTypeEnum.REMOVE:
                await self._quant_condition_repo.delete_quant_condition(condition)
            else:
                raise InvalidProposalTypeException()

        updated_quant_proposal = await self._quant_proposal_repo.approve_quant_proposal(proposal)
        return RetrieveQuantProposalResponse(**updated_quant_proposal.__dict__)

    async def reject_quant_proposal(self, proposal_id: str, user_id: str,
                                    rejection_reason: str) -> RetrieveQuantProposalResponse:
        proposal = await self._quant_proposal_repo.get_by_quant_proposal_id_and_user_id(proposal_id, user_id)
        if proposal is None:
            raise QuantProposalNotFoundException()
        self._check_status(proposal.quant_proposal_status)

        updated_quant_proposal = await self._quant_proposal_repo.reject_quant_proposal(proposal, rejection_reason)
        return RetrieveQuantProposalResponse(**updated_quant_proposal.__dict__)

    # Catalyst proposals
    async def approve_catalyst_proposal(self, proposal_id: str, user_id: str) -> RetrieveCatalystProposalResponse:
        proposal = await self._catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id(proposal_id, user_id)
        if proposal is None:
            raise CatalystProposalNotFoundException()
        self._check_status(proposal.catalyst_proposal_status)

        change = proposal.proposed_change
        proposal_type = proposal.proposal_type

        if proposal_type == ProposalTypeEnum.ADD:
            await self._catalyst_repo.create_catalyst(
                theses_id=proposal.theses_id,
                # A proposed catalyst starts where every catalyst starts: the news
                # has to confirm it through the pipeline like any other.
                state=change.get("state") or CatalystState.UNCONFIRMED.value,
                description=change.get("description"),
                evidence=change.get("evidence"),
            )

        else:
            catalyst = await self._catalyst_repo.get_catalyst_by_id_and_user(
                proposal.catalyst_id, proposal.theses_id, user_id)
            if catalyst is None:
                raise CatalystNotFoundException()

            if proposal_type == ProposalTypeEnum.UPDATE:
                # `.get()`, not `[...]`: a partial proposed_change is a partial
                # update (the repo skips None fields), not a KeyError.
                request = UpdateCatalystRequest(state=change.get("state"), description=change.get("description"),
                                                evidence=change.get("evidence"), enabled=change.get("enabled"))
                await self._catalyst_repo.update_catalyst(catalyst, request)
                await self._catalyst_proposal_repo.supersede_pending_updates(
                    catalyst_id=proposal.catalyst_id,
                    approved_proposal_id=proposal_id
                )
            elif proposal_type == ProposalTypeEnum.REMOVE:
                await self._catalyst_repo.delete_catalyst(catalyst)
            else:
                raise InvalidProposalTypeException()

        updated_catalyst_proposal = await self._catalyst_proposal_repo.approve_catalyst_proposal(proposal)
        return RetrieveCatalystProposalResponse(**updated_catalyst_proposal.__dict__)

    async def reject_catalyst_proposal(self, proposal_id: str, user_id: str,
                                       rejection_reason: str) -> RetrieveCatalystProposalResponse:
        proposal = await self._catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id(proposal_id, user_id)
        if proposal is None:
            raise CatalystProposalNotFoundException()
        self._check_status(proposal.catalyst_proposal_status)

        updated_catalyst_proposal = await self._catalyst_proposal_repo.reject_catalyst_proposal(
            proposal, rejection_reason)
        return RetrieveCatalystProposalResponse(**updated_catalyst_proposal.__dict__)

    @staticmethod
    def _check_status(current_status: str) -> None:
        if current_status != ProposalStatusEnum.PENDING:
            raise InvalidProposalStatusException()


async def get_proposal_service(theses_repo: ThesesRepository = Depends(get_theses_repository),
                               theses_proposal_repo: ThesesProposalRepository = Depends(get_theses_proposal_repository),
                               quant_condition_repo: QuantConditionRepository = Depends(get_quant_condition_repository),
                               quant_proposal_repo: QuantProposalRepository = Depends(get_quant_proposal_repository),
                               catalyst_repo: CatalystRepository = Depends(get_catalyst_repository),
                               catalyst_proposal_repo: CatalystProposalRepository = Depends(
                                   get_catalyst_proposal_repository)) -> ProposalService:
    return ProposalService(theses_repo, theses_proposal_repo, quant_condition_repo, quant_proposal_repo, catalyst_repo,
                           catalyst_proposal_repo)
