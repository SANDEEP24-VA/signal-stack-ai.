import asyncio
from datetime import datetime, timezone
import logging
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.ai import CompanyIntelligenceAnalyzer, get_active_ai_provider
from app.core.errors import NotFoundError
from app.crawlers import WebsiteResearchEngine
from app.database import Company, DiscoveredUrl, ResearchRun, SessionLocal, get_db
from app.schemas import DiscoveredUrlResponse, ResearchRunResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies/{company_id}/research", tags=["Research"])


async def run_research_pipeline(company_id: int, research_run_id: int, max_pages: int = 12) -> None:
    """Background task orchestrating website crawling and AI intelligence extraction."""
    db: Session = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        research_run = db.query(ResearchRun).filter(ResearchRun.id == research_run_id).first()

        if not company or not research_run:
            logger.error(f"Background research pipeline failed: company {company_id} or run {research_run_id} missing")
            return

        research_run.status = "RUNNING"
        db.commit()

        # Step 1: Execute website crawl with configurable page limits
        engine = WebsiteResearchEngine(
            max_pages=max_pages,
            max_depth=2,
            timeout=15.0,
            max_response_size=2 * 1024 * 1024,
            max_redirects=3,
            rate_limit_delay=1.0,
        )

        extracted_pages = await engine.execute_research(company, research_run, db)

        # Step 2: AI-Powered Two-Stage Intelligence Understanding
        if extracted_pages:
            provider = await get_active_ai_provider()
            if provider:
                analyzer = CompanyIntelligenceAnalyzer(provider)
                await analyzer.analyze_and_persist(company, research_run, extracted_pages, db)
            else:
                logger.warning(f"No AI provider available for run {research_run_id}; skipping AI analysis.")
                research_run.ai_analysis_status = "UNAVAILABLE"
                if research_run.status == "RUNNING":
                    research_run.status = "COMPLETED"
                research_run.completed_at = datetime.now(timezone.utc)
                db.commit()

        logger.info(f"Research pipeline finished for company {company.name}: status={research_run.status}")

    except Exception as e:
        logger.exception(f"Unhandled error in research pipeline for company {company_id}: {e}")
        try:
            run = db.query(ResearchRun).filter(ResearchRun.id == research_run_id).first()
            if run:
                run.status = "FAILED"
                run.error_message = f"Pipeline execution error: {e}"
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post(
    "",
    response_model=ResearchRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start automated website research run",
    description="Initiates background website crawling, content extraction, and AI intelligence understanding.",
)
def start_research(
    company_id: int,
    background_tasks: BackgroundTasks,
    max_pages: int = 12,
    db: Session = Depends(get_db),
) -> ResearchRunResponse:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise NotFoundError(f"Company with ID {company_id} not found.")

    run = ResearchRun(
        company_id=company.id,
        status="PENDING",
        started_at=datetime.now(timezone.utc),
        ai_analysis_status="PENDING",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Launch background task
    background_tasks.add_task(run_research_pipeline, company.id, run.id, max_pages)

    return ResearchRunResponse.model_validate(run)


@router.get(
    "",
    response_model=List[ResearchRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List research runs for a company",
)
def list_research_runs(
    company_id: int,
    db: Session = Depends(get_db),
) -> List[ResearchRunResponse]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise NotFoundError(f"Company with ID {company_id} not found.")

    runs = (
        db.query(ResearchRun)
        .filter(ResearchRun.company_id == company_id)
        .order_by(ResearchRun.started_at.desc())
        .all()
    )
    return [ResearchRunResponse.model_validate(r) for r in runs]


@router.get(
    "/{research_run_id}",
    response_model=ResearchRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific research run",
)
def get_research_run(
    company_id: int,
    research_run_id: int,
    db: Session = Depends(get_db),
) -> ResearchRunResponse:
    run = (
        db.query(ResearchRun)
        .filter(
            ResearchRun.id == research_run_id,
            ResearchRun.company_id == company_id,
        )
        .first()
    )
    if not run:
        raise NotFoundError(f"Research run {research_run_id} not found for company {company_id}.")
    return ResearchRunResponse.model_validate(run)


@router.get(
    "/{research_run_id}/urls",
    response_model=List[DiscoveredUrlResponse],
    status_code=status.HTTP_200_OK,
    summary="List individual discovered URLs and accounting status for a run",
)
def list_run_urls(
    company_id: int,
    research_run_id: int,
    db: Session = Depends(get_db),
) -> List[DiscoveredUrlResponse]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise NotFoundError(f"Company with ID {company_id} not found.")

    urls = (
        db.query(DiscoveredUrl)
        .filter(DiscoveredUrl.research_run_id == research_run_id)
        .order_by(DiscoveredUrl.created_at.asc())
        .all()
    )
    return [DiscoveredUrlResponse.model_validate(u) for u in urls]
