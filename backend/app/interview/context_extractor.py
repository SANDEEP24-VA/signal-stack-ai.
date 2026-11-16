"""Founder Business Context Extractor and Profile Synthesizer.

Extracts structured corporate context from non-confidential founder responses,
persists segregated FounderBusinessContext records, and generates an upgraded
CompanyProfile version with explicit provenance tagging (FOUNDER_CONFIRMED).
Public facts are never overwritten or deleted.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.ai.base import BaseAIProvider
from app.database.models import (
    Company,
    CompanyFact,
    CompanyProfile,
    FounderBusinessContext,
    InformationProvenanceType,
    InterviewAnswer,
    InterviewQuestion,
    InterviewQuestionStatus,
    InterviewSession,
    InterviewSessionStatus,
    utc_now,
)

logger = logging.getLogger(__name__)


CONTEXT_EXTRACTION_SYSTEM_PROMPT = """You are an Executive Business Intelligence Analyst for Signal Stack AI.
Your objective is to analyze verified interview answers provided by a company founder and extract structured business intelligence.

RULES:
1. Extract confirmed business context into standard executive intelligence categories:
   - revenue_streams: Monetization models, fee structures, pricing mechanics.
   - target_customers: Primary ICP, high-value segments, enterprise vs consumer breakdown.
   - customer_problems: Key pain points, unmet needs solved.
   - competitors: Named competitors, alternatives, and substitutes.
   - growth_priorities: 12-month expansion targets, geographic rollouts, product horizons.
   - strategic_risks: Operational, market, and regulatory vulnerabilities identified.
   - decision_priorities: Critical strategic questions executive intelligence must monitor.
