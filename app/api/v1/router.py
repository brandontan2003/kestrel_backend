from fastapi import APIRouter

from app.api.v1 import authorization, telegram, user, theses, proposal, evaluation, alert

v1_router = APIRouter()
v1_router.include_router(authorization.router)
v1_router.include_router(user.router)
v1_router.include_router(theses.router)
v1_router.include_router(proposal.router)
v1_router.include_router(evaluation.router)
v1_router.include_router(alert.router)
v1_router.include_router(telegram.router)

