from app.dto.base import BaseDTO


class RetrieveAllStockResponse(BaseDTO):
    stocks: list[str]
