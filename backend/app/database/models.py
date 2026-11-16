import enum
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class DiscoveredUrlStatus(str, enum.Enum):
    PENDING = "PENDING"
    FETCHED = "FETCHED"
    FAILED = "FAILED"
    SKIPPED_LIMIT = "SKIPPED_LIMIT"
    SKIPPED_ROBOTS = "SKIPPED_ROBOTS"
    SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
    SKIPPED_OUT_OF_SCOPE = "SKIPPED_OUT_OF_SCOPE"


class InterviewSessionStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class InterviewQuestionType(str, enum.Enum):
    CORE = "CORE"
    FOLLOWUP = "FOLLOWUP"


class InterviewQuestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASKED = "ASKED"
    ANSWERED = "ANSWERED"
    SKIPPED = "SKIPPED"
    CONFIDENTIAL = "CONFIDENTIAL"


class InformationProvenanceType(str, enum.Enum):
    PUBLIC_VERIFIED_FACT = "PUBLIC_VERIFIED_FACT"
    FOUNDER_CONFIRMED = "FOUNDER_CONFIRMED"
    AI_INFERENCE = "AI_INFERENCE"
    UNKNOWN = "UNKNOWN"


class CompetitorRelationshipType(str, enum.Enum):
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    SUBSTITUTE = "SUBSTITUTE"


