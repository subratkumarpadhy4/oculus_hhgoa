import React, { useState, useEffect, useRef } from 'react';
import { Terminal as TerminalIcon, X, Trash2 } from 'lucide-react';
import type { BenchmarkCase, ExecutionStep } from '../../types/investigation';
import { 
  executeTerminalCommand, 
  builtInCommands, 
  customCommands,
  type CommandOutputLine 
} from '../../utils/terminalCommands';

interface InvestigationTerminalProps {
  isOpen: boolean;
  steps: ExecutionStep[];
  isInvestigating: boolean;
  caseId?: string;
  activeCase?: BenchmarkCase | null;
  allCases?: BenchmarkCase[];
  onClose: () => void;
  onComplete?: (caseId?: string) => void;
  onRunInvestigation?: (caseId?: string) => void;
  onSelectCase?: (caseId: string) => void;
  onDownloadSar?: () => void;
}

interface OutputLine {
  key: string;
  text: string;
  color?: string;
}

// What each step produces as terminal output — step name then result
function linesForStep(step: ExecutionStep, idx: number, total: number): OutputLine[] {
  const out: OutputLine[] = [];

  // Running line
  out.push({
    key: `${idx}-run-${Date.now()}`,
    text: `[${idx + 1}/${total}] Running: ${step.title}`,
    color: '#64B5F6', // light blue
  });

  // Result line — the actual output/details
  const resultText = step.outputSnippet
    ? `    → ${step.outputSnippet}`
    : `    → ${step.details}`;
  out.push({
    key: `${idx}-result-${Date.now()}`,
    text: resultText,
    color: '#A5D6A7', // light green
  });

  return out;
}

