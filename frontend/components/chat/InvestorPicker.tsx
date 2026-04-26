'use client';

import React, { useState } from 'react';
import { INVESTOR_PERSONAS, getInvestorReviewPrompt, InvestorPersona } from '@/lib/aiPrompts';

interface InvestorPickerProps {
  onSelect: (prompt: string, investorId: string) => void;
  disabled?: boolean;
}

export default function InvestorPicker({ onSelect, disabled = false }: InvestorPickerProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const handleSelect = (investor: InvestorPersona) => {
    if (disabled) return;
    onSelect(getInvestorReviewPrompt(investor), investor.id);
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
          Get your portfolio reviewed by
        </div>
        <div className="flex-1 h-px bg-gray-100" />
      </div>

      {/* Scrollable horizontal row of character cards */}
      <div className="flex gap-2.5 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-none">
        {INVESTOR_PERSONAS.map((investor) => {
          const isHovered = hoveredId === investor.id;
          return (
            <button
              key={investor.id}
              onClick={() => handleSelect(investor)}
              onMouseEnter={() => setHoveredId(investor.id)}
              onMouseLeave={() => setHoveredId(null)}
              disabled={disabled}
              className={`group relative flex-shrink-0 w-[154px] rounded-2xl text-left transition-all duration-200 overflow-hidden disabled:opacity-50 ${
                isHovered
                  ? 'shadow-lg scale-[1.03] -translate-y-0.5'
                  : 'shadow-sm hover:shadow-md'
              }`}
            >
              {/* Gradient header with initials */}
              <div className={`bg-gradient-to-br ${investor.gradient} px-3 pt-3 pb-2.5 relative`}>
                <div className="flex items-start justify-between">
                  <div className="w-9 h-9 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                    <span className="text-[13px] font-bold text-white leading-none">{investor.initial}</span>
                  </div>
                  <svg
                    className={`w-4 h-4 text-white/50 transition-all duration-200 ${
                      isHovered ? 'text-white/90 translate-x-0.5' : ''
                    }`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.5 12h15m0 0l-6.75-6.75M19.5 12l-6.75 6.75" />
                  </svg>
                </div>
                <div className="mt-2">
                  <div className="text-[13px] font-bold text-white leading-tight">{investor.name}</div>
                  <div className="text-[10px] text-white/70 leading-tight mt-0.5">{investor.tagline}</div>
                </div>
              </div>

              {/* Quote section */}
              <div className="bg-white px-3 py-2.5 border border-t-0 border-gray-100 rounded-b-2xl">
                <p className="text-[10.5px] text-gray-500 leading-snug italic line-clamp-2">
                  &ldquo;{investor.quote}&rdquo;
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