class CompetitorReviewStatus(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class IntelligenceSourceCategory(str, enum.Enum):
    CUSTOMERS = "CUSTOMERS"
    COMPETITORS = "COMPETITORS"
    MARKET = "MARKET"
    INTERNAL = "INTERNAL"


class IntelligenceSourceType(str, enum.Enum):
    WEBSITE = "WEBSITE"
    RSS_FEED = "RSS_FEED"
    SITEMAP = "SITEMAP"
    CASE_STUDY = "CASE_STUDY"
    REGULATORY = "REGULATORY"
    NEWS_FEED = "NEWS_FEED"
    INDUSTRY_PORTAL = "INDUSTRY_PORTAL"
    COMPANY_DISCLOSURE = "COMPANY_DISCLOSURE"
    FOUNDER_CONTEXT = "FOUNDER_CONTEXT"


class IntelligenceSourceStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class Company(Base):
    """Company registered for intelligence monitoring."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_domain: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    research_runs: Mapped[List["ResearchRun"]] = relationship(
        "ResearchRun", back_populates="company", cascade="all, delete-orphan", order_by="desc(ResearchRun.started_at)"
    )
    pages: Mapped[List["ResearchPage"]] = relationship(
        "ResearchPage", back_populates="company", cascade="all, delete-orphan"
    )
    profiles: Mapped[List["CompanyProfile"]] = relationship(
        "CompanyProfile", back_populates="company", cascade="all, delete-orphan", order_by="desc(CompanyProfile.profile_version)"
    )
    facts: Mapped[List["CompanyFact"]] = relationship(
        "CompanyFact", back_populates="company", cascade="all, delete-orphan", order_by="desc(CompanyFact.created_at)"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="company", cascade="all, delete-orphan", order_by="desc(InterviewSession.created_at)"
    )
    founder_contexts: Mapped[List["FounderBusinessContext"]] = relationship(
        "FounderBusinessContext", back_populates="company", cascade="all, delete-orphan"
    )
    competitors: Mapped[List["Competitor"]] = relationship(
        "Competitor", back_populates="company", cascade="all, delete-orphan", order_by="desc(Competitor.created_at)"
    )
    sources: Mapped[List["IntelligenceSource"]] = relationship(
        "IntelligenceSource", back_populates="company", cascade="all, delete-orphan", order_by="desc(IntelligenceSource.created_at)"
    )


class ResearchRun(Base):
    """Execution record for an automated crawling and AI research run."""

    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    # Statuses: PENDING, RUNNING, COMPLETED, COMPLETED_WITH_WARNINGS, FAILED

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pages_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_skipped_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_skipped_robots: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_skipped_duplicate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_skipped_out_of_scope: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_analysis_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="research_runs")
    pages: Mapped[List["ResearchPage"]] = relationship(
        "ResearchPage", back_populates="research_run"
    )
    profiles: Mapped[List["CompanyProfile"]] = relationship(
        "CompanyProfile", back_populates="research_run"
    )
    discovered_url_records: Mapped[List["DiscoveredUrl"]] = relationship(
        "DiscoveredUrl", back_populates="research_run", cascade="all, delete-orphan"
    )

    def validate_crawl_accounting(self) -> bool:
        """Enforce invariant: discovered == fetched + failed + skipped_*"""
        total_accounted = (
            self.pages_fetched
            + self.pages_failed
            + self.pages_skipped_limit
            + self.pages_skipped_robots
            + self.pages_skipped_duplicate
            + self.pages_skipped_out_of_scope
        )
        return self.pages_discovered == total_accounted


class DiscoveredUrl(Base):
    """Detailed tracking record for an individual URL discovered during a crawl."""

    __tablename__ = "discovered_urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    research_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=DiscoveredUrlStatus.PENDING.value, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationship
    research_run: Mapped["ResearchRun"] = relationship("ResearchRun", back_populates="discovered_url_records")


class ResearchPage(Base):
    """Extracted snapshot of a crawled webpage belonging to a company."""

    __tablename__ = "research_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    research_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("research_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="pages")
    research_run: Mapped[Optional["ResearchRun"]] = relationship("ResearchRun", back_populates="pages")
    facts: Mapped[List["CompanyFact"]] = relationship("CompanyFact", back_populates="research_page")

    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute SHA-256 hash of normalized extracted text."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


class CompanyProfile(Base):
    """Structured company intelligence profile synthesised from crawled evidence and founder context."""

    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    research_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("research_runs.id", ondelete="SET NULL"), nullable=True
    )
    interview_session_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("interview_sessions.id", ondelete="SET NULL"), nullable=True
    )
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    business_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    products_services: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    target_customers: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    customer_problems: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    revenue_streams: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    geographical_markets: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    study_destinations: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    business_partners: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    positioning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    growth_related_information: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    unknown_information: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="profiles")
    research_run: Mapped[Optional["ResearchRun"]] = relationship("ResearchRun", back_populates="profiles")
    interview_session: Mapped[Optional["InterviewSession"]] = relationship("InterviewSession", back_populates="profiles")


class CompanyFact(Base):
    """Traceable, evidence-backed fact or stated assumption about a company."""

    __tablename__ = "company_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    research_page_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("research_pages.id", ondelete="SET NULL"), index=True, nullable=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    # Classification: VERIFIED_FACT, ASSUMPTION, UNKNOWN, REJECTED_UNSUPPORTED
    provenance_type: Mapped[str] = mapped_column(
        String(50), default=InformationProvenanceType.PUBLIC_VERIFIED_FACT.value, nullable=False
    )
    # Provenance: PUBLIC_VERIFIED_FACT, FOUNDER_CONFIRMED, AI_INFERENCE, UNKNOWN
    evidence_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quote_start_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quote_end_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provenance: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="facts")
    research_page: Mapped[Optional["ResearchPage"]] = relationship("ResearchPage", back_populates="facts")


# =============================================================================
# ADAPTIVE AI INTERVIEW MODELS
# =============================================================================


class InterviewSession(Base):
    """Persistent session for an adaptive AI interview with a company founder."""

    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    profile_version_at_start: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=InterviewSessionStatus.NOT_STARTED.value, nullable=False
    )
    # Statuses: NOT_STARTED, IN_PROGRESS, PAUSED, COMPLETED
    total_core_questions: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    answered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="interview_sessions")
    questions: Mapped[List["InterviewQuestion"]] = relationship(
        "InterviewQuestion", back_populates="session", cascade="all, delete-orphan", order_by="InterviewQuestion.question_order"
    )
    contexts: Mapped[List["FounderBusinessContext"]] = relationship(
        "FounderBusinessContext", back_populates="session", cascade="all, delete-orphan"
    )
    profiles: Mapped[List["CompanyProfile"]] = relationship(
        "CompanyProfile", back_populates="interview_session"
    )


class InterviewQuestion(Base):
    """An individual core or contextual follow-up question generated for the founder."""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_question_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("interview_questions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    question_type: Mapped[str] = mapped_column(
        String(20), default=InterviewQuestionType.CORE.value, nullable=False
    )
    # CORE or FOLLOWUP
    question_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    business_area: Mapped[str] = mapped_column(String(100), nullable=False)
    reason_for_asking: Mapped[str] = mapped_column(Text, nullable=False)
    information_objective: Mapped[str] = mapped_column(Text, nullable=False)
    related_company_profile_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expected_information_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=InterviewQuestionStatus.PENDING.value, nullable=False
    )
    # PENDING, ASKED, ANSWERED, SKIPPED, CONFIDENTIAL

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="questions")
    answers: Mapped[List["InterviewAnswer"]] = relationship(
        "InterviewAnswer", back_populates="question", cascade="all, delete-orphan", order_by="desc(InterviewAnswer.created_at)"
    )
    parent_question: Mapped[Optional["InterviewQuestion"]] = relationship(
        "InterviewQuestion", remote_side=[id], back_populates="followups"
    )
    followups: Mapped[List["InterviewQuestion"]] = relationship(
        "InterviewQuestion", back_populates="parent_question"
    )


class InterviewAnswer(Base):
    """Founder response to an interview question."""

    __tablename__ = "interview_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interview_questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    question: Mapped["InterviewQuestion"] = relationship("InterviewQuestion", back_populates="answers")
    context_items: Mapped[List["FounderBusinessContext"]] = relationship(
        "FounderBusinessContext", back_populates="answer"
    )


class FounderBusinessContext(Base):
    """Structured proprietary context confirmed by founder answers (strictly segregated from public facts)."""

    __tablename__ = "founder_business_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    interview_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    context_category: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. revenue_streams, highest_value_customers, customer_acquisition, competitors, growth_priorities, strategic_decisions, risks
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    confirmed_value: Mapped[Any] = mapped_column(JSON, nullable=False)
    originating_answer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("interview_answers.id", ondelete="SET NULL"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="founder_contexts")
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="contexts")
    answer: Mapped[Optional["InterviewAnswer"]] = relationship("InterviewAnswer", back_populates="context_items")


# =============================================================================
# DYNAMIC COMPETITOR DISCOVERY & SOURCE INTELLIGENCE MODELS (TASK 4)
# =============================================================================


class Competitor(Base):
    """Evidence-grounded competitor or market substitute discovered for a target company."""

    __tablename__ = "competitors"
    __table_args__ = (
        UniqueConstraint("company_id", "canonical_domain", name="uq_company_competitor_domain"),
        Index("ix_competitor_company_status", "company_id", "review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str] = mapped_column(String(1024), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    relationship_type: Mapped[str] = mapped_column(
        String(50), default=CompetitorRelationshipType.DIRECT.value, nullable=False
    )
    # DIRECT, INDIRECT, SUBSTITUTE
    products_services: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    target_customers: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    geographic_markets: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    discovery_method: Mapped[str] = mapped_column(
        String(100), default="AI_PROFILE_EXTRACTION", nullable=False
    )
    # e.g. AI_PROFILE_EXTRACTION, RESEARCH_PAGE_MENTION, FOUNDER_INTERVIEW, MANUAL_ENTRY
    supporting_evidence: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    discovery_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(50), default=CompetitorReviewStatus.CANDIDATE.value, nullable=False
    )
    # CANDIDATE, APPROVED, REJECTED, ARCHIVED

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="competitors")
    sources: Mapped[List["IntelligenceSource"]] = relationship("IntelligenceSource", back_populates="competitor")


class IntelligenceSource(Base):
    """External public or internal intelligence source registered for monitoring."""

    __tablename__ = "intelligence_sources"
    __table_args__ = (
        UniqueConstraint("company_id", "canonical_url", name="uq_company_source_url"),
        Index("ix_source_company_cat_status", "company_id", "category", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    competitor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="SET NULL"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), default=IntelligenceSourceType.WEBSITE.value, nullable=False
    )
    category: Mapped[str] = mapped_column(
        String(50), default=IntelligenceSourceCategory.MARKET.value, nullable=False
    )
    # CUSTOMERS, COMPETITORS, MARKET, INTERNAL
    secondary_categories: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    intelligence_type: Mapped[str] = mapped_column(String(255), nullable=False)
    discovery_method: Mapped[str] = mapped_column(
        String(100), default="AUTOMATED_DISCOVERY", nullable=False
    )
    # SITEMAP_DISCOVERY, RSS_PROBING, RESEARCH_PAGE_LINK, COMPETITOR_PAGE, FOUNDER_ANSWER, INSTITUTIONAL_REFERENCE, MANUAL_ENTRY
    supporting_evidence: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    credibility_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=IntelligenceSourceStatus.DISCOVERED.value, nullable=False
    )
    # DISCOVERED, PENDING_APPROVAL, APPROVED, REJECTED, PAUSED, BLOCKED, ERROR
    robots_status: Mapped[str] = mapped_column(String(50), default="ALLOWED", nullable=False)
    crawl_frequency_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False)
    last_attempted_crawl: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_crawl: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_content_change: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="sources")
    competitor: Mapped[Optional["Competitor"]] = relationship("Competitor", back_populates="sources")
    crawl_logs: Mapped[List["SourceCrawlLog"]] = relationship(
        "SourceCrawlLog", back_populates="source", cascade="all, delete-orphan", order_by="desc(SourceCrawlLog.checked_at)"
    )


class SourceCrawlLog(Base):
    """Audit log of health checks, probes, and crawl executions for an intelligence source."""

    __tablename__ = "source_crawl_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("intelligence_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    # SUCCESS, FAILED, SKIPPED_ROBOTS, SKIPPED_UNCHANGED
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationship
    source: Mapped["IntelligenceSource"] = relationship("IntelligenceSource", back_populates="crawl_logs")
