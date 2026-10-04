import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertCircle,
  CheckCircle2,
  Download,
  Play,
  Activity,
  Check
} from 'lucide-react';
import type { BenchmarkCase } from '../../types/investigation';
import { downloadSarPdf } from '../../utils/sarBuilder';

interface NbaProgressionCardProps {
  currentCase?: BenchmarkCase | null;
  isInvestigating?: boolean;
  onRunInvestigation?: () => void;
}

export const NbaProgressionCard: React.FC<NbaProgressionCardProps> = ({
  currentCase,
  isInvestigating = false,
  onRunInvestigation,
}) => {
  const [completedActions, setCompletedActions] = useState<Record<number, boolean>>({});

  // Reset checklist when switching cases
  useEffect(() => {
    setCompletedActions({});
  }, [currentCase?.case_id]);

  if (!currentCase) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 select-none">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[12px] font-semibold text-slate-700 flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-slate-400" />
            <span>Incident Review</span>
          </div>
          <span className="px-2 py-0.5 rounded text-[11px] text-slate-400 bg-slate-100">
            No Case Selected
          </span>
        </div>
        <p className="text-[12px] text-slate-400 leading-relaxed">
          Select a case from the left panel to view transaction analysis and recommended next steps.
        </p>
      </div>
    );
  }

  const isResolved = currentCase.status.startsWith('resolved') || currentCase.status === 'requires_approval';
  const isFraud = currentCase.initial_risk_score >= 0.75 || currentCase.graph_nodes.some(n => n.isFraudRing);
  const cardLast4 = currentCase.card_id.slice(-4) || '9021';

  const toggleAction = (stepIndex: number) => {
    setCompletedActions(prev => ({
      ...prev,
      [stepIndex]: !prev[stepIndex],
    }));
  };

  const handleMarkAllComplete = () => {
    const totalSteps = isFraud ? 4 : 3;
    const allDone: Record<number, boolean> = {};
    for (let i = 1; i <= totalSteps; i++) {
      allDone[i] = true;
    }
    setCompletedActions(allDone);
  };

  // Human, operational narrative describing what occurred
  const getSummary = () => {
    if (!isResolved) {
      return `Transaction of $${currentCase.amount_usd.toFixed(2)} on card ${currentCase.card_id} was flagged for review. Review the details and complete the steps below.`;
    }
    if (isFraud) {
      return `A payment of $${currentCase.amount_usd.toFixed(2)} was attempted on card ${currentCase.card_id}. The transaction came from a device tied to multiple accounts previously flagged for fraud. A two-factor authentication challenge timed out with no response.`;
    }
    return `A payment of $${currentCase.amount_usd.toFixed(2)} was held following a velocity alert. A two-factor authentication code was sent to the cardholder, who successfully confirmed the purchase within 14 seconds from their personal device.`;
  };

  const totalActions = isResolved ? (isFraud ? 4 : 3) : 2;
  const completedCount = Object.values(completedActions).filter(Boolean).length;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 select-none space-y-4 text-slate-800">
      {/* Top Header: Title & Dynamic Verdict */}
      <div className="flex items-center justify-between pb-1 border-b border-slate-100">
        <div className="flex items-center gap-2">
          {isInvestigating ? (
            <Activity className="w-4 h-4 text-indigo-600 animate-spin shrink-0" />
          ) : isResolved ? (
            isFraud ? (
              <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
            ) : (
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            )
          ) : (
            <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
          )}
          <span className="text-[13px] font-semibold text-slate-900">
            Incident Review
          </span>
        </div>

        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1 ${
          isInvestigating
            ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
            : isResolved
            ? isFraud
              ? 'bg-rose-50 text-rose-700 border border-rose-200'
              : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
            : 'bg-amber-50 text-amber-700 border border-amber-200'
        }`}>
          {isInvestigating
            ? 'Investigating...'
            : isResolved
            ? isFraud
              ? 'Confirmed Fraud'
              : 'Verified Legitimate'
            : 'Pending Hold (30m)'}
        </span>
      </div>

      {/* Section 1: What Happened */}
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
          What Happened
        </div>
        <p className="text-[12px] text-slate-700 leading-relaxed bg-slate-50 rounded-lg p-2.5 border border-slate-100">
          {getSummary()}
        </p>

        {/* Identity Verification Sub-row */}
        <div className="mt-2 flex items-center justify-between px-1 text-[11.5px]">
          <span className="text-slate-500 font-medium">Customer Verification:</span>
          <span className={`font-semibold flex items-center gap-1 ${
            isInvestigating
              ? 'text-indigo-600'
              : isResolved
              ? isFraud
                ? 'text-rose-600'
                : 'text-emerald-600'
              : 'text-amber-600'
          }`}>
            {isInvestigating ? (
              <>
                <Activity className="w-3.5 h-3.5 animate-spin" />
                <span>Checking SMS response...</span>
              </>
            ) : isResolved ? (
              isFraud ? (
                <>
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span>Failed (No response)</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Confirmed by cardholder</span>
                </>
              )
            ) : (
              <>
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Awaiting challenge verification</span>
              </>
            )}
          </span>
        </div>
      </div>

      {/* Section 2: Action Plan & Operator Checklist */}
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center justify-between">
          <span>{isResolved ? (isFraud ? 'Containment Checklist' : 'Clearance Steps') : 'Investigation Steps'}</span>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-500 font-normal">
              {completedCount} of {totalActions} done
            </span>
            {isResolved && completedCount < totalActions && (
              <button
                type="button"
                onClick={handleMarkAllComplete}
                className="text-[10px] text-indigo-600 hover:text-indigo-700 font-semibold cursor-pointer underline"
              >
                Complete All
              </button>
            )}
          </div>
        </div>

        {!isResolved ? (
          /* PRE-INVESTIGATION STEPS */
          <div className="space-y-2">
            <div 
              onClick={() => toggleAction(1)}
              className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-start gap-2.5 ${
                completedActions[1] ? 'bg-slate-50 border-slate-300 opacity-80' : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5 transition-colors ${
                completedActions[1] ? 'bg-emerald-600 text-white' : 'bg-amber-100 text-amber-800'
              }`}>
                {completedActions[1] ? <Check className="w-3 h-3 stroke-[3]" /> : '1'}
              </div>
              <div className="min-w-0 flex-1">
                <div className={`text-[12px] font-semibold ${completedActions[1] ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                  Temporary 30-Minute Hold Active
                </div>
                <div className="text-[11.5px] text-slate-500 mt-0.5 leading-snug">
                  Transaction held by risk rule pending verification check.
                </div>
              </div>
            </div>

            <div className="p-2.5 rounded-lg border border-indigo-200 bg-indigo-50/50 flex flex-col gap-2">
              <div className="flex items-start gap-2.5">
                <div className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5">
                  2
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] font-semibold text-slate-900">
                    Run Investigation
                  </div>
                  <div className="text-[11.5px] text-slate-600 mt-0.5 leading-snug">
                    Check transaction graph, prior records, and customer verification.
                  </div>
                </div>
              </div>

              {onRunInvestigation && (
                <button
                  type="button"
                  onClick={() => onRunInvestigation()}
                  disabled={isInvestigating}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {isInvestigating ? (
                    <>
                      <Activity className="w-3.5 h-3.5 animate-spin" />
                      <span>Investigating Case...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 fill-current" />
                      <span>Run Investigation</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        ) : isFraud ? (
          /* FRAUD ACTION CHECKLIST (INTERACTIVE) */
          <div className="space-y-2">
            <div 
              onClick={() => toggleAction(1)}
              className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-start gap-2.5 ${
                completedActions[1] ? 'bg-slate-50 border-slate-300 opacity-80' : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5 transition-colors ${
                completedActions[1] ? 'bg-emerald-600 text-white' : 'bg-rose-100 text-rose-700'
              }`}>
                {completedActions[1] ? <Check className="w-3 h-3 stroke-[3]" /> : '1'}
              </div>
              <div className="min-w-0 flex-1">
                <div className={`text-[12px] font-semibold ${completedActions[1] ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                  Block Card (*{cardLast4})
                </div>
                <div className="text-[11.5px] text-slate-500 mt-0.5 leading-snug">
                  Permanently disable card to prevent further unauthorized charges.
                </div>
              </div>
            </div>

            <div 
              onClick={() => toggleAction(2)}
              className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-start gap-2.5 ${
                completedActions[2] ? 'bg-slate-50 border-slate-300 opacity-80' : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5 transition-colors ${
                completedActions[2] ? 'bg-emerald-600 text-white' : 'bg-rose-100 text-rose-700'
              }`}>
                {completedActions[2] ? <Check className="w-3 h-3 stroke-[3]" /> : '2'}
              </div>
              <div className="min-w-0 flex-1">
                <div className={`text-[12px] font-semibold ${completedActions[2] ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                  Freeze Account ({currentCase.account_id})
                </div>
                <div className="text-[11.5px] text-slate-500 mt-0.5 leading-snug">
                  Restrict online access and block suspicious device fingerprint.
                </div>
              </div>
            </div>

            <div 
              onClick={() => toggleAction(3)}
              className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-start gap-2.5 ${
                completedActions[3] ? 'bg-slate-50 border-slate-300 opacity-80' : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5 transition-colors ${
                completedActions[3] ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-700'
              }`}>
                {completedActions[3] ? <Check className="w-3 h-3 stroke-[3]" /> : '3'}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1">
                  <div className={`text-[12px] font-semibold ${completedActions[3] ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                    File SAR Report
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      downloadSarPdf(currentCase, true);
                      toggleAction(3);
                    }}
                    className="text-[10.5px] font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 cursor-pointer bg-indigo-50 hover:bg-indigo-100 px-2 py-0.5 rounded transition-colors shrink-0"
                    title="Download SAR PDF report"
                  >
                    <Download className="w-3 h-3" />
                    <span>Download SAR</span>
                  </button>
                </div>
                <div className="text-[11.5px] text-slate-500 mt-0.5 leading-snug">
                  Submit regulatory report for unauthorized transaction activity.
                </div>
              </div>
            </div>

            <div 
              onClick={() => toggleAction(4)}
              className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-start gap-2.5 ${
                completedActions[4] ? 'bg-slate-50 border-slate-300 opacity-80' : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5 transition-colors ${
                completedActions[4] ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-700'
              }`}>
                {completedActions[4] ? <Check className="w-3 h-3 stroke-[3]" /> : '4'}
              </div>
              <div className="min-w-0 flex-1">
                <div className={`text-[12px] font-semibold ${completedActions[4] ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                  Notify Account Owner
                </div>
                <div className="text-[11.5px] text-slate-500 mt-0.5 leading-snug">
                  Alert cardholder of compromised credentials and reissue card.
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* BENIGN CLEARANCE CHECKLIST (INTERACTIVE) */
          <div className="space-y-2">
            <div 
              onClick={() => toggleAction(1)}
              className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-start gap-2.5 ${
                completedActions[1] ? 'bg-slate-50 border-slate-300 opacity-80' : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5 transition-colors ${
                completedActions[1] ? 'bg-emerald-600 text-white' : 'bg-emerald-100 text-emerald-700'
              }`}>
                {completedActions[1] ? <Check className="w-3 h-3 stroke-[3]" /> : '1'}
              </div>
              <div className="min-w-0 flex-1">
                <div className={`text-[12px] font-semibold ${completedActions[1] ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                  Release Transaction Hold
                </div>
                <div className="text-[11.5px] text-slate-500 mt-0.5 leading-snug">
                  Authorize payment of ${currentCase.amount_usd.toFixed(2)} and allow settlement.
                </div>
              </div>
            </div>

            <div 
              onClick={() => toggleAction(2)}
              className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-start gap-2.5 ${
                completedActions[2] ? 'bg-slate-50 border-slate-300 opacity-80' : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5 transition-colors ${
                completedActions[2] ? 'bg-emerald-600 text-white' : 'bg-emerald-100 text-emerald-700'
              }`}>
                {completedActions[2] ? <Check className="w-3 h-3 stroke-[3]" /> : '2'}
              </div>
              <div className="min-w-0 flex-1">
                <div className={`text-[12px] font-semibold ${completedActions[2] ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                  Keep Account Active
                </div>
                <div className="text-[11.5px] text-slate-500 mt-0.5 leading-snug">
                  No account restrictions required; customer status remains in good standing.
                </div>
              </div>
            </div>

            <div 
              onClick={() => toggleAction(3)}
              className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-start gap-2.5 ${
                completedActions[3] ? 'bg-slate-50 border-slate-300 opacity-80' : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5 transition-colors ${
                completedActions[3] ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-700'
              }`}>
                {completedActions[3] ? <Check className="w-3 h-3 stroke-[3]" /> : '3'}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1">
                  <div className={`text-[12px] font-semibold ${completedActions[3] ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                    Clearance Record
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      downloadSarPdf(currentCase, true);
                      toggleAction(3);
                    }}
                    className="text-[10.5px] font-semibold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 cursor-pointer bg-emerald-50 hover:bg-emerald-100 px-2 py-0.5 rounded transition-colors shrink-0"
                    title="Download Clearance Memo PDF"
                  >
                    <Download className="w-3 h-3" />
                    <span>Clearance PDF</span>
                  </button>
                </div>
                <div className="text-[11.5px] text-slate-500 mt-0.5 leading-snug">
                  Add verified phone to trusted device profile to reduce future friction.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Audit Trail Footer */}
      <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11.5px] text-slate-500">
        <span className="font-medium text-slate-700">Case {currentCase.case_number || 2}</span>
        <span className="font-mono text-slate-400 text-[11px]">{currentCase.case_id}</span>
      </div>
    </div>
  );
};
