export interface AIProviderStatus {
  configured: boolean;
  model: string;
  target?: string;
}

export interface DatabaseStatus {
  connected: boolean;
  type: string;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'offline';
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  database: DatabaseStatus;
  ai_providers: Record<string, AIProviderStatus>;
}

export type NavigationItem = {
  id: string;
  label: string;
  iconName: string;
  badge?: string;
};

// Company Intelligence Types
export interface ResearchRun {
  id: number;
  company_id: number;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'COMPLETED_WITH_WARNINGS' | 'FAILED';
  started_at: string;
  completed_at?: string | null;
  pages_discovered: number;
  pages_fetched: number;
  pages_failed: number;
  error_message?: string | null;
  ai_analysis_status?: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'UNAVAILABLE' | null;
}

export interface Company {
  id: number;
  name: string;
  website: string;
  normalized_domain: string;
  industry?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  latest_research_run?: ResearchRun | null;
  profile_version?: number | null;
}

export interface CompanyProfile {
  id: number;
  company_id: number;
  industry?: string | null;
  business_model?: string | null;
  products_services: string[];
  target_customers: string[];
  customer_problems: string[];
  revenue_streams: string[];
  geographical_markets: string[];
  positioning?: string | null;
  growth_related_information: string[];
  unknown_information: string[];
  profile_version: number;
  research_run_id?: number | null;
  updated_at: string;
}

export interface CompanyFact {
  id: number;
  company_id: number;
  research_page_id?: number | null;
  category: string;
  statement: string;
  classification: 'VERIFIED_FACT' | 'ASSUMPTION' | 'UNKNOWN';
  evidence_snippet?: string | null;
  confidence?: number | null;
  created_at: string;
  source_url?: string | null;
  source_title?: string | null;
}

export interface ResearchPage {
  id: number;
  company_id: number;
  research_run_id?: number | null;
  url: string;
  canonical_url?: string | null;
  title?: string | null;
  content_hash?: string | null;
  http_status?: number | null;
  text_length: number;
  crawled_at: string;
  first_seen_at: string;
  last_seen_at: string;
}

// =============================================================================
// ADAPTIVE AI FOUNDER INTERVIEW TYPES
// =============================================================================

export interface InterviewAnswer {
  id: number;
  question_id: number;
  answer_text?: string | null;
  is_confidential: boolean;
  created_at: string;
  updated_at: string;
}

export interface InterviewQuestion {
  id: number;
  session_id: number;
  parent_question_id?: number | null;
  question_type: 'CORE' | 'FOLLOWUP';
  question_order: number;
  question_text: string;
  business_area: string;
  reason_for_asking: string;
  information_objective: string;
  related_company_profile_field?: string | null;
  expected_information_type?: string | null;
  status: 'PENDING' | 'ASKED' | 'ANSWERED' | 'SKIPPED' | 'CONFIDENTIAL';
  created_at: string;
  answers: InterviewAnswer[];
}

export interface InterviewSession {
  id: number;
  company_id: number;
  profile_version_at_start: number;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'PAUSED' | 'COMPLETED';
  total_core_questions: number;
  answered_count: number;
  skipped_count: number;
  started_at: string;
  completed_at?: string | null;
  created_at: string;
  questions: InterviewQuestion[];
}

export interface InterviewProgress {
  session_id: number;
  company_id: number;
  status: string;
  total_core_questions: number;
  core_answered_count: number;
  core_skipped_count: number;
  core_remaining_count: number;
  followup_count: number;
  followup_answered_count: number;
  followup_remaining_count: number;
  confidential_answers_count: number;
  completion_percentage: number;
  is_ready_to_complete: boolean;
  started_at: string;
  completed_at?: string | null;
}

export interface FounderBusinessContext {
  id: number;
  company_id: number;
  interview_session_id: number;
  context_category: string;
  field_name: string;
  confirmed_value: any;
  confidence: number;
  created_at: string;
}

export interface InterviewCompletionSummary {
  session_id: number;
  company_id: number;
  status: string;
  profile_version: number;
  extracted_context_count: number;
  confidential_answers_protected: number;
  resolved_unknowns_count: number;
  completed_at: string;
}

// =============================================================================
// COMPETITOR DISCOVERY & SOURCE INTELLIGENCE TYPES (TASK 4)
// =============================================================================

export interface Competitor {
  id: number;
  company_id: number;
  name: string;
  canonical_domain: string;
  website: string;
  industry?: string | null;
  relationship_type: 'DIRECT' | 'INDIRECT' | 'SUBSTITUTE';
  products_services: string[];
  target_customers: string[];
  geographic_markets: string[];
  discovery_method: string;
  supporting_evidence: any[];
  discovery_rationale: string;
  confidence: number;
  review_status: 'CANDIDATE' | 'APPROVED' | 'REJECTED' | 'ARCHIVED';
  created_at: string;
  updated_at: string;
}

export interface SourceCrawlLog {
  id: number;
  source_id: number;
  status: string;
  http_status?: number | null;
  response_time_ms?: number | null;
  content_hash?: string | null;
  error_message?: string | null;
  checked_at: string;
}

export interface IntelligenceSource {
  id: number;
  company_id: number;
  competitor_id?: number | null;
  name: string;
  canonical_url: string;
  domain: string;
  source_type: string;
  category: 'CUSTOMERS' | 'COMPETITORS' | 'MARKET' | 'INTERNAL';
  secondary_categories: string[];
  why_it_matters: string;
  intelligence_type: string;
  discovery_method: string;
  supporting_evidence: any[];
  credibility_score: number;
  status: 'DISCOVERED' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'PAUSED' | 'BLOCKED' | 'ERROR';
  robots_status: string;
  crawl_frequency_minutes: number;
  last_attempted_crawl?: string | null;
  last_successful_crawl?: string | null;
  last_content_change?: string | null;
  last_error?: string | null;
  http_status?: number | null;
  created_at: string;
  updated_at: string;
}

export interface SourceSummaryStats {
  total_sources: number;
  approved: number;
  pending: number;
  rejected: number;
  paused: number;
  blocked: number;
  by_category: {
    CUSTOMERS: number;
    COMPETITORS: number;
    MARKET: number;
    INTERNAL: number;
    [key: string]: number;
  };
  competitors_count: number;
  approved_competitors: number;
}
