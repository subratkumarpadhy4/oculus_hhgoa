import type { BenchmarkCase } from '../types/investigation';

export interface CommandOutputLine {
  text: string;
  color?: string;
}

export interface CommandContext {
  activeCase: BenchmarkCase | null;
  allCases: BenchmarkCase[];
  isInvestigating?: boolean;
  runInvestigation?: (caseId?: string) => void;
  onSelectCase?: (caseId: string) => void;
  onDownloadSar?: () => void;
  clearTerminal: () => void;
}

export interface TerminalCommand {
  name: string;
  description: string;
  usage?: string;
  execute: (args: string[], ctx: CommandContext) => CommandOutputLine[];
}

/**
 * ============================================================================
 * CUSTOM USER COMMANDS REGISTRY
 * ----------------------------------------------------------------------------
 * Add your own custom commands here! They will automatically appear in `help`
 * and execute when typed in the terminal.
 *
 * Example:
 * {
 *   name: 'ping',
 *   description: 'Test API ping latency',
 *   execute: (args, ctx) => [
 *     { text: 'PONG: TigerGraph MCP latency 14ms', color: '#A5D6A7' }
 *   ]
 * }
 * ============================================================================
 */
export const customCommands: TerminalCommand[] = [
  {
    name: 'ping',
    description: 'Test TigerGraph MCP and mock API latency',
    execute: () => [
      { text: '→ Ping: gateway.orbit.internal [127.0.0.1]', color: '#94A3B8' },
      { text: '✓ 64 bytes from tigergraph-mcp: icmp_seq=1 time=18.4ms', color: '#A5D6A7' },
      { text: '✓ 64 bytes from risk-policy-engine: icmp_seq=2 time=12.1ms', color: '#A5D6A7' },
    ]
  },
  {
    name: 'mcp',
    description: 'Check active Model Context Protocol tools',
    execute: () => [
      { text: 'Active MCP Tool Connections:', color: '#64B5F6' },
      { text: '  • tigergraph_mcp.get_transaction_context [Connected]', color: '#A5D6A7' },
      { text: '  • risk_policy.evaluate_rules [Active: R7, R12, R21]', color: '#A5D6A7' },
      { text: '  • auth_gateway.request_step_up [SMS/OTP Ready]', color: '#A5D6A7' },
    ]
  }
];

/**
 * Standard built-in operational commands.
 */
