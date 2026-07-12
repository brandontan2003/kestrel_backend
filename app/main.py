from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.websocket import ws_router
from app.api.v1.router import v1_router
from app.config import settings
from app.database_registry import init_database_engine
from app.dto.base import HealthCheckDTO, SuccessResponse
from app.exception_handler import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database_engine(settings.DATABASE_URL)
    await health_check()
    yield


app = FastAPI(title="Kestrel Backend API Documentation", version="1.0.0", lifespan=lifespan)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URL_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(v1_router, prefix="/api/v1")
app.include_router(ws_router.router)


@app.get("/health", response_model=HealthCheckDTO)
async def health_check():
    return SuccessResponse()
