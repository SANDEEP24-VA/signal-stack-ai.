from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.database import Company, CompanyFact, CompanyProfile, ResearchPage, get_db
from app.schemas import (
    CompanyFactResponse,
    CompanyProfileResponse,
    CompanyProfileUpdate,
    ResearchPageResponse,
)

router = APIRouter(prefix="/companies/{company_id}", tags=["Company Profiles & Evidence"])


@router.get(
    "/profile",
    response_model=CompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest structured company intelligence profile",
)
def get_company_profile(
    company_id: int,
    db: Session = Depends(get_db),
) -> CompanyProfileResponse:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.company_id == company_id)
        .order_by(CompanyProfile.profile_version.desc())
        .first()
    )
    if not profile:
        raise NotFoundError(
            f"No company intelligence profile generated yet for {company.name}. "
            "Please trigger a research run first."
        )

    return CompanyProfileResponse.model_validate(profile)


@router.put(
    "/profile",
    response_model=CompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update company profile (Founder / Analyst Edits)",
    description="Updates corporate profile fields and increments the profile version.",
)
def update_company_profile(
    company_id: int,
    payload: CompanyProfileUpdate,
    db: Session = Depends(get_db),
) -> CompanyProfileResponse:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    latest = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.company_id == company_id)
        .order_by(CompanyProfile.profile_version.desc())
        .first()
    )

    now = datetime.now(timezone.utc)
    if not latest:
        # Create initial profile with version 1
        new_profile = CompanyProfile(
            company_id=company_id,
            industry=payload.industry or company.industry or "Technology",
            business_model=payload.business_model or "",
            products_services=payload.products_services or [],
            target_customers=payload.target_customers or [],
            customer_problems=payload.customer_problems or [],
            revenue_streams=payload.revenue_streams or [],
            geographical_markets=payload.geographical_markets or [],
            study_destinations=payload.study_destinations or [],
            business_partners=payload.business_partners or [],
            positioning=payload.positioning or "",
            growth_related_information=payload.growth_related_information or [],
            unknown_information=payload.unknown_information or [],
            profile_version=1,
            updated_at=now,
        )
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return CompanyProfileResponse.model_validate(new_profile)

    # Clone latest with incremented version and updated fields
    updated_profile = CompanyProfile(
        company_id=company_id,
        research_run_id=latest.research_run_id,
        industry=payload.industry if payload.industry is not None else latest.industry,
        business_model=payload.business_model if payload.business_model is not None else latest.business_model,
        products_services=payload.products_services if payload.products_services is not None else latest.products_services,
        target_customers=payload.target_customers if payload.target_customers is not None else latest.target_customers,
        customer_problems=payload.customer_problems if payload.customer_problems is not None else latest.customer_problems,
        revenue_streams=payload.revenue_streams if payload.revenue_streams is not None else latest.revenue_streams,
        geographical_markets=payload.geographical_markets if payload.geographical_markets is not None else latest.geographical_markets,
        study_destinations=payload.study_destinations if payload.study_destinations is not None else latest.study_destinations,
        business_partners=payload.business_partners if payload.business_partners is not None else latest.business_partners,
        positioning=payload.positioning if payload.positioning is not None else latest.positioning,
        growth_related_information=payload.growth_related_information if payload.growth_related_information is not None else latest.growth_related_information,
        unknown_information=payload.unknown_information if payload.unknown_information is not None else latest.unknown_information,
        profile_version=latest.profile_version + 1,
        updated_at=now,
    )
    db.add(updated_profile)
    db.commit()
    db.refresh(updated_profile)

    return CompanyProfileResponse.model_validate(updated_profile)


@router.get(
    "/facts",
    response_model=List[CompanyFactResponse],
    status_code=status.HTTP_200_OK,
    summary="Get verified facts, assumptions, and unknowns with evidence",
)
def get_company_facts(
    company_id: int,
    classification: Optional[str] = Query(
        None,
        description="Filter by classification: VERIFIED_FACT, ASSUMPTION, UNKNOWN, or REJECTED_UNSUPPORTED",
    ),
    db: Session = Depends(get_db),
) -> List[CompanyFactResponse]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    query = db.query(CompanyFact).filter(CompanyFact.company_id == company_id)
    if classification:
        query = query.filter(CompanyFact.classification == classification.upper())

    facts = query.order_by(CompanyFact.created_at.desc()).all()

    response_list = []
    for f in facts:
        item = CompanyFactResponse(
            id=f.id,
            company_id=f.company_id,
            research_page_id=f.research_page_id,
            category=f.category,
            statement=f.statement,
            classification=f.classification,
            evidence_snippet=f.evidence_snippet,
            quote_start_offset=f.quote_start_offset,
            quote_end_offset=f.quote_end_offset,
            rejection_reason=f.rejection_reason,
            provenance=f.provenance,
            confidence=f.confidence,
            created_at=f.created_at,
            source_url=f.research_page.url if f.research_page else None,
            source_title=f.research_page.title if f.research_page else None,
        )
        response_list.append(item)

    return response_list


@router.get(
    "/pages",
    response_model=List[ResearchPageResponse],
    status_code=status.HTTP_200_OK,
    summary="List extracted research webpages for a company",
)
def get_company_pages(
    company_id: int,
    db: Session = Depends(get_db),
) -> List[ResearchPageResponse]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    pages = (
        db.query(ResearchPage)
        .filter(ResearchPage.company_id == company_id)
        .order_by(ResearchPage.crawled_at.desc())
        .all()
    )

    return [
        ResearchPageResponse(
            id=p.id,
            company_id=p.company_id,
            research_run_id=p.research_run_id,
            url=p.url,
            canonical_url=p.canonical_url,
            title=p.title,
            content_hash=p.content_hash,
            http_status=p.http_status,
            text_length=len(p.extracted_text) if p.extracted_text else 0,
            crawled_at=p.crawled_at,
            first_seen_at=p.first_seen_at,
            last_seen_at=p.last_seen_at,
        )
        for p in pages
    ]
