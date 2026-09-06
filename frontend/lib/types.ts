export type Verdict = "PASS" | "WATCH" | "DILIGENCE";
export type Relation = "SUPPORTS" | "CONTRADICTS" | "QUALIFIES";
export type SourceType = "DECK" | "FOUNDER_NOTE" | "AGENT" | "WEB";

export interface Company {
  id: string;
  name: string;
  website: string | null;
  stage: string | null;
  geography: string | null;
  created_at: string;
  updated_at: string;
}

export interface PipelineRow extends Company {
  has_deck: boolean;
  has_analysis: boolean;
  recommendation: Verdict | null;
  overall_score: number | null;
  decision: Verdict | null;
  main_concern: string | null;
  last_changed: string;
}

export interface DocumentInfo {
  id: string;
  company_id: string;
  file_name: string;
  page_count: number;
  created_at: string;
}

export interface Evidence {
  id: string;
  claim_id: string | null;
  evidence_text: string;
  relation: Relation;
  source_page: number | null;
  source_url: string | null;
  source_type: SourceType;
  created_at: string;
}

export interface Claim {
  id: string;
  claim_text: string;
  category: string;
  source_page: number | null;
  supporting_text: string | null;
  evidence_strength: "LOW" | "MEDIUM" | "HIGH";
  missing_proof: string | null;
  evidence: Evidence[];
}

export interface CriterionScore {
  score: number | null;
  reason: string;
  evidence_refs: string[];
}

export interface Assessment {
  id: string;
  trigger: "DECK" | "AGENT" | "FOUNDER_NOTE";
  source_ref_id: string | null;
  criterion_scores: Record<string, CriterionScore>;
  overall_score: number | null;
  used_weight: number;
  recommendation: Verdict | null;
  summary: string;
  main_concern: string;
  created_at: string;
}

export interface Question {
  id: string;
  position: number;
  question: string;
  why_it_matters: string;
  strong_answer: string;
  weak_answer: string;
  basis: string;
}

export interface Decision {
  id: string;
  decision: Verdict;
  rationale: string;
  assessment_id: string | null;
  created_at: string;
}

export interface Criterion {
  key: string;
  label: string;
  weight: number;
  description: string;
}

export interface Thesis {
  id: string;
  name: string;
  thesis_text: string;
  criteria: Criterion[];
  positive_signals: string[];
  out_of_scope: string[];
}

export interface MonitoringEvent {
  id: string;
  agent_provider: string;
  investment_question: string;
  event_found: boolean;
  event_type: string;
  event_date: string | null;
  summary: string;
  source_url: string | null;
  relevance: string;
  claim_or_gap_affected: string | null;
  suggested_action: "NO_CHANGE" | "REVIEW";
  created_at: string;
}

export interface Snapshot {
  company_name: string | null;
  founders: { name: string; role: string | null; domain_background: string | null }[];
  problem: string | null;
  workflow: string | null;
  customer: string | null;
  buyer: string | null;
  solution: string | null;
  business_model: string | null;
  traction: string[];
  funding_ask: string | null;
  unknowns: string[];
}

export interface Analysis {
  company: Company;
  snapshot: Snapshot | null;
  document: DocumentInfo | null;
  claims: Claim[];
  assessment: Assessment | null;
  questions: Question[];
  decision: Decision | null;
  thesis: Thesis;
  monitoring_events: MonitoringEvent[];
  research: Research | null;
}

export interface ResearchFact {
  category: string;
  finding: string;
  source_url: string;
  source_title: string;
  publication_date: string | null;
  confidence: "LOW" | "MEDIUM" | "HIGH";
  claim_id: string | null;
  relation: Relation | null;
}

export interface Research {
  id: string;
  brief: string;
  queries: string[];
  result_count: number;
  domain_count: number;
  facts_kept: number;
  facts_dropped: number;
  search_provider: string;
  summary: string;
  entity_note: string | null;
  facts: ResearchFact[];
  unknowns: string[];
  created_at: string;
  reassessment: Reassessment | null;
}

export interface CriterionDelta {
  key: string;
  label: string;
  old: number | null;
  new: number | null;
  reason: string;
}

export interface Reassessment {
  trigger: "AGENT" | "FOUNDER_NOTE" | "RESEARCH";
  event: MonitoringEvent | null;
  note_summary: string | null;
  new_evidence: Evidence[];
  assessment_before: Assessment | null;
  assessment_after: Assessment;
  deltas: CriterionDelta[];
  recommendation: { before: Verdict | null; after: Verdict | null; changed: boolean };
  human_decision: Decision | null;
  matters: boolean;
  explanation: string;
}

export interface ChangeEntry {
  id: string;
  ts: string;
  kind: "DECK_UPLOADED" | "ASSESSMENT" | "DECISION" | "AGENT_EVENT" | "FOUNDER_NOTE" | "QUESTIONS" | "RESEARCH";
  title: string;
  detail: string;
  source_url: string | null;
  recommendation: Verdict | null;
  overall_score: number | null;
  deltas: CriterionDelta[];
  recommendation_before: Verdict | null;
  human_decision_at_time: Verdict | null;
}
