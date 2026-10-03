import React from 'react';
import type { BenchmarkCase } from '../../types/investigation';

interface HeaderProps {
  activeCase?: BenchmarkCase | null;
}

export const Header: React.FC<HeaderProps> = ({ activeCase }) => {
  return (
    <header className="h-11 bg-white border-b border-slate-200 px-4 flex items-center justify-between select-none z-30 shrink-0 text-slate-800">
      {/* Left: Enhanced Orbit Logo & Brand Name */}
      <div className="flex items-center space-x-2.5">
        <img 
          src="/orbit-icon-enhanced.png" 
          alt="Orbit" 
          className="h-7 w-7 object-contain" 
        />
        <span className="text-[15px] font-bold tracking-tight text-slate-900 font-sans">
          Orbit
        </span>
      </div>

      {/* Middle: Active Case Indicator */}
      {activeCase && (
        <div className="hidden md:flex items-center space-x-2 text-xs text-slate-600 bg-slate-50 border border-slate-200/80 px-3 py-1 rounded-full">
          <span className="font-semibold text-slate-900">{activeCase.case_id}</span>
          <span className="text-slate-300">•</span>
          <span className="text-slate-600 font-medium">{activeCase.primary_pattern}</span>
          <span className="text-slate-300">•</span>
          <span className="font-semibold text-slate-900">${activeCase.amount_usd.toFixed(2)}</span>
        </div>
      )}

      {/* Right: Clean minimal space */}
      <div className="flex items-center space-x-3 text-xs" />
    </header>
  );
};
