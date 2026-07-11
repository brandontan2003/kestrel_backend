from fastapi import Depends

from app.dto.alert import RetrieveAllAlertResponse, RetrieveAlertResponse
from app.repository.alert_repository import AlertRepository, get_alert_repository


class AlertService:
    def __init__(self, alert_repo: AlertRepository):
        self._alert_repo = alert_repo

    async def retrieve_all_alerts(self, user_id: str, page: int, page_size: int) -> RetrieveAllAlertResponse:
        alerts, total = await self._alert_repo.get_all_alerts_by_user_id(user_id=user_id, page=page,
                                                                         page_size=page_size)
        result = [RetrieveAlertResponse(**alert.__dict__, evaluation=alert.evaluations_mapping) for alert in alerts]

        return RetrieveAllAlertResponse(alerts=result, total=total, page=page, page_size=page_size,
                                        total_pages=-(-total // page_size))


async def get_alert_service(alert_repo: AlertRepository = Depends(get_alert_repository)) -> AlertService:
    return AlertService(alert_repo)
