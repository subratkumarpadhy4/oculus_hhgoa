import type { BenchmarkCase, GraphNode } from '../types/investigation';

export const BENCHMARK_CASES: BenchmarkCase[] = [
  {
    case_id: 'HHG-001',
    case_number: 1,
    transaction_id: '3514030',
    account_id: 'C12382',
    card_id: 'C12382-K1',
    card_network: 'visa',
    card_type: 'debit',
    amount_usd: 894.20,
    timestamp: '2016-11-14 18:24:10 UTC',
    initial_risk_score: 0.88,
    status: 'under_investigation',
    primary_pattern: 'SharedDeviceRing',
    pre_evidence_uncertainty: 'MEDIUM',
    post_evidence_uncertainty: 'HIGH',
    pre_evidence_nba: {
      action: 'VERIFY_WITH_CUSTOMER',
      action_id: 'ACT-VERIFY-OTP',
      approval_tier: 'auto',
      approval_route: 'Automated Rule #12',
      rationale: 'Initial anomaly 88% with multi-account device ring cluster. Step-up authentication challenge dispatched.',
      alternatives_considered: ['BLOCK_CARD', 'MONITOR_CARD'],
      simulated_api: 'core_banking_engine.dispatch_verification_challenge()'
    },
    evidence_injected: {
      request_type: 'request_step_up_auth',
      label: 'Step-up Authentication (SMS OTP)',
      status: 'FAILED',
      timestamp: '2016-11-14 18:26:10 UTC',
      response_payload: {
        method: 'SMS_OTP',
        destination: '+1 (555) ***-9021',
        result: 'FAILED — no response within 3 attempts',
        seconds_elapsed: 180
      }
    },
    post_evidence_nba: {
      action: 'BLOCK_CARD',
      action_id: 'ACT-BLOCK-FREEZE-SAR',
      approval_tier: 'L2',
      approval_route: 'Requires Senior Analyst Sign-off',
      rationale: 'Failed step-up auth with confirmed device ring linkage. Sufficiency score 2.8 / 2.5 SUFFICIENT.',
      alternatives_considered: ['MONITOR_CARD', 'EXTEND_HOLD'],
      simulated_api: 'risk_management.execute_containment_and_sar()'
    },
    uncertainty_dimensions: {
      fraud_risk_signal: 3,
      graph_evidence: 3,
      behavioral_evidence: 2,
      policy_support: 3,
      contradictory_evidence: 0,
      calculated_score: 2.8,
      threshold: 2.5,
      status: 'SUFFICIENT'
    },
    historical_counts: {
      prior_fraud_cases: 4,
      customers_on_device: 7,
      transactions_on_device: 14,
      devices_on_customer: 1,
      prior_cases_referenced: 'CC-1066, CC-2967, CC-3587, CC-1673'
    },
    evidence_pack: {
      trigger: {
        type: 'risk_score',
        risk_signal: 0.88,
        source: 'IEEE-CIS XGBoost Real-Time Detector',
        timestamp: '2016-11-14 18:24:10 UTC'
      },
      transaction_context: {
        transaction_id: '3514030',
        amount_usd: 894.20,
        card_bin: '411111 (Visa Consumer)',
        product_cd: 'W',
        p_emaildomain: 'protonmail.com',
        device_info: 'c72bd41105eb39dd85c6622e779423fe',
        ip_address: '198.51.100.44',
        geo_location: 'Billing region 444.0',
        c_features_summary: 'C1=7, C2=14 (Burst activity)',
        v_features_summary: 'V201=1, V202=894.20'
      },
      connected_entities: [
        { type: 'Device', id: 'c72bd41105eb39dd85c6622e779423fe', linkage: 'Shared across 7 customer profiles', historical_fraud: true },
        { type: 'Card', id: 'C12382-K1', linkage: 'Target credential', historical_fraud: false },
        { type: 'Account', id: 'C12382', linkage: 'Subject customer', historical_fraud: false },
        { type: 'IP', id: '198.51.100.44', linkage: 'Datacenter egress proxy', historical_fraud: true },
        { type: 'PriorCase', id: 'CC-1066', linkage: 'Confirmed device ring fraud (Loss $4.2k)', historical_fraud: true }
      ],
      detected_patterns: [
        {
          pattern: 'SharedDeviceRing',
          strength: 'strong',
          observations: [
            '7 distinct customer accounts on device c72bd41105eb39dd85c6622e779423fe',
            '14 transactions in 48-hour window',
            '3 associated accounts previously closed for fraud'
          ]
        },
        {
          pattern: 'VelocityBurst',
          strength: 'none',
          observations: [
            '1 txn in 1h, 6 in 24h on card within expected velocity envelope'
          ]
        },
        {
          pattern: 'AmountAnomaly',
          strength: 'none',
          observations: [
            '$894.20 aligned with account historical baseline'
          ]
        },
        {
          pattern: 'NewDeviceWithProxy',
          strength: 'none',
          observations: [
            'In-person transaction, no proxy or VPN headers identified'
          ]
        }
      ],
      prior_cases: {
        note: 'Contextual support only',
        related: [
          { case_id: 'CC-1066', shared_entity: 'c72bd41105eb39dd85c6622e779423fe', outcome: 'Confirmed Fraud ($4.2k Loss)' },
          { case_id: 'CC-2967', shared_entity: 'c72bd41105eb39dd85c6622e779423fe', outcome: 'Chargeback Loss ($1.8k)' }
        ],
        similar: []
      },
      policy_rules: [
        {
          rule_id: 'R7',
          title: 'Shared-Device Fraud Rings',
          text: 'Where three or more accounts share a device fingerprint within a rolling 7-day window and any linked account has a prior confirmed fraud outcome, the case is treated as directive evidence of a coordinated ring.',
          source: 'Fraud Operations Standard §4.2'
        },
        {
          rule_id: 'R12',
          title: 'Step-Up Authentication Failure',
          text: 'A failed or non-responsive step-up challenge on a flagged transaction removes behavioral ambiguity and authorizes escalation to account-level action.',
          source: 'Risk Containment Policy §2.1'
        },
        {
          rule_id: 'R21',
          title: 'SAR Filing Threshold',
          text: 'Confirmed device-ring fraud exceeding the reporting threshold requires a Suspicious Activity Report within the regulatory filing window.',
          source: 'FinCEN BSA 31 CFR § 1020.320'
        }
      ],
      missing_evidence: [],
      contradictions: []
    },
    sar: {
      narrative: 'On 2016-11-14, card C12382-K1 belonging to customer C12382 was used for an online authorization of $894.20 under product code W. The transaction originated from hardware device c72bd41105eb39dd85c6622e779423fe in Billing region 444.0, which converged with 7 distinct customer accounts and 14 transactions in a 48-hour window. The device was previously documented on closed fraud cases CC-1066, CC-2967, CC-3587, and CC-1673. Dynamic step-up SMS OTP challenge was dispatched but timed out with zero cardholder response after 3 attempts. In accordance with Rule R7 and R12, card C12382-K1 was placed on BLOCK_CARD status, customer account C12382 frozen, and this SAR filed for total unauthorized amount of $894.20.'
    },
    graph_nodes: [
      { id: 'C12382', label: 'Customer\nC12382', type: 'Account', properties: { created: '3d ago', kyc: 'Tier 1' }, x: 130, y: 150 },
      { id: 'C12382-K1', label: 'Card\nC12382-K1', type: 'Card', properties: { brand: 'Visa', type: 'Debit' }, x: 120, y: 280 },
      { id: '3514030', label: 'TXN #3514030\n$894.20', type: 'Transaction', riskScore: 0.88, isFraudRing: true, properties: { amount: '$894.20', status: 'Pending Hold', time: '18:24:10 UTC' }, x: 365, y: 215 },
      { id: 'CC-1066', label: 'Prior Case\nCC-1066 ($4.2k)', type: 'PriorCase', isFraudRing: true, properties: { outcome: 'Fraud Confirmed', loss: '$4,200' }, x: 440, y: 80 },
      { id: 'c72bd41105eb39dd85c6622e779423fe', label: 'Device\nc72bd411...', type: 'Device', isFraudRing: true, properties: { hash: 'c72bd41105eb39dd85c6622e779423fe', accounts_seen: 7 }, x: 605, y: 175 },
      { id: 'IP-198', label: 'IP Address\n198.51.100.44', type: 'IP', isFraudRing: true, properties: { vpn: true, isp: 'Datacenter' }, x: 550, y: 310 },
      { id: 'C09821', label: 'Linked Cust\nC09821', type: 'Account', isFraudRing: true, properties: { status: 'Closed Fraud' }, x: 835, y: 120 },
      { id: 'C04712', label: 'Linked Cust\nC04712', type: 'Account', isFraudRing: true, properties: { status: 'Chargeback' }, x: 845, y: 245 }
    ],
    graph_edges: [
      { id: 'e1', source: 'C12382', target: '3514030', label: 'INITIATED', type: 'OWNS' },
      { id: 'e2', source: 'C12382-K1', target: '3514030', label: 'PAYMENT_VIA', type: 'USES_CARD' },
      { id: 'e3', source: '3514030', target: 'c72bd41105eb39dd85c6622e779423fe', label: 'EXECUTED', type: 'ON_DEVICE', isSuspicious: true },
      { id: 'e4', source: '3514030', target: 'IP-198', label: 'ROUTED_THROUGH', type: 'FROM_IP', isSuspicious: true },
      { id: 'e5', source: 'IP-198', target: 'c72bd41105eb39dd85c6622e779423fe', label: 'ORIGIN_PAIR', type: 'LINKED_TO' },
      { id: 'e6', source: 'CC-1066', target: 'c72bd41105eb39dd85c6622e779423fe', label: 'PRIOR_SUBJECT', type: 'LINKED_TO', isSuspicious: true },
      { id: 'e7', source: 'c72bd41105eb39dd85c6622e779423fe', target: 'C09821', label: 'SHARED_HARDWARE', type: 'LINKED_TO', isSuspicious: true },
      { id: 'e8', source: 'c72bd41105eb39dd85c6622e779423fe', target: 'C04712', label: 'SHARED_HARDWARE', type: 'LINKED_TO', isSuspicious: true }
    ],
    execution_steps: [
      {
        id: 1,
        title: 'Transaction Flagged',
        subtitle: 'Risk score evaluated against baseline',
        status: 'complete',
        timestamp: '18:24:10.104',
        details: 'Transaction 3514030 flagged with 88% risk score for customer C12382 due to velocity and device deviation.',
        mcpCall: { tool: 'webhook_listener', latencyMs: 14, summary: 'Score 0.88 on 3514030' }
      },
      {
        id: 2,
        title: 'Network & Device Analysis',
        subtitle: 'Entity graph queried for linked accounts',
        status: 'complete',
        timestamp: '18:24:10.820',
        details: 'Hardware device c72bd41105eb39dd85c6622e779423fe linked to 7 distinct accounts and prior fraud case CC-1066.',
        mcpCall: { tool: 'tigergraph_mcp.find_connected_entities', latencyMs: 48, summary: 'Discovered shared device c72bd411... with 7 accounts' }
      },
      {
        id: 3,
        title: 'Initial Risk Evaluation',
        subtitle: 'Assessing evidence sufficiency',
        status: 'complete',
        timestamp: '18:24:11.205',
        details: 'High-risk device nexus detected. Initiating cardholder verification challenge.',
        outputSnippet: 'Initial assessment: Suspicious. Sending verification challenge.'
      },
      {
        id: 4,
        title: 'Customer Verification',
        subtitle: 'Step-up authentication requested from cardholder',
        status: 'complete',
        timestamp: '18:27:11.450',
        details: 'Verification challenge sent via SMS OTP to +1 (555) ***-9021. Result: FAILED — no response after 3 attempts.',
        outputSnippet: 'Challenge result: FAILED (Timeout, 3 attempts)'
      },
      {
        id: 5,
        title: 'Decision & Containment',
        subtitle: 'Confirmed unauthorized activity',
        status: 'complete',
        timestamp: '18:27:12.110',
        details: 'Cardholder failed verification. Coordinated ring activity confirmed. Card blocked and SAR report prepared.',
        outputSnippet: 'Action: BLOCK_CARD (Awaiting L2 Sign-off)'
      }
    ],
    sar_status: 'Pending',
  },
  {
    case_id: 'HHG-002',
    case_number: 2,
    transaction_id: '3514188',
    account_id: 'C08421',
    card_id: 'C08421-K1',
    card_network: 'mastercard',
    card_type: 'credit',
    amount_usd: 118.20,
    timestamp: '2016-11-14 14:02:18 UTC',
    initial_risk_score: 0.58,
    status: 'resolved_cleared',
    sar_status: 'Cleared',
    primary_pattern: 'Benign Velocity Spike',
    pre_evidence_uncertainty: 'MEDIUM',
    post_evidence_uncertainty: 'LOW',
    pre_evidence_nba: {
      action: 'STEP_UP_AUTH',
      action_id: 'ACT-AUTH-SMS',
      approval_tier: 'auto',
      approval_route: 'Automated Rule #12',
      rationale: 'Transaction velocity is 3.5x normal baseline. Step-up confirmation initiated.',
      alternatives_considered: ['BLOCK_CARD', 'MONITOR_CARD']
    },
    evidence_injected: {
      request_type: 'request_customer_validation',
      label: 'Step-up Authentication (SMS OTP)',
      status: 'PASSED',
      timestamp: '2016-11-14 14:02:45 UTC',
      response_payload: {
        method: 'SMS_OTP',
        result: 'PASSED — confirmed from known device',
        duration_seconds: 14
      }
    },
    post_evidence_nba: {
      action: 'ALLOW_TRANSACTION',
      action_id: 'ACT-ALLOW-CLEAR',
      approval_tier: 'auto',
      approval_route: 'Automated Rule #4',
      rationale: 'Cardholder confirmed purchase within 14 seconds via known device a839f1107ef4c89012a98124b489ef01. Cleared as false positive velocity spike.',
      alternatives_considered: ['MONITOR_CARD']
    },
    uncertainty_dimensions: {
      fraud_risk_signal: 2,
      graph_evidence: 0,
      behavioral_evidence: 2,
      policy_support: 1,
      contradictory_evidence: 3,
      calculated_score: 0.4,
      threshold: 2.5,
      status: 'CONTRADICTORY'
    },
    historical_counts: {
      prior_fraud_cases: 0,
      customers_on_device: 1,
      transactions_on_device: 1,
      devices_on_customer: 1,
      prior_cases_referenced: 'None'
    },
    evidence_pack: {
      trigger: {
        type: 'risk_score',
        risk_signal: 0.58,
        source: 'IEEE-CIS Velocity Monitor',
        timestamp: '2016-11-14 14:02:18 UTC'
      },
      transaction_context: {
        transaction_id: '3514188',
        amount_usd: 118.20,
        card_bin: '542418 (Mastercard)',
        product_cd: 'W',
        p_emaildomain: 'gmail.com',
        device_info: 'a839f1107ef4c89012a98124b489ef01',
        ip_address: '88.14.120.33',
        geo_location: 'Billing region 299.0',
        c_features_summary: 'C1=4 (Burst in 15m)',
        v_features_summary: 'V100=4, V101=118.20'
      },
      connected_entities: [
        { type: 'Device', id: 'a839f1107ef4c89012a98124b489ef01', linkage: 'Known trusted customer device (480 days)', historical_fraud: false },
        { type: 'Account', id: 'C08421', linkage: 'Customer profile with clean history', historical_fraud: false },
        { type: 'Card', id: 'C08421-K1', linkage: 'Primary credit card', historical_fraud: false }
      ],
      detected_patterns: [
        {
          pattern: 'SharedDeviceRing',
          strength: 'none',
          observations: ['1 customer, 1 device on transaction record; no shared device cluster']
        },
        {
          pattern: 'VelocityBurst',
          strength: 'moderate',
          observations: ['4 consecutive transactions within 15 minutes; holiday shopping surge']
        },
        {
          pattern: 'AmountAnomaly',
          strength: 'none',
          observations: ['$118.20 within historical 30-day spending envelope']
        },
        {
          pattern: 'NewDeviceWithProxy',
          strength: 'none',
          observations: ['Residential broadband egress IP; no proxy headers']
        }
      ],
      prior_cases: {
        note: 'Contextual support only',
        related: [],
        similar: []
      },
      policy_rules: [
        {
          rule_id: 'R4',
          title: 'Velocity-Only Signals',
          text: 'A velocity deviation with no corroborating graph or device evidence is advisory only and does not by itself authorize account-level action.',
          source: 'Card Risk Guidelines §3.1'
        },
        {
          rule_id: 'R9',
          title: 'Successful Step-Up Resolution',
          text: 'A passed step-up challenge from a previously known device resolves ordinary velocity anomalies without escalation.',
          source: 'Cardholder Authentication Standard §1.4'
        }
      ],
      missing_evidence: [],
      contradictions: ['Customer passed authentication immediately from trusted hardware']
    },
    sar: {
      narrative: 'On 2016-11-14, card C08421-K1 belonging to customer C08421 was flagged for an online purchase of $118.20 under product code W due to velocity variation against baseline. Graph analysis confirmed a single-account topology with no shared device linkages or proxy convergence. Dynamic step-up authentication challenge was dispatched and successfully completed by the verified cardholder within 14 seconds from trusted device a839f1107ef4c89012a98124b489ef01. The transaction was approved under ALLOW_TRANSACTION policy directive and normal monitoring was resumed.'
    },
    graph_nodes: [
      { id: 'C08421', label: 'Customer\nC08421', type: 'Account', properties: { status: 'Good Standing' }, x: 180, y: 160 },
      { id: 'C08421-K1', label: 'Mastercard\nC08421-K1', type: 'Card', properties: { brand: 'Mastercard' }, x: 180, y: 290 },
      { id: '3514188', label: 'TXN #3514188\n$118.20', type: 'Transaction', riskScore: 0.58, properties: { amount: '$118.20', status: 'Cleared' }, x: 440, y: 225 },
      { id: 'a839f1107ef4c89012a98124b489ef01', label: 'Device\na839f110... (known)', type: 'Device', properties: { model: 'iPhone 14', trusted_days: 480 }, x: 700, y: 160 },
      { id: 'IP-88-14', label: 'IP Address\n88.14.120.33', type: 'IP', properties: { isp: 'Residential Fiber' }, x: 700, y: 290 }
    ],
    graph_edges: [
      { id: 'e1', source: 'C08421', target: '3514188', label: 'OWNS', type: 'OWNS' },
      { id: 'e2', source: '3514188', target: 'C08421-K1', label: 'PAYMENT_VIA', type: 'USES_CARD' },
      { id: 'e3', source: '3514188', target: 'a839f1107ef4c89012a98124b489ef01', label: 'AUTHENTICATED_ON', type: 'ON_DEVICE' },
      { id: 'e4', source: '3514188', target: 'IP-88-14', label: 'HOME_NETWORK', type: 'FROM_IP' }
    ],
    execution_steps: [
      { id: 1, title: 'Transaction Flagged', subtitle: 'Velocity burst crosses threshold', status: 'complete', details: 'Transaction burst flagged. Risk score: 0.58.' },
      { id: 2, title: 'Network & Device Analysis', subtitle: 'Verified single known device & IP', status: 'complete', details: 'Zero shared devices or prior fraud linkage detected.' },
      { id: 3, title: 'Risk Evaluation', subtitle: 'Precautionary verification check', status: 'complete', details: 'Precautionary verification initiated.' },
      { id: 4, title: 'Customer Verification', subtitle: 'Customer verification passed', status: 'complete', details: 'Cardholder validated identity via OTP within 14 seconds.' },
      { id: 5, title: 'Decision & Clearance', subtitle: 'Case resolved as legitimate purchase', status: 'complete', details: 'Confirmed legitimate velocity spike. Resumed standard monitoring.' }
    ]
  },
  {
    case_id: 'HHG-003',
    case_number: 3,
    transaction_id: '3514299',
    account_id: 'C00377',
    card_id: 'C00377-K1',
    card_network: 'visa',
    card_type: 'credit',
    amount_usd: 268.43,
    timestamp: '2016-11-14 09:12:44 UTC',
    initial_risk_score: 0.94,
    status: 'under_investigation',
    sar_status: 'Pending',
    primary_pattern: 'CardTesting',
    pre_evidence_uncertainty: 'HIGH',
    post_evidence_uncertainty: 'LOW',
    pre_evidence_nba: {
      action: 'STEP_UP_AUTH',
      action_id: 'ACT-TEST-STEPUP',
      approval_tier: 'auto',
      approval_route: 'Automated Rule #12',
      rationale: 'Pre-auth micro-charges followed by high dollar online purchase. Step-up auth challenge dispatched.',
      alternatives_considered: ['BLOCK_CARD', 'MONITOR_CARD']
    },
    evidence_injected: {
      request_type: 'request_customer_validation',
      label: 'Cardholder Direct Contact Challenge',
      status: 'FAILED',
      timestamp: '2016-11-14 09:14:10 UTC',
      response_payload: {
        method: 'VOICE_CALL',
        result: 'FAILED — customer stated they did not authorize purchase',
        duration_seconds: 60
      }
    },
    post_evidence_nba: {
      action: 'BLOCK_CARD',
      action_id: 'ACT-BLOCK-CARDTEST',
      approval_tier: 'L2',
      approval_route: 'Requires Senior Analyst Sign-off',
      rationale: 'Customer stated they did not authorize purchase. Card testing sequence confirmed on device c72bd41105eb39dd85c6622e779423fe.',
      alternatives_considered: ['MONITOR_CARD']
    },
    uncertainty_dimensions: {
      fraud_risk_signal: 3,
      graph_evidence: 3,
      behavioral_evidence: 2,
      policy_support: 3,
      contradictory_evidence: 0,
      calculated_score: 3.0,
      threshold: 2.5,
      status: 'SUFFICIENT'
    },
    historical_counts: {
      prior_fraud_cases: 2,
      customers_on_device: 3,
      transactions_on_device: 8,
      devices_on_customer: 2,
      prior_cases_referenced: 'CC-0141, CC-0877'
    },
    evidence_pack: {
      trigger: {
        type: 'risk_score',
        risk_signal: 0.94,
        source: 'IEEE-CIS Micro-Charge Bot Detector',
        timestamp: '2016-11-14 09:12:44 UTC'
      },
      transaction_context: {
        transaction_id: '3514299',
        amount_usd: 268.43,
        card_bin: '400000 (Visa Classic)',
        product_cd: 'W',
        p_emaildomain: 'temp-mail.org',
        device_info: 'c72bd41105eb39dd85c6622e779423fe',
        ip_address: '203.0.113.19',
        geo_location: 'Billing region 444.0',
        c_features_summary: 'C1=18 (Rapid enumeration probes)',
        v_features_summary: 'V310=268.43'
      },
      connected_entities: [
        { type: 'Device', id: 'c72bd41105eb39dd85c6622e779423fe', linkage: 'Device previously recorded on CC-0141', historical_fraud: true },
        { type: 'Account', id: 'C00377', linkage: 'Target victim customer', historical_fraud: false },
        { type: 'Card', id: 'C00377-K1', linkage: 'Compromised card credential', historical_fraud: false }
      ],
      detected_patterns: [
        {
          pattern: 'SharedDeviceRing',
          strength: 'moderate',
          observations: ['Device shared with previously closed fraud case CC-0141']
        },
        {
          pattern: 'VelocityBurst',
          strength: 'moderate',
          observations: ['Three rapid authorizations followed by $259.98 purchase in under 3 minutes']
        },
        {
          pattern: 'AmountAnomaly',
          strength: 'strong',
          observations: ['Sequence of $1.10, $2.40, $0.95 followed by sudden $259.98 anomaly']
        },
        {
          pattern: 'NewDeviceWithProxy',
          strength: 'none',
          observations: ['Direct connection; no anonymous proxy detected']
        }
      ],
      prior_cases: {
        note: 'Contextual support only',
        related: [
          { case_id: 'CC-0141', shared_entity: 'c72bd41105eb39dd85c6622e779423fe', outcome: 'Confirmed BIN Attack ($1.2k Loss)' }
        ],
        similar: []
      },
      policy_rules: [
        {
          rule_id: 'R2',
          title: 'Card Testing Typology',
          text: 'Rapid low-value authorizations against a device previously linked to confirmed fraud are treated as directive evidence under the Card Testing typology.',
          source: 'Card Security Directive §1.1'
        },
        {
          rule_id: 'R21',
          title: 'SAR Filing Threshold',
          text: 'Confirmed card testing fraud exceeding the reporting threshold requires a Suspicious Activity Report within the regulatory filing window.',
          source: 'FinCEN BSA 31 CFR § 1020.320'
        }
      ],
      missing_evidence: [],
      contradictions: []
    },
    sar: {
      narrative: 'On 2016-11-14, card C00377-K1 belonging to customer C00377 was used for three online authorizations of $1.10, $2.40, and $0.95 followed by a $259.98 online purchase under a product code the cardholder had never used. All four transactions came from device c72bd41105eb39dd85c6622e779423fe marked New for this account, previously recorded on closed case CC-0141 and on card C00877-K1 on 2016-11-12. The cardholder, contacted the same day, stated they did not make these purchases and remained in possession of the card. The sequence of small authorizations followed by a larger purchase is consistent with testing of a stolen card number. Total unauthorized amount: $268.43.'
    },
    graph_nodes: [
      { id: 'C00377', label: 'Customer\nC00377', type: 'Account', properties: { status: 'Victim' }, x: 180, y: 150 },
      { id: 'C00377-K1', label: 'Card\nC00377-K1', type: 'Card', properties: { bin: '400000', attempts: 4 }, x: 180, y: 280 },
      { id: '3514299', label: 'TXN #3514299\n$268.43', type: 'Transaction', riskScore: 0.94, isFraudRing: true, properties: { amount: '$268.43', status: 'Blocked' }, x: 420, y: 220 },
      { id: 'c72bd41105eb39dd85c6622e779423fe', label: 'Device\nc72bd411...', type: 'Device', isFraudRing: true, properties: { model: 'Known Fraud Device' }, x: 670, y: 150 },
      { id: 'CC-0141', label: 'Prior Case\nCC-0141', type: 'PriorCase', isFraudRing: true, properties: { outcome: 'Confirmed BIN Attack' }, x: 670, y: 290 }
    ],
    graph_edges: [
      { id: 'e1', source: 'C00377', target: '3514299', label: 'OWNS', type: 'OWNS' },
      { id: 'e2', source: '3514299', target: 'C00377-K1', label: 'PAYMENT_VIA', type: 'USES_CARD' },
      { id: 'e3', source: '3514299', target: 'c72bd41105eb39dd85c6622e779423fe', label: 'EXECUTED_ON', type: 'ON_DEVICE', isSuspicious: true },
      { id: 'e4', source: 'c72bd41105eb39dd85c6622e779423fe', target: 'CC-0141', label: 'LINKED_TO', type: 'LINKED_TO', isSuspicious: true }
    ],
    execution_steps: [
      { id: 1, title: 'Transaction Flagged', subtitle: 'Micro-charge pattern identified', status: 'complete', details: 'Micro-charge probe followed by $259.98 flagged. Risk score 0.94.' },
      { id: 2, title: 'Network & Device Analysis', subtitle: 'Card testing pattern detected', status: 'complete', details: 'Device c72bd41105eb39dd85c6622e779423fe linked to closed fraud case CC-0141.' },
      { id: 3, title: 'Risk Evaluation', subtitle: 'Cardholder verification required', status: 'complete', details: 'High probability of stolen credentials. Contacting cardholder.' },
      { id: 4, title: 'Customer Verification', subtitle: 'Customer confirmed unauthorized usage', status: 'complete', details: 'Cardholder confirmed physical card in possession; did not authorize purchase.' },
      { id: 5, title: 'Decision & Containment', subtitle: 'Card blocked and SAR report prepared', status: 'complete', details: 'Confirmed stolen card number. BLOCK_CARD executed and SAR prepared.' }
    ]
  },
  ...generateRemainingBenchmarkCases()
];

