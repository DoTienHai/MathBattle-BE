"""Profile API endpoints — G01_F02 (SF01, SF02, SF03)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.database.connection import get_db
from app.schemas.profile import UpdateProfileRequest
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
async def get_basic_profile(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Return basic profile info for the authenticated user (SF01)."""
    data = await ProfileService.get_basic_profile(db, user_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_NOT_FOUND", "message": "Profile not found"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": {
                **data,
                "join_date": data["join_date"].isoformat(),
            },
            "error": None,
        },
    )


@router.get("/stats")
async def get_personal_stats(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Return personal statistics for the authenticated user (SF02)."""
    data = await ProfileService.get_personal_stats(db, user_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_NOT_FOUND", "message": "Profile not found"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": data, "error": None},
    )


@router.get("/badges")
async def get_badges(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JSONResponse:
    """Return paginated list of earned badges for the authenticated user (SF03)."""
    data = await ProfileService.get_user_badges(db, user_id, limit, offset)

    def serialize_badge(b: dict) -> dict:
        return {**b, "earned_at": b["earned_at"].isoformat()}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": {
                "total": data["total"],
                "badges": [serialize_badge(b) for b in data["badges"]],
            },
            "error": None,
        },
    )


@router.patch("")
async def update_profile(
    body: UpdateProfileRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Update username and/or full_name for the authenticated user (SF04)."""
    success, result = await ProfileService.update_profile(
        db, user_id, body.username, body.full_name
    )
    if not success:
        raise HTTPException(
            status_code=result["status_code"],
            detail={"code": result["code"], "message": result["message"]},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": result, "error": None},
    )
