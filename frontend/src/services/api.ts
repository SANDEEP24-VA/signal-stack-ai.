import {
  Company,
  CompanyFact,
  CompanyProfile,
  Competitor,
  FounderBusinessContext,
  IntelligenceSource,
  InterviewAnswer,
  InterviewCompletionSummary,
  InterviewProgress,
  InterviewQuestion,
  InterviewSession,
  ResearchPage,
  ResearchRun,
  SourceCrawlLog,
  SourceSummaryStats,
  SystemHealth,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson.error?.message) {
        errorDetail = errJson.error.message;
      } else if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore JSON parse error
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

// System Health
export async function fetchSystemHealth(): Promise<SystemHealth> {
  const url = API_BASE.endsWith('/health') ? API_BASE : `${API_BASE}/health`;
  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<SystemHealth>(response);
}

// Company Management
export async function fetchCompanies(): Promise<Company[]> {
  const response = await fetch(`${API_BASE}/companies`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Company[]>(response);
}

export async function createCompany(data: {
  name: string;
  website: string;
  industry?: string;
}): Promise<Company> {
  const response = await fetch(`${API_BASE}/companies`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(data),
  });
  return handleResponse<Company>(response);
}

export async function fetchCompany(id: number): Promise<Company> {
  const response = await fetch(`${API_BASE}/companies/${id}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Company>(response);
}

// Research Execution & Status
export async function startResearch(companyId: number): Promise<ResearchRun> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/research`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<ResearchRun>(response);
}

export async function fetchResearchRuns(companyId: number): Promise<ResearchRun[]> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/research`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<ResearchRun[]>(response);
}

export async function fetchResearchRun(companyId: number, runId: number): Promise<ResearchRun> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/research/${runId}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<ResearchRun>(response);
}

// Profile & Intelligence
export async function fetchCompanyProfile(companyId: number): Promise<CompanyProfile> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/profile`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<CompanyProfile>(response);
}

export async function updateCompanyProfile(
  companyId: number,
  data: Partial<CompanyProfile>
): Promise<CompanyProfile> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/profile`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(data),
  });
  return handleResponse<CompanyProfile>(response);
}

// Facts & Evidence
export async function fetchCompanyFacts(
  companyId: number,
  classification?: string
): Promise<CompanyFact[]> {
  const query = classification ? `?classification=${encodeURIComponent(classification)}` : '';
  const response = await fetch(`${API_BASE}/companies/${companyId}/facts${query}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<CompanyFact[]>(response);
}

// Crawled Pages
export async function fetchCompanyPages(companyId: number): Promise<ResearchPage[]> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/pages`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<ResearchPage[]>(response);
}

// =============================================================================
// ADAPTIVE AI FOUNDER INTERVIEW API
// =============================================================================

export async function startInterview(companyId: number): Promise<InterviewSession> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/interviews`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<InterviewSession>(response);
}

export async function fetchCompanyInterviews(companyId: number): Promise<InterviewSession[]> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/interviews`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<InterviewSession[]>(response);
}

export async function fetchInterviewSession(sessionId: number): Promise<InterviewSession> {
  const response = await fetch(`${API_BASE}/interviews/${sessionId}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<InterviewSession>(response);
}

