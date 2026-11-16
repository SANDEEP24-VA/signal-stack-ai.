from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.errors import AppException, NotFoundError
from app.crawlers.url_utils import normalize_domain, validate_url_syntax
from app.database import Company, CompanyProfile, ResearchRun, get_db
from app.schemas import CompanyCreate, CompanyResponse, ResearchRunSummary

router = APIRouter(prefix="/companies", tags=["Companies"])


def build_company_response(company: Company, db: Session) -> CompanyResponse:
    latest_run = (
        db.query(ResearchRun)
        .filter(ResearchRun.company_id == company.id)
        .order_by(ResearchRun.started_at.desc())
        .first()
    )
    latest_profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.company_id == company.id)
        .order_by(CompanyProfile.profile_version.desc())
        .first()
    )

    run_summary = None
    if latest_run:
        run_summary = ResearchRunSummary(
            id=latest_run.id,
            status=latest_run.status,
            started_at=latest_run.started_at,
            completed_at=latest_run.completed_at,
            pages_discovered=latest_run.pages_discovered,
            pages_fetched=latest_run.pages_fetched,
            pages_failed=latest_run.pages_failed,
            ai_analysis_status=latest_run.ai_analysis_status,
        )

    return CompanyResponse(
        id=company.id,
        name=company.name,
        website=company.website,
        normalized_domain=company.normalized_domain,
        industry=company.industry,
        status=company.status,
        created_at=company.created_at,
        updated_at=company.updated_at,
        latest_research_run=run_summary,
        profile_version=latest_profile.profile_version if latest_profile else None,
    )


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a company",
    description="Registers a new company target with domain normalization and URL validation.",
)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
) -> CompanyResponse:
    # 1. Validate URL protocol and syntax
    valid_syntax, err_msg = validate_url_syntax(payload.website)
    if not valid_syntax:
        raise AppException(
            message=f"Invalid website URL: {err_msg}",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_URL",
        )

    # 2. Normalize domain
    try:
        norm_domain = normalize_domain(payload.website)
    except ValueError as e:
        raise AppException(
            message=f"Failed to normalize website domain: {e}",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_DOMAIN",
        )

    # 3. Check for duplicate normalized domain
    existing = (
        db.query(Company)
        .filter(Company.normalized_domain == norm_domain)
        .first()
    )
    if existing:
        raise AppException(
            message=f"Company with normalized domain '{norm_domain}' is already registered (ID: {existing.id}, Name: {existing.name}).",
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_COMPANY",
            details={"existing_company_id": existing.id, "domain": norm_domain},
        )

    # Standardize website URL format
    website_clean = payload.website.strip()
    if not website_clean.startswith(("http://", "https://")):
        website_clean = f"https://{website_clean}"

    company = Company(
        name=payload.name.strip(),
        website=website_clean,
        normalized_domain=norm_domain,
        industry=payload.industry.strip() if payload.industry else None,
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    return build_company_response(company, db)


@router.get(
    "",
    response_model=List[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="List all registered companies",
)
def list_companies(db: Session = Depends(get_db)) -> List[CompanyResponse]:
    companies = db.query(Company).order_by(Company.created_at.desc()).all()
    return [build_company_response(c, db) for c in companies]


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get company details by ID",
)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
) -> CompanyResponse:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise NotFoundError(f"Company with ID {company_id} does not exist.")
    return build_company_response(company, db)
