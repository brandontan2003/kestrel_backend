from fastapi import APIRouter, Depends

from app.dto.base import DataResponse
from app.dto.error import ErrorResponse
from app.dto.stock import RetrieveAllStockResponse
from app.enums.ErrorEnum import ErrorEnum
from app.service.stock_service import StockService, get_stock_service

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("/listed", response_model=DataResponse[RetrieveAllStockResponse],
            responses={422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}})
async def retrieve_listed_stocks(service: StockService = Depends(get_stock_service)):
    return DataResponse(result=await service.retrieve_listed_stocks())
