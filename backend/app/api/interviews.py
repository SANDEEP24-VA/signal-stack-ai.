"""Adaptive AI Founder Interview API Endpoints."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ai.manager import get_active_ai_provider
from app.core.errors import BadRequestError, NotFoundError
from app.database import (
    Company,
    FounderBusinessContext,
    InterviewAnswer,
    InterviewQuestion,
    InterviewSession,
    get_db,
)
from app.interview import (
    FollowUpGenerator,
    FounderContextExtractor,
    InterviewGenerator,
    InterviewStateMachine,
)
from app.schemas import (
    FounderBusinessContextResponse,
    InterviewAnswerCreate,
    InterviewAnswerResponse,
    InterviewAnswerSubmitResponse,
    InterviewAnswerUpdate,
    InterviewCompletionSummaryResponse,
    InterviewProgressResponse,
    InterviewQuestionResponse,
    InterviewSessionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Adaptive Founder Interview"])


async def get_state_machine(db: Session = Depends(get_db)) -> InterviewStateMachine:
    """Helper to instantiate InterviewStateMachine with active AI provider."""
    provider = await get_active_ai_provider()
    generator = InterviewGenerator(provider)
    followup_gen = FollowUpGenerator(provider)
    return InterviewStateMachine(db=db, generator=generator, followup_generator=followup_gen)


# =============================================================================
# COMPANY INTERVIEW SESSIONS
# =============================================================================


@router.post(
    "/companies/{company_id}/interviews",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize adaptive interview session and synthesize 10 core questions",
)
async def create_interview_session(
    company_id: int,
    db: Session = Depends(get_db),
    state_machine: InterviewStateMachine = Depends(get_state_machine),
) -> InterviewSessionResponse:
    company = db.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    try:
        session = await state_machine.start_session(company_id=company_id)
        return InterviewSessionResponse.model_validate(session)
    except Exception as exc:
        logger.error(f"Failed to initialize interview for company {company_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Interview initialization failed: {str(exc)}",
        )


@router.get(
    "/companies/{company_id}/interviews",
    response_model=List[InterviewSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="List all interview sessions for a company",
)
def list_company_interviews(
    company_id: int,
    db: Session = Depends(get_db),
) -> List[InterviewSessionResponse]:
    company = db.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    sessions = (
        db.scalars(
            select(InterviewSession)
            .where(InterviewSession.company_id == company_id)
            .order_by(desc(InterviewSession.created_at))
        ).all()
    )
    return [InterviewSessionResponse.model_validate(s) for s in sessions]


@router.get(
    "/companies/{company_id}/founder-context",
    response_model=List[FounderBusinessContextResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve founder-confirmed business context records",
)
def get_company_founder_context(
    company_id: int,
    db: Session = Depends(get_db),
) -> List[FounderBusinessContextResponse]:
    company = db.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    contexts = (
        db.scalars(
            select(FounderBusinessContext)
            .where(FounderBusinessContext.company_id == company_id)
            .order_by(desc(FounderBusinessContext.created_at))
        ).all()
    )
    return [FounderBusinessContextResponse.model_validate(c) for c in contexts]


# =============================================================================
# INDIVIDUAL INTERVIEW SESSION CONTROL
# =============================================================================


@router.get(
    "/interviews/{session_id}",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get interview session details and questions",
)
def get_interview_session(
    session_id: int,
    state_machine: InterviewStateMachine = Depends(get_state_machine),
) -> InterviewSessionResponse:
    session = state_machine.get_session(session_id)
    if not session:
        raise NotFoundError(f"Interview session {session_id} not found.")
    return InterviewSessionResponse.model_validate(session)


@router.get(
    "/interviews/{session_id}/progress",
    response_model=InterviewProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get real-time interview progress metrics",
)
def get_interview_progress(
    session_id: int,
    state_machine: InterviewStateMachine = Depends(get_state_machine),
) -> InterviewProgressResponse:
    try:
        progress = state_machine.get_progress(session_id)
        return InterviewProgressResponse(**progress)
    except ValueError as exc:
        raise NotFoundError(str(exc))


@router.get(
    "/interviews/{session_id}/next",
    response_model=Optional[InterviewQuestionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get single active or next pending question (core or follow-up)",
)
def get_next_question(
    session_id: int,
    response: Response,
    state_machine: InterviewStateMachine = Depends(get_state_machine),
) -> Optional[InterviewQuestionResponse]:
    question = state_machine.get_next_question(session_id)
    if not question:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    return InterviewQuestionResponse.model_validate(question)


@router.post(
    "/interviews/{session_id}/answers",
    response_model=InterviewAnswerSubmitResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit answer, skip, or confidential flag for a question",
)
async def submit_answer(
    session_id: int,
    payload: InterviewAnswerCreate,
    state_machine: InterviewStateMachine = Depends(get_state_machine),
) -> InterviewAnswerSubmitResponse:
    try:
        answer, followup = await state_machine.record_answer(
            session_id=session_id,
            question_id=payload.question_id,
            answer_text=payload.answer_text,
            is_confidential=payload.is_confidential,
            is_skip=payload.is_skip,
            allow_followup=payload.allow_followup,
        )
        return InterviewAnswerSubmitResponse(
            answer=InterviewAnswerResponse.model_validate(answer),
            followup_question=InterviewQuestionResponse.model_validate(followup) if followup else None,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc))
    except Exception as exc:
        logger.error(f"Error submitting answer in session {session_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit answer: {str(exc)}",
        )


@router.patch(
    "/interviews/{session_id}/answers/{answer_id}",
    response_model=InterviewAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit a previously submitted answer",
)
def edit_answer(
    session_id: int,
    answer_id: int,
    payload: InterviewAnswerUpdate,
    state_machine: InterviewStateMachine = Depends(get_state_machine),
) -> InterviewAnswerResponse:
    try:
        updated_answer = state_machine.edit_answer(
            session_id=session_id,
            answer_id=answer_id,
            new_text=payload.answer_text,
            is_confidential=payload.is_confidential,
        )
        return InterviewAnswerResponse.model_validate(updated_answer)
    except ValueError as exc:
        raise BadRequestError(str(exc))


@router.post(
    "/interviews/{session_id}/pause",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause active interview session",
)
def pause_interview(
    session_id: int,
    state_machine: InterviewStateMachine = Depends(get_state_machine),
) -> InterviewSessionResponse:
    try:
        session = state_machine.pause_session(session_id)
        return InterviewSessionResponse.model_validate(session)
    except ValueError as exc:
        raise BadRequestError(str(exc))


@router.post(
    "/interviews/{session_id}/resume",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume paused interview session",
)
def resume_interview(
    session_id: int,
    state_machine: InterviewStateMachine = Depends(get_state_machine),
) -> InterviewSessionResponse:
    try:
        session = state_machine.resume_session(session_id)
        return InterviewSessionResponse.model_validate(session)
    except ValueError as exc:
        raise BadRequestError(str(exc))


@router.post(
    "/interviews/{session_id}/complete",
    response_model=InterviewCompletionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Finalize interview session, extract structured context, and update profile",
)
async def complete_interview(
    session_id: int,
    db: Session = Depends(get_db),
) -> InterviewCompletionSummaryResponse:
    provider = await get_active_ai_provider()
    extractor = FounderContextExtractor(db=db, provider=provider)
    try:
        summary = await extractor.complete_and_extract(session_id=session_id)
        return InterviewCompletionSummaryResponse(**summary)
    except ValueError as exc:
        raise NotFoundError(str(exc))
    except Exception as exc:
        logger.error(f"Error completing interview session {session_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete interview: {str(exc)}",
        )
