import React from 'react';
import { 
  FileText, 
  Download,
  CheckCircle2,
  AlertTriangle,
  Clock
} from 'lucide-react';
import type { BenchmarkCase } from '../../types/investigation';
import { downloadSarPdf } from '../../utils/sarBuilder';

interface SarGeneratorProps {
  caseItem?: BenchmarkCase | null;
  sarStatus?: 'Pending' | 'Cleared';
  onStatusChange?: (status: 'Pending' | 'Cleared') => void;
  compact?: boolean;
}

export const SarGenerator: React.FC<SarGeneratorProps> = ({ 
  caseItem, 
  sarStatus = 'Pending',
  compact = false,
}) => {
  if (!caseItem) {
    if (compact) {
      return (
        <div className="pt-3 border-t border-slate-200 space-y-2">
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span className="font-semibold uppercase tracking-wider">Regulatory Filing</span>
            <span>Standby</span>
          </div>
          <p className="text-[11.5px] text-slate-400 leading-snug">
            Select a case to prepare SAR report exports.
          </p>
        </div>
      );
    }
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 select-none">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[12px] font-semibold text-slate-700 flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-slate-400" />
            <span>Regulatory Filing</span>
          </div>
          <span className="px-2 py-0.5 rounded text-[11px] text-slate-400 bg-slate-100">
            No Case Selected
          </span>
        </div>
        <p className="text-[12px] text-slate-400 leading-relaxed">
          Select a case to prepare regulatory SAR documentation and compliance records.
        </p>
      </div>
    );
  }

  const isResolved = sarStatus === 'Cleared' || caseItem.status.startsWith('resolved') || caseItem.status === 'requires_approval';
  const isFraud = caseItem.initial_risk_score >= 0.75 || caseItem.graph_nodes.some(n => n.isFraudRing);

  // Compact layout: integrated under Case Details in the left panel
  if (compact) {
    return (
      <div className="pt-3 border-t border-slate-200 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
            <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-mono">
              Regulatory Filing
            </span>
          </div>

          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold flex items-center gap-1 border ${
            isResolved 
              ? (isFraud ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200')
              : 'bg-amber-50 text-amber-700 border-amber-200'
          }`}>
            {isResolved ? (
              isFraud ? <AlertTriangle className="w-3 h-3 text-rose-600" /> : <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            ) : (
              <Clock className="w-3 h-3 text-amber-600" />
            )}
            <span>
              {isResolved 
                ? (isFraud ? 'SAR Required' : 'Cleared') 
                : 'Under Review'}
            </span>
          </span>
        </div>

        <button
          type="button"
          onClick={() => downloadSarPdf(caseItem, isResolved)}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-xs cursor-pointer"
          title="Download SAR PDF report"
        >
          <Download className="w-3.5 h-3.5" />
          <span>
            {isResolved 
              ? (isFraud ? 'Download SAR Report (PDF)' : 'Download Clearance Memo (PDF)')
              : 'Download Report (PDF)'}
          </span>
        </button>
      </div>
    );
  }

  // Full standalone card layout
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 select-none space-y-3.5 text-slate-800">
      {/* Header: Title and Status Badge */}
      <div className="flex items-center justify-between pb-1 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-indigo-600 shrink-0" />
          <span className="text-[13px] font-semibold text-slate-900">
            Regulatory Filing
          </span>
        </div>
        
        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1 ${
          isResolved 
            ? (isFraud ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200')
            : 'bg-amber-50 text-amber-700 border border-amber-200'
        }`}>
          {isResolved ? (
            isFraud ? <AlertTriangle className="w-3.5 h-3.5 text-rose-600" /> : <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          ) : (
            <Clock className="w-3.5 h-3.5 text-amber-600" />
          )}
          <span>
            {isResolved 
              ? (isFraud ? 'SAR Required' : 'Cleared') 
              : 'Under Review'}
          </span>
        </span>
      </div>

      {/* Case Overview Table */}
      <div className="bg-slate-50 rounded-lg p-2.5 border border-slate-100 space-y-1.5 text-[11.5px]">
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Report Form:</span>
          <span className="font-medium text-slate-800">Suspicious Activity Report</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Subject Account:</span>
          <span className="font-medium text-slate-800">{caseItem.account_id}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Disputed Amount:</span>
          <span className="font-semibold text-slate-900">${caseItem.amount_usd.toFixed(2)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Status:</span>
          <span className="font-medium text-slate-800">
            {isResolved 
              ? (isFraud ? 'Ready to file' : 'Cleared — legitimate purchase')
              : 'Evidence collected to date'}
          </span>
        </div>
      </div>

      {/* Download Action Button */}
      <div className="pt-0.5">
        <button
          type="button"
          onClick={() => downloadSarPdf(caseItem, isResolved)}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-xs cursor-pointer"
          title="Download SAR PDF report"
        >
          <Download className="w-3.5 h-3.5" />
          <span>
            {isResolved 
              ? (isFraud ? 'Download SAR Report (PDF)' : 'Download Clearance Memo (PDF)')
              : 'Download Report (PDF)'}
          </span>
        </button>
      </div>
    </div>
  );
};
