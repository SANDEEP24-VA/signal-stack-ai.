"""Adaptive Interview Generation Service.

Dynamically synthesizes exactly 10 core business questions tailored to a specific company
based on its industry, verified facts, products, customers, and missing intelligence.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, ValidationError

from app.ai.base import BaseAIProvider
from app.database.models import Company, CompanyProfile

logger = logging.getLogger(__name__)


class CoreQuestionSchema(BaseModel):
    question_order: int = Field(..., ge=1, le=10)
    question_text: str = Field(..., min_length=10)
    business_area: str = Field(..., min_length=2)
    reason_for_asking: str = Field(..., min_length=10)
    information_objective: str = Field(..., min_length=10)
    related_company_profile_field: str = Field(default="business_model")
    expected_information_type: str = Field(default="qualitative_breakdown")
    priority: int = Field(default=1, ge=1, le=10)


class QuestionGenerationOutput(BaseModel):
    questions: List[CoreQuestionSchema] = Field(default_factory=list)


INTERVIEW_GENERATION_SYSTEM_PROMPT = """You are the Senior Executive Intelligence Architect for Signal Stack AI.
Your task is to review a company's verified research profile and synthesize EXACTLY 10 highly tailored,
strategic interview questions for the founder.

CRITICAL INTERVIEW GUIDELINES:
1. Generate EXACTLY 10 questions numbered 1 through 10.
2. Every question must be tailored specifically to the company's named products, industry, and identified customers.
3. Target missing business intelligence (e.g. unstated revenue streams, real competitors, unit economics, strategic risks).
4. NEVER state unverified inferences or assumptions as established facts in the question text.
5. Provide a transparent 'reason_for_asking' explaining how this information empowers executive monitoring.
6. Return valid JSON adhering strictly to the schema.
"""


class InterviewGenerator:
    """Generates company-specific, evidence-grounded founder interview questions."""

    def __init__(self, provider: BaseAIProvider):
        self.provider = provider

    async def generate_core_questions(
        self,
        company: Company,
        profile: Optional[CompanyProfile] = None,
        verified_facts: Optional[List[str]] = None,
    ) -> List[CoreQuestionSchema]:
        """
        Synthesize exactly 10 non-duplicate, profile-tailored core questions.
        If LLM returns fewer or duplicates, dynamically completes using profile-aware fallback templates.
        """
        # Assemble profile intelligence snapshot
        industry = profile.industry if profile and profile.industry else company.industry or "Technology"
        business_model = profile.business_model if profile and profile.business_model else "Not publicly specified"
        products = profile.products_services if profile and profile.products_services else []
        customers = profile.target_customers if profile and profile.target_customers else []
        unknowns = profile.unknown_information if profile and profile.unknown_information else []
        destinations = getattr(profile, "study_destinations", []) if profile else []

        products_str = ", ".join([str(p) for p in products[:6]]) if products else "Not listed"
        customers_str = ", ".join([str(c) for c in customers[:5]]) if customers else "Not specified"
        unknowns_str = "; ".join([str(u) for u in unknowns[:5]]) if unknowns else "Monetization and unit economics"

        user_prompt = (
            f"Generate 10 strategic founder interview questions for '{company.name}'.\n\n"
            f"COMPANY CONTEXT:\n"
            f"- Domain: {company.normalized_domain}\n"
            f"- Industry: {industry}\n"
            f"- Current Stated Model: {business_model}\n"
            f"- Key Products & Offerings: {products_str}\n"
            f"- Stated Customer Segments: {customers_str}\n"
            f"- Public Unknowns / Blindspots: {unknowns_str}\n"
            + (f"- Stated Destinations / Geographies: {', '.join(destinations[:5])}\n" if destinations else "")
            + "\n"
            "Generate questions across these 10 distinct strategic areas:\n"
            "1. Primary Revenue Streams & Commercial Monetization\n"
            "2. Highest-Value Customer Segments & Pricing Power\n"
            "3. Customer Acquisition Channels & Conversion Dynamics\n"
            "4. Core Unmet Pain Points Solved for Customers\n"
            "5. Proprietary Competitive Advantages & Defensibility\n"
            "6. Top Competitors & Alternative Substitutes\n"
            "7. Key Market, Regulatory, or Technology Trends\n"
            "8. Critical Operational & Strategic Risks\n"
            "9. 12-Month Growth & Expansion Priorities\n"
            "10. Strategic Decisions Executive Intelligence Must Support\n\n"
            "Return JSON adhering to this exact schema:\n"
            "{\n"
            '  "questions": [\n'
            '    {\n'
            '      "question_order": 1,\n'
            '      "question_text": "Tailored question string mentioning specific company context?",\n'
            '      "business_area": "revenue_streams",\n'
            '      "reason_for_asking": "Why this is critical for intelligence monitoring",\n'
            '      "information_objective": "Specific business data sought",\n'
            '      "related_company_profile_field": "revenue_streams",\n'
            '      "expected_information_type": "commercial_breakdown",\n'
            '      "priority": 1\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        candidate_questions: List[CoreQuestionSchema] = []

        try:
            completion = await self.provider.generate_completion(
                prompt=user_prompt,
                system_instruction=INTERVIEW_GENERATION_SYSTEM_PROMPT,
                temperature=0.2,
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
            raw_list = data.get("questions", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

            seen_texts: Set[str] = set()
            for item in raw_list:
                if isinstance(item, dict):
                    try:
                        q_obj = CoreQuestionSchema(
                            question_order=len(candidate_questions) + 1,
                            question_text=str(item.get("question_text") or "").strip(),
                            business_area=str(item.get("business_area") or "general").strip(),
                            reason_for_asking=str(item.get("reason_for_asking") or "").strip(),
                            information_objective=str(item.get("information_objective") or "").strip(),
                            related_company_profile_field=str(item.get("related_company_profile_field") or "business_model"),
                            expected_information_type=str(item.get("expected_information_type") or "qualitative"),
                            priority=int(item.get("priority") or len(candidate_questions) + 1),
                        )
                        # Check duplicate text
                        norm_q = re.sub(r"\s+", " ", q_obj.question_text.lower()).strip()
                        if norm_q and norm_q not in seen_texts and len(norm_q) >= 15:
                            seen_texts.add(norm_q)
                            candidate_questions.append(q_obj)
                            if len(candidate_questions) == 10:
                                break
                    except ValidationError:
                        continue
        except Exception as e:
            logger.warning(f"AI question generation notice for {company.name}: {e}")

        # Ensure exactly 10 questions using profile-aware fallback templates if needed
        final_questions = self._complete_ten_questions(
            candidate_questions=candidate_questions,
            company=company,
            industry=industry,
            products=products,
            customers=customers,
        )

        return final_questions

    def _complete_ten_questions(
        self,
        candidate_questions: List[CoreQuestionSchema],
        company: Company,
        industry: str,
        products: List[Any],
        customers: List[Any],
    ) -> List[CoreQuestionSchema]:
        """Fill any missing question slots up to exactly 10 using company-specific fallbacks."""
        existing_areas = {q.business_area.lower() for q in candidate_questions}
        existing_texts = {re.sub(r"\s+", " ", q.question_text.lower()).strip() for q in candidate_questions}

        product_sample = str(products[0]) if products else "your core services"
        customer_sample = str(customers[0]) if customers else "your primary customer demographic"

        # 10 canonical business templates adapted to company specifics
        canonical_templates = [
            (
                "revenue_streams",
                f"How does {company.name} monetize {product_sample}, and what percentage does each revenue model contribute?",
                "Public web presence does not disclose monetization details; understanding primary commercial revenue streams is vital to monitoring financial health.",
                "Identify commercial monetization models (e.g., student fees, institutional commission, subscription, licensing).",
                "revenue_streams",
                "commercial_breakdown",
            ),
            (
                "customer_segments",
                f"Among segments like {customer_sample}, which specific group generates the highest customer lifetime value for {company.name}?",
                "Public pages describe general audiences; executive intelligence requires knowing which exact customer tier yields maximum enterprise value.",
                "Pinpoint highest-margin and highest-retaining customer sub-segments.",
                "target_customers",
                "customer_tier_ranking",
            ),
            (
                "customer_acquisition",
                f"What are the top customer acquisition channels for {company.name}, and how has acquisition cost evolved over the last year?",
                "Acquisition efficiency determines whether marketing and sales strategies are scaling sustainably.",
                "Determine organic vs. paid channel dependencies and growth scalability.",
                "growth_related_information",
                "channel_breakdown",
            ),
            (
                "customer_problems",
                f"Beyond listed offerings like {product_sample}, what is the single most urgent pain point that causes customers to choose {company.name} over alternatives?",
                "Understanding the core value proposition helps identify potential churn triggers and product expansion opportunities.",
                "Articulate critical customer friction points resolved by the platform.",
                "customer_problems",
                "pain_point_hierarchy",
            ),
            (
                "competitors",
                f"Who are the top 2-3 direct competitors or alternative solutions that {company.name} encounters most frequently in sales conversations?",
                "Public sites rarely list competitors; knowing true adversaries is mandatory for monitoring competitive signals.",
                "Map named direct competitors, indirect substitutes, and emerging rivals.",
                "competitors",
                "competitor_list",
            ),
            (
                "competitive_advantages",
                f"What is {company.name}'s primary defensible moat (e.g., proprietary technology, exclusive partnerships, network effects) against well-funded incumbents?",
                "Defensibility determines resistance to market encroachment and margin compression.",
                "Isolate proprietary moats and strategic barriers to entry.",
                "positioning",
                "defensibility_factors",
            ),
            (
                "market_developments",
                f"Which external policy, macroeconomic, or technological shift currently presents the greatest tailwind or headwind for {company.name} in {industry}?",
                "External regulatory and industry shifts drive systemic risks and expansion timing.",
                "Identify high-impact external catalysts to configure radar tracking alerts.",
                "growth_related_information",
                "market_trends",
            ),
            (
                "business_risks",
                f"What is the most significant operational, regulatory, or partner risk that could disrupt {company.name}'s trajectory over the next 18 months?",
                "Early risk identification allows Signal Stack to establish proactive warning tripwires.",
                "Uncover critical dependencies (e.g. visa policies, key partner institutions, single-channel risks).",
                "unknown_information",
                "risk_taxonomy",
            ),
            (
                "growth_objectives",
                f"What are {company.name}'s top 1-2 strategic milestones (e.g., geographic expansion, new vertical launch, ARR targets) for the upcoming year?",
                "Signal Stack benchmarks competitive maneuvers against the company's explicit growth roadmap.",
                "Capture quantifiable near-term corporate goals and expansion vectors.",
                "growth_related_information",
                "strategic_milestones",
            ),
            (
                "intelligence_decisions",
                f"What high-stakes strategic decision are you facing in the next 3-6 months where external intelligence on competitors or partners would be most valuable?",
                "Aligns automated briefing feeds with active executive decisions rather than passive noise.",
                "Define executive intelligence requirements and decision support triggers.",
                "positioning",
                "decision_triggers",
            ),
        ]

        # Re-number and supplement
        results: List[CoreQuestionSchema] = list(candidate_questions)

        for area, text, reason, obj, field, exp_type in canonical_templates:
            if len(results) >= 10:
                break
            norm = re.sub(r"\s+", " ", text.lower()).strip()
            if area not in existing_areas and norm not in existing_texts:
                existing_areas.add(area)
                existing_texts.add(norm)
                results.append(
                    CoreQuestionSchema(
                        question_order=len(results) + 1,
                        question_text=text,
                        business_area=area,
                        reason_for_asking=reason,
                        information_objective=obj,
                        related_company_profile_field=field,
                        expected_information_type=exp_type,
                        priority=len(results) + 1,
                    )
                )

        # Enforce exact length of 10 and clean 1..10 ordering
        final_10 = results[:10]
        for idx, q in enumerate(final_10, 1):
            q.question_order = idx

        return final_10
