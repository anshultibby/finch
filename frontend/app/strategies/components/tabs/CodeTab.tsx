'use client';

import React, { useState } from 'react';
import type { Strategy } from '@/lib/types';

interface CodeTabProps {
  strategy: Strategy;
}

export function CodeTab({ strategy }: CodeTabProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>('entry');

  // Mock code content - in real implementation, fetch from ChatFiles
  const entryCode = `# Entry Logic
async def check_entry(ctx):
    """Check for entry signals"""
    signals = []
    
    # Example: Check market conditions
    markets = await ctx.get_markets()
    
    for market in markets:
        if should_enter(market):
            signals.append({
                'market_id': market.id,
                'market_name': market.name,
                'side': 'yes',
                'reason': 'Market conditions favorable',
                'confidence': 0.8
            })
    
    return signals
`;

  const exitCode = `# Exit Logic
async def check_exit(ctx, position):
    """Check if position should be exited"""
    
    # Example: Exit on profit target or stop loss
    pnl_pct = (position.current_price - position.entry_price) / position.entry_price
    
    if pnl_pct > 0.10:  # 10% profit
        return {
            'position_id': position.position_id,
            'reason': 'Profit target reached (+10%)',
        }
    
    if pnl_pct < -0.05:  # 5% loss
        return {
            'position_id': position.position_id,
            'reason': 'Stop loss triggered (-5%)',
        }
    
    return None
`;

  const configJson = JSON.stringify({
    name: strategy.name,
    thesis: strategy.config?.thesis || strategy.description,
    platform: strategy.config?.platform || 'polymarket',
    execution_frequency: strategy.config?.execution_frequency || 60,
    entry_script: 'entry.py',
    exit_script: 'exit.py',
    entry_description: strategy.config?.entry_description || '',
    exit_description: strategy.config?.exit_description || '',
    capital: strategy.config?.capital || {},
    parameters: strategy.config?.parameters || {}
  }, null, 2);

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // Could add toast notification here
  };

  const openInChat = (filename: string) => {
    // Navigate to chat with prepopulated message
    window.location.href = `/?message=Edit ${filename} in strategy ${strategy.name}`;
  };

  return (
    <div className="space-y-4">
      {/* Entry.py */}
      <CodeSection
        title="entry.py"
        subtitle="Entry signal logic"
        code={entryCode}
        language="python"
        isExpanded={expandedSection === 'entry'}
        onToggle={() => toggleSection('entry')}
        onCopy={() => copyToClipboard(entryCode)}
        onEdit={() => openInChat('entry.py')}
        lastModified="2 hours ago"
      />

      {/* Exit.py */}
      <CodeSection
        title="exit.py"
        subtitle="Exit signal logic"
        code={exitCode}
        language="python"
        isExpanded={expandedSection === 'exit'}
        onToggle={() => toggleSection('exit')}
        onCopy={() => copyToClipboard(exitCode)}
        onEdit={() => openInChat('exit.py')}
        lastModified="2 hours ago"
      />

      {/* Config.json */}
      <CodeSection
        title="config.json"
        subtitle="Strategy configuration"
        code={configJson}
        language="json"
        isExpanded={expandedSection === 'config'}
        onToggle={() => toggleSection('config')}
        onCopy={() => copyToClipboard(configJson)}
        onEdit={() => openInChat('config.json')}
        lastModified="2 hours ago"
      />
    </div>
  );
}

interface CodeSectionProps {
  title: string;
  subtitle: string;
  code: string;
  language: string;
  isExpanded: boolean;
  onToggle: () => void;
  onCopy: () => void;
  onEdit: () => void;
  lastModified: string;
}

function CodeSection({
  title,
  subtitle,
  code,
  language,
  isExpanded,
  onToggle,
  onCopy,
  onEdit,
  lastModified
}: CodeSectionProps) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div
        onClick={onToggle}
        className="bg-gray-50 px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-gray-400">{isExpanded ? '▼' : '▶'}</span>
          <div>
            <div className="font-mono font-semibold text-gray-900">{title}</div>
            <div className="text-xs text-gray-500">{subtitle}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Modified {lastModified}</span>
          <button
            onClick={(e) => { e.stopPropagation(); onCopy(); }}
            className="px-3 py-1 bg-white border border-gray-300 rounded text-xs hover:bg-gray-50 transition-colors"
          >
            📋 Copy
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(); }}
            className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 transition-colors"
          >
            ✏️ Edit in Chat
          </button>
        </div>
      </div>

      {/* Code Content */}
      {isExpanded && (
        <div className="bg-gray-900 p-4 overflow-x-auto">
          <pre className="text-sm text-gray-100 font-mono">
            <code className={`language-${language}`}>{code}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