function generateRemainingBenchmarkCases(): BenchmarkCase[] {
  const typologies = [
    { pattern: 'EmailDomainCluster', name: 'Disposable Domain Syndicate', risk: 0.81, amount: 640.00, status: 'requires_approval' as const },
    { pattern: 'GeoMismatch', name: 'Impossible Velocity Travel Mismatch', risk: 0.77, amount: 1250.00, status: 'under_investigation' as const },
    { pattern: 'AmountAnomaly', name: 'High-Value Outlier Surge', risk: 0.85, amount: 4890.00, status: 'requires_approval' as const },
    { pattern: 'SharedDeviceRing', name: 'Emulated Device ID Farm', risk: 0.91, amount: 720.00, status: 'resolved_fraud' as const },
    { pattern: 'VelocityBurst', name: 'Rapid Re-order Sequence', risk: 0.45, amount: 110.00, status: 'resolved_cleared' as const },
    { pattern: 'CardTesting', name: 'Batch Pre-auth Micro-charges', risk: 0.93, amount: 0.99, status: 'resolved_fraud' as const },
    { pattern: 'EmailDomainCluster', name: 'Temporary Mailbox Spurt', risk: 0.69, amount: 340.00, status: 'under_investigation' as const },
    { pattern: 'GeoMismatch', name: 'Cross-Continent IP vs Billing Jump', risk: 0.83, amount: 1890.00, status: 'requires_approval' as const },
    { pattern: 'SharedDeviceRing', name: 'Multi-identity Mobile Nexus', risk: 0.87, amount: 940.00, status: 'resolved_fraud' as const },
    { pattern: 'VelocityBurst', name: 'Legitimate Salary Payday Surge', risk: 0.38, amount: 450.00, status: 'resolved_cleared' as const },
    { pattern: 'AmountAnomaly', name: 'Luxury Goods Sudden Purchase', risk: 0.79, amount: 3200.00, status: 'under_investigation' as const },
    { pattern: 'CardTesting', name: 'Algorithmic Expiry Date Probe', risk: 0.92, amount: 2.10, status: 'resolved_fraud' as const },
    { pattern: 'SharedDeviceRing', name: 'Mule Ring Reselling Electronics', risk: 0.89, amount: 1450.00, status: 'requires_approval' as const },
    { pattern: 'EmailDomainCluster', name: 'Coordinated Mailbox Generator', risk: 0.74, amount: 510.00, status: 'under_investigation' as const },
    { pattern: 'GeoMismatch', name: 'Simultaneous Physical POS & Web Txn', risk: 0.86, amount: 980.00, status: 'resolved_fraud' as const },
    { pattern: 'VelocityBurst', name: 'Authorized Corporate Purchasing', risk: 0.41, amount: 2300.00, status: 'resolved_cleared' as const },
    { pattern: 'AmountAnomaly', name: 'First-time International Wire Draft', risk: 0.82, amount: 5600.00, status: 'requires_approval' as const }
  ];

  const channelCodes = ['W', 'C', 'H', 'R', 'S'];

  return typologies.map((t, idx) => {
    const caseNum = idx + 4;
    const caseId = `HHG-${caseNum.toString().padStart(3, '0')}`;
    const txnId = `${3514000 + caseNum * 23}`;
    const custId = `C${10000 + caseNum * 137}`;
    const cardId = `${custId}-K1`;
    const deviceHash = `d${(caseNum * 8371923).toString(16).padEnd(31, 'f')}`;
    const region = `Billing region ${(150 + caseNum * 17) % 500}.0`;
    const channel = channelCodes[caseNum % channelCodes.length];
    const isFraud = t.status === 'resolved_fraud' || t.status === 'requires_approval';

    return {
      case_id: caseId,
      case_number: caseNum,
      transaction_id: txnId,
      account_id: custId,
      card_id: cardId,
      card_network: caseNum % 2 === 0 ? 'visa' : 'mastercard',
      card_type: caseNum % 3 === 0 ? 'debit' : 'credit',
      amount_usd: t.amount,
      timestamp: `2016-11-${(10 + caseNum % 18).toString().padStart(2, '0')} ${(1 + caseNum % 22).toString().padStart(2, '0')}:${(caseNum * 7 % 60).toString().padStart(2, '0')} UTC`,
      initial_risk_score: t.risk,
      status: t.status,
      primary_pattern: t.name,
      pre_evidence_uncertainty: isFraud ? 'MEDIUM' : 'HIGH',
      post_evidence_uncertainty: isFraud ? 'LOW' : 'LOW',
      pre_evidence_nba: {
        action: isFraud ? 'VERIFY_WITH_CUSTOMER' : 'STEP_UP_AUTH',
        action_id: `ACT-PRE-${caseNum}`,
        approval_tier: 'auto',
        approval_route: 'Automated Rule #12',
        rationale: `Pattern ${t.pattern} flagged. Pre-emptive verification challenge initiated.`,
        alternatives_considered: ['BLOCK_CARD', 'MONITOR_CARD']
      },
      evidence_injected: {
        request_type: isFraud ? 'request_step_up_auth' : 'request_customer_validation',
        label: 'Step-up Authentication (SMS OTP)',
        status: isFraud ? 'FAILED' : 'PASSED',
        timestamp: `2016-11-14 18:26 UTC`,
        response_payload: isFraud ? { result: 'FAILED — timeout / no response' } : { result: 'PASSED — confirmed from known device' }
      },
      post_evidence_nba: {
        action: isFraud ? 'BLOCK_CARD' : 'ALLOW_TRANSACTION',
        action_id: `ACT-POST-${caseNum}`,
        approval_tier: isFraud ? 'L2' : 'auto',
        approval_route: isFraud ? 'Requires Senior Analyst Sign-off' : 'Automated Rule #4',
        rationale: isFraud ? `Confirmed pattern ${t.pattern} with failed secondary verification.` : 'Customer confirmed valid transaction intent.',
        alternatives_considered: ['MONITOR_CARD']
      },
      uncertainty_dimensions: {
        fraud_risk_signal: t.risk > 0.8 ? 3 : 2,
        graph_evidence: isFraud ? 2 : 1,
        behavioral_evidence: 2,
        policy_support: isFraud ? 3 : 1,
        contradictory_evidence: isFraud ? 0 : 3,
        calculated_score: isFraud ? 2.7 : 0.6,
        threshold: 2.5,
        status: isFraud ? 'SUFFICIENT' : 'CONTRADICTORY'
      },
      historical_counts: {
        prior_fraud_cases: isFraud ? 2 : 0,
        customers_on_device: isFraud ? 5 : 1,
        transactions_on_device: isFraud ? 11 : 1,
        devices_on_customer: 1,
        prior_cases_referenced: isFraud ? `CC-00${caseNum + 10}, CC-00${caseNum + 20}` : 'None'
      },
      evidence_pack: {
        trigger: {
          type: 'risk_score',
          risk_signal: t.risk,
          source: 'IEEE-CIS Pipeline',
          timestamp: `2016-11-14 14:00:${caseNum} UTC`
        },
        transaction_context: {
          transaction_id: txnId,
          amount_usd: t.amount,
          card_bin: '411111',
          product_cd: channel,
          p_emaildomain: 'domain-mail.com',
          device_info: deviceHash,
          ip_address: `198.51.100.${caseNum * 7 % 250}`,
          geo_location: region,
          c_features_summary: `C1=${caseNum}`,
          v_features_summary: `V200=1`
        },
        connected_entities: [
          { type: 'Account', id: custId, linkage: 'Customer Account Node', historical_fraud: isFraud },
          { type: 'Card', id: cardId, linkage: 'Active payment token', historical_fraud: false },
          { type: 'Device', id: deviceHash, linkage: 'Primary transaction device', historical_fraud: isFraud }
        ],
        detected_patterns: [
          {
            pattern: 'SharedDeviceRing',
            strength: isFraud && t.pattern === 'SharedDeviceRing' ? 'strong' : 'none',
            observations: isFraud && t.pattern === 'SharedDeviceRing' 
              ? [`Detected signature for ${t.name}`, `Anomaly score ${t.risk}`]
              : ['1 customer, 1 device on transaction record; no shared device cluster']
          },
          {
            pattern: 'VelocityBurst',
            strength: t.pattern === 'VelocityBurst' ? (isFraud ? 'strong' : 'moderate') : 'none',
            observations: t.pattern === 'VelocityBurst'
              ? [`Burst frequency detected for ${cardId}`, `Anomaly score ${t.risk}`]
              : ['1 txn in 1h, 6 in 24h on card within expected velocity envelope']
          },
          {
            pattern: 'AmountAnomaly',
            strength: t.pattern === 'AmountAnomaly' ? 'strong' : 'none',
            observations: t.pattern === 'AmountAnomaly'
              ? [`$${t.amount.toFixed(2)} exceeds 99th percentile baseline`]
              : [`$${t.amount.toFixed(2)} aligned with account historical baseline`]
          },
          {
            pattern: 'NewDeviceWithProxy',
            strength: isFraud ? 'moderate' : 'none',
            observations: isFraud
              ? [`Egress proxy detected on IP 198.51.100.${caseNum * 7 % 250}`]
              : ['Residential egress IP; no proxy or VPN headers identified']
          }
        ],
        prior_cases: {
          note: 'Contextual support only',
          related: isFraud ? [
            { case_id: `CC-00${caseNum + 10}`, shared_entity: deviceHash, outcome: 'Confirmed Fraud ($1.5k Loss)' }
          ] : [],
          similar: []
        },
        policy_rules: [
          {
            rule_id: 'R7',
            title: 'Shared-Device Fraud Rings',
            text: 'Where three or more accounts share a device fingerprint within a rolling 7-day window and any linked account has a prior confirmed fraud outcome, the case is treated as directive evidence of a coordinated ring.',
            source: 'Institutional Policy v5'
          }
        ],
        missing_evidence: [],
        contradictions: isFraud ? [] : ['Cardholder confirmed intent']
      },
      sar: {
        narrative: isFraud
          ? `On 2016-11-14, card ${cardId} belonging to customer ${custId} was used for an online authorization of $${t.amount.toFixed(2)} under product code ${channel}. The transaction originated from hardware device ${deviceHash} in ${region}, which converged with distinct customer accounts in a rolling window. Dynamic step-up SMS OTP challenge was dispatched but timed out with zero cardholder response. In accordance with Rule R7, card ${cardId} was placed on BLOCK_CARD status, customer account ${custId} frozen, and this SAR filed for total unauthorized amount of $${t.amount.toFixed(2)}.`
          : `On 2016-11-14, card ${cardId} belonging to customer ${custId} was flagged for an online purchase of $${t.amount.toFixed(2)} under product code ${channel} due to velocity variation against baseline. Graph analysis confirmed a single-account topology with no shared device linkages or proxy convergence. Dynamic step-up authentication challenge was dispatched and successfully completed by the verified cardholder within 14 seconds from trusted device ${deviceHash}. The transaction was approved under ALLOW_TRANSACTION policy directive and normal monitoring was resumed.`
      },
      graph_nodes: [
        { id: txnId, label: `TXN #${txnId}\n$${t.amount.toFixed(2)}`, type: 'Transaction' as const, riskScore: t.risk, isFraudRing: isFraud, properties: { amount: `$${t.amount.toFixed(2)}` }, x: 380, y: 220 },
        { id: custId, label: `Customer\n${custId}`, type: 'Account' as const, properties: { status: 'Active' }, x: 230, y: 170 },
        { id: cardId, label: `Card\n${cardId}`, type: 'Card' as const, properties: { brand: 'Visa' }, x: 220, y: 290 },
        { id: deviceHash, label: `Device\n${deviceHash.slice(0, 8)}...`, type: 'Device' as const, isFraudRing: isFraud, properties: { model: 'Browser' }, x: 530, y: 180 },
        { id: `IP-${caseNum}`, label: `IP Address\n198.51.100.${caseNum}`, type: 'IP' as const, isFraudRing: isFraud, properties: { risk: isFraud ? 'High' : 'Low' }, x: 530, y: 300 }
      ] as GraphNode[],
      graph_edges: [
        { id: `e1-${caseNum}`, source: custId, target: txnId, label: 'OWNS', type: 'OWNS' },
        { id: `e2-${caseNum}`, source: txnId, target: cardId, label: 'PAYMENT_VIA', type: 'USES_CARD' },
        { id: `e3-${caseNum}`, source: txnId, target: deviceHash, label: 'ON_DEVICE', type: 'ON_DEVICE', isSuspicious: isFraud },
        { id: `e4-${caseNum}`, source: txnId, target: `IP-${caseNum}`, label: 'FROM_IP', type: 'FROM_IP', isSuspicious: isFraud }
      ],
      execution_steps: [
        { id: 1, title: 'Transaction Flagged', subtitle: `Risk score ${(t.risk * 100).toFixed(0)}% evaluated`, status: 'complete', details: `Transaction ${txnId} flagged for review.` },
        { id: 2, title: 'Network & Device Analysis', subtitle: 'Checking linked accounts and devices', status: 'complete', details: isFraud ? `Device linked to multiple accounts with prior fraud records.` : `Single customer account on known personal device.` },
        { id: 3, title: 'Risk Evaluation', subtitle: 'Assessing transaction risk factors', status: 'complete', details: isFraud ? 'Multiple risk factors identified; customer verification required.' : 'Low risk profile; verifying transaction with cardholder.' },
        { id: 4, title: 'Customer Verification', subtitle: 'Two-factor authentication challenge', status: 'complete', details: isFraud ? 'Verification challenge timed out with no response.' : 'Cardholder successfully verified transaction.' },
        { id: 5, title: isFraud ? 'Decision & Containment' : 'Decision & Clearance', subtitle: isFraud ? 'Card blocked and SAR report prepared' : 'Transaction cleared and approved', status: 'complete', details: isFraud ? 'Confirmed fraud. Card blocked and SAR report prepared.' : 'Verified legitimate. Transaction hold released.' }
      ],
      sar_status: isFraud ? 'Pending' : 'Cleared'
    };
  });
}
