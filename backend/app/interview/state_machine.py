"""Interview State Machine and Session Management.

Manages the lifecycle of an adaptive founder interview session:
- Lifecycle: NOT_STARTED -> IN_PROGRESS -> (PAUSED <-> IN_PROGRESS) -> COMPLETED
- Question progression: exactly one active question at a time
- Handles ANSWERED, SKIPPED, and CONFIDENTIAL responses
- Integrates with contextual follow-up generation without altering core 10 indices
- Supports answer review and editing with full audit trail
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.database.models import (
    Company,
    CompanyProfile,
    InformationProvenanceType,
    InterviewAnswer,
    InterviewQuestion,
    InterviewQuestionStatus,
    InterviewQuestionType,
    InterviewSession,
    InterviewSessionStatus,
    utc_now,
)
from app.interview.followup import FollowUpGenerator
from app.interview.generator import InterviewGenerator

logger = logging.getLogger(__name__)


class InterviewStateMachine:
    """Manages interview session lifecycle, question sequencing, and answer states."""

    def __init__(
        self,
        db: Session,
        generator: InterviewGenerator,
        followup_generator: FollowUpGenerator,
    ):
        self.db = db
        self.generator = generator
        self.followup_generator = followup_generator

    async def start_session(
        self,
        company_id: int,
        profile_version: Optional[int] = None,
    ) -> InterviewSession:
        """
        Initialize a new interview session and synthesize exactly 10 core questions
        tailored to the company's verified research profile.
        """
        company = self.db.get(Company, company_id)
        if not company:
            raise ValueError(f"Company {company_id} does not exist.")

        # Get latest company profile
        query = (
            select(CompanyProfile)
            .where(CompanyProfile.company_id == company_id)
            .order_by(desc(CompanyProfile.profile_version))
        )
        if profile_version is not None:
            query = query.where(CompanyProfile.profile_version == profile_version)
        profile = self.db.scalars(query).first()

        start_profile_version = profile.profile_version if profile else 1

        # Create session record
        session = InterviewSession(
            company_id=company_id,
            profile_version_at_start=start_profile_version,
            status=InterviewSessionStatus.IN_PROGRESS.value,
            total_core_questions=10,
            answered_count=0,
            skipped_count=0,
            started_at=utc_now(),
        )
        self.db.add(session)
        self.db.flush()  # obtain session.id

        # Generate exactly 10 core questions
        core_questions = await self.generator.generate_core_questions(
            company=company,
            profile=profile,
        )

        # Persist questions
        for q in core_questions:
            db_question = InterviewQuestion(
                session_id=session.id,
                parent_question_id=None,
                question_type=InterviewQuestionType.CORE.value,
                question_order=q.question_order,
                question_text=q.question_text,
                business_area=q.business_area,
                reason_for_asking=q.reason_for_asking,
                information_objective=q.information_objective,
                related_company_profile_field=q.related_company_profile_field,
                expected_information_type=q.expected_information_type,
                status=InterviewQuestionStatus.PENDING.value,
            )
            self.db.add(db_question)

        self.db.commit()
        self.db.refresh(session)
        logger.info(
            f"Started interview session {session.id} for company '{company.name}' with 10 core questions."
        )
        return session

    def get_session(self, session_id: int) -> Optional[InterviewSession]:
        """Retrieve interview session with eager-loaded questions and answers."""
        stmt = (
            select(InterviewSession)
            .options(
                selectinload(InterviewSession.questions).selectinload(InterviewQuestion.answers),
                selectinload(InterviewSession.questions).selectinload(InterviewQuestion.followups),
                selectinload(InterviewSession.company),
            )
            .where(InterviewSession.id == session_id)
        )
        return self.db.scalars(stmt).first()

    def get_next_question(self, session_id: int) -> Optional[InterviewQuestion]:
        """
        Return the single active or next pending question.
        Precedence:
        1. Currently ASKED question that is not yet resolved.
        2. Unresolved follow-up questions.
        3. Next PENDING core question in sequence (marked ASKED upon retrieval).
        If all 10 core questions (and their follow-ups) are resolved, returns None.
        """
        session = self.get_session(session_id)
        if not session or session.status in (
            InterviewSessionStatus.COMPLETED.value,
            InterviewSessionStatus.PAUSED.value,
        ):
            return None

        # 1. Check if there is an active ASKED question currently awaiting answer
        stmt_active = (
            select(InterviewQuestion)
            .where(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.status == InterviewQuestionStatus.ASKED.value,
            )
            .order_by(
                # Followups first, then core order
                InterviewQuestion.question_type.desc(),
                InterviewQuestion.question_order.asc(),
                InterviewQuestion.id.asc(),
            )
        )
        active_q = self.db.scalars(stmt_active).first()
        if active_q:
            return active_q

        # 2. Check for any PENDING follow-up questions
        stmt_followup = (
            select(InterviewQuestion)
            .where(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.question_type == InterviewQuestionType.FOLLOWUP.value,
                InterviewQuestion.status == InterviewQuestionStatus.PENDING.value,
            )
            .order_by(InterviewQuestion.id.asc())
        )
        next_followup = self.db.scalars(stmt_followup).first()
        if next_followup:
            next_followup.status = InterviewQuestionStatus.ASKED.value
            self.db.commit()
            self.db.refresh(next_followup)
            return next_followup

        # 3. Next PENDING core question
        stmt_core = (
            select(InterviewQuestion)
            .where(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.question_type == InterviewQuestionType.CORE.value,
                InterviewQuestion.status == InterviewQuestionStatus.PENDING.value,
            )
            .order_by(InterviewQuestion.question_order.asc())
        )
        next_core = self.db.scalars(stmt_core).first()
        if next_core:
            next_core.status = InterviewQuestionStatus.ASKED.value
            self.db.commit()
            self.db.refresh(next_core)
            return next_core

        return None

    async def record_answer(
        self,
        session_id: int,
        question_id: int,
        answer_text: Optional[str] = None,
        is_confidential: bool = False,
        is_skip: bool = False,
        allow_followup: bool = True,
    ) -> Tuple[InterviewAnswer, Optional[InterviewQuestion]]:
        """
        Record a founder's answer, skip, or confidential response.
        Optionally evaluates and creates a contextual follow-up question if ambiguity warrants it.
        Returns (InterviewAnswer, Optional[InterviewQuestion for generated follow-up]).
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")

        if session.status != InterviewSessionStatus.IN_PROGRESS.value:
            raise ValueError(f"Cannot record answer: session is in '{session.status}' state.")

        question = self.db.get(InterviewQuestion, question_id)
        if not question or question.session_id != session_id:
            raise ValueError(f"Question {question_id} does not belong to session {session_id}.")

        generated_followup = None

        if is_skip:
            question.status = InterviewQuestionStatus.SKIPPED.value
            if question.question_type == InterviewQuestionType.CORE.value:
                session.skipped_count += 1
            answer = InterviewAnswer(
                question_id=question.id,
                answer_text="[SKIPPED BY FOUNDER]",
                is_confidential=False,
            )
            self.db.add(answer)
        elif is_confidential:
            question.status = InterviewQuestionStatus.CONFIDENTIAL.value
            if question.question_type == InterviewQuestionType.CORE.value:
                session.answered_count += 1
            answer = InterviewAnswer(
                question_id=question.id,
                answer_text=(answer_text or "").strip(),
                is_confidential=True,
            )
            self.db.add(answer)
        else:
            cleaned_text = (answer_text or "").strip()
            if not cleaned_text:
                raise ValueError("Answer text cannot be empty unless question is skipped.")

            question.status = InterviewQuestionStatus.ANSWERED.value
            if question.question_type == InterviewQuestionType.CORE.value:
                session.answered_count += 1
            answer = InterviewAnswer(
                question_id=question.id,
                answer_text=cleaned_text,
                is_confidential=False,
            )
            self.db.add(answer)
            self.db.flush()

            # Contextual Follow-up evaluation:
            # Only trigger follow-up for CORE questions that haven't already spawned a follow-up
            if allow_followup and question.question_type == InterviewQuestionType.CORE.value:
                existing_followups = [
                    q for q in question.followups if q.status != InterviewQuestionStatus.SKIPPED.value
                ]
                if not existing_followups:
                    followup_rec = await self.followup_generator.evaluate_and_generate(
                        company=session.company,
                        question=question,
                        answer=answer,
                    )
                    if followup_rec and followup_rec.should_followup and followup_rec.question_text:
                        followup_q = InterviewQuestion(
                            session_id=session.id,
                            parent_question_id=question.id,
                            question_type=InterviewQuestionType.FOLLOWUP.value,
                            question_order=question.question_order,
                            question_text=followup_rec.question_text,
                            business_area=f"{question.business_area} (Follow-Up)",
                            reason_for_asking=followup_rec.reason_for_asking
                            or f"Clarify commercial details for '{question.business_area}'",
                            information_objective=followup_rec.information_objective
                            or question.information_objective,
                            related_company_profile_field=question.related_company_profile_field,
                            expected_information_type=followup_rec.expected_information_type
                            or "clarification",
                            status=InterviewQuestionStatus.PENDING.value,
                        )
                        self.db.add(followup_q)
                        self.db.flush()
                        generated_followup = followup_q
                        logger.info(
                            f"Generated follow-up question {followup_q.id} for core question {question.id} in session {session_id}."
                        )

        self.db.commit()
        self.db.refresh(answer)
        if generated_followup:
            self.db.refresh(generated_followup)

        return answer, generated_followup

    def edit_answer(
        self,
        session_id: int,
        answer_id: int,
        new_text: str,
        is_confidential: Optional[bool] = None,
    ) -> InterviewAnswer:
        """Edit an existing answer while preserving audit trail."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        answer = self.db.get(InterviewAnswer, answer_id)
        if not answer:
            raise ValueError(f"Answer {answer_id} not found.")

        question = self.db.get(InterviewQuestion, answer.question_id)
        if not question or question.session_id != session_id:
            raise ValueError(f"Answer {answer_id} does not belong to session {session_id}.")

        clean_text = new_text.strip()
        if not clean_text:
            raise ValueError("Updated answer text cannot be empty.")

        answer.answer_text = clean_text
        if is_confidential is not None:
            answer.is_confidential = is_confidential
            question.status = (
                InterviewQuestionStatus.CONFIDENTIAL.value
                if is_confidential
                else InterviewQuestionStatus.ANSWERED.value
            )

        answer.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(answer)
        logger.info(f"Edited answer {answer_id} in session {session_id}.")
        return answer

    def pause_session(self, session_id: int) -> InterviewSession:
        """Pause an in-progress interview session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")
        if session.status != InterviewSessionStatus.IN_PROGRESS.value:
            raise ValueError(f"Cannot pause session in '{session.status}' state.")

        session.status = InterviewSessionStatus.PAUSED.value
        self.db.commit()
        self.db.refresh(session)
        logger.info(f"Paused interview session {session_id}.")
        return session

    def resume_session(self, session_id: int) -> InterviewSession:
        """Resume a paused interview session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")
        if session.status != InterviewSessionStatus.PAUSED.value:
            raise ValueError(f"Cannot resume session in '{session.status}' state.")

        session.status = InterviewSessionStatus.IN_PROGRESS.value
        self.db.commit()
        self.db.refresh(session)
        logger.info(f"Resumed interview session {session_id}.")
        return session

    def get_progress(self, session_id: int) -> Dict[str, Any]:
        """Compute comprehensive session progress metrics."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        core_questions = [
            q for q in session.questions if q.question_type == InterviewQuestionType.CORE.value
        ]
        followup_questions = [
            q for q in session.questions if q.question_type == InterviewQuestionType.FOLLOWUP.value
        ]

        core_answered = sum(
            1 for q in core_questions if q.status in (InterviewQuestionStatus.ANSWERED.value, InterviewQuestionStatus.CONFIDENTIAL.value)
        )
        core_skipped = sum(
            1 for q in core_questions if q.status == InterviewQuestionStatus.SKIPPED.value
        )
        core_pending = sum(
            1 for q in core_questions if q.status in (InterviewQuestionStatus.PENDING.value, InterviewQuestionStatus.ASKED.value)
        )

        followup_answered = sum(
            1 for q in followup_questions if q.status in (InterviewQuestionStatus.ANSWERED.value, InterviewQuestionStatus.CONFIDENTIAL.value)
        )
        followup_pending = sum(
            1 for q in followup_questions if q.status in (InterviewQuestionStatus.PENDING.value, InterviewQuestionStatus.ASKED.value)
        )

        confidential_count = sum(
            1 for q in session.questions for a in q.answers if a.is_confidential
        )

        total_core = 10
        completion_pct = round(((core_answered + core_skipped) / total_core) * 100, 1)

        is_all_core_done = core_pending == 0
        is_all_followup_done = followup_pending == 0
        is_ready_to_complete = is_all_core_done and is_all_followup_done

        return {
            "session_id": session.id,
            "company_id": session.company_id,
            "status": session.status,
            "total_core_questions": total_core,
            "core_answered_count": core_answered,
            "core_skipped_count": core_skipped,
            "core_remaining_count": core_pending,
            "followup_count": len(followup_questions),
            "followup_answered_count": followup_answered,
            "followup_remaining_count": followup_pending,
            "confidential_answers_count": confidential_count,
            "completion_percentage": min(100.0, completion_pct),
            "is_ready_to_complete": is_ready_to_complete,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
        }
