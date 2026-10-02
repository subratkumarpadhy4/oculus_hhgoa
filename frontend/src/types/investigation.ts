export type CaseStatus = 'under_investigation' | 'requires_approval' | 'resolved_fraud' | 'resolved_cleared' | 'escalated_human';

export type UncertaintyLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export type SufficiencyStatus = 'INSUFFICIENT' | 'SUFFICIENT' | 'CONTRADICTORY';

export type ApprovalTier = 'auto' | 'L1' | 'L2';

export interface GraphNode {
  id: string;
  label: string;
  type: 'Transaction' | 'Account' | 'Card' | 'Device' | 'IP' | 'PriorCase' | 'EmailDomain';
  riskScore?: number;
  isFraudRing?: boolean;
  properties: Record<string, string | number | boolean | undefined>;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: 'OWNS' | 'ON_DEVICE' | 'FROM_IP' | 'USES_CARD' | 'LINKED_TO' | 'MATCHES_PATTERN';
  isSuspicious?: boolean;
}

export interface PatternObservation {
  pattern: 'SharedDeviceRing' | 'VelocityBurst' | 'AmountAnomaly' | 'GeoMismatch' | 'EmailDomainCluster' | 'CardTesting' | 'NewDeviceWithProxy';
  strength: 'none' | 'weak' | 'moderate' | 'strong';
  observations: string[];
}

export interface EvidencePack {
  trigger: {
    type: 'risk_score' | 'customer_report' | 'analyst_request' | 'system_event';
    risk_signal: number;
    source: string;
    timestamp: string;
  };
  transaction_context: {
    transaction_id: string;
    amount_usd: number;
    card_bin: string;
    product_cd: string;
    p_emaildomain: string;
    r_emaildomain?: string;
    device_info: string;
    ip_address: string;
    geo_location: string;
    c_features_summary: string;
    v_features_summary: string;
  };
  connected_entities: {
    type: string;
    id: string;
    linkage: string;
    historical_fraud: boolean;
  }[];
  detected_patterns: PatternObservation[];
  prior_cases: {
    note: string;
    related: { case_id: string; shared_entity: string; outcome: string }[];
    similar: {
      case_id: string;
      relevance_score: number;
      matching_dimensions: string[];
      outcome: string;
      analyst_decision: string;
    }[];
  };
  policy_rules: {
    rule_id: string;
    title: string;
    text: string;
    source: string;
  }[];
  missing_evidence: string[];
  contradictions: string[];
}

export interface UncertaintyDimensions {
  fraud_risk_signal: 1 | 2 | 3; // low=1, medium=2, high=3
  graph_evidence: 0 | 1 | 2 | 3; // none=0, weak=1, moderate=2, strong=3
  behavioral_evidence: 0 | 2; // normal=0, anomalous=2
  policy_support: 0 | 1 | 3; // none=0, advisory=1, directive=3
  contradictory_evidence: 0 | 1 | 3; // none=0, minor=1, major=3 (subtracted)
  calculated_score: number;
  threshold: number;
  status: SufficiencyStatus;
}

export interface NbaRecommendation {
  action: string;
  action_id: string;
  approval_tier: ApprovalTier;
  approval_route: string;
  rationale: string;
  alternatives_considered: string[];
  simulated_api?: string;
}

export interface DynamicEvidenceRequest {
  request_type: 
    | 'request_step_up_auth' 
    | 'request_customer_validation' 
    | 'request_device_fingerprint' 
    | 'request_kyc_reverification' 
    | 'request_transaction_history_extension' 
    | 'request_analyst_review';
  label: string;
  status: 'PENDING' | 'DISPATCHED' | 'RECEIVED' | 'FAILED' | 'PASSED' | 'TIMEOUT';
  response_payload: Record<string, any>;
  timestamp: string;
}

export interface ExecutionStep {
  id: number;
  title: string;
  subtitle: string;
  status: 'complete' | 'in_progress' | 'pending' | 'failed';
  timestamp?: string;
  details: string;
  mcpCall?: {
    tool: string;
    latencyMs: number;
    summary: string;
  };
  outputSnippet?: string;
}

export interface SarReport {
  sar_id: string;
  filing_date: string;
  subject_name: string;
  subject_account: string;
  transaction_amount: number;
  activity_start: string;
  activity_end: string;
  primary_violation: string;
  narrative: string;
  regulatory_basis: string;
  compliance_analyst: string;
}

export interface BenchmarkCase {
  case_id: string;
  case_number: number; // 1 to 20
  transaction_id: string;
  account_id: string;
  card_id: string;
  amount_usd: number;
  timestamp: string;
  initial_risk_score: number;
  status: CaseStatus;
  primary_pattern: string;
  pre_evidence_uncertainty: UncertaintyLevel;
  post_evidence_uncertainty: UncertaintyLevel;
  pre_evidence_nba: NbaRecommendation;
  evidence_injected: DynamicEvidenceRequest;
  post_evidence_nba: NbaRecommendation;
  evidence_pack: EvidencePack;
  uncertainty_dimensions: UncertaintyDimensions;
  graph_nodes: GraphNode[];
  graph_edges: GraphEdge[];
  execution_steps: ExecutionStep[];
  card_network?: string;
  card_type?: string;
  sar_report?: SarReport;
  sar?: {
    narrative?: string;
  };
  historical_counts?: {
    prior_fraud_cases?: number;
    customers_on_device?: number;
    transactions_on_device?: number;
    devices_on_customer?: number;
    prior_cases_referenced?: string;
  };
  sar_status?: 'Pending' | 'Cleared';
  analyst_notes?: string;
}

export type CaseLifecycleStatus = 'Resolved' | 'Closed' | 'Pending';

export function getCaseLifecycleStatus(c: { status: CaseStatus | string }): CaseLifecycleStatus {
  if (c.status === 'resolved_cleared' || c.status === 'resolved') {
    return 'Resolved';
  }
  if (c.status === 'resolved_fraud' || c.status === 'closed' || c.status === 'escalated_human') {
    return 'Closed';
  }
  return 'Pending';
}

export function getStatusDot(status: CaseLifecycleStatus): {
  colorClass: string;
  dotBg: string;
  label: string;
} {
  switch (status) {
    case 'Resolved':
      return { colorClass: 'bg-emerald-500', dotBg: '#10B981', label: 'Resolved' };
    case 'Closed':
      return { colorClass: 'bg-rose-500', dotBg: '#F43F5E', label: 'Closed' };
    case 'Pending':
    default:
      return { colorClass: 'bg-amber-400', dotBg: '#FBBF24', label: 'Pending' };
  }
}
