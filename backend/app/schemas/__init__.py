from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Official company name")
    website: str = Field(..., max_length=1024, description="Company website URL (HTTP/HTTPS)")
    industry: Optional[str] = Field(None, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Company name must not be empty or whitespace only")
        return clean


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    website: Optional[str] = Field(None, max_length=1024)
    industry: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=50)


class ResearchRunSummary(BaseModel):
    id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    pages_discovered: int = 0
    pages_fetched: int = 0
    pages_failed: int = 0
    pages_skipped_limit: int = 0
    pages_skipped_robots: int = 0
    pages_skipped_duplicate: int = 0
    pages_skipped_out_of_scope: int = 0
    ai_analysis_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyResponse(BaseModel):
    id: int
    name: str
    website: str
    normalized_domain: str
    industry: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    latest_research_run: Optional[ResearchRunSummary] = None
    profile_version: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DiscoveredUrlResponse(BaseModel):
    id: int
    research_run_id: int
    url: str
    status: str
    depth: int = 0
    priority: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResearchRunResponse(BaseModel):
    id: int
    company_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    pages_discovered: int = 0
    pages_fetched: int = 0
    pages_failed: int = 0
    pages_skipped_limit: int = 0
    pages_skipped_robots: int = 0
    pages_skipped_duplicate: int = 0
    pages_skipped_out_of_scope: int = 0
    error_message: Optional[str] = None
    ai_analysis_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyProfileBase(BaseModel):
    industry: Optional[str] = None
    business_model: Optional[str] = None
    products_services: List[Any] = Field(default_factory=list)
    target_customers: List[Any] = Field(default_factory=list)
    customer_problems: List[Any] = Field(default_factory=list)
    revenue_streams: List[Any] = Field(default_factory=list)
    geographical_markets: List[Any] = Field(default_factory=list)
    study_destinations: List[Any] = Field(default_factory=list)
    business_partners: List[Any] = Field(default_factory=list)
    positioning: Optional[str] = None
    growth_related_information: List[Any] = Field(default_factory=list)
    unknown_information: List[Any] = Field(default_factory=list)


class CompanyProfileResponse(CompanyProfileBase):
    id: int
    company_id: int
    research_run_id: Optional[int] = None
    profile_version: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyProfileUpdate(BaseModel):
    industry: Optional[str] = None
    business_model: Optional[str] = None
    products_services: Optional[List[Any]] = None
    target_customers: Optional[List[Any]] = None
    customer_problems: Optional[List[Any]] = None
    revenue_streams: Optional[List[Any]] = None
    geographical_markets: Optional[List[Any]] = None
    study_destinations: Optional[List[Any]] = None
    business_partners: Optional[List[Any]] = None
    positioning: Optional[str] = None
    growth_related_information: Optional[List[Any]] = None
    unknown_information: Optional[List[Any]] = None


class CompanyFactResponse(BaseModel):
    id: int
    company_id: int
    research_page_id: Optional[int] = None
    category: str
    statement: str
    classification: str  # VERIFIED_FACT, ASSUMPTION, UNKNOWN, REJECTED_UNSUPPORTED
    evidence_snippet: Optional[str] = None
    quote_start_offset: Optional[int] = None
    quote_end_offset: Optional[int] = None
    rejection_reason: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    created_at: datetime
    source_url: Optional[str] = None
    source_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ResearchPageResponse(BaseModel):
    id: int
    company_id: int
    research_run_id: Optional[int] = None
    url: str
    canonical_url: Optional[str] = None
    title: Optional[str] = None
    content_hash: Optional[str] = None
    http_status: Optional[int] = None
    text_length: int = 0
    crawled_at: datetime
    first_seen_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# INTERVIEW SCHEMAS
# =============================================================================


class InterviewAnswerCreate(BaseModel):
    question_id: int
    answer_text: Optional[str] = None
    is_confidential: bool = False
    is_skip: bool = False
    allow_followup: bool = True


class InterviewAnswerUpdate(BaseModel):
    answer_text: str
    is_confidential: Optional[bool] = None


