from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from app.config import get_db
from app.dto.theses import CatalystRequest, UpdateCatalystRequest
from app.models import Catalyst, Theses


class CatalystRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def bulk_create_catalysts(self, theses_id: str, catalysts: list[CatalystRequest]) -> None:
        objects = [
            Catalyst(
                theses_id=theses_id,
                state=cat.state,
                description=cat.description,
                evidence=cat.evidence,
            )
            for cat in catalysts
        ]
        self._db.add_all(objects)
        await self._db.flush()

    async def create_catalyst(self, theses_id: str, state: str, description: str | None,
                              evidence: dict | None) -> Catalyst:
        catalyst = Catalyst(
            theses_id=theses_id,
            state=state,
            description=description,
            evidence=evidence,
        )
        self._db.add(catalyst)
        await self._db.flush()
        await self._db.refresh(catalyst)
        return catalyst

    async def get_catalyst_by_id_and_user(self, catalyst_id: str, theses_id: str, user_id: str) -> Catalyst | None:
        result = await self._db.execute(
            select(Catalyst)
            .join(Theses, Theses.theses_id == Catalyst.theses_id)
            .where(
                Catalyst.catalyst_id == catalyst_id,
                Catalyst.theses_id == theses_id,
                Theses.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_catalyst(self, catalyst: Catalyst, request: UpdateCatalystRequest) -> Catalyst:
        state = request.state
        if state is not None:
            catalyst.state = state

        description = request.description
        if description is not None:
            catalyst.description = description

        evidence = request.evidence
        if evidence is not None:
            catalyst.evidence = evidence

        enabled = request.enabled
        if enabled is not None:
            catalyst.enabled = enabled
        await self._db.flush()
        return catalyst

    async def record_verdict(self, catalyst: Catalyst, new_state: str, evidence_entry: dict,
                             state_changed: bool) -> Catalyst:
        """Append one classifier verdict to a catalyst's evidence trail, and
        advance its state if the state machine changed it.

        Reassigns `evidence` (rather than mutating the list in place) so
        SQLAlchemy detects the change on the JSON column.
        """
        existing = catalyst.evidence if isinstance(catalyst.evidence, list) else []
        catalyst.evidence = existing + [evidence_entry]
        if state_changed:
            catalyst.state = new_state
        await self._db.flush()
        return catalyst

    async def delete_catalyst(self, catalyst: Catalyst) -> None:
        catalyst.enabled = False
        await self._db.flush()


async def get_catalyst_repository(db: AsyncSession = Depends(get_db)) -> CatalystRepository:
    return CatalystRepository(db)
