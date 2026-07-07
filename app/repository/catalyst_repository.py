from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_db
from app.dto.theses import CatalystRequest
from app.models import Catalyst


class CatalystRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def bulk_create_catalysts(self, theses_id: str, catalysts: list[CatalystRequest]) -> None:
        objects = [
            Catalyst(
                theses_id=theses_id,
                state=cat.state.value,
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


async def get_catalyst_repository(db: AsyncSession = Depends(get_db)) -> CatalystRepository:
    return CatalystRepository(db)
