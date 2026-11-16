"""Company Intelligence Analyzer — Two-Stage Evidence Extraction Architecture.

Stage A: Page-Level Fact Extraction with Strict Evidence Validation.
Stage B: Company Profile Synthesis with Deterministic Facet Integration.
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.ai.base import BaseAIProvider
from app.ai.extractor import PageLevelFactExtractor, ValidatedPageFacts
from app.ai.synthesizer import CompanyProfileSynthesizer, SynthesizedProfileData
from app.ai.validator import FactValidationResult
from app.database.models import Company, CompanyFact, CompanyProfile, ResearchPage, ResearchRun

logger = logging.getLogger(__name__)


class CompanyIntelligenceAnalyzer:
    """Orchestrates Stage A (Page Extraction) and Stage B (Profile Synthesis)."""

    def __init__(self, provider: BaseAIProvider):
        self.provider = provider
        self.extractor = PageLevelFactExtractor(provider)
        self.synthesizer = CompanyProfileSynthesizer()

    async def analyze_and_persist(
        self,
        company: Company,
        research_run: ResearchRun,
        pages: List[ResearchPage],
        db: Session,
    ) -> Optional[CompanyProfile]:
        """
        Execute two-stage evidence extraction and persist profile and facts.
        Preserves all historical records while advancing profile_version.
        """
        if not pages:
            logger.warning(f"No pages available to analyze for company {company.id}")
            research_run.ai_analysis_status = "FAILED"
            research_run.error_message = "Cannot run AI analysis: no webpage content was successfully extracted."
            db.commit()
            return None

        logger.info(
            f"Starting Two-Stage AI Analysis for {company.name} across {len(pages)} pages "
            f"using provider '{self.provider.model_name}'"
        )
        research_run.ai_analysis_status = "RUNNING"
        db.commit()

        # =====================================================================
        # STAGE A: PAGE-LEVEL FACT EXTRACTION & STRICT VALIDATION
        # =====================================================================
        validated_pages: List[ValidatedPageFacts] = []
        all_candidate_facts: List[FactValidationResult] = []
        extraction_errors: List[str] = []

        for p in pages:
            try:
                v_page = await self.extractor.extract_page(p, company_name=company.name)
                validated_pages.append(v_page)
                all_candidate_facts.extend(v_page.validated_facts)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed Stage A extraction for page {p.id} ({p.url}): invalid JSON: {e}")
                extraction_errors.append(f"invalid JSON from AI: {e}")
            except Exception as e:
                logger.error(f"Failed Stage A extraction for page {p.id} ({p.url}): {e}")
                extraction_errors.append(str(e))

        if not validated_pages:
            research_run.ai_analysis_status = "FAILED"
            research_run.error_message = (
                f"AI returned invalid JSON schema: {extraction_errors[0] if extraction_errors else 'No valid outputs'}"
            )
            db.commit()
            return None

        # =====================================================================
        # STAGE B: PROFILE SYNTHESIS, DEDUPLICATION & CONFLICT RESOLUTION
        # =====================================================================
        active_facts, rejected_facts = self.synthesizer.merge_facts(all_candidate_facts)

        synth_data: SynthesizedProfileData = self.synthesizer.synthesize_profile(
            company_name=company.name,
            validated_pages=validated_pages,
            active_facts=active_facts,
        )

        # =====================================================================
        # DATABASE PERSISTENCE
        # =====================================================================
        now = datetime.now(timezone.utc)

        # 1. Persist CompanyFact records (both active and rejected for complete audit trail)
        all_facts_to_save = active_facts + rejected_facts
        for f in all_facts_to_save:
            db_fact = CompanyFact(
                company_id=company.id,
                research_page_id=f.research_page_id,
                category=f.provenance.get("category", "general") if f.provenance else "general",
                statement=f.statement,
                classification=f.classification,
                evidence_snippet=f.evidence_snippet,
                quote_start_offset=f.quote_start_offset,
                quote_end_offset=f.quote_end_offset,
                rejection_reason=f.rejection_reason,
                provenance=f.provenance,
                confidence=f.confidence,
                created_at=now,
            )
            db.add(db_fact)

        # 2. Persist CompanyProfile (incrementing profile_version)
        latest_profile = (
            db.query(CompanyProfile)
            .filter(CompanyProfile.company_id == company.id)
            .order_by(CompanyProfile.profile_version.desc())
            .first()
        )
        new_version = (latest_profile.profile_version + 1) if latest_profile else 1

        new_profile = CompanyProfile(
            company_id=company.id,
            research_run_id=research_run.id,
            industry=synth_data.industry or company.industry or "Technology",
            business_model=synth_data.business_model,
            products_services=synth_data.products_services,
            target_customers=synth_data.target_customers,
            customer_problems=synth_data.customer_problems,
            revenue_streams=synth_data.revenue_streams,
            geographical_markets=synth_data.geographical_markets,
            study_destinations=synth_data.study_destinations,
            business_partners=synth_data.business_partners,
            positioning=synth_data.positioning,
            growth_related_information=synth_data.growth_related_information,
            unknown_information=synth_data.unknown_information,
            profile_version=new_version,
            updated_at=now,
        )
        db.add(new_profile)

        # Update company industry if currently blank
        if not company.industry and synth_data.industry:
            company.industry = synth_data.industry

        research_run.ai_analysis_status = "COMPLETED"
        research_run.completed_at = now
        db.commit()

        verified_count = sum(1 for f in active_facts if f.classification == "VERIFIED_FACT")
        rejected_count = len(rejected_facts)
        logger.info(
            f"Successfully synthesized Profile v{new_version} for {company.name} "
            f"({verified_count} verified facts, {len(active_facts)} active facts, {rejected_count} rejected claims)"
        )

        return new_profile