2. Return strictly valid JSON adhering to the specified schema.
"""


class ExtractedContextItem(BaseModel):
    category: str = Field(..., description="e.g. revenue_streams, target_customers, competitors, growth_priorities, strategic_risks, decision_priorities")
    field_name: str = Field(..., description="Specific metric or attribute name")
    confirmed_value: Any = Field(..., description="Structured string, list, or dictionary")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class StructuredExtractionResult(BaseModel):
    items: List[ExtractedContextItem] = Field(default_factory=list)
    resolved_unknowns: List[str] = Field(default_factory=list)


class FounderContextExtractor:
    """Extracts structured intelligence from founder interview answers and upgrades company profile."""

    def __init__(self, db: Session, provider: BaseAIProvider):
        self.db = db
        self.provider = provider

    async def complete_and_extract(
        self,
        session_id: int,
    ) -> Dict[str, Any]:
        """
        Finalizes an interview session:
        1. Extracts structured context from non-confidential answers.
        2. Persists FounderBusinessContext records.
        3. Updates CompanyProfile to next version with FOUNDER_CONFIRMED provenance.
        4. Preserves all historical research records and public verified facts.
        """
        session = self.db.get(InterviewSession, session_id)
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")

        company = self.db.get(Company, session.company_id)
        if not company:
            raise ValueError(f"Company {session.company_id} not found.")

        # 1. Fetch non-confidential answered questions
        stmt = (
            select(InterviewQuestion)
            .where(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.status.in_([
                    InterviewQuestionStatus.ANSWERED.value,
                    InterviewQuestionStatus.CONFIDENTIAL.value,
                ]),
            )
            .order_by(InterviewQuestion.question_order.asc(), InterviewQuestion.id.asc())
        )
        questions = list(self.db.scalars(stmt).all())

        # Segregate confidential answers: they are NEVER sent to LLM or stored in public profile
        public_qa_pairs: List[Dict[str, Any]] = []
        confidential_qa_count = 0

        for q in questions:
            for ans in q.answers:
                if ans.is_confidential:
                    confidential_qa_count += 1
                elif ans.answer_text and ans.answer_text.strip() and not ans.answer_text.startswith("[SKIPPED"):
                    public_qa_pairs.append({
                        "question_id": q.id,
                        "answer_id": ans.id,
                        "business_area": q.business_area,
                        "question_text": q.question_text,
                        "answer_text": ans.answer_text.strip(),
                        "objective": q.information_objective,
                    })

        # 2. Extract structured business context
        extraction_result = await self._extract_business_context(
            company=company,
            qa_pairs=public_qa_pairs,
        )

        # 3. Persist FounderBusinessContext rows
        created_contexts: List[FounderBusinessContext] = []
        for item in extraction_result.items:
            # Locate corresponding answer_id if possible
            matching_ans_id = None
            for qa in public_qa_pairs:
                if (
                    item.category.lower() in qa["business_area"].lower()
                    or item.field_name.lower() in qa["question_text"].lower()
                ):
                    matching_ans_id = qa["answer_id"]
                    break

            if not matching_ans_id and public_qa_pairs:
                matching_ans_id = public_qa_pairs[0]["answer_id"]

            context_row = FounderBusinessContext(
                company_id=company.id,
                interview_session_id=session.id,
                context_category=item.category,
                field_name=item.field_name,
                confirmed_value=item.confirmed_value,
                originating_answer_id=matching_ans_id,
                confidence=item.confidence,
                created_at=utc_now(),
            )
            self.db.add(context_row)
            created_contexts.append(context_row)

        self.db.flush()

        # 4. Fetch latest profile
        latest_profile = (
            self.db.scalars(
                select(CompanyProfile)
                .where(CompanyProfile.company_id == company.id)
                .order_by(desc(CompanyProfile.profile_version))
            ).first()
        )

        new_version = (latest_profile.profile_version + 1) if latest_profile else 1

        # Synthesize upgraded profile while keeping public facts strictly untouched
        new_profile = self._synthesize_updated_profile(
            company=company,
            previous_profile=latest_profile,
            new_version=new_version,
            session_id=session.id,
            extracted_items=extraction_result.items,
            resolved_unknowns=extraction_result.resolved_unknowns,
        )
        self.db.add(new_profile)

        # 5. Mark session completed
        session.status = InterviewSessionStatus.COMPLETED.value
        session.completed_at = utc_now()

        self.db.commit()
        self.db.refresh(session)
        self.db.refresh(new_profile)

        logger.info(
            f"Successfully finalized interview {session.id} for company '{company.name}'. "
            f"Profile upgraded to v{new_profile.profile_version} with {len(created_contexts)} context records."
        )

        return {
            "session_id": session.id,
            "company_id": company.id,
            "status": session.status,
            "profile_version": new_profile.profile_version,
            "extracted_context_count": len(created_contexts),
            "confidential_answers_protected": confidential_qa_count,
            "resolved_unknowns_count": len(extraction_result.resolved_unknowns),
            "completed_at": session.completed_at,
        }

    async def _extract_business_context(
        self,
        company: Company,
        qa_pairs: List[Dict[str, Any]],
    ) -> StructuredExtractionResult:
        """Run LLM extraction with deterministic fallback on founder responses."""
        if not qa_pairs:
            return StructuredExtractionResult(items=[], resolved_unknowns=[])

        prompt_qa = "\n\n".join([
            f"[{i+1}] TOPIC: {qa['business_area']}\n"
            f"QUESTION: {qa['question_text']}\n"
            f"FOUNDER ANSWER: {qa['answer_text']}"
            for i, qa in enumerate(qa_pairs)
        ])

        user_prompt = (
            f"Company: '{company.name}' ({company.normalized_domain})\n\n"
            f"Analyze the founder's verified interview answers below and extract structured corporate context:\n\n"
            f"{prompt_qa}\n\n"
            "Return JSON adhering strictly to this schema:\n"
            "{\n"
            '  "items": [\n'
            '    {\n'
            '      "category": "revenue_streams",\n'
            '      "field_name": "primary_monetization",\n'
            '      "confirmed_value": "Description or list of revenue streams",\n'
            '      "confidence": 1.0\n'
            '    }\n'
            '  ],\n'
            '  "resolved_unknowns": ["Item previously unknown that is now clarified"]\n'
            "}"
        )

        try:
            completion = await self.provider.generate_completion(
                prompt=user_prompt,
                system_instruction=CONTEXT_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1,
            )
            raw = completion.raw_text.strip()
            if raw.startswith("```"):
                lines = raw.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw = "\n".join(lines).strip()

            data = json.loads(raw)
            items = []
            for item_data in data.get("items", []):
                items.append(ExtractedContextItem(
                    category=str(item_data.get("category", "general_context")),
                    field_name=str(item_data.get("field_name", "confirmed_data")),
                    confirmed_value=item_data.get("confirmed_value", ""),
                    confidence=float(item_data.get("confidence", 1.0)),
                ))
            resolved = [str(r) for r in data.get("resolved_unknowns", [])]
            if items:
                return StructuredExtractionResult(items=items, resolved_unknowns=resolved)
        except Exception as exc:
            logger.warning(f"LLM context extraction failed, utilizing deterministic fallback: {exc}")

        # Deterministic fallback mapping based on business areas
        return self._deterministic_fallback_extraction(qa_pairs)

    def _deterministic_fallback_extraction(
        self,
        qa_pairs: List[Dict[str, Any]],
    ) -> StructuredExtractionResult:
        """Rule-based extractor guaranteeing structured records when LLM is unavailable."""
        items: List[ExtractedContextItem] = []
        resolved: List[str] = []

        for qa in qa_pairs:
            topic = qa["business_area"].lower()
            text = qa["answer_text"]

            if "revenue" in topic or "monetization" in topic or "pricing" in topic:
                items.append(ExtractedContextItem(
                    category="revenue_streams",
                    field_name="monetization_structure",
                    confirmed_value=text,
                    confidence=1.0,
                ))
                resolved.append("Commercial monetization model")
            elif "customer" in topic or "acquisition" in topic or "icp" in topic:
                items.append(ExtractedContextItem(
                    category="target_customers",
                    field_name="primary_customer_segments",
                    confirmed_value=text,
                    confidence=1.0,
                ))
            elif "problem" in topic or "pain" in topic or "value" in topic:
                items.append(ExtractedContextItem(
                    category="customer_problems",
                    field_name="core_problems_solved",
                    confirmed_value=text,
                    confidence=1.0,
                ))
            elif "competitor" in topic or "substitute" in topic or "alternative" in topic:
                items.append(ExtractedContextItem(
                    category="competitors",
                    field_name="key_competitors",
                    confirmed_value=text,
                    confidence=1.0,
                ))
                resolved.append("Competitive landscape and direct rivals")
            elif "growth" in topic or "expansion" in topic or "12-month" in topic:
                items.append(ExtractedContextItem(
                    category="growth_priorities",
                    field_name="growth_roadmap",
                    confirmed_value=text,
                    confidence=1.0,
                ))
            elif "risk" in topic or "vulnerability" in topic:
                items.append(ExtractedContextItem(
                    category="strategic_risks",
                    field_name="identified_business_risks",
                    confirmed_value=text,
                    confidence=1.0,
                ))
            elif "decision" in topic or "support" in topic or "executive" in topic:
                items.append(ExtractedContextItem(
                    category="decision_priorities",
                    field_name="executive_decision_support",
                    confirmed_value=text,
                    confidence=1.0,
                ))
            else:
                items.append(ExtractedContextItem(
                    category="operational_context",
                    field_name=qa["business_area"].lower().replace(" ", "_"),
                    confirmed_value=text,
                    confidence=1.0,
                ))

        return StructuredExtractionResult(items=items, resolved_unknowns=resolved)

    def _synthesize_updated_profile(
        self,
        company: Company,
        previous_profile: Optional[CompanyProfile],
        new_version: int,
        session_id: int,
        extracted_items: List[ExtractedContextItem],
        resolved_unknowns: List[str],
    ) -> CompanyProfile:
        """
        Synthesize next profile version merging public facts with founder confirmation.
        Public facts remain immutable.
        """
        # Base values from previous profile or empty defaults
        industry = previous_profile.industry if previous_profile else company.industry
        business_model = previous_profile.business_model if previous_profile else None
        positioning = previous_profile.positioning if previous_profile else None
        research_run_id = previous_profile.research_run_id if previous_profile else None

        products = list(previous_profile.products_services) if previous_profile and previous_profile.products_services else []
        customers = list(previous_profile.target_customers) if previous_profile and previous_profile.target_customers else []
        problems = list(previous_profile.customer_problems) if previous_profile and previous_profile.customer_problems else []
        revenue_streams = list(previous_profile.revenue_streams) if previous_profile and previous_profile.revenue_streams else []
        geo_markets = list(previous_profile.geographical_markets) if previous_profile and previous_profile.geographical_markets else []
        study_destinations = list(getattr(previous_profile, "study_destinations", [])) if previous_profile else []
        business_partners = list(previous_profile.business_partners) if previous_profile and previous_profile.business_partners else []
        growth_info = list(previous_profile.growth_related_information) if previous_profile and previous_profile.growth_related_information else []
        unknown_info = list(previous_profile.unknown_information) if previous_profile and previous_profile.unknown_information else []

        # Merge extracted founder context
        for item in extracted_items:
            val = item.confirmed_value
            val_str = str(val).strip()

            if item.category == "revenue_streams":
                entry = f"[Founder Confirmed] {val_str}"
                if entry not in revenue_streams:
                    revenue_streams.append(entry)
            elif item.category == "target_customers":
                entry = f"[Founder Confirmed] {val_str}"
                if entry not in customers:
                    customers.append(entry)
            elif item.category == "customer_problems":
                entry = f"[Founder Confirmed] {val_str}"
                if entry not in problems:
                    problems.append(entry)
            elif item.category == "growth_priorities":
                entry = f"[Founder Confirmed] {val_str}"
                if entry not in growth_info:
                    growth_info.append(entry)
            elif item.category == "competitors":
                entry = f"[Founder Confirmed Competitor] {val_str}"
                if entry not in business_partners and entry not in positioning:
                    positioning = f"{positioning or ''} | Founder Competitor Context: {val_str}".strip(" |")

        # Prune resolved unknowns
        if resolved_unknowns:
            lower_resolved = [r.lower() for r in resolved_unknowns]
            pruned_unknowns = []
            for u in unknown_info:
                u_str = str(u).lower()
                if not any(res in u_str for res in lower_resolved):
                    pruned_unknowns.append(u)
            unknown_info = pruned_unknowns

        new_profile = CompanyProfile(
            company_id=company.id,
            research_run_id=research_run_id,
            interview_session_id=session_id,
            industry=industry,
            business_model=business_model,
            products_services=products,
            target_customers=customers,
            customer_problems=problems,
            revenue_streams=revenue_streams,
            geographical_markets=geo_markets,
            study_destinations=study_destinations,
            business_partners=business_partners,
            positioning=positioning,
            growth_related_information=growth_info,
            unknown_information=unknown_info,
            profile_version=new_version,
            updated_at=utc_now(),
        )
        return new_profile
