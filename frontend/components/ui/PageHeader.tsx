'use client';

import React from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: React.ReactNode;
  /** Right-aligned actions (buttons). */
  actions?: React.ReactNode;
  className?: string;
}

/**
 * One header pattern for every panel page: left-aligned bold title, a muted
 * subtitle, and right-aligned actions — filling the content width.
 */
export default function PageHeader({ title, subtitle, actions, className = '' }: PageHeaderProps) {
  return (
    <div className={`flex items-end justify-between gap-4 mb-7 ${className}`}>
      <div className="min-w-0">
        <h1 className="text-[26px] font-bold text-gray-900 tracking-tight leading-none">{title}</h1>
        {subtitle && <div className="text-[13px] text-gray-500 mt-2">{subtitle}</div>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </div>
  );
}
