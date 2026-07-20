import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.authentication.dependencies import get_current_active_user, RoleChecker
from app.repositories.all_repositories import ad_repo, analytics_log_repo
from app.schemas.all_schemas import StandardResponse, AdvertisementResponse, AdvertisementCreate, AdvertisementUpdate

router = APIRouter()

# Role guards
admin_checker = RoleChecker(["Super Admin", "Transport Admin"])

@router.get("/active", response_model=StandardResponse[List[AdvertisementResponse]])
async def get_active_advertisements(
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all active sponsorships and advertisements valid for the current timeframe."""
    ads = await ad_repo.get_active_ads(db)
    
    # Increment impressions count for each retrieved ad
    for ad in ads:
        ad.impressions += 1
        db.add(ad)
    await db.flush()
    
    return StandardResponse(
        success=True,
        message="Active advertisements loaded.",
        data=[AdvertisementResponse.model_validate(a) for a in ads]
    )

@router.post("/click/{id}", response_model=StandardResponse[dict])
async def log_ad_click(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Logs a click event on an advertisement and increments statistics."""
    ad = await ad_repo.get(db, id=id)
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advertisement not found.")
        
    ad.clicks += 1
    db.add(ad)
    await db.flush()
    
    # Audit event to Analytics Log
    await analytics_log_repo.create(
        db,
        obj_in={
            "event_type": "AD_CLICK",
            "payload": {
                "ad_id": str(id),
                "ad_type": ad.ad_type,
                "title": ad.title
            }
        }
    )
    
    return StandardResponse(
        success=True,
        message="Ad click logged.",
        data={"clicks": ad.clicks}
    )

@router.post("", response_model=StandardResponse[AdvertisementResponse])
async def create_advertisement(
    ad_in: AdvertisementCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Creates a new advertisement slot. Requires Admin role."""
    new_ad = await ad_repo.create(db, obj_in=ad_in.model_dump())
    return StandardResponse(
        success=True,
        message="Advertisement registered.",
        data=AdvertisementResponse.model_validate(new_ad)
    )

@router.put("/{id}", response_model=StandardResponse[AdvertisementResponse])
async def update_advertisement(
    id: uuid.UUID,
    ad_in: AdvertisementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Updates advertisement configurations. Requires Admin role."""
    ad = await ad_repo.get(db, id=id)
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advertisement not found.")
        
    updated_ad = await ad_repo.update(db, db_obj=ad, obj_in=ad_in)
    return StandardResponse(
        success=True,
        message="Advertisement updated.",
        data=AdvertisementResponse.model_validate(updated_ad)
    )
