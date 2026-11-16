"""Stage A: Page-Level Fact Extractor.

Processes individual ResearchPage instances to extract evidence-grounded candidate facts,
products/services, target customers, and business model statements with exact quotations.
Passes each candidate fact through StrictEvidenceValidator.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.ai.base import BaseAIProvider
from app.ai.validator import FactValidationResult, StrictEvidenceValidator
from app.crawlers.facets import DeterministicFacetExtractor, PageFacets
from app.database.models import ResearchPage

logger = logging.getLogger(__name__)


class CandidateFactItem(BaseModel):
    statement: str
    evidence_snippet: str = ""
    category: str = "general"
    classification: str = "VERIFIED_FACT"  # VERIFIED_FACT, ASSUMPTION, UNKNOWN


class PageExtractionOutput(BaseModel):
    page_id: int
    url: str
    title: Optional[str] = None
    products_services: List[str] = Field(default_factory=list)
    target_customers: List[str] = Field(default_factory=list)
    customer_problems: List[str] = Field(default_factory=list)
    study_destinations: List[str] = Field(default_factory=list)
    operational_locations: List[str] = Field(default_factory=list)
    business_model: Optional[str] = None
    revenue_streams: List[str] = Field(default_factory=list)
    positioning: Optional[str] = None
    facts: List[CandidateFactItem] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)


class ValidatedPageFacts(BaseModel):
    page_id: int
    url: str
    title: Optional[str] = None
    products_services: List[str] = Field(default_factory=list)
    target_customers: List[str] = Field(default_factory=list)
    customer_problems: List[str] = Field(default_factory=list)
    study_destinations: List[str] = Field(default_factory=list)
    operational_locations: List[str] = Field(default_factory=list)
    business_model: Optional[str] = None
    revenue_streams: List[str] = Field(default_factory=list)
    positioning: Optional[str] = None
    validated_facts: List[FactValidationResult] = Field(default_factory=list)


PAGE_EXTRACTION_SYSTEM_PROMPT = """You are a rigorous Company Intelligence Extraction Engine.
Your task is to analyze a SINGLE webpage and extract verified, evidence-grounded company facts.

CRITICAL TRUTH & ANTI-HALLUCINATION RULES:
1. ONLY extract information explicitly stated in the provided webpage text.
2. For EVERY item in 'facts', you MUST provide an exact, verbatim quotation ('evidence_snippet') from the text.
3. NEVER invent or guess founding dates, inception years, or company history. If not in the text, leave blank.
4. NEVER invent percentages, statistics, or client satisfaction metrics (e.g. do not guess 95%).
5. NEVER generate placeholder competitors (e.g., do NOT output 'ABC Education' or 'DEF Consulting').
6. NEVER infer revenue streams (e.g. do NOT guess ads, affiliate marketing, or commissions) unless explicitly stated.
7. Distinguish clearly between:
   - Target customers (e.g. students seeking education)
   - Business partners (e.g. partner universities)
   - Study destinations (countries students go to) vs. Operational presence (where the company has offices)
