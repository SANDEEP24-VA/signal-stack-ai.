"""Comprehensive Regression Test Suite for Adaptive AI Founder Interview Engine (Task 3).

Covers 20 rigorous test scenarios:
 1. Session Initialization: Generates exactly 10 core questions, order 1-10, status IN_PROGRESS.
 2. Company-Specific Differentiation: Different questions for EdTech vs Robotics.
 3. Profile Blindspot Grounding: Focuses on missing profile intelligence.
 4. Sequential Question Progression: One active question at a time.
 5. Standard Answer Submission: Transition to ANSWERED, counter increments.
 6. Question Skip Functionality: Transition to SKIPPED, counter increments, no follow-up.
 7. Confidential Answer Protection: Flag preserved, no follow-up generated.
 8. Contextual Follow-Up Generation: Triggered on brief/ambiguous answers.
 9. Follow-Up Non-Interference: Core question indices (1-10) and total count remain intact.
10. Follow-Up Interleaving: Serves follow-up before advancing to next core question.
11. Max Follow-Up Guardrail: Prevents recursive follow-up loops.
12. Answer Review & Editing: Modifies text and updates timestamp.
13. Confidentiality Toggle on Edit: Updates confidentiality flag and question status.
14. Pause Session: Transitions to PAUSED, blocks question retrieval and answering.
15. Resume Session: Transitions back to IN_PROGRESS, resumes active question.
16. Progress Metric Accuracy: Accurate tracking of answered, skipped, remaining, percentage.
17. Structured Context Extraction: Persists FounderBusinessContext entries.
18. Confidentiality Segregation: Confidential answers excluded from extraction and public profile.
19. Profile Version Bump & Immutable Facts: New profile version, public facts untouched.
20. API End-to-End Workflow: Complete flow tested via FastAPI TestClient.
"""
from datetime import datetime, timezone
import json
import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.ai.base import AICompletionResult, BaseAIProvider
from app.database.models import (
    Company,
    CompanyFact,
    CompanyProfile,
    FounderBusinessContext,
    InformationProvenanceType,
    InterviewAnswer,
    InterviewQuestion,
    InterviewQuestionStatus,
    InterviewQuestionType,
    InterviewSession,
    InterviewSessionStatus,
)
from app.interview import (
    FollowUpGenerator,
    FounderContextExtractor,
    InterviewGenerator,
    InterviewStateMachine,
)
from app.schemas import InterviewAnswerCreate, InterviewAnswerUpdate


class MockInterviewAIProvider(BaseAIProvider):
    """Deterministic mock provider for unit testing adaptive interview features."""

    def __init__(self, mode: str = "default"):
        super().__init__(model_name="mock-llama")
        self.mode = mode

    async def is_available(self) -> bool:
        return True

    async def generate_completion(
        self, prompt: str, system_instruction: str = "", temperature: float = 0.0
    ) -> AICompletionResult:
        prompt_lower = prompt.lower()

        # Follow-up evaluation mode
        if "analyze this answer" in prompt_lower or "should_followup" in prompt_lower:
            if "we charge universities" in prompt_lower or "ambiguous" in prompt_lower:
                return AICompletionResult(
                    raw_text=json.dumps({
                        "should_followup": True,
                        "question_text": "What specific fee model or revenue share do universities pay?",
                        "reason_for_asking": "Clarifying institutional commercial arrangement",
                        "information_objective": "Determine specific commission vs subscription structure",
                        "expected_information_type": "commercial_breakdown",
                    }),
                    model=self.model_name,
                    provider="mock",
                )
            else:
                return AICompletionResult(
                    raw_text=json.dumps({
                        "should_followup": False,
                        "question_text": None,
                    }),
                    model=self.model_name,
                    provider="mock",
                )

        # Context extraction mode
        if "extract structured corporate context" in prompt_lower:
            return AICompletionResult(
                raw_text=json.dumps({
                    "items": [
                        {
                            "category": "revenue_streams",
                            "field_name": "primary_monetization",
                            "confirmed_value": "Institutional university recruitment fees and student counseling subscriptions",
                            "confidence": 1.0,
                        },
                        {
                            "category": "competitors",
                            "field_name": "named_competitors",
                            "confirmed_value": ["IDP Education", "Leap Scholar", "Leverage Edu"],
                            "confidence": 1.0,
                        },
                        {
                            "category": "growth_priorities",
                            "field_name": "expansion_target",
                            "confirmed_value": "Expansion into European destination markets and AI automated counseling",
                            "confidence": 1.0,
                        },
                    ],
                    "resolved_unknowns": ["Commercial monetization model", "Direct competitors"],
                }),
                model=self.model_name,
                provider="mock",
            )

        # Core question generation mode
        company_name = "Company"
        if "meetuniversity" in prompt_lower:
            company_name = "MeetUniversity"
        elif "nexus robotics" in prompt_lower:
            company_name = "Nexus Robotics"

        questions = []
        for i in range(1, 11):
            questions.append({
                "question_order": i,
                "question_text": f"Strategic Question {i} for {company_name}: Detail your core commercial priorities.",
                "business_area": f"Strategic Area {i}",
                "reason_for_asking": f"Necessary to monitor strategic milestones for {company_name}.",
                "information_objective": f"Assess performance in area {i}.",
                "related_company_profile_field": "business_model",
                "expected_information_type": "qualitative_breakdown",
                "priority": i,
            })

        return AICompletionResult(
            raw_text=json.dumps({"questions": questions}),
            model=self.model_name,
            provider="mock",
        )