export const builtInCommands: TerminalCommand[] = [
  {
    name: 'help',
    description: 'List all available terminal commands',
    usage: 'help',
    execute: () => {
      const lines: CommandOutputLine[] = [
        { text: 'Orbit Investigation Terminal — Available Commands:', color: '#64B5F6' },
        { text: '---------------------------------------------------------', color: '#475569' },
      ];

      const all = [...builtInCommands, ...customCommands];
      all.forEach(cmd => {
        lines.push({
          text: `  ${cmd.name.padEnd(16)} ${cmd.description}`,
          color: '#E2E8F0'
        });
      });

      lines.push({ text: '---------------------------------------------------------', color: '#475569' });
      lines.push({ text: 'Tip: Add your custom commands in src/utils/terminalCommands.ts', color: '#94A3B8' });
      return lines;
    }
  },
  {
    name: 'clear',
    description: 'Clear the terminal output',
    usage: 'clear',
    execute: (_args, ctx) => {
      ctx.clearTerminal();
      return [];
    }
  },
  {
    name: 'cls',
    description: 'Clear the terminal output (alias)',
    usage: 'cls',
    execute: (_args, ctx) => {
      ctx.clearTerminal();
      return [];
    }
  },
  {
    name: 'case',
    description: 'Show current case details or switch to another case (e.g. case HHG-002)',
    usage: 'case [case_id]',
    execute: (args, ctx) => {
      if (args.length > 0) {
        const targetId = args[0].toUpperCase();
        const found = ctx.allCases.find(c => c.case_id.toUpperCase() === targetId);
        if (found) {
          ctx.onSelectCase?.(found.case_id);
          return [
            { text: `✓ Switched active case to ${found.case_id}`, color: '#A5D6A7' },
            { text: `  Customer: ${found.account_id} | Amount: $${found.amount_usd.toFixed(2)} | Typology: ${found.primary_pattern}`, color: '#94A3B8' }
          ];
        }
        return [
          { text: `Error: Case '${args[0]}' not found. Available cases: HHG-001 through HHG-020.`, color: '#F87171' }
        ];
      }

      if (!ctx.activeCase) {
        return [{ text: 'No active case selected. Use `case HHG-001` or choose from left panel.', color: '#FBBF24' }];
      }

      const c = ctx.activeCase;
      return [
        { text: `Case Record: ${c.case_id}`, color: '#64B5F6' },
        { text: `  Customer Account : ${c.account_id}`, color: '#E2E8F0' },
        { text: `  Card Identifier  : ${c.card_id}`, color: '#E2E8F0' },
        { text: `  Transaction ID   : ${c.transaction_id}`, color: '#E2E8F0' },
        { text: `  Amount (USD)     : $${c.amount_usd.toFixed(2)}`, color: '#E2E8F0' },
        { text: `  Timestamp        : ${c.timestamp}`, color: '#E2E8F0' },
        { text: `  Primary Typology : ${c.primary_pattern}`, color: '#E2E8F0' },
        { text: `  Risk Score       : ${(c.initial_risk_score * 100).toFixed(0)}%`, color: c.initial_risk_score >= 0.75 ? '#F87171' : '#A5D6A7' },
        { text: `  Lifecycle Status : ${c.status}`, color: '#E2E8F0' },
        { text: `  SAR Status       : ${c.sar_status || 'Pending'}`, color: '#E2E8F0' }
      ];
    }
  },
  {
    name: 'cases',
    description: 'List all benchmark investigation cases',
    usage: 'cases',
    execute: (_args, ctx) => {
      const lines: CommandOutputLine[] = [
        { text: 'Available Cases (20 benchmark records):', color: '#64B5F6' }
      ];
      ctx.allCases.forEach(c => {
        const isCurrent = ctx.activeCase?.case_id === c.case_id;
        const prefix = isCurrent ? '→ *' : '   ';
        lines.push({
          text: `${prefix} ${c.case_id.padEnd(8)} | $${c.amount_usd.toFixed(2).padStart(7)} | ${c.primary_pattern.padEnd(26)} | Status: ${c.status}`,
          color: isCurrent ? '#A5D6A7' : '#94A3B8'
        });
      });
      return lines;
    }
  },
  {
    name: 'orbit',
    description: 'Orbit autonomous investigation CLI (e.g. `orbit investigate [case_id]`)',
    usage: 'orbit <investigate|status|case|cases|sar|block|freeze|ping|help> [args]',
    execute: (args, ctx) => {
      const sub = (args[0] || '').toLowerCase();

      if (!sub || sub === 'help' || sub === '--help' || sub === '-h') {
        return [
          { text: 'Orbit Autonomous Investigation CLI [v1.2]', color: '#64B5F6' },
          { text: 'Usage: orbit <subcommand> [arguments]', color: '#94A3B8' },
          { text: '---------------------------------------------------------', color: '#475569' },
          { text: '  orbit investigate [case_id]  Trigger investigation directly (active or target case)', color: '#E2E8F0' },
          { text: '  orbit run [case_id]          Alias for orbit investigate', color: '#E2E8F0' },
          { text: '  orbit status [case_id]       Display case risk score and lifecycle status', color: '#E2E8F0' },
          { text: '  orbit case [case_id]         View active case or switch (e.g. orbit case HHG-002)', color: '#E2E8F0' },
          { text: '  orbit cases                  List all 20 benchmark dataset cases', color: '#E2E8F0' },
          { text: '  orbit sar [download]         Preview or export SAR compliance report', color: '#E2E8F0' },
          { text: '  orbit block                  Trigger card block containment action', color: '#E2E8F0' },
          { text: '  orbit freeze                 Trigger account administrative freeze', color: '#E2E8F0' },
          { text: '  orbit ping                   Test TigerGraph MCP and policy engine latency', color: '#E2E8F0' },
          { text: '  orbit help                   Display this command reference', color: '#E2E8F0' },
          { text: '---------------------------------------------------------', color: '#475569' },
        ];
      }

      if (sub === 'investigate' || sub === 'run') {
        if (ctx.isInvestigating) {
          return [{ text: '⚠️  Investigation is already in progress. Please wait for completion.', color: '#FBBF24' }];
        }

        const targetId = args[1]?.toUpperCase();
        if (targetId) {
          const found = ctx.allCases.find(c => c.case_id.toUpperCase() === targetId);
          if (!found) {
            return [{ text: `Error: Case '${args[1]}' not found. Available cases: HHG-001 through HHG-020.`, color: '#F87171' }];
          }
          ctx.onSelectCase?.(found.case_id);
          ctx.runInvestigation?.(found.case_id);
          return [
            { text: `→ Triggering Orbit autonomous investigation for case ${found.case_id}...`, color: '#64B5F6' },
            { text: `  Customer: ${found.account_id} | Card: ${found.card_id} | Amount: $${found.amount_usd.toFixed(2)}`, color: '#94A3B8' },
            { text: `  Typology: ${found.primary_pattern} (Risk: ${(found.initial_risk_score * 100).toFixed(0)}%)`, color: '#94A3B8' },
            { text: `  Executing autonomous policy gates and TigerGraph context traversal...`, color: '#A5D6A7' }
          ];
        }

        if (!ctx.activeCase) {
          return [{ text: 'Error: No active case selected. Specify a case (e.g. `orbit investigate HHG-001`).', color: '#F87171' }];
        }

        const target = ctx.activeCase;
        ctx.runInvestigation?.(target.case_id);
        return [
          { text: `→ Triggering Orbit autonomous investigation for case ${target.case_id}...`, color: '#64B5F6' },
          { text: `  Customer: ${target.account_id} | Card: ${target.card_id} | Amount: $${target.amount_usd.toFixed(2)}`, color: '#94A3B8' },
          { text: `  Typology: ${target.primary_pattern} (Risk: ${(target.initial_risk_score * 100).toFixed(0)}%)`, color: '#94A3B8' },
          { text: `  Executing autonomous policy gates and TigerGraph context traversal...`, color: '#A5D6A7' }
        ];
      }

      if (sub === 'status') {
        const targetId = args[1]?.toUpperCase();
        const targetCase = targetId 
          ? ctx.allCases.find(c => c.case_id.toUpperCase() === targetId) 
          : ctx.activeCase;
        if (!targetCase) {
          return [{ text: targetId ? `Case '${args[1]}' not found.` : 'No active case selected.', color: '#F87171' }];
        }
        const isFraud = targetCase.initial_risk_score >= 0.75;
        return [
          { text: `Orbit Case Status: ${targetCase.case_id}`, color: '#64B5F6' },
          { text: `  Customer : ${targetCase.account_id} | Card: ${targetCase.card_id}`, color: '#E2E8F0' },
          { text: `  Verdict  : ${isFraud ? 'CONFIRMED FRAUD' : 'CLEARED (FALSE POSITIVE)'}`, color: isFraud ? '#F87171' : '#A5D6A7' },
          { text: `  Risk     : ${(targetCase.initial_risk_score * 100).toFixed(0)}%`, color: isFraud ? '#F87171' : '#A5D6A7' },
          { text: `  State    : ${targetCase.status}`, color: '#E2E8F0' },
          { text: `  SAR      : ${targetCase.sar_status || 'Pending'}`, color: '#E2E8F0' }
        ];
      }

      if (sub === 'case') {
        const caseCmd = builtInCommands.find(c => c.name === 'case');
        return caseCmd ? caseCmd.execute(args.slice(1), ctx) : [];
      }

      if (sub === 'cases') {
        const casesCmd = builtInCommands.find(c => c.name === 'cases');
        return casesCmd ? casesCmd.execute([], ctx) : [];
      }

      if (sub === 'sar') {
        const sarCmd = builtInCommands.find(c => c.name === 'sar');
        return sarCmd ? sarCmd.execute(args.slice(1), ctx) : [];
      }

      if (sub === 'block') {
        const blockCmd = builtInCommands.find(c => c.name === 'block');
        return blockCmd ? blockCmd.execute(args.slice(1), ctx) : [];
      }

      if (sub === 'freeze') {
        const freezeCmd = builtInCommands.find(c => c.name === 'freeze');
        return freezeCmd ? freezeCmd.execute(args.slice(1), ctx) : [];
      }

      if (sub === 'ping') {
        const pingCmd = customCommands.find(c => c.name === 'ping');
        return pingCmd ? pingCmd.execute(args.slice(1), ctx) : [];
      }

      return [
        { text: `Unknown orbit subcommand: '${sub}'`, color: '#F87171' },
        { text: "Type 'orbit help' or 'orbit investigate' to trigger investigation.", color: '#94A3B8' }
      ];
    }
  },
  {
    name: 'run',
    description: 'Run investigation on active or target case (alias for `orbit investigate`)',
    usage: 'run [case_id]',
    execute: (args, ctx) => {
      const orbitCmd = builtInCommands.find(c => c.name === 'orbit');
      return orbitCmd ? orbitCmd.execute(['run', ...args], ctx) : [];
    }
  },
  {
    name: 'investigate',
    description: 'Trigger autonomous investigation directly (alias for `orbit investigate`)',
    usage: 'investigate [case_id]',
    execute: (args, ctx) => {
      const orbitCmd = builtInCommands.find(c => c.name === 'orbit');
      return orbitCmd ? orbitCmd.execute(['investigate', ...args], ctx) : [];
    }
  },
  {
    name: 'status',
    description: 'Show active case status and risk indicators',
    usage: 'status',
    execute: (_args, ctx) => {
      if (!ctx.activeCase) {
        return [{ text: 'No active case selected.', color: '#FBBF24' }];
      }
      const c = ctx.activeCase;
      const isFraud = c.initial_risk_score >= 0.75;
      return [
        { text: `Case Status: ${c.case_id}`, color: '#64B5F6' },
        { text: `  Verdict : ${isFraud ? 'CONFIRMED FRAUD' : 'CLEARED (FALSE POSITIVE)'}`, color: isFraud ? '#F87171' : '#A5D6A7' },
        { text: `  Risk    : ${(c.initial_risk_score * 100).toFixed(0)}%`, color: isFraud ? '#F87171' : '#A5D6A7' },
        { text: `  State   : ${c.status}`, color: '#E2E8F0' },
        { text: `  SAR     : ${c.sar_status || 'Pending'}`, color: '#E2E8F0' }
      ];
    }
  },
  {
    name: 'graph',
    description: 'Show connected entities summary for active case',
    usage: 'graph',
    execute: (_args, ctx) => {
      if (!ctx.activeCase) {
        return [{ text: 'No active case selected.', color: '#FBBF24' }];
      }
      const c = ctx.activeCase;
      const lines: CommandOutputLine[] = [
        { text: `Topology Graph: ${c.case_id} (${c.graph_nodes.length} nodes, ${c.graph_edges.length} edges)`, color: '#64B5F6' }
      ];
      c.graph_nodes.forEach(n => {
        lines.push({
          text: `  [${n.type.padEnd(11)}] ID: ${n.id}${n.isFraudRing ? ' (FLAGGED)' : ''}`,
          color: n.isFraudRing ? '#F87171' : '#E2E8F0'
        });
      });
      return lines;
    }
  },
  {
    name: 'patterns',
    description: 'List evaluated fraud patterns for active case',
    usage: 'patterns',
    execute: (_args, ctx) => {
      if (!ctx.activeCase) {
        return [{ text: 'No active case selected.', color: '#FBBF24' }];
      }
      const patterns = ctx.activeCase.evidence_pack?.detected_patterns || [];
      if (patterns.length === 0) {
        return [{ text: 'No specific anomalous patterns detected.', color: '#A5D6A7' }];
      }
      const lines: CommandOutputLine[] = [
        { text: `Detected Patterns for ${ctx.activeCase.case_id}:`, color: '#64B5F6' }
      ];
      patterns.forEach(p => {
        lines.push({
          text: `  • ${p.pattern} [Strength: ${p.strength.toUpperCase()}]`,
          color: p.strength === 'strong' ? '#F87171' : p.strength === 'moderate' ? '#FBBF24' : '#94A3B8'
        });
        p.observations.forEach(o => {
          lines.push({ text: `      → ${o}`, color: '#94A3B8' });
        });
      });
      return lines;
    }
  },
  {
    name: 'block',
    description: 'Execute card block containment for active case',
    usage: 'block',
    execute: (_args, ctx) => {
      if (!ctx.activeCase) {
        return [{ text: 'No active case selected.', color: '#FBBF24' }];
      }
      return [
        { text: `✓ Card ${ctx.activeCase.card_id} placed on BLOCK_CARD status.`, color: '#F87171' },
        { text: `  Authorization network notified. Subsequent purchase attempts will decline.`, color: '#94A3B8' }
      ];
    }
  },
  {
    name: 'freeze',
    description: 'Execute account freeze containment for active case',
    usage: 'freeze',
    execute: (_args, ctx) => {
      if (!ctx.activeCase) {
        return [{ text: 'No active case selected.', color: '#FBBF24' }];
      }
      return [
        { text: `✓ Account ${ctx.activeCase.account_id} placed on administrative freeze.`, color: '#F87171' },
        { text: `  Online login sessions revoked. Device fingerprint blocked from authentication.`, color: '#94A3B8' }
      ];
    }
  },
  {
    name: 'verify',
    description: 'Simulate step-up verification challenge to customer',
    usage: 'verify [pass|fail]',
    execute: (args, ctx) => {
      if (!ctx.activeCase) {
        return [{ text: 'No active case selected.', color: '#FBBF24' }];
      }
      const mode = args[0]?.toLowerCase();
      if (mode === 'pass') {
        return [
          { text: '→ Dispatching SMS OTP to customer registered phone...', color: '#64B5F6' },
          { text: '✓ Verified: Cardholder responded within 14s. Purchase confirmed legitimate.', color: '#A5D6A7' }
        ];
      }
      return [
        { text: '→ Dispatching SMS OTP to customer registered phone...', color: '#64B5F6' },
        { text: '✗ Verification FAILED: Timeout (no response after 3 attempts / 180s).', color: '#F87171' }
      ];
    }
  },
  {
    name: 'sar',
    description: 'Preview or download Suspicious Activity Report (e.g. `sar` or `sar download`)',
    usage: 'sar [download]',
    execute: (args, ctx) => {
      if (!ctx.activeCase) {
        return [{ text: 'No active case selected.', color: '#FBBF24' }];
      }
      if (args[0]?.toLowerCase() === 'download' || args[0]?.toLowerCase() === 'export') {
        ctx.onDownloadSar?.();
        return [
          { text: `✓ Triggered SAR PDF export for case ${ctx.activeCase.case_id}.`, color: '#A5D6A7' }
        ];
      }
      const narrative = ctx.activeCase.sar?.narrative || 'No narrative generated yet.';
      return [
        { text: `SAR Narrative Preview [Case ${ctx.activeCase.case_id}]:`, color: '#64B5F6' },
        { text: narrative, color: '#E2E8F0' },
        { text: 'Tip: Type `sar download` to export the printable compliance PDF.', color: '#94A3B8' }
      ];
    }
  },
  {
    name: 'rules',
    description: 'Display policy rules evaluated for active case',
    usage: 'rules',
    execute: (_args, ctx) => {
      if (!ctx.activeCase) {
        return [{ text: 'No active case selected.', color: '#FBBF24' }];
      }
      const rules = ctx.activeCase.evidence_pack?.policy_rules || [];
      const lines: CommandOutputLine[] = [
        { text: `Evaluated Policy Rules for ${ctx.activeCase.case_id}:`, color: '#64B5F6' }
      ];
      rules.forEach(r => {
        lines.push({
          text: `  • ${r.rule_id} (${r.title}) - ${r.source}`,
          color: '#A5D6A7'
        });
        lines.push({
          text: `      ${r.text}`,
          color: '#94A3B8'
        });
      });
      return lines;
    }
  },
  {
    name: 'echo',
    description: 'Echo back text to the terminal',
    usage: 'echo <text>',
    execute: (args) => {
      return [{ text: args.join(' '), color: '#E2E8F0' }];
    }
  },
  {
    name: 'date',
    description: 'Show current UTC timestamp',
    usage: 'date',
    execute: () => {
      return [{ text: new Date().toUTCString(), color: '#E2E8F0' }];
    }
  },
  {
    name: 'whoami',
    description: 'Print current operator and session credentials',
    usage: 'whoami',
    execute: () => {
      return [
        { text: 'User: compliance-operator@orbit.internal', color: '#A5D6A7' },
        { text: 'Role: Level-2 Fraud Compliance Officer', color: '#94A3B8' },
        { text: 'Session: Active (Authenticated via SSO)', color: '#94A3B8' }
      ];
    }
  }
];

/**
 * Dispatches an entered command line string against registered built-in and custom commands.
 */
export function executeTerminalCommand(
  rawInput: string,
  ctx: CommandContext
): CommandOutputLine[] {
  const trimmed = rawInput.trim();
  if (!trimmed) return [];

  const parts = trimmed.split(/\s+/);
  const commandName = parts[0].toLowerCase();
  const args = parts.slice(1);

  // Check custom commands first (allows users to override or define their own)
  const custom = customCommands.find(c => c.name.toLowerCase() === commandName);
  if (custom) {
    try {
      return custom.execute(args, ctx);
    } catch (err: any) {
      return [{ text: `Error executing '${commandName}': ${err.message || String(err)}`, color: '#F87171' }];
    }
  }

  // Check built-in commands
  const builtin = builtInCommands.find(c => c.name.toLowerCase() === commandName);
  if (builtin) {
    try {
      return builtin.execute(args, ctx);
    } catch (err: any) {
      return [{ text: `Error executing '${commandName}': ${err.message || String(err)}`, color: '#F87171' }];
    }
  }

  return [
    { text: `command not found: ${commandName}`, color: '#F87171' },
    { text: "Type 'help' to see all available commands.", color: '#94A3B8' }
  ];
}