8. Output MUST be valid JSON adhering strictly to the requested schema.
"""


class PageLevelFactExtractor:
    """Stage A: Extracts candidate facts from individual ResearchPages."""

    def __init__(self, provider: BaseAIProvider):
        self.provider = provider
        self.facet_extractor = DeterministicFacetExtractor()

    async def extract_page(self, page: ResearchPage, company_name: str) -> ValidatedPageFacts:
        """Process an individual ResearchPage through LLM extraction and deterministic validation."""
        page_text = page.extracted_text or ""
        clean_text_preview = page_text[:4000]

        # 1. Deterministic facet extraction
        page_facets = self.facet_extractor.process_page(
            url=page.url,
            title=page.title,
            text=page_text,
            page_id=page.id,
        )

        user_prompt = (
            f"Analyze the following webpage for '{company_name}':\n"
            f"PAGE ID: {page.id}\n"
            f"URL: {page.url}\n"
            f"TITLE: {page.title or 'N/A'}\n\n"
            f"WEBPAGE CONTENT:\n{clean_text_preview}\n\n"
            "Extract structured findings and return a JSON object with this exact schema:\n"
            "{\n"
            '  "products_services": ["exact service or product mentioned"],\n'
            '  "target_customers": ["customer segment mentioned"],\n'
            '  "customer_problems": ["problem solved mentioned"],\n'
            '  "study_destinations": ["country mentioned as a study destination"],\n'
            '  "operational_locations": ["city or country where company has an office/presence"],\n'
            '  "business_model": "brief stated model or null",\n'
            '  "revenue_streams": ["explicitly stated revenue sources or leave empty"],\n'
            '  "positioning": "stated positioning/motto or null",\n'
            '  "facts": [\n'
            '    {\n'
            '      "statement": "concise factual statement",\n'
            '      "evidence_snippet": "exact verbatim quote from text supporting it",\n'
            '      "category": "products_services | history | customers | positioning | locations",\n'
            '      "classification": "VERIFIED_FACT"\n'
            '    }\n'
            '  ],\n'
            '  "assumptions": ["reasonable inference if any"],\n'
            '  "unknowns": ["information not stated on this page"]\n'
            "}"
        )

        completion = await self.provider.generate_completion(
            prompt=user_prompt,
            system_instruction=PAGE_EXTRACTION_SYSTEM_PROMPT,
            temperature=0.0,
        )
        raw_text = completion.raw_text.strip()
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        data = json.loads(raw_text)
        if not isinstance(data, dict):
            raise ValueError("Expected top-level JSON dictionary from AI completion")

        # Parse candidate facts defensively (supporting both 'facts' and 'verified_facts')
        raw_facts_data = data.get("facts") or data.get("verified_facts") or []
        raw_facts: List[CandidateFactItem] = []
        for item in raw_facts_data:
            if isinstance(item, dict) and item.get("statement"):
                raw_facts.append(
                    CandidateFactItem(
                        statement=str(item["statement"]),
                        evidence_snippet=str(item.get("evidence_snippet") or item.get("quote") or ""),
                        category=str(item.get("category") or "general"),
                        classification=str(item.get("classification") or "VERIFIED_FACT"),
                    )
                )

        # Parse assumptions (supporting both dicts and strings)
        raw_assump_data = data.get("assumptions") or []
        assumptions_list: List[str] = []
        for item in raw_assump_data:
            if isinstance(item, dict):
                stmt = str(item.get("statement") or item.get("assumption") or "")
            else:
                stmt = str(item)
            if stmt.strip():
                assumptions_list.append(stmt.strip())

        # Parse unknowns (supporting both 'unknowns' and 'unknown_information')
        raw_unknowns_data = data.get("unknowns") or data.get("unknown_information") or []
        unknowns_list: List[str] = []
        for item in raw_unknowns_data:
            if isinstance(item, dict):
                stmt = str(item.get("statement") or "")
            else:
                stmt = str(item)
            if stmt.strip():
                unknowns_list.append(stmt.strip())

        extracted_raw = PageExtractionOutput(
            page_id=page.id,
            url=page.url,
            title=page.title,
            products_services=[str(x) for x in data.get("products_services", []) if x],
            target_customers=[str(x) for x in data.get("target_customers", []) if x],
            customer_problems=[str(x) for x in data.get("customer_problems", []) if x],
            study_destinations=[str(x) for x in data.get("study_destinations", []) if x],
            operational_locations=[str(x) for x in data.get("operational_locations", []) if x],
            business_model=data.get("business_model"),
            revenue_streams=[str(x) for x in data.get("revenue_streams", []) if x],
            positioning=data.get("positioning"),
            facts=raw_facts,
            assumptions=assumptions_list,
            unknowns=unknowns_list,
        )

        # Combine deterministic facets with LLM extracted lists
        merged_destinations = list(page_facets.study_destinations)
        merged_services = list(page_facets.services)
        merged_locations = list(page_facets.operational_locations)

        for d in extracted_raw.study_destinations:
            if d and d not in merged_destinations:
                canonical = self.facet_extractor.country_aliases.get(d.lower()) or d
                if canonical not in merged_destinations:
                    merged_destinations.append(canonical)

        for s in extracted_raw.products_services:
            if s and s not in merged_services:
                merged_services.append(s)

        for loc in extracted_raw.operational_locations:
            if loc and loc not in merged_locations:
                merged_locations.append(loc)

        # 2. Strict evidence validation on candidate facts
        validated_facts: List[FactValidationResult] = []

        for fact in extracted_raw.facts:
            v_res = StrictEvidenceValidator.validate_candidate_fact(
                statement=fact.statement,
                category=fact.category,
                raw_classification=fact.classification,
                evidence_snippet=fact.evidence_snippet,
                page_text=page_text,
                page_id=page.id,
                source_url=page.url,
            )
            validated_facts.append(v_res)

        for assump in extracted_raw.assumptions:
            v_res = StrictEvidenceValidator.validate_candidate_fact(
                statement=assump,
                category="strategy",
                raw_classification="ASSUMPTION",
                evidence_snippet=None,
                page_text=page_text,
                page_id=page.id,
                source_url=page.url,
            )
            validated_facts.append(v_res)

        for unk in extracted_raw.unknowns:
            v_res = StrictEvidenceValidator.validate_candidate_fact(
                statement=unk,
                category="unknown",
                raw_classification="UNKNOWN",
                evidence_snippet=None,
                page_text=None,
                page_id=None,
                source_url=page.url,
            )
            validated_facts.append(v_res)

        return ValidatedPageFacts(
            page_id=page.id,
            url=page.url,
            title=page.title,
            products_services=merged_services,
            target_customers=extracted_raw.target_customers,
            customer_problems=extracted_raw.customer_problems,
            study_destinations=merged_destinations,
            operational_locations=merged_locations,
            business_model=extracted_raw.business_model,
            revenue_streams=extracted_raw.revenue_streams,
            positioning=extracted_raw.positioning,
            validated_facts=validated_facts,
        )
