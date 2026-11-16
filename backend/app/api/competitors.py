"""Competitor Discovery and Governance REST API."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ai.manager import get_active_ai_provider
from app.core.errors import BadRequestError, NotFoundError
from app.database import (
    Company,
    Competitor,
    get_db,
)
from app.discovery import CompetitorDiscoveryEngine, CompetitorGovernanceManager
from app.schemas import (
    CompetitorCreate,
    CompetitorResponse,
    CompetitorUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Competitor Discovery & Intelligence"])


# =============================================================================
# COMPANY COMPETITOR ENDPOINTS
# =============================================================================


@router.post(
    "/companies/{company_id}/competitors/discover",
    response_model=List[CompetitorResponse],
    status_code=status.HTTP_200_OK,
    summary="Trigger dynamic competitor discovery for a target company",
)
async def discover_competitors(
    company_id: int,
    verify_domains: bool = Query(True, description="Lightweight safe HTTP probe to verify existence"),
    db: Session = Depends(get_db),
) -> List[CompetitorResponse]:
    company = db.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    provider = await get_active_ai_provider()
    engine = CompetitorDiscoveryEngine(db=db, provider=provider)
    try:
        results = await engine.discover_competitors(company_id=company_id, verify_domains=verify_domains)
        return [CompetitorResponse.model_validate(c) for c in results]
    except Exception as exc:
        logger.error(f"Competitor discovery failed for company {company_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Competitor discovery failed: {str(exc)}",
        )


@router.get(
    "/companies/{company_id}/competitors",
    response_model=List[CompetitorResponse],
    status_code=status.HTTP_200_OK,
    summary="List all discovered and manual competitors for a company",
)
def list_competitors(
    company_id: int,
    status_filter: Optional[str] = Query(None, alias="status", description="CANDIDATE, APPROVED, REJECTED, ARCHIVED"),
    relationship_filter: Optional[str] = Query(None, alias="relationship", description="DIRECT, INDIRECT, SUBSTITUTE"),
    db: Session = Depends(get_db),
) -> List[CompetitorResponse]:
    company = db.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    stmt = select(Competitor).where(Competitor.company_id == company_id)
    if status_filter:
        stmt = stmt.where(Competitor.review_status == status_filter.upper())
    if relationship_filter:
        stmt = stmt.where(Competitor.relationship_type == relationship_filter.upper())

    stmt = stmt.order_by(desc(Competitor.created_at))
    competitors = list(db.scalars(stmt).all())
    return [CompetitorResponse.model_validate(c) for c in competitors]


@router.post(
    "/companies/{company_id}/competitors",
    response_model=CompetitorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually add a verified competitor",
)
async def add_competitor_manual(
    company_id: int,
    payload: CompetitorCreate,
    db: Session = Depends(get_db),
) -> CompetitorResponse:
    provider = await get_active_ai_provider()
    engine = CompetitorDiscoveryEngine(db=db, provider=provider)
    try:
        competitor = await engine.manual_add_competitor(
            company_id=company_id,
            name=payload.name,
            website=payload.website,
            relationship_type=payload.relationship_type,
            industry=payload.industry,
            products_services=payload.products_services,
            target_customers=payload.target_customers,
            geographic_markets=payload.geographic_markets,
            discovery_rationale=payload.discovery_rationale,
        )
        return CompetitorResponse.model_validate(competitor)
    except ValueError as exc:
        raise BadRequestError(str(exc))


# =============================================================================
# INDIVIDUAL COMPETITOR GOVERNANCE
# =============================================================================


@router.get(
    "/competitors/{competitor_id}",
    response_model=CompetitorResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve competitor details",
)
def get_competitor(
    competitor_id: int,
    db: Session = Depends(get_db),
) -> CompetitorResponse:
    competitor = db.get(Competitor, competitor_id)
    if not competitor:
        raise NotFoundError(f"Competitor {competitor_id} not found.")
    return CompetitorResponse.model_validate(competitor)


@router.patch(
    "/competitors/{competitor_id}",
    response_model=CompetitorResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit competitor information and classification",
)
def update_competitor(
    competitor_id: int,
    payload: CompetitorUpdate,
    db: Session = Depends(get_db),
) -> CompetitorResponse:
    manager = CompetitorGovernanceManager(db=db)
    try:
        updated = manager.edit_competitor(
            competitor_id=competitor_id,
            name=payload.name,
            website=payload.website,
            relationship_type=payload.relationship_type,
            industry=payload.industry,
            products_services=payload.products_services,
            target_customers=payload.target_customers,
            geographic_markets=payload.geographic_markets,
            discovery_rationale=payload.discovery_rationale,
        )
        if payload.review_status:
            stat_upper = payload.review_status.upper()
            if stat_upper == "APPROVED":
                updated = manager.approve_competitor(competitor_id)
            elif stat_upper == "REJECTED":
                updated = manager.reject_competitor(competitor_id)
            elif stat_upper == "ARCHIVED":
                updated = manager.archive_competitor(competitor_id)

        return CompetitorResponse.model_validate(updated)
    except ValueError as exc:
        raise BadRequestError(str(exc))


@router.post(
    "/competitors/{competitor_id}/approve",
    response_model=CompetitorResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a candidate competitor",
)
def approve_competitor(
    competitor_id: int,
    db: Session = Depends(get_db),
) -> CompetitorResponse:
    manager = CompetitorGovernanceManager(db=db)
    try:
        approved = manager.approve_competitor(competitor_id)
        return CompetitorResponse.model_validate(approved)
    except ValueError as exc:
        raise NotFoundError(str(exc))


@router.post(
    "/competitors/{competitor_id}/reject",
    response_model=CompetitorResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject an inaccurate competitor candidate",
)
def reject_competitor(
    competitor_id: int,
    db: Session = Depends(get_db),
) -> CompetitorResponse:
    manager = CompetitorGovernanceManager(db=db)
    try:
        rejected = manager.reject_competitor(competitor_id)
        return CompetitorResponse.model_validate(rejected)
    except ValueError as exc:
        raise NotFoundError(str(exc))


@router.post(
    "/competitors/{competitor_id}/archive",
    response_model=CompetitorResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive a competitor record",
)
def archive_competitor(
    competitor_id: int,
    db: Session = Depends(get_db),
) -> CompetitorResponse:
    manager = CompetitorGovernanceManager(db=db)
    try:
        archived = manager.archive_competitor(competitor_id)
        return CompetitorResponse.model_validate(archived)
    except ValueError as exc:
        raise NotFoundError(str(exc))
