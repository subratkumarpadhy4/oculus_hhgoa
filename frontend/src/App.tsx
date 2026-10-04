import React, { useState, useCallback } from 'react';
import { Header } from './components/layout/Header';
import { CaseSelectorPanel } from './components/layout/CaseSelectorPanel';
import { CaseTabBar } from './components/layout/CaseTabBar';
import { GraphCanvas } from './components/investigation/GraphCanvas';
import { InvestigationTerminal } from './components/investigation/InvestigationTerminal';
import { NbaProgressionCard } from './components/decision/NbaProgressionCard';
import { BENCHMARK_CASES } from './data/benchmarkCases';
import type { BenchmarkCase } from './types/investigation';
import { downloadSarPdf } from './utils/sarBuilder';

export const App: React.FC = () => {
  const [cases, setCases] = useState<BenchmarkCase[]>(BENCHMARK_CASES);
  const [openCaseIds, setOpenCaseIds] = useState<string[]>([
    BENCHMARK_CASES[0].case_id,
    BENCHMARK_CASES[1].case_id
  ]);
  const [activeCaseId, setActiveCaseId] = useState<string>(BENCHMARK_CASES[0].case_id);
  const [isInvestigating, setIsInvestigating] = useState<boolean>(false);
  const [isTerminalOpen, setIsTerminalOpen] = useState<boolean>(false);

  // Active case accessor: null if no case is active
  const activeCase = cases.find(c => c.case_id === activeCaseId) || null;

  // Select tab handler (switching between already open cases)
  const handleSelectTab = (caseId: string) => {
    setActiveCaseId(caseId);
  };

  // Open case from dropdown (adds as a new tab if not open, and switches to it in the same window)
  const handleOpenCase = (caseId: string) => {
    if (!openCaseIds.includes(caseId)) {
      setOpenCaseIds(prev => [...prev, caseId]);
    }
    setActiveCaseId(caseId);
  };

  // Close tab handler - ALLOWS CLOSING ALL TABS
  const handleCloseTab = (caseId: string) => {
    const newOpenIds = openCaseIds.filter(id => id !== caseId);
    setOpenCaseIds(newOpenIds);
    if (activeCaseId === caseId) {
      if (newOpenIds.length > 0) {
        setActiveCaseId(newOpenIds[newOpenIds.length - 1]);
      } else {
        setActiveCaseId('');
      }
    }
  };

  // Trigger autonomous investigation: open terminal and start sequential stream
  const handleRunAutonomousInvestigation = useCallback((targetCaseId?: unknown) => {
    if (isInvestigating) return;

    let targetCase = activeCase;
    if (typeof targetCaseId === 'string' && targetCaseId.trim()) {
      const found = cases.find(c => c.case_id.toUpperCase() === targetCaseId.trim().toUpperCase());
      if (found) {
        if (!openCaseIds.includes(found.case_id)) {
          setOpenCaseIds(prev => [...prev, found.case_id]);
        }
        setActiveCaseId(found.case_id);
        targetCase = found;
      }
    }

    if (!targetCase) return;

    setIsTerminalOpen(true);
    setIsInvestigating(true);
  }, [isInvestigating, activeCase, cases, openCaseIds]);

  // Complete autonomous investigation and transition active case to resolved verdict
  const handleInvestigationComplete = useCallback((completedCaseId?: unknown) => {
    setIsInvestigating(false);
    const targetId = typeof completedCaseId === 'string' && completedCaseId ? completedCaseId : activeCaseId;
    if (!targetId) return;

    setCases(prev => prev.map(c => {
      if (c.case_id === targetId) {
        const isFraudCase = c.initial_risk_score >= 0.75 || c.graph_nodes.some(n => n.isFraudRing);
        const resolvedStatus = isFraudCase ? 'resolved_fraud' : 'resolved_cleared';
        const sarVerdict: 'Pending' | 'Cleared' = isFraudCase ? 'Pending' : 'Cleared';
        return { ...c, status: resolvedStatus, sar_status: sarVerdict };
      }
      return c;
    }));
  }, [activeCaseId]);

  return (
    <div className="flex flex-col h-screen w-screen bg-[#F8FAFC] text-slate-900 overflow-hidden font-sans antialiased">
      {/* Top Header: Platform Branding */}
      <Header activeCase={activeCase} />

      {/* 3-Column Cockpit Grid: Left Case Space (280px) + Middle Larger Box (flex-1) + Right Decision & SAR (320px) */}
      <main className="flex-1 flex overflow-hidden min-h-0">
        {/* Column 1: Left Separate Space for Case Dropbox & Selection (280px) */}
        <section className="w-[280px] shrink-0 h-full flex flex-col bg-slate-50/70 border-r border-slate-200" aria-label="Case Management">
          <CaseSelectorPanel
            activeCase={activeCase}
            allCases={cases}
            openCaseIds={openCaseIds}
            onOpenCase={handleOpenCase}
            isInvestigating={isInvestigating}
            onRunInvestigation={handleRunAutonomousInvestigation}
            onSarStatusChange={(newStatus) => {
              if (!activeCase) return;
              setCases(prev => prev.map(c => 
                c.case_id === activeCase.case_id 
                  ? { ...c, sar_status: newStatus } 
                  : c
              ));
            }}
          />
        </section>

        {/* Column 2: Investigation Core - Larger Middle Box (flex-1) */}
        <section className="flex-1 flex flex-col h-full min-w-0 bg-white border-r border-slate-200 overflow-hidden" aria-label="Investigation Core">
          {/* Browser-Styled Case Tab Bar */}
          <CaseTabBar
            openCaseIds={openCaseIds}
            activeCaseId={activeCase ? activeCase.case_id : ''}
            allCases={cases}
            isTerminalOpen={isTerminalOpen}
            onSelectTab={handleSelectTab}
            onCloseTab={handleCloseTab}
            onToggleTerminal={() => setIsTerminalOpen(prev => !prev)}
          />

          {/* Interactive Topology Graph Canvas — full flex height */}
          <div className="flex-1 min-h-0 relative flex flex-col overflow-hidden">
            <GraphCanvas
              nodes={activeCase ? activeCase.graph_nodes : []}
              edges={activeCase ? activeCase.graph_edges : []}
              caseId={activeCase ? activeCase.case_id : ''}
              isInvestigating={isInvestigating}
              isTerminalOpen={isTerminalOpen}
            />
          </div>

          {/* Terminal — inline below graph, only visible when open */}
          <InvestigationTerminal
            isOpen={isTerminalOpen}
            steps={activeCase ? activeCase.execution_steps : []}
            isInvestigating={isInvestigating}
            caseId={activeCase ? activeCase.case_id : ''}
            activeCase={activeCase}
            allCases={cases}
            onClose={() => setIsTerminalOpen(false)}
            onComplete={handleInvestigationComplete}
            onRunInvestigation={handleRunAutonomousInvestigation}
            onSelectCase={handleOpenCase}
            onDownloadSar={() => {
              if (activeCase) {
                downloadSarPdf(activeCase, activeCase.status.startsWith('resolved'));
              }
            }}
          />
        </section>

        {/* Column 3: Decision Engine, Policy Gates & Incident Review (320px) */}
        <section className="w-[320px] shrink-0 h-full flex flex-col bg-slate-50/70 overflow-hidden" aria-label="Decision Engine and Policy Gates">
          <div className="flex-1 overflow-y-auto p-3.5 space-y-3.5">
            {/* Next-Best Action Progression / Incident Review */}
            <NbaProgressionCard
              currentCase={activeCase}
              isInvestigating={isInvestigating}
              onRunInvestigation={handleRunAutonomousInvestigation}
            />
          </div>
        </section>
      </main>
    </div>
  );
};

export default App;