class InterviewAnswerResponse(BaseModel):
    id: int
    question_id: int
    answer_text: Optional[str] = None
    is_confidential: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewQuestionResponse(BaseModel):
    id: int
    session_id: int
    parent_question_id: Optional[int] = None
    question_type: str
    question_order: int
    question_text: str
    business_area: str
    reason_for_asking: str
    information_objective: str
    related_company_profile_field: Optional[str] = None
    expected_information_type: Optional[str] = None
    status: str
    created_at: datetime
    answers: List[InterviewAnswerResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InterviewAnswerSubmitResponse(BaseModel):
    answer: InterviewAnswerResponse
    followup_question: Optional[InterviewQuestionResponse] = None


class InterviewSessionResponse(BaseModel):
    id: int
    company_id: int
    profile_version_at_start: int
    status: str
    total_core_questions: int
    answered_count: int
    skipped_count: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    questions: List[InterviewQuestionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InterviewProgressResponse(BaseModel):
    session_id: int
    company_id: int
    status: str
    total_core_questions: int
    core_answered_count: int
    core_skipped_count: int
    core_remaining_count: int
    followup_count: int
    followup_answered_count: int
    followup_remaining_count: int
    confidential_answers_count: int
    completion_percentage: float
    is_ready_to_complete: bool
    started_at: datetime
    completed_at: Optional[datetime] = None


class FounderBusinessContextResponse(BaseModel):
    id: int
    company_id: int
    interview_session_id: int
    context_category: str
    field_name: str
    confirmed_value: Any
    confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewCompletionSummaryResponse(BaseModel):
    session_id: int
    company_id: int
    status: str
    profile_version: int
    extracted_context_count: int
    confidential_answers_protected: int
    resolved_unknowns_count: int
    completed_at: datetime


# =============================================================================
# DYNAMIC COMPETITOR & SOURCE INTELLIGENCE SCHEMAS (TASK 4)
# =============================================================================


class CompetitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    website: str = Field(..., min_length=4, max_length=1024)
    industry: Optional[str] = None
    relationship_type: str = Field(default="DIRECT")
    products_services: List[str] = Field(default_factory=list)
    target_customers: List[str] = Field(default_factory=list)
    geographic_markets: List[str] = Field(default_factory=list)
    discovery_rationale: Optional[str] = None


class CompetitorUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    relationship_type: Optional[str] = None
    products_services: Optional[List[str]] = None
    target_customers: Optional[List[str]] = None
    geographic_markets: Optional[List[str]] = None
    discovery_rationale: Optional[str] = None
    review_status: Optional[str] = None


class CompetitorResponse(BaseModel):
    id: int
    company_id: int
    name: str
    canonical_domain: str
    website: str
    industry: Optional[str] = None
    relationship_type: str
    products_services: List[Any] = Field(default_factory=list)
    target_customers: List[Any] = Field(default_factory=list)
    geographic_markets: List[Any] = Field(default_factory=list)
    discovery_method: str
    supporting_evidence: List[Any] = Field(default_factory=list)
    discovery_rationale: str
    confidence: float
    review_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntelligenceSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    canonical_url: str = Field(..., min_length=5, max_length=1024)
    category: str = Field(default="MARKET")
    source_type: str = Field(default="WEBSITE")
    secondary_categories: List[str] = Field(default_factory=list)
    why_it_matters: Optional[str] = None
    intelligence_type: Optional[str] = None
    credibility_score: float = Field(default=0.85, ge=0.0, le=1.0)
    competitor_id: Optional[int] = None


class IntelligenceSourceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    secondary_categories: Optional[List[str]] = None
    why_it_matters: Optional[str] = None
    intelligence_type: Optional[str] = None
    crawl_frequency_minutes: Optional[int] = None
    status: Optional[str] = None


class SourceCrawlLogResponse(BaseModel):
    id: int
    source_id: int
    status: str
    http_status: Optional[int] = None
    response_time_ms: Optional[int] = None
    content_hash: Optional[str] = None
    error_message: Optional[str] = None
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntelligenceSourceResponse(BaseModel):
    id: int
    company_id: int
    competitor_id: Optional[int] = None
    name: str
    canonical_url: str
    domain: str
    source_type: str
    category: str
    secondary_categories: List[Any] = Field(default_factory=list)
    why_it_matters: str
    intelligence_type: str
    discovery_method: str
    supporting_evidence: List[Any] = Field(default_factory=list)
    credibility_score: float
    status: str
    robots_status: str
    crawl_frequency_minutes: int
    last_attempted_crawl: Optional[datetime] = None
    last_successful_crawl: Optional[datetime] = None
    last_content_change: Optional[datetime] = None
    last_error: Optional[str] = None
    http_status: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceSummaryStats(BaseModel):
    total_sources: int
    approved: int
    pending: int
    rejected: int
    paused: int
    blocked: int
    by_category: Dict[str, int]
    competitors_count: int
    approved_competitors: int