export const InvestigationTerminal: React.FC<InvestigationTerminalProps> = ({
  isOpen,
  steps,
  isInvestigating,
  caseId,
  activeCase = null,
  allCases = [],
  onClose,
  onComplete,
  onRunInvestigation,
  onSelectCase,
  onDownloadSar,
}) => {
  const [lines, setLines] = useState<OutputLine[]>([]);
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const stepsRef = useRef(steps);
  stepsRef.current = steps;

  const caseIdRef = useRef(caseId);
  caseIdRef.current = caseId;

  // Initialize or update welcome lines on case change
  useEffect(() => {
    if (lines.length === 0) {
      setLines([
        {
          key: 'init-1',
          text: `Orbit Fraud Ops Terminal [v1.2] · Active Case: ${caseId || 'STANDBY'}`,
          color: '#64B5F6',
        },
        {
          key: 'init-2',
          text: "Type 'orbit investigate' to trigger investigation directly or 'help' for commands.",
          color: '#94A3B8',
        },
      ]);
    }
  }, [caseId]);

  // Stream investigation steps sequentially (1 step per second)
  useEffect(() => {
    if (!isInvestigating) return;

    const currentCaseId = caseIdRef.current || 'CASE';
    const currentSteps = stepsRef.current;
    if (currentSteps.length === 0) return;

    // Output starting header
    setLines(prev => [
      ...prev,
      {
        key: `start-${Date.now()}`,
        text: `Starting automated investigation workflow for ${currentCaseId}...`,
        color: '#FBBF24',
      },
    ]);

    const timers: ReturnType<typeof setTimeout>[] = [];

    currentSteps.forEach((step, idx) => {
      const stepLines = linesForStep(step, idx, currentSteps.length);
      const timer = setTimeout(() => {
        setLines(prev => [...prev, ...stepLines]);
      }, (idx + 1) * 900);
      timers.push(timer);
    });

    // Schedule completion line
    const doneTimer = setTimeout(() => {
      setLines(prev => [
        ...prev,
        {
          key: `done-${Date.now()}`,
          text: '✓ Investigation workflow complete. Next-best action recalibrated.',
          color: '#A5D6A7',
        },
      ]);
      onCompleteRef.current?.(currentCaseId);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }, (currentSteps.length + 1) * 900);
    timers.push(doneTimer);

    return () => {
      timers.forEach(t => clearTimeout(t));
    };
  }, [isInvestigating]);

  // Auto-scroll to bottom whenever new lines appear or input changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines, input]);

  // Focus input when terminal opens
  useEffect(() => {
    if (isOpen && !isInvestigating) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [isOpen, isInvestigating]);

  // Handle command execution
  const handleExecuteCommand = (rawCommand: string) => {
    const trimmed = rawCommand.trim();
    if (!trimmed) return;

    // Add command to history
    setHistory(prev => [...prev, trimmed]);
    setHistoryIndex(-1);

    // Echo the command in terminal
    const echoLine: OutputLine = {
      key: `cmd-${Date.now()}`,
      text: `$ ${trimmed}`,
      color: '#F1F5F9',
    };

    const ctx = {
      activeCase,
      allCases,
      isInvestigating,
      runInvestigation: onRunInvestigation,
      onSelectCase,
      onDownloadSar,
      clearTerminal: () => setLines([]),
    };

    const resultLines: CommandOutputLine[] = executeTerminalCommand(trimmed, ctx);

    // If command was clear / cls, executeTerminalCommand already cleared lines
    if (trimmed.toLowerCase() === 'clear' || trimmed.toLowerCase() === 'cls') {
      setInput('');
      return;
    }

    const formattedResults: OutputLine[] = resultLines.map((r, i) => ({
      key: `res-${Date.now()}-${i}`,
      text: r.text,
      color: r.color || '#E2E8F0',
    }));

    setLines(prev => [...prev, echoLine, ...formattedResults]);
    setInput('');
  };

  // Keyboard navigation for history (Up/Down) & Tab completion
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length === 0) return;
      const nextIndex = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1);
      setHistoryIndex(nextIndex);
      setInput(history[nextIndex]);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (history.length === 0 || historyIndex === -1) return;
      const nextIndex = historyIndex + 1;
      if (nextIndex >= history.length) {
        setHistoryIndex(-1);
        setInput('');
      } else {
        setHistoryIndex(nextIndex);
        setInput(history[nextIndex]);
      }
    } else if (e.key === 'Tab') {
      e.preventDefault();
      const current = input.trim().toLowerCase();
      if (!current) return;

      // Autocomplete orbit subcommands if input begins with 'orbit '
      if (current.startsWith('orbit')) {
        const parts = input.trim().split(/\s+/);
        if (parts.length === 1 && current === 'orbit') {
          setInput('orbit ');
          return;
        }
        if (parts.length >= 2) {
          const subArg = parts[1].toLowerCase();
          const orbitSubs = ['investigate', 'run', 'status', 'case', 'cases', 'sar', 'block', 'freeze', 'ping', 'help'];
          const matches = orbitSubs.filter(sub => sub.startsWith(subArg));
          if (matches.length === 1) {
            setInput(`orbit ${matches[0]} `);
            return;
          } else if (matches.length > 1) {
            setLines(prev => [
              ...prev,
              { key: `tab-${Date.now()}`, text: `$ ${input}`, color: '#94A3B8' },
              { key: `tab-list-${Date.now()}`, text: matches.map(m => `orbit ${m}`).join('   '), color: '#64B5F6' },
            ]);
            return;
          }
        }
      }

      const allCommandNames = [...builtInCommands, ...customCommands].map(c => c.name);
      const matches = allCommandNames.filter(name => name.startsWith(current));

      if (matches.length === 1) {
        setInput(matches[0] + ' ');
      } else if (matches.length > 1) {
        setLines(prev => [
          ...prev,
          {
            key: `tab-${Date.now()}`,
            text: `$ ${input}`,
            color: '#94A3B8',
          },
          {
            key: `tab-list-${Date.now()}`,
            text: matches.join('   '),
            color: '#64B5F6',
          },
        ]);
      }
    }
  };

  const handleClear = () => {
    setLines([]);
    inputRef.current?.focus();
  };

  if (!isOpen) return null;

  return (
    <div 
      className="shrink-0 border-t border-[#1e1e1e] flex flex-col transition-all select-text" 
      style={{ height: '230px', background: '#090D16' }}
      onClick={() => inputRef.current?.focus()}
    >
      {/* Terminal Title Bar */}
      <div
        className="flex items-center justify-between px-3 py-1.5 shrink-0 select-none"
        style={{ background: '#0F172A', borderBottom: '1px solid #1E293B' }}
      >
        <div className="flex items-center gap-2">
          <TerminalIcon className="w-3.5 h-3.5 text-indigo-400" />
          <span style={{ fontFamily: 'monospace', fontSize: '11px', fontWeight: 600, color: '#94A3B8' }}>
            TERMINAL · INTERACTIVE SHELL
          </span>
          <span 
            className={`w-1.5 h-1.5 rounded-full ${
              isInvestigating ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'
            }`} 
            title={isInvestigating ? 'Investigating...' : 'Online & Ready'}
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleClear();
            }}
            className="text-slate-400 hover:text-slate-200 p-0.5 rounded transition-colors cursor-pointer"
            title="Clear terminal (clear)"
          >
            <Trash2 className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            style={{ 
              fontFamily: 'monospace', 
              fontSize: '14px', 
              color: '#64748B', 
              background: 'none', 
              border: 'none', 
              cursor: 'pointer', 
              lineHeight: 1 
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#fff')}
            onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}
            title="Close terminal"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Output Stream & Prompt */}
      <div
        className="flex-1 overflow-y-auto px-3.5 py-2 font-mono text-[12px] leading-relaxed"
        style={{ scrollbarWidth: 'thin', scrollbarColor: '#334155 #090D16' }}
      >
        {/* Render lines */}
        {lines.map(line => (
          <div
            key={line.key}
            style={{
              color: line.color || '#E2E8F0',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              lineHeight: '1.55',
            }}
          >
            {line.text}
          </div>
        ))}

        {/* Interactive Command Input Line */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleExecuteCommand(input);
          }}
          className="flex items-center gap-1.5 mt-1"
        >
          <span className="text-emerald-400 font-bold select-none shrink-0">$</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isInvestigating}
            placeholder={
              isInvestigating 
                ? "investigation in progress..." 
                : "type a command (e.g. 'orbit investigate', 'orbit status', 'help')..."
            }
            className="flex-1 bg-transparent border-none outline-none text-[#F8FAFC] font-mono text-[12px] p-0 focus:ring-0 focus:outline-none placeholder:text-slate-600 caret-white"
            autoComplete="off"
            spellCheck={false}
          />
        </form>

        <div ref={bottomRef} />
      </div>
    </div>
  );
};
