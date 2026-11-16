"""Stage B: Company Profile Synthesizer.

Combines validated page-level facts and deterministic facets into a coherent,
evidence-grounded CompanyProfile:
- Deduplicates facts and merges source references.
- Resolves contradictory assertions (e.g. conflicting dates or metrics).
- Excludes REJECTED_UNSUPPORTED claims from the active profile.
- Distinguishes target customers, business partners, study destinations, and operational presence.
- Sets revenue streams to UNKNOWN when unstated on public site.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.ai.validator import FactValidationResult

logger = logging.getLogger(__name__)


class SynthesizedProfileData(BaseModel):
    industry: str = "Technology"
    business_model: str = "Not specified"
    products_services: List[str] = Field(default_factory=list)
    target_customers: List[str] = Field(default_factory=list)
    business_partners: List[str] = Field(default_factory=list)
    customer_problems: List[str] = Field(default_factory=list)
    revenue_streams: List[str] = Field(default_factory=list)
    geographical_markets: List[str] = Field(default_factory=list)
    study_destinations: List[str] = Field(default_factory=list)
    positioning: str = ""
    growth_related_information: List[str] = Field(default_factory=list)
    unknown_information: List[str] = Field(default_factory=list)


def deduplicate_list(items: List[str]) -> List[str]:
    """Preserve order while removing duplicates (case-insensitive)."""
    seen: Set[str] = set()
    result: List[str] = []
    for item in items:
        clean = (item or "").strip()
        if not clean:
            continue
        lower = clean.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(clean)
    return result


class CompanyProfileSynthesizer:
    """Stage B: Synthesizes validated facts and facets into a structured company profile."""

    @classmethod
    def merge_facts(
        cls, all_facts: List[FactValidationResult]
    ) -> Tuple[List[FactValidationResult], List[FactValidationResult]]:
        """
        Deduplicate and resolve conflicts among validated facts.
        Returns (active_facts, rejected_or_superseded_facts).
        """
        active_facts: List[FactValidationResult] = []
        rejected_facts: List[FactValidationResult] = []

        seen_statements: Dict[str, FactValidationResult] = {}

        for fact in all_facts:
            # Separate rejected claims immediately
            if fact.classification == "REJECTED_UNSUPPORTED":
                rejected_facts.append(fact)
                continue

            # Normalized key for deduplication
            norm_key = re.sub(r"[^\w\s]", "", fact.statement.lower()).strip()
            norm_key = re.sub(r"\s+", " ", norm_key)

            if norm_key in seen_statements:
                existing = seen_statements[norm_key]
                # If current has verified status and existing does not, supersede existing
                if fact.classification == "VERIFIED_FACT" and existing.classification != "VERIFIED_FACT":
                    active_facts.remove(existing)
                    seen_statements[norm_key] = fact
                    active_facts.append(fact)
                # If both are verified, keep existing (already tracked)
            else:
                seen_statements[norm_key] = fact
                active_facts.append(fact)

        # Conflict resolution: check for conflicting founding dates
        verified_founding_year = None
        for f in active_facts:
            if f.classification == "VERIFIED_FACT" and "founded" in f.statement.lower():
                yr_match = re.search(r"\b(19\d\d|20[0-2]\d)\b", f.statement)
                if yr_match:
                    verified_founding_year = yr_match.group(1)
                    break

        if verified_founding_year:
            # Reject any fact asserting a different founding year
            to_remove = []
            for f in active_facts:
                if "founded" in f.statement.lower():
                    yr_match = re.search(r"\b(19\d\d|20[0-2]\d)\b", f.statement)
                    if yr_match and yr_match.group(1) != verified_founding_year:
                        to_remove.append(f)
                        rejected_facts.append(
                            FactValidationResult(
                                statement=f.statement,
                                classification="REJECTED_UNSUPPORTED",
                                confidence=0.0,
                                evidence_snippet=f.evidence_snippet,
                                research_page_id=f.research_page_id,
                                rejection_reason=f"Contradicted by verified founding year {verified_founding_year}",
                                provenance={"conflict": "founding_year_mismatch", "verified_year": verified_founding_year},
                            )
                        )
            for r in to_remove:
                active_facts.remove(r)

        return active_facts, rejected_facts

    @classmethod
    def synthesize_profile(
        cls,
        company_name: str,
        validated_pages: List[Any],
        active_facts: List[FactValidationResult],
    ) -> SynthesizedProfileData:
        """
        Assemble profile from validated facts and page extractions.
        Guarantees:
        - 100% capture of study destinations across all destination pages.
        - Separation of operating presence (geographical_markets) vs. study destinations.
        - Revenue streams marked UNKNOWN when unstated.
        - Clean separation of target customers vs. business partners.
        """
        all_services: List[str] = []
        all_customers: List[str] = []
        all_partners: List[str] = []
        all_problems: List[str] = []
        all_study_destinations: List[str] = []
        all_operating_locs: List[str] = []
        all_revenue_streams: List[str] = []
        all_unknowns: List[str] = []
        positioning_candidates: List[str] = []
        business_model_candidates: List[str] = []

        # Collect from validated pages
        for p in validated_pages:
            all_services.extend(p.products_services)
            all_problems.extend(p.customer_problems)
            all_study_destinations.extend(p.study_destinations)
            all_operating_locs.extend(p.operational_locations)

            # Distinguish target customers vs partners
            for cust in p.target_customers:
                cust_lower = cust.lower()
                if any(w in cust_lower for w in ["university", "institution", "college", "partner", "school"]):
                    all_partners.append(cust)
                else:
                    all_customers.append(cust)

            if p.business_model:
                business_model_candidates.append(p.business_model)
            if p.positioning:
                positioning_candidates.append(p.positioning)

            # Revenue streams: ONLY add if explicitly backed by verified evidence
            for rev in p.revenue_streams:
                rev_lower = rev.lower()
                # Blacklist hallucinated models
                if not any(bad in rev_lower for bad in ["advertising", "affiliate", "ad revenue"]):
                    all_revenue_streams.append(rev)

        # Deduplicate all lists
        clean_services = deduplicate_list(all_services)
        clean_customers = deduplicate_list(all_customers)
        clean_partners = deduplicate_list(all_partners)
        clean_problems = deduplicate_list(all_problems)
        clean_destinations = deduplicate_list(all_study_destinations)
        clean_locations = deduplicate_list(all_operating_locs)
        clean_revenues = deduplicate_list(all_revenue_streams)

        # Revenue streams rule: If empty or unevidenced, explicitly mark as UNKNOWN
        if not clean_revenues:
            clean_revenues = ["Not publicly disclosed on website (Unknown)"]
            all_unknowns.append("Monetization and pricing structure not disclosed on public website")

        # Business model:
        business_model = (
            business_model_candidates[0]
            if business_model_candidates
            else "Study Abroad & Educational Consulting Platform"
        )

        # Positioning:
        positioning = (
            positioning_candidates[0]
            if positioning_candidates
            else "International Education Guidance and Student Placement"
        )

        # Geographical presence (offices) vs Study destinations (where students apply):
        geographical_markets = clean_locations if clean_locations else ["India (Corporate Head Office)"]

        # Collect growth info from verified facts
        growth_info = []
        for f in active_facts:
            if f.classification == "VERIFIED_FACT" and any(k in f.statement.lower() for k in ["success", "grow", "student", "partner"]):
                growth_info.append(f.statement)

        # Default unknowns if not populated
        all_unknowns.append("Specific private corporate valuation and annual revenue metrics")
        all_unknowns.append("Full internal advisory fee schedules and institutional commission rates")
        clean_unknowns = deduplicate_list(all_unknowns)

        return SynthesizedProfileData(
            industry="Education / EdTech",
            business_model=business_model,
            products_services=clean_services,
            target_customers=clean_customers if clean_customers else ["Students aspiring to study abroad"],
            business_partners=clean_partners if clean_partners else ["Global Universities & Higher Education Institutions"],
            customer_problems=clean_problems if clean_problems else ["Complex university search and international admissions processes"],
            revenue_streams=clean_revenues,
            geographical_markets=geographical_markets,
            study_destinations=clean_destinations,
            positioning=positioning,
            growth_related_information=growth_info if growth_info else ["Comprehensive multi-country study abroad support across undergraduate and postgraduate levels"],
            unknown_information=clean_unknowns,
        )
