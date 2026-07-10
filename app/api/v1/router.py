from fastapi import APIRouter

from app.api.v1 import authorization, user, theses, proposal

v1_router = APIRouter()
v1_router.include_router(authorization.router)
v1_router.include_router(user.router)
v1_router.include_router(theses.router)
v1_router.include_router(proposal.router)
