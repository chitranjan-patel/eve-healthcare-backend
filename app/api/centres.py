from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.cache import cache_get, cache_set
from app.db import get_db
from app.deps import get_current_user
from app.models import CentreTest, DiagnosticCentre, User
from app.schemas import CentreDetailOut, CentreOut, CentreTestOut

router = APIRouter(prefix="/centres", tags=["centres"])


@router.get("/", response_model=dict)
def list_centres(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    cache_key = f"centres:list:{skip}:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    query = db.query(DiagnosticCentre).order_by(DiagnosticCentre.name)
    total = query.count()
    centres = query.offset(skip).limit(limit).all()
    result = {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [CentreOut.model_validate(c).model_dump(mode="json") for c in centres],
    }
    cache_set(cache_key, result)
    return result


@router.get("/{centre_id}", response_model=CentreDetailOut)
def get_centre(
    centre_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DiagnosticCentre:
    cache_key = f"centres:detail:{centre_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    centre = (
        db.query(DiagnosticCentre)
        .options(joinedload(DiagnosticCentre.tests))
        .filter(DiagnosticCentre.id == centre_id)
        .first()
    )
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic centre not found")

    data = CentreDetailOut(
        id=centre.id,
        name=centre.name,
        location=centre.location,
        tests=[CentreTestOut.model_validate(t) for t in centre.tests if t.is_active],
    )
    payload = data.model_dump(mode="json")
    cache_set(cache_key, payload)
    return payload


@router.get("/{centre_id}/tests", response_model=dict)
def list_centre_tests(
    centre_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic centre not found")

    cache_key = f"centres:tests:{centre_id}:{skip}:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    query = (
        db.query(CentreTest)
        .filter(CentreTest.centre_id == centre_id, CentreTest.is_active.is_(True))
        .order_by(CentreTest.name)
    )
    total = query.count()
    tests = query.offset(skip).limit(limit).all()
    result = {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [CentreTestOut.model_validate(t).model_dump(mode="json") for t in tests],
    }
    cache_set(cache_key, result)
    return result
