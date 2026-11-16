"""Intelligence Source Discovery, Registry, and Governance REST API."""
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.ai.manager import get_active_ai_provider
from app.core.errors import BadRequestError, NotFoundError
from app.database import (
    Company,
    Competitor,
    CompetitorReviewStatus,
    IntelligenceSource,
    IntelligenceSourceCategory,
    IntelligenceSourceStatus,
    SourceCrawlLog,
    get_db,
)
from app.discovery import SourceDiscoveryEngine, SourceGovernanceManager
from app.schemas import (
    IntelligenceSourceCreate,
    IntelligenceSourceResponse,
    IntelligenceSourceUpdate,
    SourceCrawlLogResponse,
    SourceSummaryStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Source Intelligence Management"])


# =============================================================================
# COMPANY SOURCE MANAGEMENT & DISCOVERY
# =============================================================================


@router.post(
    "/companies/{company_id}/sources/discover",
    response_model=List[IntelligenceSourceResponse],
    status_code=status.HTTP_200_OK,
    summary="Trigger multi-channel intelligence source discovery across categories",
)
async def discover_company_sources(
    company_id: int,
    probe_reachability: bool = Query(True, description="Verify reachability without blocking"),
    db: Session = Depends(get_db),
) -> List[IntelligenceSourceResponse]:
    company = db.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    provider = await get_active_ai_provider()
    engine = SourceDiscoveryEngine(db=db, provider=provider)
    try:
        sources = await engine.discover_sources_for_company(
            company_id=company_id,
            probe_reachability=probe_reachability,
        )
        return [IntelligenceSourceResponse.model_validate(s) for s in sources]
    except Exception as exc:
        logger.error(f"Source discovery failed for company {company_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Source discovery failed: {str(exc)}",
        )


@router.get(
    "/companies/{company_id}/sources",
    response_model=List[IntelligenceSourceResponse],
    status_code=status.HTTP_200_OK,
    summary="List registered intelligence sources with pagination and filters",
)
def list_company_sources(
    company_id: int,
    category: Optional[str] = Query(None, description="CUSTOMERS, COMPETITORS, MARKET, INTERNAL"),
    status: Optional[str] = Query(None, description="DISCOVERED, PENDING_APPROVAL, APPROVED, REJECTED, PAUSED, BLOCKED, ERROR"),
    competitor_id: Optional[int] = Query(None, description="Filter by associated competitor"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[IntelligenceSourceResponse]:
    company = db.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    stmt = select(IntelligenceSource).where(IntelligenceSource.company_id == company_id)
    if category:
        stmt = stmt.where(IntelligenceSource.category == category.upper())
    if status:
        stmt = stmt.where(IntelligenceSource.status == status.upper())
    if competitor_id:
        stmt = stmt.where(IntelligenceSource.competitor_id == competitor_id)

    stmt = stmt.order_by(desc(IntelligenceSource.created_at)).offset(offset).limit(limit)
    sources = list(db.scalars(stmt).all())
    return [IntelligenceSourceResponse.model_validate(s) for s in sources]


@router.get(
    "/companies/{company_id}/sources/summary",
    response_model=SourceSummaryStats,
    status_code=status.HTTP_200_OK,
    summary="Get source and competitor summary statistics for executive overview",
)
def get_source_summary_stats(
    company_id: int,
    db: Session = Depends(get_db),
) -> SourceSummaryStats:
    company = db.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    sources = db.scalars(
        select(IntelligenceSource).where(IntelligenceSource.company_id == company_id)
    ).all()

    total = len(sources)
    approved = sum(1 for s in sources if s.status == IntelligenceSourceStatus.APPROVED.value)
    pending = sum(
        1 for s in sources
        if s.status in (IntelligenceSourceStatus.PENDING_APPROVAL.value, IntelligenceSourceStatus.DISCOVERED.value)
    )
    rejected = sum(1 for s in sources if s.status == IntelligenceSourceStatus.REJECTED.value)
    paused = sum(1 for s in sources if s.status == IntelligenceSourceStatus.PAUSED.value)
    blocked = sum(
        1 for s in sources
        if s.status in (IntelligenceSourceStatus.BLOCKED.value, IntelligenceSourceStatus.ERROR.value)
    )

    by_cat: Dict[str, int] = {
        IntelligenceSourceCategory.CUSTOMERS.value: 0,
        IntelligenceSourceCategory.COMPETITORS.value: 0,
        IntelligenceSourceCategory.MARKET.value: 0,
        IntelligenceSourceCategory.INTERNAL.value: 0,
    }
    for s in sources:
        if s.category in by_cat:
            by_cat[s.category] += 1

    competitors = db.scalars(
        select(Competitor).where(Competitor.company_id == company_id)
    ).all()
    comp_total = len(competitors)
    comp_approved = sum(1 for c in competitors if c.review_status == CompetitorReviewStatus.APPROVED.value)

    return SourceSummaryStats(
        total_sources=total,
        approved=approved,
        pending=pending,
        rejected=rejected,
        paused=paused,
        blocked=blocked,
        by_category=by_cat,
        competitors_count=comp_total,
        approved_competitors=comp_approved,
    )


@router.post(
    "/companies/{company_id}/sources",
    response_model=IntelligenceSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually register an intelligence source",
)
async def add_source_manual(
    company_id: int,
    payload: IntelligenceSourceCreate,
    db: Session = Depends(get_db),
) -> IntelligenceSourceResponse:
    provider = await get_active_ai_provider()
    engine = SourceDiscoveryEngine(db=db, provider=provider)
    try:
        source = await engine.manual_add_source(
            company_id=company_id,
            name=payload.name,
            url=payload.canonical_url,
            category=payload.category,
            source_type=payload.source_type,
            why_it_matters=payload.why_it_matters,
            intelligence_type=payload.intelligence_type,
            credibility_score=payload.credibility_score,
            competitor_id=payload.competitor_id,
        )
        return IntelligenceSourceResponse.model_validate(source)
    except ValueError as exc:
        raise BadRequestError(str(exc))


# =============================================================================
# INDIVIDUAL SOURCE GOVERNANCE
# =============================================================================


@router.get(
    "/sources/{source_id}",
    response_model=IntelligenceSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve intelligence source details",
)
def get_source(
    source_id: int,
    db: Session = Depends(get_db),
) -> IntelligenceSourceResponse:
    source = db.get(IntelligenceSource, source_id)
    if not source:
        raise NotFoundError(f"Intelligence source {source_id} not found.")
    return IntelligenceSourceResponse.model_validate(source)


@router.patch(
    "/sources/{source_id}",
    response_model=IntelligenceSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit source metadata, categorization, or schedule",
)
def update_source(
    source_id: int,
    payload: IntelligenceSourceUpdate,
    db: Session = Depends(get_db),
) -> IntelligenceSourceResponse:
    manager = SourceGovernanceManager(db=db)
    try:
        updated = manager.edit_source(
            source_id=source_id,
            name=payload.name,
            category=payload.category,
            why_it_matters=payload.why_it_matters,
            intelligence_type=payload.intelligence_type,
            crawl_frequency_minutes=payload.crawl_frequency_minutes,
        )
        if payload.status:
            stat_upper = payload.status.upper()
            if stat_upper == IntelligenceSourceStatus.APPROVED.value:
                updated = manager.approve_source(source_id)
            elif stat_upper == IntelligenceSourceStatus.REJECTED.value:
                updated = manager.reject_source(source_id)
            elif stat_upper == IntelligenceSourceStatus.PAUSED.value:
                updated = manager.pause_source(source_id)

        return IntelligenceSourceResponse.model_validate(updated)
    except ValueError as exc:
        raise BadRequestError(str(exc))


@router.post(
    "/sources/{source_id}/approve",
    response_model=IntelligenceSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a discovered source for active intelligence monitoring",
)
def approve_source(
    source_id: int,
    db: Session = Depends(get_db),
) -> IntelligenceSourceResponse:
    manager = SourceGovernanceManager(db=db)
    try:
        approved = manager.approve_source(source_id)
        return IntelligenceSourceResponse.model_validate(approved)
    except ValueError as exc:
        raise NotFoundError(str(exc))


@router.post(
    "/sources/{source_id}/reject",
    response_model=IntelligenceSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject an irrelevant or inaccurate source candidate",
)
def reject_source(
    source_id: int,
    reason: Optional[str] = Query(None, description="Optional rejection reason"),
    db: Session = Depends(get_db),
) -> IntelligenceSourceResponse:
    manager = SourceGovernanceManager(db=db)
    try:
        rejected = manager.reject_source(source_id, reason=reason)
        return IntelligenceSourceResponse.model_validate(rejected)
    except ValueError as exc:
        raise NotFoundError(str(exc))


@router.post(
    "/sources/{source_id}/pause",
    response_model=IntelligenceSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause monitoring for an approved source",
)
def pause_source(
    source_id: int,
    db: Session = Depends(get_db),
) -> IntelligenceSourceResponse:
    manager = SourceGovernanceManager(db=db)
    try:
        paused = manager.pause_source(source_id)
        return IntelligenceSourceResponse.model_validate(paused)
    except ValueError as exc:
        raise NotFoundError(str(exc))


@router.post(
    "/sources/{source_id}/resume",
    response_model=IntelligenceSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume monitoring for a paused source",
)
def resume_source(
    source_id: int,
    db: Session = Depends(get_db),
) -> IntelligenceSourceResponse:
    manager = SourceGovernanceManager(db=db)
    try:
        resumed = manager.resume_source(source_id)
        return IntelligenceSourceResponse.model_validate(resumed)
    except ValueError as exc:
        raise NotFoundError(str(exc))


@router.delete(
    "/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an intelligence source record",
)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
):
    manager = SourceGovernanceManager(db=db)
    try:
        manager.delete_source(source_id)
    except ValueError as exc:
        raise NotFoundError(str(exc))


@router.post(
    "/sources/{source_id}/probe",
    response_model=SourceCrawlLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Safely execute health verification and probe source reachability",
)
async def probe_source(
    source_id: int,
    db: Session = Depends(get_db),
) -> SourceCrawlLogResponse:
    manager = SourceGovernanceManager(db=db)
    try:
        log = await manager.probe_source_health(source_id)
        return SourceCrawlLogResponse.model_validate(log)
    except ValueError as exc:
        raise NotFoundError(str(exc))


@router.get(
    "/sources/{source_id}/logs",
    response_model=List[SourceCrawlLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve crawl and health verification history for a source",
)
def list_source_logs(
    source_id: int,
    db: Session = Depends(get_db),
) -> List[SourceCrawlLogResponse]:
    source = db.get(IntelligenceSource, source_id)
    if not source:
        raise NotFoundError(f"Intelligence source {source_id} not found.")

    logs = (
        db.scalars(
            select(SourceCrawlLog)
            .where(SourceCrawlLog.source_id == source_id)
            .order_by(desc(SourceCrawlLog.checked_at))
            .limit(50)
        ).all()
    )
    return [SourceCrawlLogResponse.model_validate(l) for l in logs]