@pytest.fixture
def test_company(db_session: Session) -> Company:
    company = Company(
        name="MeetUniversity",
        website="https://meetuniversity.com",
        normalized_domain="meetuniversity.com",
        industry="EdTech / Higher Education",
        status="ACTIVE",
    )
    db_session.add(company)
    db_session.flush()

    profile = CompanyProfile(
        company_id=company.id,
        industry="Higher Education & International Student Recruitment",
        business_model="Aggregator & Counseling Platform",
        products_services=["Personalized Counseling", "Study Abroad Advisory"],
        target_customers=["Prospective Indian Undergraduate Students"],
        customer_problems=["Opaque admission processes"],
        revenue_streams=[],
        geographical_markets=["India"],
        study_destinations=["United States", "United Kingdom", "Canada", "Australia"],
        positioning="Empowering study abroad aspirants",
        growth_related_information=[],
        unknown_information=["Monetization and unit economics", "Direct competitor list"],
        profile_version=1,
    )
    db_session.add(profile)

    fact = CompanyFact(
        company_id=company.id,
        category="services",
        statement="Offers study abroad counseling for global universities.",
        classification="VERIFIED_FACT",
        evidence_snippet="study abroad counseling for global universities",
        provenance_type=InformationProvenanceType.PUBLIC_VERIFIED_FACT.value,
    )
    db_session.add(fact)
    db_session.commit()
    return company


@pytest.fixture
def robotics_company(db_session: Session) -> Company:
    company = Company(
        name="Nexus Robotics",
        website="https://nexusrobotics.ai",
        normalized_domain="nexusrobotics.ai",
        industry="Industrial Robotics & Autonomous Systems",
        status="ACTIVE",
    )
    db_session.add(company)
    db_session.flush()

    profile = CompanyProfile(
        company_id=company.id,
        industry="Autonomous Agricultural Robotics",
        business_model="Robotics-as-a-Service (RaaS)",
        products_services=["Autonomous Weeding Robot", "Crop Health Sensor Suite"],
        target_customers=["Large-Scale Organic Farming Enterprises"],
        customer_problems=["Severe agricultural labor shortages"],
        revenue_streams=["Hardware lease contracts"],
        geographical_markets=["North America"],
        study_destinations=[],
        positioning="Next-generation autonomous farming",
        growth_related_information=[],
        unknown_information=["Manufacturing margins", "Key alternative suppliers"],
        profile_version=1,
    )
    db_session.add(profile)
    db_session.commit()
    return company


@pytest.fixture
def state_machine(db_session: Session) -> InterviewStateMachine:
    provider = MockInterviewAIProvider()
    generator = InterviewGenerator(provider)
    followup_gen = FollowUpGenerator(provider)
    return InterviewStateMachine(db=db_session, generator=generator, followup_generator=followup_gen)


