"""Contextual Follow-Up Generation Engine.

Evaluates founder answers against the expected information objective and generates
a targeted follow-up question ONLY when clarification materially enriches corporate intelligence.
Follow-up questions are strictly additive and do not alter the 10 core question indices.
"""
import json
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.ai.base import BaseAIProvider
from app.database.models import Company, InterviewAnswer, InterviewQuestion

logger = logging.getLogger(__name__)


class FollowUpRecommendation(BaseModel):
    should_followup: bool = False
    question_text: Optional[str] = None
    reason_for_asking: Optional[str] = None
    information_objective: Optional[str] = None
    expected_information_type: Optional[str] = None


FOLLOWUP_SYSTEM_PROMPT = """You are an expert executive intelligence interviewer.
Your task is to review a founder's answer to a business question and decide if a targeted follow-up is necessary.

DECISION CRITERIA:
1. Return 'should_followup': false if the founder's answer is already thorough, detailed, or self-explanatory.
2. Return 'should_followup': true ONLY if the answer is brief, ambiguous, or names a high-value commercial mechanism (e.g. 'university partnerships', 'referrals', 'subscriptions') without clarifying the commercial structure or unit economics.
3. Keep the follow-up sharp, polite, and directly focused on resolving the specific ambiguity.
4. Return valid JSON adhering strictly to the schema.
"""


class FollowUpGenerator:
    """Evaluates answer completeness and synthesizes context-aware follow-up inquiries."""

    def __init__(self, provider: BaseAIProvider):
        self.provider = provider

    async def evaluate_and_generate(
        self,
        company: Company,
        question: InterviewQuestion,
        answer: InterviewAnswer,
        previous_qa_context: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[FollowUpRecommendation]:
        """Determine if an answer warrants a follow-up inquiry and generate it if needed."""
        # 1. Guardrails: No follow-up on confidential, skipped, or empty answers
        if answer.is_confidential or not answer.answer_text or not answer.answer_text.strip():
            return None

        clean_answer = answer.answer_text.strip()

        # If answer is extremely short (< 4 words), it almost certainly needs clarification
        # If answer is comprehensive (> 80 words with metrics), likely does not need follow-up
        word_count = len(clean_answer.split())

        user_prompt = (
            f"Analyze this answer from the founder of '{company.name}':\n\n"
            f"QUESTION ASKED: {question.question_text}\n"
            f"BUSINESS AREA: {question.business_area}\n"
            f"INFORMATION OBJECTIVE: {question.information_objective}\n"
            f"FOUNDER ANSWER: \"{clean_answer}\"\n\n"
            "Decide if a single follow-up question is necessary to clarify the commercial or operational specifics.\n\n"
            "Return JSON adhering to this schema:\n"
            "{\n"
            '  "should_followup": true,\n'
            '  "question_text": "Clarifying follow-up question?",\n'
            '  "reason_for_asking": "Why this specific detail matters for executive monitoring",\n'
            '  "information_objective": "Specific clarification sought",\n'
            '  "expected_information_type": "commercial_clarification"\n'
            "}"
        )

        try:
            completion = await self.provider.generate_completion(
                prompt=user_prompt,
                system_instruction=FOLLOWUP_SYSTEM_PROMPT,
                temperature=0.1,
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
            if isinstance(data, dict) and data.get("should_followup") and data.get("question_text"):
                return FollowUpRecommendation(
                    should_followup=True,
                    question_text=str(data["question_text"]).strip(),
                    reason_for_asking=str(data.get("reason_for_asking") or "Clarifying underlying commercial arrangement"),
                    information_objective=str(data.get("information_objective") or question.information_objective),
                    expected_information_type=str(data.get("expected_information_type") or "clarification"),
                )
        except Exception as e:
            logger.warning(f"Follow-up generation notice for question {question.id}: {e}")

        # Deterministic heuristic fallback for short ambiguous answers
        if word_count < 10 and any(k in clean_answer.lower() for k in ["partnership", "commission", "b2b", "subscription", "referral", "agency"]):
            return FollowUpRecommendation(
                should_followup=True,
                question_text=f"Could you elaborate briefly on how the {clean_answer} model is structured commercially (e.g., fixed fee vs. success commission)?",
                reason_for_asking="Clarifying the commercial revenue mechanism ensures accurate tracking of financial and partner signals.",
                information_objective=f"Commercial structure of {clean_answer}",
                expected_information_type="commercial_breakdown",
            )

        return None
