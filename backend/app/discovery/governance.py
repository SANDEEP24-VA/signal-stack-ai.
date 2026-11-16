"""Source and Competitor Governance Engine.

Provides lifecycle management, status transitions, metadata editing,
and safe health check execution for registered sources and competitors.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.url_utils import normalize_domain, normalize_url, validate_ip_security, validate_url_syntax
from app.database.models import (
    Competitor,
    CompetitorReviewStatus,
    IntelligenceSource,
    IntelligenceSourceStatus,
    SourceCrawlLog,
    utc_now,
)

logger = logging.getLogger(__name__)


class SourceGovernanceManager:
    """Manages source approval workflow, state transitions, and health verification."""

    def __init__(self, db: Session):
        self.db = db

    def approve_source(self, source_id: int) -> IntelligenceSource:
        """Approve a discovered source for intelligence monitoring."""
        source = self.db.get(IntelligenceSource, source_id)
        if not source:
            raise ValueError(f"Intelligence source {source_id} not found.")

        source.status = IntelligenceSourceStatus.APPROVED.value
        source.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(source)
        logger.info(f"Approved intelligence source {source_id} ('{source.name}').")
        return source

    def reject_source(self, source_id: int, reason: Optional[str] = None) -> IntelligenceSource:
        """Reject a discovered source and record rationale."""
        source = self.db.get(IntelligenceSource, source_id)
        if not source:
            raise ValueError(f"Intelligence source {source_id} not found.")

        source.status = IntelligenceSourceStatus.REJECTED.value
        if reason:
            source.last_error = f"Rejected: {reason}"
        source.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(source)
        logger.info(f"Rejected intelligence source {source_id} ('{source.name}').")
        return source

    def pause_source(self, source_id: int) -> IntelligenceSource:
        """Pause monitoring for an approved source."""
        source = self.db.get(IntelligenceSource, source_id)
        if not source:
            raise ValueError(f"Intelligence source {source_id} not found.")

        source.status = IntelligenceSourceStatus.PAUSED.value
        source.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(source)
        logger.info(f"Paused intelligence source {source_id}.")
        return source

    def resume_source(self, source_id: int) -> IntelligenceSource:
        """Resume monitoring for a paused source."""
        source = self.db.get(IntelligenceSource, source_id)
        if not source:
            raise ValueError(f"Intelligence source {source_id} not found.")

        source.status = IntelligenceSourceStatus.APPROVED.value
        source.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(source)
        logger.info(f"Resumed intelligence source {source_id}.")
        return source

    def edit_source(
        self,
        source_id: int,
        name: Optional[str] = None,
        category: Optional[str] = None,
        why_it_matters: Optional[str] = None,
        intelligence_type: Optional[str] = None,
        crawl_frequency_minutes: Optional[int] = None,
    ) -> IntelligenceSource:
        """Update source metadata, categorization, or schedule."""
        source = self.db.get(IntelligenceSource, source_id)
        if not source:
            raise ValueError(f"Intelligence source {source_id} not found.")

        if name and name.strip():
            source.name = name.strip()
        if category and category.strip():
            source.category = category.strip().upper()
        if why_it_matters and why_it_matters.strip():
            source.why_it_matters = why_it_matters.strip()
        if intelligence_type and intelligence_type.strip():
            source.intelligence_type = intelligence_type.strip()
        if crawl_frequency_minutes is not None and crawl_frequency_minutes > 0:
            source.crawl_frequency_minutes = crawl_frequency_minutes

        source.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete_source(self, source_id: int) -> bool:
        """Remove an intelligence source."""
        source = self.db.get(IntelligenceSource, source_id)
        if not source:
            raise ValueError(f"Intelligence source {source_id} not found.")

        self.db.delete(source)
        self.db.commit()
        return True

    async def probe_source_health(self, source_id: int) -> SourceCrawlLog:
        """Safely probes source URL, checks HTTP status, computes content hash, and logs result."""
        source = self.db.get(IntelligenceSource, source_id)
        if not source:
            raise ValueError(f"Intelligence source {source_id} not found.")

        now = utc_now()
        source.last_attempted_crawl = now

        # Validate IP security
        is_safe_ip, msg = validate_ip_security(source.domain)
        if not is_safe_ip:
            source.status = IntelligenceSourceStatus.BLOCKED.value
            source.last_error = f"Blocked by IP security: {msg}"
            log = SourceCrawlLog(
                source_id=source.id,
                status="FAILED",
                error_message=source.last_error,
                checked_at=now,
            )
            self.db.add(log)
            self.db.commit()
            return log

        try:
            start_time = datetime.now()
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                resp = await client.get(source.canonical_url)
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            source.http_status = resp.status_code
            text_bytes = resp.content
            new_hash = hashlib.sha256(text_bytes).hexdigest()

            if resp.status_code < 400:
                source.last_successful_crawl = now
                source.last_error = None
                if source.status == IntelligenceSourceStatus.ERROR.value:
                    source.status = IntelligenceSourceStatus.APPROVED.value

                log = SourceCrawlLog(
                    source_id=source.id,
                    status="SUCCESS",
                    http_status=resp.status_code,
                    response_time_ms=duration_ms,
                    content_hash=new_hash,
                    checked_at=now,
                )
            else:
                source.last_error = f"HTTP {resp.status_code}"
                log = SourceCrawlLog(
                    source_id=source.id,
                    status="FAILED",
                    http_status=resp.status_code,
                    response_time_ms=duration_ms,
                    error_message=f"HTTP {resp.status_code}",
                    checked_at=now,
                )
        except Exception as e:
            source.last_error = str(e)
            log = SourceCrawlLog(
                source_id=source.id,
                status="FAILED",
                error_message=str(e),
                checked_at=now,
            )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(source)
        self.db.refresh(log)
        return log


class CompetitorGovernanceManager:
    """Manages competitor review status, edits, and lifecycle."""

    def __init__(self, db: Session):
        self.db = db

    def approve_competitor(self, competitor_id: int) -> Competitor:
        competitor = self.db.get(Competitor, competitor_id)
        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found.")

        competitor.review_status = CompetitorReviewStatus.APPROVED.value
        competitor.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(competitor)
        return competitor

    def reject_competitor(self, competitor_id: int) -> Competitor:
        competitor = self.db.get(Competitor, competitor_id)
        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found.")

        competitor.review_status = CompetitorReviewStatus.REJECTED.value
        competitor.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(competitor)
        return competitor

    def archive_competitor(self, competitor_id: int) -> Competitor:
        competitor = self.db.get(Competitor, competitor_id)
        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found.")

        competitor.review_status = CompetitorReviewStatus.ARCHIVED.value
        competitor.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(competitor)
        return competitor

    def edit_competitor(
        self,
        competitor_id: int,
        name: Optional[str] = None,
        website: Optional[str] = None,
        relationship_type: Optional[str] = None,
        industry: Optional[str] = None,
        products_services: Optional[List[str]] = None,
        target_customers: Optional[List[str]] = None,
        geographic_markets: Optional[List[str]] = None,
        discovery_rationale: Optional[str] = None,
    ) -> Competitor:
        competitor = self.db.get(Competitor, competitor_id)
        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found.")

        if name and name.strip():
            competitor.name = name.strip()
        if website and website.strip():
            is_valid, msg = validate_url_syntax(website)
            if not is_valid:
                raise ValueError(f"Invalid website URL: {msg}")
            competitor.canonical_domain = normalize_domain(website)
            competitor.website = normalize_url(website)
        if relationship_type and relationship_type.upper() in ("DIRECT", "INDIRECT", "SUBSTITUTE"):
            competitor.relationship_type = relationship_type.upper()
        if industry and industry.strip():
            competitor.industry = industry.strip()
        if products_services is not None:
            competitor.products_services = products_services
        if target_customers is not None:
            competitor.target_customers = target_customers
        if geographic_markets is not None:
            competitor.geographic_markets = geographic_markets
        if discovery_rationale and discovery_rationale.strip():
            competitor.discovery_rationale = discovery_rationale.strip()

        competitor.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(competitor)
        return competitor
