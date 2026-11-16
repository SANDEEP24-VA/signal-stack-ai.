import React, { useState, useEffect, useCallback } from 'react';
import {
  BrainCircuit,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Edit3,
  HelpCircle,
  Info,
  MessageSquare,
  Pause,
  Play,
  RotateCcw,
  Send,
  Shield,
  Sparkles,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import {
  completeInterview,
  editAnswer,
  fetchCompanies,
  fetchCompanyFounderContext,
  fetchCompanyInterviews,
  fetchInterviewProgress,
  fetchNextQuestion,
  pauseInterview,
  resumeInterview,
  startInterview,
  submitAnswer,
} from '../../services/api';
import {
  Company,
  FounderBusinessContext,
  InterviewCompletionSummary,
  InterviewProgress,
  InterviewQuestion,
  InterviewSession,
} from '../../types';

export const FounderInterviewView: React.FC = () => {
  // Company & Session State
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null);
  const [pastSessions, setPastSessions] = useState<InterviewSession[]>([]);
  const [progress, setProgress] = useState<InterviewProgress | null>(null);
  const [founderContexts, setFounderContexts] = useState<FounderBusinessContext[]>([]);
  const [completionSummary, setCompletionSummary] = useState<InterviewCompletionSummary | null>(null);

  // Active Question State
  const [currentQuestion, setCurrentQuestion] = useState<InterviewQuestion | null>(null);
  const [answerText, setAnswerText] = useState<string>('');
  const [isConfidential, setIsConfidential] = useState<boolean>(false);
  const [showRationale, setShowRationale] = useState<boolean>(true);
  const [historyOpen, setHistoryOpen] = useState<boolean>(false);

  // Editing State
  const [editingAnswerId, setEditingAnswerId] = useState<number | null>(null);
  const [editText, setEditText] = useState<string>('');
  const [editConfidential, setEditConfidential] = useState<boolean>(false);

  // Status & Feedback
  const [loading, setLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [followupNotice, setFollowupNotice] = useState<string | null>(null);

  // 1. Initial Load: Fetch companies
  useEffect(() => {
    async function loadCompanies() {
      try {
        setLoading(true);
        const data = await fetchCompanies();
        setCompanies(data);
        if (data.length > 0 && !selectedCompanyId) {
          setSelectedCompanyId(data[0].id);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load companies.');
      } finally {
        setLoading(false);
      }
    }
    loadCompanies();
  }, []);

  // 2. Load sessions and context when company changes
  const loadCompanyData = useCallback(async (companyId: number) => {
    try {
      setLoading(true);
      setError(null);
      setFollowupNotice(null);
      setCompletionSummary(null);

      const [sessions, contexts] = await Promise.all([
        fetchCompanyInterviews(companyId),
        fetchCompanyFounderContext(companyId),
      ]);

      setPastSessions(sessions);
      setFounderContexts(contexts);

      // Select in-progress or paused session if available, else latest session
      const active = sessions.find(
        (s) => s.status === 'IN_PROGRESS' || s.status === 'PAUSED'
      ) || sessions[0] || null;

      setActiveSession(active);

      if (active) {
        await refreshSessionState(active.id);
      } else {
        setCurrentQuestion(null);
        setProgress(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load company interview history.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCompanyId) {
      loadCompanyData(selectedCompanyId);
    }
  }, [selectedCompanyId, loadCompanyData]);

  // Refresh active question and progress metrics
  const refreshSessionState = async (sessionId: number) => {
    try {
      const [prog, nextQ] = await Promise.all([
        fetchInterviewProgress(sessionId),
        fetchNextQuestion(sessionId),
      ]);
      setProgress(prog);
      setCurrentQuestion(nextQ);
      setAnswerText('');
      setIsConfidential(false);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch current question.');
    }
  };

  // Start new interview session
  const handleStartSession = async () => {
    if (!selectedCompanyId) return;
    try {
      setSubmitting(true);
      setError(null);
      setFollowupNotice(null);
      setCompletionSummary(null);

      const newSession = await startInterview(selectedCompanyId);
      setActiveSession(newSession);
      await refreshSessionState(newSession.id);
      const updatedSessions = await fetchCompanyInterviews(selectedCompanyId);
      setPastSessions(updatedSessions);
    } catch (err: any) {
      setError(err.message || 'Failed to initialize interview session.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Answer
  const handleSubmitAnswer = async () => {
    if (!activeSession || !currentQuestion) return;
    if (!answerText.trim()) {
      setError('Please provide an answer before submitting, or use "Skip Question".');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      setFollowupNotice(null);

      const result = await submitAnswer(activeSession.id, {
        question_id: currentQuestion.id,
        answer_text: answerText.trim(),
        is_confidential: isConfidential,
        is_skip: false,
        allow_followup: true,
      });

      if (result.followup_question) {
        setFollowupNotice(
          `Clarification Inquiry: The AI requested specific commercial details regarding your answer to "${currentQuestion.business_area}".`
        );
      }

      await refreshSessionState(activeSession.id);
      // Reload sessions for history
      const sessions = await fetchCompanyInterviews(selectedCompanyId!);
      setPastSessions(sessions);
    } catch (err: any) {
      setError(err.message || 'Failed to submit answer.');
    } finally {
      setSubmitting(false);
    }
  };

  // Skip Question
  const handleSkipQuestion = async () => {
    if (!activeSession || !currentQuestion) return;

    try {
      setSubmitting(true);
      setError(null);
      setFollowupNotice(null);

      await submitAnswer(activeSession.id, {
        question_id: currentQuestion.id,
        is_skip: true,
      });

      await refreshSessionState(activeSession.id);
      const sessions = await fetchCompanyInterviews(selectedCompanyId!);
      setPastSessions(sessions);
    } catch (err: any) {
      setError(err.message || 'Failed to skip question.');
    } finally {
      setSubmitting(false);
    }
  };

  // Pause / Resume Session
  const handleTogglePause = async () => {
    if (!activeSession) return;
    try {
      setSubmitting(true);
      setError(null);

      if (activeSession.status === 'IN_PROGRESS') {
        const paused = await pauseInterview(activeSession.id);
        setActiveSession(paused);
      } else if (activeSession.status === 'PAUSED') {
        const resumed = await resumeInterview(activeSession.id);
        setActiveSession(resumed);
      }
      await refreshSessionState(activeSession.id);
    } catch (err: any) {
      setError(err.message || 'Failed to update interview pause state.');
    } finally {
      setSubmitting(false);
    }
  };

  // Complete Interview
  const handleCompleteInterview = async () => {
    if (!activeSession) return;
    try {
      setSubmitting(true);
      setError(null);

      const summary = await completeInterview(activeSession.id);
      setCompletionSummary(summary);
      if (selectedCompanyId) {
        await loadCompanyData(selectedCompanyId);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to finalize interview.');
    } finally {
      setSubmitting(false);
    }
  };

  // Edit an answer
  const handleSaveEdit = async (answerId: number) => {
    if (!activeSession || !editText.trim()) return;
    try {
      setSubmitting(true);
      await editAnswer(activeSession.id, answerId, {
        answer_text: editText.trim(),
        is_confidential: editConfidential,
      });
      setEditingAnswerId(null);
      await refreshSessionState(activeSession.id);
      if (selectedCompanyId) {
        const sessions = await fetchCompanyInterviews(selectedCompanyId);
        setPastSessions(sessions);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to update answer.');
    } finally {
      setSubmitting(false);
    }
  };

  const selectedCompany = companies.find((c) => c.id === selectedCompanyId);

  return (
    <div className="space-y-6">
      {/* 1. TOP HEADER & CONTROLS */}
      <div className="flex flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
            <BrainCircuit className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">Adaptive AI Founder Interview</h1>
              <span className="rounded-full bg-purple-500/10 px-2.5 py-0.5 text-xs font-semibold text-purple-400 border border-purple-500/20">
                Task 3 Engine
              </span>
            </div>
            <p className="text-sm text-slate-400">
              Evidence-grounded conversational inquiry uncovering non-public commercial intelligence for{' '}
              <strong className="text-slate-200">{selectedCompany?.name || 'Company'}</strong>{' '}
              {selectedCompany?.industry ? `(${selectedCompany.industry})` : ''}.
            </p>
          </div>
        </div>

        {/* Company Selector Dropdown & Sessions */}
        <div className="flex flex-wrap items-center gap-3">
          {pastSessions.length > 1 && (
            <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-1.5">
              <span className="text-xs text-slate-400">Run:</span>
              <select
                value={activeSession?.id || ''}
                onChange={(e) => {
                  const s = pastSessions.find((item) => item.id === Number(e.target.value));
                  if (s) {
                    setActiveSession(s);
                    refreshSessionState(s.id);
                  }
                }}
                className="bg-transparent text-xs font-medium text-slate-200 focus:outline-none"
              >
                {pastSessions.map((s) => (
                  <option key={s.id} value={s.id} className="bg-slate-900 text-slate-200">
                    Session #{s.id} ({s.status})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-1.5">
            <Building2 className="h-4 w-4 text-slate-400" />
            <select
              value={selectedCompanyId || ''}
              onChange={(e) => setSelectedCompanyId(Number(e.target.value))}
              className="bg-transparent text-sm font-medium text-slate-200 focus:outline-none"
            >
              {companies.map((comp) => (
                <option key={comp.id} value={comp.id} className="bg-slate-900 text-slate-200">
                  {comp.name} ({comp.normalized_domain})
                </option>
              ))}
            </select>
          </div>

          {/* New Session Button */}
          <button
            onClick={handleStartSession}
            disabled={submitting || loading || !selectedCompanyId}
            className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-purple-500/20 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            {activeSession && activeSession.status === 'IN_PROGRESS' ? 'Restart Interview' : 'Start AI Interview'}
          </button>
        </div>
      </div>

      {/* ERROR ALERT BANNER */}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          <XCircle className="h-5 w-5 flex-shrink-0 text-red-400" />
          <div className="flex-1">{error}</div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200">
            Dismiss
          </button>
        </div>
      )}

      {/* FOLLOW-UP NOTICE BANNER */}
      {followupNotice && (
        <div className="flex items-center gap-3 rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-4 text-sm text-cyan-300 animate-fadeIn">
          <Info className="h-5 w-5 flex-shrink-0 text-cyan-400" />
          <div className="flex-1">{followupNotice}</div>
          <button onClick={() => setFollowupNotice(null)} className="text-cyan-400 hover:text-cyan-200">
            Dismiss
          </button>
        </div>
      )}

      {/* 2. PROGRESS & CONTROLS BAR */}
      {activeSession && progress && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <span
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${
                  activeSession.status === 'IN_PROGRESS'
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                    : activeSession.status === 'PAUSED'
                    ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                    : 'border-blue-500/30 bg-blue-500/10 text-blue-400'
                }`}
              >
                {activeSession.status === 'IN_PROGRESS' && <Play className="h-3 w-3 animate-pulse" />}
                {activeSession.status === 'PAUSED' && <Pause className="h-3 w-3" />}
                {activeSession.status === 'COMPLETED' && <CheckCircle2 className="h-3 w-3" />}
                Session #{activeSession.id} • {activeSession.status.replace('_', ' ')}
              </span>

              <span className="text-xs text-slate-400">
                Core Progress: <strong className="text-white">{progress.core_answered_count + progress.core_skipped_count}</strong> / 10
              </span>

              {progress.followup_count > 0 && (
                <span className="rounded-full bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 text-xs text-cyan-400">
                  +{progress.followup_count} Clarifying Follow-ups
                </span>
              )}

              {progress.confidential_answers_count > 0 && (
                <span className="flex items-center gap-1 rounded-full bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 text-xs text-purple-400">
                  <Shield className="h-3 w-3" />
                  {progress.confidential_answers_count} Confidential
                </span>
              )}
            </div>

            {/* Session Action Controls */}
            <div className="flex items-center gap-2">
              {activeSession.status !== 'COMPLETED' && (
                <button
                  onClick={handleTogglePause}
                  disabled={submitting}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700"
                >
                  {activeSession.status === 'IN_PROGRESS' ? (
                    <>
                      <Pause className="h-3.5 w-3.5" /> Pause
                    </>
                  ) : (
                    <>
                      <Play className="h-3.5 w-3.5 text-emerald-400" /> Resume
                    </>
                  )}
                </button>
              )}

              <button
                onClick={() => setHistoryOpen(!historyOpen)}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700"
              >
                <MessageSquare className="h-3.5 w-3.5" />
                {historyOpen ? 'Hide History' : 'Review Answers'}
              </button>

              {activeSession.status !== 'COMPLETED' && (
                <button
                  onClick={handleCompleteInterview}
                  disabled={submitting}
                  className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 shadow-md shadow-emerald-600/20 disabled:opacity-50"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Finalize & Upgrade Profile
                </button>
              )}
            </div>
          </div>

          {/* Stepper Progress Bar */}
          <div className="mt-4">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
              <span>Interview Progression</span>
              <span>{progress.completion_percentage}% Completed</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full bg-gradient-to-r from-purple-500 via-indigo-500 to-emerald-500 transition-all duration-500 ease-out"
                style={{ width: `${progress.completion_percentage}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* 3. COMPLETION SUMMARY CARD (When interview finishes) */}
      {completionSummary && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-6 backdrop-blur-md">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Interview Finalized & Structured Context Extracted</h2>
              <p className="text-xs text-slate-400">
                Company intelligence profile upgraded to <strong>v{completionSummary.profile_version}</strong> with verified founder provenance.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
              <div className="text-xs text-slate-400">Extracted Context Items</div>
              <div className="mt-1 text-2xl font-bold text-white">{completionSummary.extracted_context_count}</div>
              <div className="text-xs text-emerald-400 mt-1">Founder confirmed</div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
              <div className="text-xs text-slate-400">Protected Confidential Answers</div>
              <div className="mt-1 text-2xl font-bold text-purple-400">{completionSummary.confidential_answers_protected}</div>
              <div className="text-xs text-slate-500 mt-1">Segregated from public feeds</div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
              <div className="text-xs text-slate-400">Resolved Unknowns</div>
              <div className="mt-1 text-2xl font-bold text-cyan-400">{completionSummary.resolved_unknowns_count}</div>
              <div className="text-xs text-slate-500 mt-1">Monetization & moats clarified</div>
            </div>
          </div>
        </div>
      )}

      {/* 4. ACTIVE QUESTION INTERACTION CARD */}
      {activeSession && activeSession.status === 'IN_PROGRESS' && currentQuestion ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl backdrop-blur-md">
          {/* Question Metadata Header */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-4 mb-5">
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  currentQuestion.question_type === 'FOLLOWUP'
                    ? 'border border-cyan-500/30 bg-cyan-500/10 text-cyan-300'
                    : 'border border-purple-500/30 bg-purple-500/10 text-purple-300'
                }`}
              >
                {currentQuestion.question_type === 'FOLLOWUP' ? 'Clarifying Follow-Up' : `Question ${currentQuestion.question_order} of 10`}
              </span>

              <span className="rounded-full border border-slate-700 bg-slate-800/80 px-2.5 py-0.5 text-xs text-slate-300">
                {currentQuestion.business_area}
              </span>
            </div>

            <div className="text-xs text-slate-400 flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              Target Objective: {currentQuestion.related_company_profile_field || 'Strategy'}
            </div>
          </div>

          {/* Question Prompt */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold leading-relaxed text-slate-100">
              {currentQuestion.question_text}
            </h2>

            {/* Expandable Rationale Accordion */}
            <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
              <button
                onClick={() => setShowRationale(!showRationale)}
                className="flex w-full items-center justify-between text-left text-xs font-semibold text-slate-400 hover:text-slate-200"
              >
                <span className="flex items-center gap-1.5">
                  <HelpCircle className="h-3.5 w-3.5 text-purple-400" />
                  Why Signal Stack is asking this question
                </span>
                {showRationale ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              </button>

              {showRationale && (
                <div className="mt-3 space-y-2 text-xs text-slate-400 border-t border-slate-800/80 pt-3">
                  <p>
                    <strong className="text-slate-300">Intelligence Purpose: </strong>
                    {currentQuestion.reason_for_asking}
                  </p>
                  <p>
                    <strong className="text-slate-300">Executive Goal: </strong>
                    {currentQuestion.information_objective}
                  </p>
                </div>
              )}
            </div>

            {/* Answer Input Textarea */}
            <div className="mt-4 space-y-3">
              <label className="block text-xs font-medium text-slate-300">
                Founder Response
              </label>
              <textarea
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                placeholder="Provide detailed commercial context, monetization models, customer specifics, or operational milestones..."
                rows={4}
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-3.5 text-sm text-slate-200 placeholder-slate-500 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              />

              {/* Confidentiality Toggle & Controls */}
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pt-2">
                <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={isConfidential}
                    onChange={(e) => setIsConfidential(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-purple-600 focus:ring-purple-500"
                  />
                  <span className="flex items-center gap-1 font-medium text-slate-300">
                    <Shield className={`h-3.5 w-3.5 ${isConfidential ? 'text-purple-400' : 'text-slate-500'}`} />
                    Mark as Confidential (Founder Eyes Only)
                  </span>
                  <span className="text-slate-500 text-[11px]">(Will never be exposed or sent externally)</span>
                </label>

                <div className="flex items-center gap-3">
                  <button
                    onClick={handleSkipQuestion}
                    disabled={submitting}
                    className="rounded-lg border border-slate-700 bg-transparent px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-50"
                  >
                    Skip Question
                  </button>

                  <button
                    onClick={handleSubmitAnswer}
                    disabled={submitting || !answerText.trim()}
                    className="flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-emerald-600/20 hover:bg-emerald-500 disabled:opacity-50"
                  >
                    <Send className="h-3.5 w-3.5" />
                    {submitting ? 'Recording...' : 'Submit Answer'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : activeSession && activeSession.status === 'PAUSED' ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-8 text-center backdrop-blur-md">
          <Pause className="mx-auto h-10 w-10 text-amber-400 mb-3" />
          <h2 className="text-lg font-semibold text-white">Interview Session is Paused</h2>
          <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
            You can resume the conversation anytime without losing previously submitted responses.
          </p>
          <button
            onClick={handleTogglePause}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-xs font-semibold text-white hover:bg-amber-500"
          >
            <Play className="h-4 w-4" /> Resume Interview
          </button>
        </div>
      ) : activeSession && activeSession.status === 'COMPLETED' ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8 text-center backdrop-blur-md">
          <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-400 mb-3" />
          <h2 className="text-lg font-semibold text-white">Interview Session Completed</h2>
          <p className="text-sm text-slate-400 mt-1">
            All 10 core areas have been resolved. The structured context has been integrated into the executive intelligence profile.
          </p>
          <button
            onClick={handleStartSession}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-xs font-semibold text-white hover:bg-purple-500"
          >
            <RotateCcw className="h-4 w-4" /> Start New Interview Session
          </button>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8 text-center backdrop-blur-md">
          <BrainCircuit className="mx-auto h-12 w-12 text-slate-600 mb-3" />
          <h2 className="text-lg font-semibold text-white">No Active AI Interview</h2>
          <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
            Initiate a company-tailored interview to bridge blindspots identified during website crawling.
          </p>
          <button
            onClick={handleStartSession}
            disabled={submitting || loading || !selectedCompanyId}
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-5 py-2.5 text-xs font-semibold text-white hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" /> Start 10-Question Founder Interview
          </button>
        </div>
      )}

      {/* 5. HISTORY & ANSWER REVIEW DRAWER */}
      {historyOpen && activeSession && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-6 backdrop-blur-md">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-purple-400" />
              <h3 className="font-semibold text-white text-sm">Session Answers & Audit Trail</h3>
            </div>
            <span className="text-xs text-slate-500">
              {activeSession.questions.filter((q) => q.status === 'ANSWERED' || q.status === 'CONFIDENTIAL').length} answered
            </span>
          </div>

          <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
            {activeSession.questions.map((q) => {
              const latestAns = q.answers[0];
              const isEditing = editingAnswerId === latestAns?.id;

              return (
                <div
                  key={q.id}
                  className={`rounded-lg border p-4 ${
                    q.status === 'ANSWERED'
                      ? 'border-emerald-500/20 bg-emerald-500/5'
                      : q.status === 'CONFIDENTIAL'
                      ? 'border-purple-500/20 bg-purple-500/5'
                      : q.status === 'SKIPPED'
                      ? 'border-amber-500/20 bg-amber-500/5'
                      : 'border-slate-800 bg-slate-950/40 opacity-70'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-xs font-semibold text-slate-300">
                      #{q.question_order} • {q.business_area} ({q.question_type})
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        q.status === 'ANSWERED'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : q.status === 'CONFIDENTIAL'
                          ? 'bg-purple-500/20 text-purple-400'
                          : q.status === 'SKIPPED'
                          ? 'bg-amber-500/20 text-amber-400'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {q.status}
                    </span>
                  </div>

                  <p className="text-xs font-medium text-slate-300 mb-2">{q.question_text}</p>

                  {/* Answers Display or Edit Box */}
                  {latestAns && (
                    <div className="mt-2 rounded border border-slate-800/80 bg-slate-950/80 p-3">
                      {isEditing ? (
                        <div className="space-y-2">
                          <textarea
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            rows={3}
                            className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-xs text-slate-200"
                          />
                          <div className="flex items-center justify-between">
                            <label className="flex items-center gap-1.5 text-xs text-slate-400">
                              <input
                                type="checkbox"
                                checked={editConfidential}
                                onChange={(e) => setEditConfidential(e.target.checked)}
                              />
                              Confidential
                            </label>
                            <div className="flex gap-2">
                              <button
                                onClick={() => setEditingAnswerId(null)}
                                className="px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => handleSaveEdit(latestAns.id)}
                                className="rounded bg-emerald-600 px-3 py-1 text-xs font-semibold text-white hover:bg-emerald-500"
                              >
                                Save Edit
                              </button>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-start justify-between gap-3">
                          <div className="text-xs text-slate-200 leading-relaxed">
                            {latestAns.is_confidential && (
                              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-purple-400 mr-2">
                                <Shield className="h-3 w-3" /> [CONFIDENTIAL]
                              </span>
                            )}
                            {latestAns.answer_text}
                          </div>
                          {q.status !== 'SKIPPED' && (
                            <button
                              onClick={() => {
                                setEditingAnswerId(latestAns.id);
                                setEditText(latestAns.answer_text || '');
                                setEditConfidential(latestAns.is_confidential);
                              }}
                              className="text-slate-400 hover:text-purple-400"
                              title="Edit answer"
                            >
                              <Edit3 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 6. FOUNDER BUSINESS CONTEXT TABLE (If any extracted) */}
      {founderContexts.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-emerald-400" />
              <h3 className="font-semibold text-white text-sm">Founder-Confirmed Proprietary Intelligence</h3>
            </div>
            <span className="text-xs text-slate-400">{founderContexts.length} verified records</span>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {founderContexts.map((ctx) => (
              <div key={ctx.id} className="rounded-lg border border-slate-800 bg-slate-950/60 p-3.5">
                <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                  <span className="font-bold uppercase tracking-wider text-purple-400">
                    {ctx.context_category.replace('_', ' ')}
                  </span>
                  <span>Confidence: {(ctx.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="text-xs font-semibold text-white mb-1.5">{ctx.field_name}</div>
                <div className="text-xs text-slate-300">
                  {typeof ctx.confirmed_value === 'object'
                    ? JSON.stringify(ctx.confirmed_value, null, 2)
                    : String(ctx.confirmed_value)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