export async function fetchInterviewProgress(sessionId: number): Promise<InterviewProgress> {
  const response = await fetch(`${API_BASE}/interviews/${sessionId}/progress`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<InterviewProgress>(response);
}

export async function fetchNextQuestion(sessionId: number): Promise<InterviewQuestion | null> {
  const response = await fetch(`${API_BASE}/interviews/${sessionId}/next`, {
    headers: { Accept: 'application/json' },
  });
  if (response.status === 204) {
    return null;
  }
  return handleResponse<InterviewQuestion | null>(response);
}

export async function submitAnswer(
  sessionId: number,
  payload: {
    question_id: number;
    answer_text?: string;
    is_confidential?: boolean;
    is_skip?: boolean;
    allow_followup?: boolean;
  }
): Promise<{ answer: InterviewAnswer; followup_question?: InterviewQuestion | null }> {
  const response = await fetch(`${API_BASE}/interviews/${sessionId}/answers`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<{ answer: InterviewAnswer; followup_question?: InterviewQuestion | null }>(response);
}

export async function editAnswer(
  sessionId: number,
  answerId: number,
  payload: { answer_text: string; is_confidential?: boolean }
): Promise<InterviewAnswer> {
  const response = await fetch(`${API_BASE}/interviews/${sessionId}/answers/${answerId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<InterviewAnswer>(response);
}

export async function pauseInterview(sessionId: number): Promise<InterviewSession> {
  const response = await fetch(`${API_BASE}/interviews/${sessionId}/pause`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<InterviewSession>(response);
}

export async function resumeInterview(sessionId: number): Promise<InterviewSession> {
  const response = await fetch(`${API_BASE}/interviews/${sessionId}/resume`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<InterviewSession>(response);
}

export async function completeInterview(sessionId: number): Promise<InterviewCompletionSummary> {
  const response = await fetch(`${API_BASE}/interviews/${sessionId}/complete`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<InterviewCompletionSummary>(response);
}

export async function fetchCompanyFounderContext(companyId: number): Promise<FounderBusinessContext[]> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/founder-context`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<FounderBusinessContext[]>(response);
}


// =============================================================================
// COMPETITOR DISCOVERY & SOURCE INTELLIGENCE API (TASK 4)
// =============================================================================

// Competitor APIs
export async function discoverCompetitors(companyId: number, verifyDomains: boolean = true): Promise<Competitor[]> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/competitors/discover?verify_domains=${verifyDomains}`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Competitor[]>(response);
}

export async function fetchCompetitors(companyId: number, status?: string, relationship?: string): Promise<Competitor[]> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (relationship) params.append('relationship', relationship);
  const qs = params.toString() ? `?${params.toString()}` : '';

  const response = await fetch(`${API_BASE}/companies/${companyId}/competitors${qs}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Competitor[]>(response);
}

export async function createCompetitor(companyId: number, payload: {
  name: string;
  website: string;
  industry?: string;
  relationship_type?: string;
  products_services?: string[];
  target_customers?: string[];
  geographic_markets?: string[];
  discovery_rationale?: string;
}): Promise<Competitor> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/competitors`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<Competitor>(response);
}

export async function approveCompetitor(competitorId: number): Promise<Competitor> {
  const response = await fetch(`${API_BASE}/competitors/${competitorId}/approve`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Competitor>(response);
}

export async function rejectCompetitor(competitorId: number): Promise<Competitor> {
  const response = await fetch(`${API_BASE}/competitors/${competitorId}/reject`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Competitor>(response);
}

export async function archiveCompetitor(competitorId: number): Promise<Competitor> {
  const response = await fetch(`${API_BASE}/competitors/${competitorId}/archive`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<Competitor>(response);
}

export async function updateCompetitor(competitorId: number, payload: Partial<Competitor>): Promise<Competitor> {
  const response = await fetch(`${API_BASE}/competitors/${competitorId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<Competitor>(response);
}

// Source Intelligence APIs
export async function discoverSources(companyId: number, probeReachability: boolean = true): Promise<IntelligenceSource[]> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/sources/discover?probe_reachability=${probeReachability}`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<IntelligenceSource[]>(response);
}

export async function fetchSources(companyId: number, params?: {
  category?: string;
  status?: string;
  competitor_id?: number;
  limit?: number;
  offset?: number;
}): Promise<IntelligenceSource[]> {
  const urlParams = new URLSearchParams();
  if (params?.category) urlParams.append('category', params.category);
  if (params?.status) urlParams.append('status', params.status);
  if (params?.competitor_id) urlParams.append('competitor_id', params.competitor_id.toString());
  if (params?.limit) urlParams.append('limit', params.limit.toString());
  if (params?.offset) urlParams.append('offset', params.offset.toString());
  const qs = urlParams.toString() ? `?${urlParams.toString()}` : '';

  const response = await fetch(`${API_BASE}/companies/${companyId}/sources${qs}`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<IntelligenceSource[]>(response);
}

export async function fetchSourceSummary(companyId: number): Promise<SourceSummaryStats> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/sources/summary`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<SourceSummaryStats>(response);
}

export async function createSource(companyId: number, payload: {
  name: string;
  canonical_url: string;
  category: string;
  source_type?: string;
  secondary_categories?: string[];
  why_it_matters?: string;
  intelligence_type?: string;
  credibility_score?: number;
  competitor_id?: number;
}): Promise<IntelligenceSource> {
  const response = await fetch(`${API_BASE}/companies/${companyId}/sources`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<IntelligenceSource>(response);
}

export async function approveSource(sourceId: number): Promise<IntelligenceSource> {
  const response = await fetch(`${API_BASE}/sources/${sourceId}/approve`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<IntelligenceSource>(response);
}

export async function rejectSource(sourceId: number, reason?: string): Promise<IntelligenceSource> {
  const qs = reason ? `?reason=${encodeURIComponent(reason)}` : '';
  const response = await fetch(`${API_BASE}/sources/${sourceId}/reject${qs}`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<IntelligenceSource>(response);
}

export async function pauseSource(sourceId: number): Promise<IntelligenceSource> {
  const response = await fetch(`${API_BASE}/sources/${sourceId}/pause`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<IntelligenceSource>(response);
}

export async function resumeSource(sourceId: number): Promise<IntelligenceSource> {
  const response = await fetch(`${API_BASE}/sources/${sourceId}/resume`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<IntelligenceSource>(response);
}

export async function deleteSource(sourceId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/sources/${sourceId}`, {
    method: 'DELETE',
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(`Failed to delete source: HTTP ${response.status}`);
  }
}

export async function probeSource(sourceId: number): Promise<SourceCrawlLog> {
  const response = await fetch(`${API_BASE}/sources/${sourceId}/probe`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<SourceCrawlLog>(response);
}

export async function fetchSourceLogs(sourceId: number): Promise<SourceCrawlLog[]> {
  const response = await fetch(`${API_BASE}/sources/${sourceId}/logs`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<SourceCrawlLog[]>(response);
}
