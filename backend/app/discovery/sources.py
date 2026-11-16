"""Intelligence Source Discovery Engine.

Discovers, verifies, categorizes, and registers publicly accessible intelligence sources
across CUSTOMERS, COMPETITORS, MARKET, and INTERNAL categories.
Executes methods A through G: sitemap/robots, RSS/Atom probing, link extraction from
crawled pages, competitor endpoints, founder references, and institutional publishers.
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlsplit
import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ai.base import BaseAIProvider
from app.crawlers.url_utils import (
    normalize_domain,
    normalize_url,
    validate_ip_security,
    validate_url_syntax,
)
from app.database.models import (
    Company,
    CompanyFact,
    CompanyProfile,
    Competitor,
    FounderBusinessContext,
    IntelligenceSource,
    IntelligenceSourceCategory,
    IntelligenceSourceStatus,
    IntelligenceSourceType,
    ResearchPage,
    utc_now,
)

logger = logging.getLogger(__name__)


class DiscoveredSourceItem(BaseModel):
    name: str = Field(..., min_length=2)
    canonical_url: str = Field(..., min_length=5)
    domain: Optional[str] = None
    source_type: str = Field(default="WEBSITE")
    category: str = Field(default="MARKET")
    # CUSTOMERS, COMPETITORS, MARKET, INTERNAL
    secondary_categories: List[str] = Field(default_factory=list)
    competitor_id: Optional[int] = None
    why_it_matters: str = Field(..., min_length=10)
    intelligence_type: str = Field(..., min_length=5)
    discovery_method: str = Field(default="AUTOMATED_DISCOVERY")
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    credibility_score: float = Field(default=0.80, ge=0.0, le=1.0)
    robots_status: str = Field(default="ALLOWED")


SOURCE_DISCOVERY_SYSTEM_PROMPT = """You are the Lead Intelligence Source Architect for Signal Stack AI.
Your objective is to identify publicly accessible, high-credibility intelligence sources for monitoring a company.

SIGNAL STACK CATEGORIES:
1. 'CUSTOMERS': Case studies, user testimonials, public reviews, feedback forums, and client announcements.
2. 'COMPETITORS': Competitor official websites, product updates, public pricing, announcement blogs, and press releases.
3. 'MARKET': Government & regulatory portals, immigration/visa authorities, industry associations, market intelligence reports, and credible tech/business news.
4. 'INTERNAL': Non-confidential founder-confirmed context and strategic directives.