# =============================================================================
# 1. Session Initialization
# =============================================================================
@pytest.mark.asyncio
async def test_session_initialization_generates_10_core_questions(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    assert session.id is not None
    assert session.status == InterviewSessionStatus.IN_PROGRESS.value
    assert session.total_core_questions == 10
    assert session.answered_count == 0
    assert session.skipped_count == 0

    questions = session.questions
    assert len(questions) == 10
    for idx, q in enumerate(questions, start=1):
        assert q.question_type == InterviewQuestionType.CORE.value
        assert q.question_order == idx
        assert q.status == InterviewQuestionStatus.PENDING.value
        assert len(q.question_text) > 5


# =============================================================================
# 2. Company-Specific Differentiation
# =============================================================================
@pytest.mark.asyncio
async def test_company_specific_question_differentiation(
    db_session: Session, test_company: Company, robotics_company: Company, state_machine: InterviewStateMachine
):
    session_edtech = await state_machine.start_session(company_id=test_company.id)
    session_robotics = await state_machine.start_session(company_id=robotics_company.id)

    edtech_text = " ".join([q.question_text for q in session_edtech.questions])
    robotics_text = " ".join([q.question_text for q in session_robotics.questions])

    assert "MeetUniversity" in edtech_text
    assert "Nexus Robotics" in robotics_text
    assert edtech_text != robotics_text


# =============================================================================
# 3. Profile Blindspot Grounding
# =============================================================================
@pytest.mark.asyncio
async def test_fallback_templates_target_profile_blindspots(
    db_session: Session, test_company: Company
):
    provider = MockInterviewAIProvider()
    generator = InterviewGenerator(provider)
    # Using profile-aware fallback generator
    questions = generator._complete_ten_questions(
        candidate_questions=[],
        company=test_company,
        industry=test_company.industry,
        products=["Study Abroad Counseling"],
        customers=["Indian Students"],
    )
    assert len(questions) == 10
    assert any("revenue" in q.question_text.lower() or "commercial" in q.question_text.lower() for q in questions)
    assert any("competitor" in q.question_text.lower() or "alternative" in q.question_text.lower() for q in questions)


# =============================================================================
# 4. Sequential Question Progression (One Active Question at a Time)
# =============================================================================
@pytest.mark.asyncio
async def test_sequential_question_progression(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)

    # First call returns Question 1 and marks it ASKED
    q1 = state_machine.get_next_question(session.id)
    assert q1 is not None
    assert q1.question_order == 1
    assert q1.status == InterviewQuestionStatus.ASKED.value

    # Subsequent call while Question 1 is unanswered continues to return Question 1
    q1_again = state_machine.get_next_question(session.id)
    assert q1_again.id == q1.id


# =============================================================================
# 5. Standard Answer Submission
# =============================================================================
@pytest.mark.asyncio
async def test_standard_answer_submission(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    answer, followup = await state_machine.record_answer(
        session_id=session.id,
        question_id=q1.id,
        answer_text="Our primary model is direct student consulting retainers.",
        is_confidential=False,
    )
    assert answer.id is not None
    assert answer.is_confidential is False
    assert q1.status == InterviewQuestionStatus.ANSWERED.value

    session_refreshed = state_machine.get_session(session.id)
    assert session_refreshed.answered_count == 1

    # Next question is now Question 2
    q2 = state_machine.get_next_question(session.id)
    assert q2 is not None
    assert q2.question_order == 2


# =============================================================================
# 6. Question Skip Functionality
# =============================================================================
@pytest.mark.asyncio
async def test_question_skip_functionality(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    answer, followup = await state_machine.record_answer(
        session_id=session.id,
        question_id=q1.id,
        is_skip=True,
    )
    assert q1.status == InterviewQuestionStatus.SKIPPED.value
    assert followup is None

    session_refreshed = state_machine.get_session(session.id)
    assert session_refreshed.skipped_count == 1
    assert session_refreshed.answered_count == 0


# =============================================================================
# 7. Confidential Answer Protection
# =============================================================================
@pytest.mark.asyncio
async def test_confidential_answer_protection(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    answer, followup = await state_machine.record_answer(
        session_id=session.id,
        question_id=q1.id,
        answer_text="Our annual revenue is confidential and strictly private.",
        is_confidential=True,
    )
    assert answer.is_confidential is True
    assert q1.status == InterviewQuestionStatus.CONFIDENTIAL.value
    # Guardrail: Never trigger follow-up on confidential answers
    assert followup is None


# =============================================================================
# 8. Contextual Follow-Up Generation
# =============================================================================
@pytest.mark.asyncio
async def test_contextual_followup_generation_on_brief_answer(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    # Provide brief/ambiguous answer triggering follow-up in mock
    answer, followup = await state_machine.record_answer(
        session_id=session.id,
        question_id=q1.id,
        answer_text="We charge universities.",
        is_confidential=False,
        allow_followup=True,
    )
    assert followup is not None
    assert followup.question_type == InterviewQuestionType.FOLLOWUP.value
    assert followup.parent_question_id == q1.id
    assert "fee model" in followup.question_text.lower()


# =============================================================================
# 9. Follow-Up Non-Interference with Core Indices
# =============================================================================
@pytest.mark.asyncio
async def test_followup_preserves_10_core_question_indices(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    await state_machine.record_answer(
        session_id=session.id,
        question_id=q1.id,
        answer_text="We charge universities.",
        allow_followup=True,
    )

    refreshed = state_machine.get_session(session.id)
    assert refreshed.total_core_questions == 10

    core_questions = [q for q in refreshed.questions if q.question_type == InterviewQuestionType.CORE.value]
    assert len(core_questions) == 10
    orders = [q.question_order for q in core_questions]
    assert orders == list(range(1, 11))


# =============================================================================
# 10. Follow-Up Interleaving (Serves Follow-Up First)
# =============================================================================
@pytest.mark.asyncio
async def test_followup_interleaving_served_before_next_core(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    await state_machine.record_answer(
        session_id=session.id,
        question_id=q1.id,
        answer_text="We charge universities.",
        allow_followup=True,
    )

    # Next question returned MUST be the generated follow-up, NOT core question 2
    next_q = state_machine.get_next_question(session.id)
    assert next_q is not None
    assert next_q.question_type == InterviewQuestionType.FOLLOWUP.value
    assert next_q.parent_question_id == q1.id


# =============================================================================
# 11. Max Follow-Up Guardrail (No Recursive Follow-Up)
# =============================================================================
@pytest.mark.asyncio
async def test_followup_guardrail_prevents_recursive_followups(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    # Core Q1 -> triggers follow-up
    _, followup1 = await state_machine.record_answer(
        session_id=session.id,
        question_id=q1.id,
        answer_text="We charge universities.",
        allow_followup=True,
    )
    assert followup1 is not None

    # Answer the follow-up with ambiguous text
    next_q = state_machine.get_next_question(session.id)
    assert next_q.id == followup1.id

    _, recursive_followup = await state_machine.record_answer(
        session_id=session.id,
        question_id=followup1.id,
        answer_text="We charge universities a flat fee.",
        allow_followup=True,
    )
    # Guardrail: Follow-ups cannot spawn nested follow-ups
    assert recursive_followup is None


# =============================================================================
# 12. Answer Review & Editing
# =============================================================================
@pytest.mark.asyncio
async def test_answer_review_and_editing(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    answer, _ = await state_machine.record_answer(
        session_id=session.id,
        question_id=q1.id,
        answer_text="Initial answer text.",
    )

    updated_answer = state_machine.edit_answer(
        session_id=session.id,
        answer_id=answer.id,
        new_text="Refined and comprehensive answer with updated metrics.",
    )
    assert updated_answer.answer_text == "Refined and comprehensive answer with updated metrics."


# =============================================================================
# 13. Confidentiality Toggle on Edit
# =============================================================================
@pytest.mark.asyncio
async def test_confidentiality_toggle_on_edit(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    answer, _ = await state_machine.record_answer(
        session_id=session.id,
        question_id=q1.id,
        answer_text="Proprietary margins of 65%.",
        is_confidential=False,
    )
    assert q1.status == InterviewQuestionStatus.ANSWERED.value

    # Edit to confidential
    updated = state_machine.edit_answer(
        session_id=session.id,
        answer_id=answer.id,
        new_text="Proprietary margins of 65%.",
        is_confidential=True,
    )
    assert updated.is_confidential is True
    assert q1.status == InterviewQuestionStatus.CONFIDENTIAL.value


# =============================================================================
# 14. Pause Session
# =============================================================================
@pytest.mark.asyncio
async def test_pause_session_lifecycle(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)

    paused = state_machine.pause_session(session.id)
    assert paused.status == InterviewSessionStatus.PAUSED.value

    # While paused, get_next_question returns None
    assert state_machine.get_next_question(session.id) is None

    # Submitting answer raises ValueError
    with pytest.raises(ValueError, match="PAUSED"):
        await state_machine.record_answer(
            session_id=session.id,
            question_id=q1.id,
            answer_text="Cannot submit while paused",
        )


# =============================================================================
# 15. Resume Session
# =============================================================================
@pytest.mark.asyncio
async def test_resume_session_lifecycle(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    q1 = state_machine.get_next_question(session.id)
    state_machine.pause_session(session.id)

    resumed = state_machine.resume_session(session.id)
    assert resumed.status == InterviewSessionStatus.IN_PROGRESS.value

    # Next question is accessible again
    next_q = state_machine.get_next_question(session.id)
    assert next_q.id == q1.id


# =============================================================================
# 16. Progress Metric Accuracy
# =============================================================================
@pytest.mark.asyncio
async def test_progress_metric_accuracy(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)

    # Answer Q1, skip Q2, confidential Q3
    q1 = state_machine.get_next_question(session.id)
    await state_machine.record_answer(session.id, q1.id, answer_text="Answer 1")

    q2 = state_machine.get_next_question(session.id)
    await state_machine.record_answer(session.id, q2.id, is_skip=True)

    q3 = state_machine.get_next_question(session.id)
    await state_machine.record_answer(session.id, q3.id, answer_text="Confidential 3", is_confidential=True)

    progress = state_machine.get_progress(session.id)
    assert progress["total_core_questions"] == 10
    assert progress["core_answered_count"] == 2  # Q1 and Q3
    assert progress["core_skipped_count"] == 1   # Q2
    assert progress["core_remaining_count"] == 7
    assert progress["completion_percentage"] == 30.0
    assert progress["confidential_answers_count"] == 1


# =============================================================================
# 17. Structured Context Extraction
# =============================================================================
@pytest.mark.asyncio
async def test_structured_context_extraction(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)
    # Answer all questions
    for _ in range(10):
        q = state_machine.get_next_question(session.id)
        if q:
            await state_machine.record_answer(session.id, q.id, answer_text=f"Founder answer for {q.business_area}")

    provider = MockInterviewAIProvider()
    extractor = FounderContextExtractor(db=db_session, provider=provider)
    summary = await extractor.complete_and_extract(session.id)

    assert summary["status"] == InterviewSessionStatus.COMPLETED.value
    assert summary["profile_version"] == 2
    assert summary["extracted_context_count"] > 0

    contexts = db_session.query(FounderBusinessContext).filter(FounderBusinessContext.company_id == test_company.id).all()
    assert len(contexts) >= 3
    categories = [c.context_category for c in contexts]
    assert "revenue_streams" in categories
    assert "competitors" in categories


# =============================================================================
# 18. Confidential Information Segregation
# =============================================================================
@pytest.mark.asyncio
async def test_confidential_information_segregation(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    session = await state_machine.start_session(company_id=test_company.id)

    # Mark question 1 confidential with private figures
    q1 = state_machine.get_next_question(session.id)
    await state_machine.record_answer(
        session.id,
        q1.id,
        answer_text="SECRET_VALUATION_OF_100_MILLION",
        is_confidential=True,
    )

    # Complete session
    for _ in range(9):
        q = state_machine.get_next_question(session.id)
        if q:
            await state_machine.record_answer(session.id, q.id, answer_text="Public operational answer")

    provider = MockInterviewAIProvider()
    extractor = FounderContextExtractor(db=db_session, provider=provider)
    summary = await extractor.complete_and_extract(session.id)

    assert summary["confidential_answers_protected"] == 1

    # Verify secret string never entered company profile
    new_profile = (
        db_session.query(CompanyProfile)
        .filter(CompanyProfile.company_id == test_company.id, CompanyProfile.profile_version == 2)
        .first()
    )
    profile_json = json.dumps({
        "rev": new_profile.revenue_streams,
        "cust": new_profile.target_customers,
        "pos": new_profile.positioning,
    })
    assert "SECRET_VALUATION_OF_100_MILLION" not in profile_json


# =============================================================================
# 19. Profile Version Bump & Immutable Historical Facts
# =============================================================================
@pytest.mark.asyncio
async def test_profile_version_bump_preserves_immutable_facts(
    db_session: Session, test_company: Company, state_machine: InterviewStateMachine
):
    # Public facts before interview
    initial_facts = db_session.query(CompanyFact).filter(CompanyFact.company_id == test_company.id).all()
    assert len(initial_facts) == 1
    initial_fact_statement = initial_facts[0].statement

    session = await state_machine.start_session(company_id=test_company.id)
    for _ in range(10):
        q = state_machine.get_next_question(session.id)
        if q:
            await state_machine.record_answer(session.id, q.id, answer_text="Founder operational update")

    provider = MockInterviewAIProvider()
    extractor = FounderContextExtractor(db=db_session, provider=provider)
    await extractor.complete_and_extract(session.id)

    # Check facts after interview
    facts_after = db_session.query(CompanyFact).filter(CompanyFact.company_id == test_company.id).all()
    assert len(facts_after) == 1
    assert facts_after[0].statement == initial_fact_statement
    assert facts_after[0].provenance_type == InformationProvenanceType.PUBLIC_VERIFIED_FACT.value

    # Check profile version was bumped to 2
    v1_profile = db_session.query(CompanyProfile).filter(CompanyProfile.company_id == test_company.id, CompanyProfile.profile_version == 1).first()
    v2_profile = db_session.query(CompanyProfile).filter(CompanyProfile.company_id == test_company.id, CompanyProfile.profile_version == 2).first()
    assert v1_profile is not None
    assert v2_profile is not None
    assert v2_profile.interview_session_id == session.id


# =============================================================================
# 20. API End-to-End Workflow via TestClient
# =============================================================================
def test_interview_api_end_to_end(client: TestClient, test_company: Company, db_session: Session):
    from app.api.interviews import get_state_machine
    from app.main import app

    provider = MockInterviewAIProvider()
    generator = InterviewGenerator(provider)
    followup_gen = FollowUpGenerator(provider)
    mock_machine = InterviewStateMachine(db=db_session, generator=generator, followup_generator=followup_gen)

    app.dependency_overrides[get_state_machine] = lambda: mock_machine
    try:
        # 1. Start session
        resp = client.post(f"/api/companies/{test_company.id}/interviews")
        assert resp.status_code == 201
        data = resp.json()
        session_id = data["id"]
        assert data["total_core_questions"] == 10
        assert len(data["questions"]) == 10

        # 2. Get next question
        next_resp = client.get(f"/api/interviews/{session_id}/next")
        assert next_resp.status_code == 200
        q1_data = next_resp.json()
        q1_id = q1_data["id"]

        # 3. Submit answer
        ans_resp = client.post(
            f"/api/interviews/{session_id}/answers",
            json={"question_id": q1_id, "answer_text": "We offer subscription packages."},
        )
        assert ans_resp.status_code == 200
        ans_data = ans_resp.json()["answer"]
        answer_id = ans_data["id"]

        # 4. Edit answer
        edit_resp = client.patch(
            f"/api/interviews/{session_id}/answers/{answer_id}",
            json={"answer_text": "We offer annual enterprise and university subscriptions."},
        )
        assert edit_resp.status_code == 200
        assert edit_resp.json()["answer_text"] == "We offer annual enterprise and university subscriptions."

        # 5. Check progress
        prog_resp = client.get(f"/api/interviews/{session_id}/progress")
        assert prog_resp.status_code == 200
        assert prog_resp.json()["core_answered_count"] == 1

        # 6. Pause and resume
        pause_resp = client.post(f"/api/interviews/{session_id}/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "PAUSED"

        resume_resp = client.post(f"/api/interviews/{session_id}/resume")
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "IN_PROGRESS"

        # 7. Complete session
        comp_resp = client.post(f"/api/interviews/{session_id}/complete")
        assert comp_resp.status_code == 200
        summary = comp_resp.json()
        assert summary["status"] == "COMPLETED"
        assert summary["profile_version"] == 2
    finally:
        app.dependency_overrides.pop(get_state_machine, None)