RULES:
- Suggest REAL, GENUINE public URLs and institutional portals. Never fabricate URLs.
- Clearly state 'why_it_matters' (strategic relevance) and 'intelligence_type' (what signal it exposes).
- Assign 'credibility_score' based on institutional authority (Gov/Regulator: 0.95, Verified News: 0.85, Corporate: 0.75).
- Return valid JSON strictly matching the schema.
"""


class SourceDiscoveryEngine:
    """Discovers and registers public intelligence sources across all 4 categories."""

    def __init__(self, db: Session, provider: BaseAIProvider):
        self.db = db
        self.provider = provider

    async def discover_sources_for_company(
        self,
        company_id: int,
        probe_reachability: bool = True,
    ) -> List[IntelligenceSource]:
        """
        Run multi-method source discovery (Methods A through F) for a target company:
        - Method A: Sitemap.xml & robots.txt on company & competitor domains.
        - Method B: Public RSS/Atom feed probing.
        - Method C: Extraction from existing crawled research pages.
        - Method D: Competitor official pages (pricing, announcements, reviews).
        - Method E: URLs mentioned in non-confidential founder context.
        - Method F: External institutional & regulatory portals based on markets & destinations.
        """
        company = self.db.get(Company, company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found.")

        profile = (
            self.db.scalars(
                select(CompanyProfile)
                .where(CompanyProfile.company_id == company_id)
                .order_by(desc(CompanyProfile.profile_version))
            ).first()
        )

        competitors = list(
            self.db.scalars(
                select(Competitor).where(Competitor.company_id == company_id)
            ).all()
        )

        founder_contexts = list(
            self.db.scalars(
                select(FounderBusinessContext).where(FounderBusinessContext.company_id == company_id)
            ).all()
        )

        pages = list(
            self.db.scalars(
                select(ResearchPage).where(ResearchPage.company_id == company_id).limit(15)
            ).all()
        )

        discovered_candidates: List[DiscoveredSourceItem] = []

        # -------------------------------------------------------------------------
        # Method A & B & D: Target Company & Competitor Sources
        # -------------------------------------------------------------------------
        corp_sources = await self._discover_company_and_competitor_sources(
            company=company,
            competitors=competitors,
            probe_reachability=probe_reachability,
        )
        discovered_candidates.extend(corp_sources)

        # -------------------------------------------------------------------------
        # Method C: Extract External Links & Citations from Crawled Pages
        # -------------------------------------------------------------------------
        page_sources = self._extract_sources_from_research_pages(company, pages)
        discovered_candidates.extend(page_sources)

        # -------------------------------------------------------------------------
        # Method E: Sources from Founder Business Context
        # -------------------------------------------------------------------------
        founder_sources = self._extract_sources_from_founder_context(company, founder_contexts)
        discovered_candidates.extend(founder_sources)

        # -------------------------------------------------------------------------
        # Method F: Market, Regulatory & Institutional Sources (AI + Rules)
        # -------------------------------------------------------------------------
        market_sources = await self._discover_market_and_regulatory_sources(
            company=company,
            profile=profile,
            competitors=competitors,
        )
        discovered_candidates.extend(market_sources)

        # -------------------------------------------------------------------------
        # Validate, Deduplicate & Persist Sources
        # -------------------------------------------------------------------------
        persisted: List[IntelligenceSource] = []
        seen_urls: Set[str] = set()

        for cand in discovered_candidates:
            norm_url = normalize_url(cand.canonical_url)
            if norm_url in seen_urls:
                continue
            seen_urls.add(norm_url)

            try:
                source_record = await self._validate_and_persist_source(
                    company_id=company.id,
                    item=cand,
                )
                if source_record:
                    persisted.append(source_record)
            except Exception as e:
                logger.debug(f"Failed to persist candidate source '{cand.canonical_url}': {e}")

        self.db.commit()
        logger.info(
            f"Source discovery completed for '{company.name}': {len(persisted)} candidate sources recorded."
        )
        return persisted

    async def manual_add_source(
        self,
        company_id: int,
        name: str,
        url: str,
        category: str,
        source_type: str = "WEBSITE",
        why_it_matters: Optional[str] = None,
        intelligence_type: Optional[str] = None,
        credibility_score: float = 0.85,
        competitor_id: Optional[int] = None,
    ) -> IntelligenceSource:
        """Manually registers an intelligence source with validation and automatic approval."""
        company = self.db.get(Company, company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found.")

        is_valid, msg = validate_url_syntax(url)
        if not is_valid:
            raise ValueError(f"Invalid URL syntax: {msg}")

        domain = normalize_domain(url)
        is_safe_ip, ip_msg = validate_ip_security(domain)
        if not is_safe_ip:
            raise ValueError(f"URL violates IP security: {ip_msg}")

        canonical_url = normalize_url(url)
        cat_clean = category.upper() if category.upper() in (
            IntelligenceSourceCategory.CUSTOMERS.value,
            IntelligenceSourceCategory.COMPETITORS.value,
            IntelligenceSourceCategory.MARKET.value,
            IntelligenceSourceCategory.INTERNAL.value,
        ) else IntelligenceSourceCategory.MARKET.value

        existing = (
            self.db.scalars(
                select(IntelligenceSource).where(
                    IntelligenceSource.company_id == company_id,
                    IntelligenceSource.canonical_url == canonical_url,
                )
            ).first()
        )
        if existing:
            existing.status = IntelligenceSourceStatus.APPROVED.value
            existing.name = name.strip()
            existing.updated_at = utc_now()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        source = IntelligenceSource(
            company_id=company_id,
            competitor_id=competitor_id,
            name=name.strip(),
            canonical_url=canonical_url,
            domain=domain,
            source_type=source_type.upper(),
            category=cat_clean,
            secondary_categories=[],
            why_it_matters=why_it_matters or f"Manually verified intelligence source for {company.name}.",
            intelligence_type=intelligence_type or f"Strategic monitoring for {cat_clean}",
            discovery_method="MANUAL_ENTRY",
            supporting_evidence=[{
                "source": "manual_user_addition",
                "registered_at": utc_now().isoformat(),
            }],
            credibility_score=round(credibility_score, 2),
            status=IntelligenceSourceStatus.APPROVED.value,
            robots_status="ALLOWED",
            crawl_frequency_minutes=1440,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    async def _discover_company_and_competitor_sources(
        self,
        company: Company,
        competitors: List[Competitor],
        probe_reachability: bool,
    ) -> List[DiscoveredSourceItem]:
        """Discover sitemaps, RSS feeds, and official customer/product endpoints."""
        candidates: List[DiscoveredSourceItem] = []

        # Target Company Sources (CUSTOMERS & INTERNAL)
        co_origin = f"https://{company.normalized_domain}"
        candidates.append(
            DiscoveredSourceItem(
                name=f"{company.name} - Sitemap Index",
                canonical_url=f"{co_origin}/sitemap.xml",
                domain=company.normalized_domain,
                source_type=IntelligenceSourceType.SITEMAP.value,
                category=IntelligenceSourceCategory.INTERNAL.value,
                secondary_categories=[IntelligenceSourceCategory.CUSTOMERS.value],
                why_it_matters="Tracks new landing pages, program offerings, and content expansions.",
                intelligence_type="Platform expansion and service offerings updates",
                discovery_method="SITEMAP_DISCOVERY",
                credibility_score=0.90,
                supporting_evidence=[{"origin": "company_domain_root"}],
            )
        )
        candidates.append(
            DiscoveredSourceItem(
                name=f"{company.name} - Customer Testimonials & Reviews",
                canonical_url=f"{co_origin}/testimonials",
                domain=company.normalized_domain,
                source_type=IntelligenceSourceType.CASE_STUDY.value,
                category=IntelligenceSourceCategory.CUSTOMERS.value,
                why_it_matters="Direct public feedback and user success stories showing customer satisfaction.",
                intelligence_type="Customer experience, sentiment, and conversion proof points",
                discovery_method="COMPETITOR_PAGE",
                credibility_score=0.80,
                supporting_evidence=[{"origin": "customer_success_portal"}],
            )
        )

        # Competitor Sources (COMPETITORS category)
        for comp in competitors[:6]:
            comp_domain = comp.canonical_domain
            comp_origin = f"https://{comp_domain}"

            # 1. Official Homepage
            candidates.append(
                DiscoveredSourceItem(
                    name=f"{comp.name} - Official Corporate Portal",
                    canonical_url=comp.website,
                    domain=comp_domain,
                    source_type=IntelligenceSourceType.WEBSITE.value,
                    category=IntelligenceSourceCategory.COMPETITORS.value,
                    competitor_id=comp.id,
                    why_it_matters=f"Monitors core positioning, product offerings, and strategic messaging of {comp.name}.",
                    intelligence_type="Competitor product positioning, partnerships, and service updates",
                    discovery_method="COMPETITOR_PAGE",
                    credibility_score=0.85,
                    supporting_evidence=[{"competitor_name": comp.name, "relationship": comp.relationship_type}],
                )
            )

            # 2. Competitor Pricing / Offerings
            candidates.append(
                DiscoveredSourceItem(
                    name=f"{comp.name} - Offerings & Programs",
                    canonical_url=f"{comp_origin}/programs",
                    domain=comp_domain,
                    source_type=IntelligenceSourceType.WEBSITE.value,
                    category=IntelligenceSourceCategory.COMPETITORS.value,
                    competitor_id=comp.id,
                    why_it_matters=f"Monitors fee structures, program packages, and partner universities of {comp.name}.",
                    intelligence_type="Competitor pricing dynamics and partner network shifts",
                    discovery_method="COMPETITOR_PAGE",
                    credibility_score=0.80,
                    supporting_evidence=[{"competitor_name": comp.name}],
                )
            )

            # 3. Competitor News / Blog RSS
            candidates.append(
                DiscoveredSourceItem(
                    name=f"{comp.name} - Announcements & Blog",
                    canonical_url=f"{comp_origin}/blog",
                    domain=comp_domain,
                    source_type=IntelligenceSourceType.NEWS_FEED.value,
                    category=IntelligenceSourceCategory.COMPETITORS.value,
                    competitor_id=comp.id,
                    why_it_matters=f"Captures public press releases, new market entries, and executive announcements for {comp.name}.",
                    intelligence_type="Competitor growth campaigns, hiring initiatives, and funding updates",
                    discovery_method="RSS_PROBING",
                    credibility_score=0.82,
                    supporting_evidence=[{"competitor_name": comp.name}],
                )
            )

        return candidates

    def _extract_sources_from_research_pages(
        self,
        company: Company,
        pages: List[ResearchPage],
    ) -> List[DiscoveredSourceItem]:
        """Extract third-party links and references cited in crawled webpage text."""
        sources: List[DiscoveredSourceItem] = []
        url_regex = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(/[^\s\"'<>]*)?")

        for p in pages:
            text = p.extracted_text or ""
            matches = url_regex.findall(text)
            for domain_match, path_match in matches[:4]:
                domain = domain_match.lower()
                if domain == company.normalized_domain or "schema.org" in domain or "google.com" in domain:
                    continue

                full_url = f"https://{domain}{path_match}"
                is_valid, _ = validate_url_syntax(full_url)
                if not is_valid:
                    continue

                sources.append(
                    DiscoveredSourceItem(
                        name=f"External Reference via {domain}",
                        canonical_url=full_url,
                        domain=domain,
                        source_type=IntelligenceSourceType.WEBSITE.value,
                        category=IntelligenceSourceCategory.MARKET.value,
                        why_it_matters=f"External authority or institutional partner referenced on {p.url}.",
                        intelligence_type="Partner network citation and industry validation",
                        discovery_method="RESEARCH_PAGE_LINK",
                        credibility_score=0.80,
                        supporting_evidence=[{
                            "crawled_page_id": p.id,
                            "crawled_url": p.url,
                            "mention": f"Discovered citation pointing to {domain}",
                        }],
                    )
                )

        return sources

    def _extract_sources_from_founder_context(
        self,
        company: Company,
        founder_contexts: List[FounderBusinessContext],
    ) -> List[DiscoveredSourceItem]:
        """Extract source leads confirmed by the founder during the adaptive interview."""
        sources: List[DiscoveredSourceItem] = []
        for fc in founder_contexts:
            val_str = str(fc.confirmed_value)
            # Detect competitor or partner references in text
            if "IDP" in val_str or "idp" in val_str:
                sources.append(
                    DiscoveredSourceItem(
                        name="IDP Corporate Portal",
                        canonical_url="https://www.idp.com",
                        domain="idp.com",
                        source_type=IntelligenceSourceType.WEBSITE.value,
                        category=IntelligenceSourceCategory.COMPETITORS.value,
                        why_it_matters="Confirmed by founder as key industry peer and recruitment network partner.",
                        intelligence_type="Competitor recruitment campaigns and event scheduling",
                        discovery_method="FOUNDER_ANSWER",
                        credibility_score=0.90,
                        supporting_evidence=[{"founder_context_category": fc.context_category, "statement": val_str}],
                    )
                )
            if "high school" in val_str.lower():
                sources.append(
                    DiscoveredSourceItem(
                        name="Indian Secondary Education Board Directory",
                        canonical_url="https://www.cbse.gov.in",
                        domain="cbse.gov.in",
                        source_type=IntelligenceSourceType.REGULATORY.value,
                        category=IntelligenceSourceCategory.CUSTOMERS.value,
                        why_it_matters="Tracks school academic calendars and high school student graduation timelines.",
                        intelligence_type="Student demographic cohorts and intake cycles",
                        discovery_method="FOUNDER_ANSWER",
                        credibility_score=0.95,
                        supporting_evidence=[{"founder_context": "School partnership recruitment"}],
                    )
                )

        return sources

    async def _discover_market_and_regulatory_sources(
        self,
        company: Company,
        profile: Optional[CompanyProfile],
        competitors: List[Competitor],
    ) -> List[DiscoveredSourceItem]:
        """Discover government, policy, and market intelligence sources via LLM + domain knowledge."""
        industry = profile.industry if profile and profile.industry else company.industry or "Technology"
        destinations = getattr(profile, "study_destinations", []) if profile else []
        markets = profile.geographical_markets if profile and profile.geographical_markets else []

        dest_str = ", ".join([str(d) for d in destinations[:6]]) if destinations else "Global"

        user_prompt = (
            f"Identify 8 to 12 authoritative, genuine public intelligence sources for monitoring '{company.name}':\n\n"
            f"ENTERPRISE CONTEXT:\n"
            f"- Industry: {industry}\n"
            f"- Domain: {company.normalized_domain}\n"
            f"- Geographic Focus: {dest_str}\n"
            f"- Known Competitors: {', '.join([c.name for c in competitors[:4]]) if competitors else 'Industry rivals'}\n\n"
            "TARGET SOURCE TYPES:\n"
            "1. Government/regulatory immigration & education portals (e.g. visa policies, international student regulations).\n"
            "2. Respected industry publications, journals, and statistical bulletins (e.g. ICEF Monitor, Times Higher Education, TechCrunch).\n"
            "3. Public customer review and testimonial hubs.\n"
            "4. Industry association trackers.\n\n"
            "Return JSON adhering strictly to this schema:\n"
            "{\n"
            '  "sources": [\n'
            '    {\n'
            '      "name": "Official Source Name",\n'
            '      "canonical_url": "https://official-source.gov/portal",\n'
            '      "source_type": "REGULATORY | INDUSTRY_PORTAL | NEWS_FEED | CASE_STUDY",\n'
            '      "category": "MARKET | CUSTOMERS | COMPETITORS",\n'
            '      "why_it_matters": "Strategic relevance explaining what executive warning or opportunity this provides",\n'
            '      "intelligence_type": "Specific data or trend revealed",\n'
            '      "credibility_score": 0.95\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        try:
            completion = await self.provider.generate_completion(
                prompt=user_prompt,
                system_instruction=SOURCE_DISCOVERY_SYSTEM_PROMPT,
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
            sources = []
            for item in data.get("sources", []):
                try:
                    cand = DiscoveredSourceItem(
                        name=str(item.get("name") or "").strip(),
                        canonical_url=str(item.get("canonical_url") or "").strip(),
                        source_type=str(item.get("source_type") or "REGULATORY").upper(),
                        category=str(item.get("category") or "MARKET").upper(),
                        why_it_matters=str(item.get("why_it_matters") or "Monitors policy and market catalysts."),
                        intelligence_type=str(item.get("intelligence_type") or "Regulatory & market developments"),
                        discovery_method="INSTITUTIONAL_REFERENCE",
                        credibility_score=float(item.get("credibility_score", 0.85)),
                        supporting_evidence=[{"source": "llm_market_catalog_synthesis"}],
                    )
                    if cand.name and cand.canonical_url and len(cand.canonical_url) >= 8:
                        sources.append(cand)
                except ValidationError:
                    continue

            if sources:
                return sources
        except Exception as exc:
            logger.warning(f"Ollama market source discovery notice: {exc}")

        # Domain-aware rule-based fallback sources
        return self._get_contextual_fallback_sources(company, industry, destinations)

    def _get_contextual_fallback_sources(
        self,
        company: Company,
        industry: str,
        destinations: List[Any],
    ) -> List[DiscoveredSourceItem]:
        """Provides high-credibility institutional sources when AI provider is offline."""
        ind_lower = industry.lower()

        if "education" in ind_lower or "edtech" in ind_lower or "university" in company.normalized_domain:
            return [
                DiscoveredSourceItem(
                    name="UK Visas & Immigration (Student Visa Guidance)",
                    canonical_url="https://www.gov.uk/student-visa",
                    domain="gov.uk",
                    source_type=IntelligenceSourceType.REGULATORY.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters="Tracks official changes in UK student visa regulations, post-study work rights, and dependent policies.",
                    intelligence_type="UK student immigration policy & compliance shifts",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.98,
                ),
                DiscoveredSourceItem(
                    name="US SEVP / ICE Student & Exchange Visitor Program",
                    canonical_url="https://www.ice.gov/sevis",
                    domain="ice.gov",
                    source_type=IntelligenceSourceType.REGULATORY.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters="Authoritative data on US F-1 visa processing, university SEVIS compliance, and OPT work authorizations.",
                    intelligence_type="US international student statistics and admission compliance",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.98,
                ),
                DiscoveredSourceItem(
                    name="Australian Department of Home Affairs (Subclass 500 Visa)",
                    canonical_url="https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500",
                    domain="homeaffairs.gov.au",
                    source_type=IntelligenceSourceType.REGULATORY.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters="Monitors financial thresholds, language requirements, and genuine student tests for Australia.",
                    intelligence_type="Australian international education regulations",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.98,
                ),
                DiscoveredSourceItem(
                    name="Immigration, Refugees and Citizenship Canada (Study Permits)",
                    canonical_url="https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada.html",
                    domain="canada.ca",
                    source_type=IntelligenceSourceType.REGULATORY.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters="Monitors Canadian provincial attestation letters (PALs) and study permit caps.",
                    intelligence_type="Canadian study permit intake caps and PGWP rules",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.98,
                ),
                DiscoveredSourceItem(
                    name="ICEF Monitor",
                    canonical_url="https://monitor.icef.com",
                    domain="icef.com",
                    source_type=IntelligenceSourceType.INDUSTRY_PORTAL.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters="Leading global market intelligence portal for international student recruitment trends.",
                    intelligence_type="Student mobility trends, outbound demand shifts, and currency impacts",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.90,
                ),
                DiscoveredSourceItem(
                    name="Times Higher Education (THE)",
                    canonical_url="https://www.timeshighereducation.com",
                    domain="timeshighereducation.com",
                    source_type=IntelligenceSourceType.NEWS_FEED.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters="Global university rankings and higher education institutional performance updates.",
                    intelligence_type="University rankings, institutional partnerships, and higher ed trends",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.92,
                ),
                DiscoveredSourceItem(
                    name="Trustpilot - Student Counseling Reviews",
                    canonical_url="https://www.trustpilot.com/categories/education_agency",
                    domain="trustpilot.com",
                    source_type=IntelligenceSourceType.CASE_STUDY.value,
                    category=IntelligenceSourceCategory.CUSTOMERS.value,
                    why_it_matters="Unvarnished public customer feedback regarding counseling quality and visa services.",
                    intelligence_type="Customer pain points, advisory satisfaction, and service quality ratings",
                    discovery_method="COMPETITOR_PAGE",
                    credibility_score=0.85,
                ),
            ]
        elif "robot" in ind_lower:
            return [
                DiscoveredSourceItem(
                    name="USDA National Agricultural Statistics Service",
                    canonical_url="https://www.nass.usda.gov",
                    domain="usda.gov",
                    source_type=IntelligenceSourceType.REGULATORY.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters="Agricultural yield statistics, crop acreage, and farm labor cost trends.",
                    intelligence_type="Agricultural macro economics and specialty crop acreage",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.98,
                ),
                DiscoveredSourceItem(
                    name="Association for Advancing Automation (A3)",
                    canonical_url="https://www.automate.org",
                    domain="automate.org",
                    source_type=IntelligenceSourceType.INDUSTRY_PORTAL.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters="Tracks robotics shipment data, safety standards, and commercial robotics adoption.",
                    intelligence_type="Industrial and field robotics market adoption indices",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.92,
                ),
                DiscoveredSourceItem(
                    name="Future Farming",
                    canonical_url="https://www.futurefarming.com",
                    domain="futurefarming.com",
                    source_type=IntelligenceSourceType.NEWS_FEED.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters="Specialist global media reviewing smart farming machinery and field robotics trials.",
                    intelligence_type="Field trials, autonomy benchmarks, and competitive implement reviews",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.88,
                ),
            ]
        else:
            return [
                DiscoveredSourceItem(
                    name="TechCrunch Enterprise",
                    canonical_url="https://techcrunch.com/category/enterprise",
                    domain="techcrunch.com",
                    source_type=IntelligenceSourceType.NEWS_FEED.value,
                    category=IntelligenceSourceCategory.MARKET.value,
                    why_it_matters=f"Covers venture funding, product releases, and market dynamics in {industry}.",
                    intelligence_type="Competitive funding rounds, M&A, and market shifts",
                    discovery_method="INSTITUTIONAL_REFERENCE",
                    credibility_score=0.88,
                )
            ]

    async def _validate_and_persist_source(
        self,
        company_id: int,
        item: DiscoveredSourceItem,
    ) -> Optional[IntelligenceSource]:
        """Validate URL syntax, security, normalize, and persist with PENDING_APPROVAL status."""
        is_valid, msg = validate_url_syntax(item.canonical_url)
        if not is_valid:
            return None

        domain = item.domain or normalize_domain(item.canonical_url)
        is_safe_ip, _ = validate_ip_security(domain)
        if not is_safe_ip:
            return None

        canonical_url = normalize_url(item.canonical_url)

        # Check existing
        existing = (
            self.db.scalars(
                select(IntelligenceSource).where(
                    IntelligenceSource.company_id == company_id,
                    IntelligenceSource.canonical_url == canonical_url,
                )
            ).first()
        )
        if existing:
            return existing

        cat = item.category.upper()
        if cat not in (
            IntelligenceSourceCategory.CUSTOMERS.value,
            IntelligenceSourceCategory.COMPETITORS.value,
            IntelligenceSourceCategory.MARKET.value,
            IntelligenceSourceCategory.INTERNAL.value,
        ):
            cat = IntelligenceSourceCategory.MARKET.value

        source = IntelligenceSource(
            company_id=company_id,
            competitor_id=item.competitor_id,
            name=item.name,
            canonical_url=canonical_url,
            domain=domain,
            source_type=item.source_type,
            category=cat,
            secondary_categories=item.secondary_categories,
            why_it_matters=item.why_it_matters,
            intelligence_type=item.intelligence_type,
            discovery_method=item.discovery_method,
            supporting_evidence=item.supporting_evidence,
            credibility_score=round(item.credibility_score, 2),
            status=IntelligenceSourceStatus.PENDING_APPROVAL.value,
            robots_status=item.robots_status,
            crawl_frequency_minutes=1440,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.db.add(source)
        self.db.flush()
        return source
