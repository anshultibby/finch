'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { strategiesApi } from '@/lib/api';
import type { Strategy, StrategyCodeResponse } from '@/lib/types';

interface CodeTabProps {
  strategy: Strategy;
}

export function CodeTab({ strategy }: CodeTabProps) {
  const { user } = useAuth();
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [codeData, setCodeData] = useState<StrategyCodeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadCode = async () => {
      if (!user?.id) return;
      setIsLoading(true);
      setError(null);
      try {
        const response = await strategiesApi.getStrategyCode(user.id, strategy.id);
        if (!response?.strategy_id) {
          throw new Error(response?.detail || 'Unable to load strategy code');
        }
        setCodeData(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load strategy code');
        setCodeData(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadCode();
  }, [user?.id, strategy.id]);

  const codeFiles = useMemo(() => {
    const files = codeData?.files || {};
    const entries = Object.entries(files).map(([filename, content]) => ({
      filename,
      content,
      language: getLanguageForFilename(filename),
      isGenerated: false,
    }));

    const hasConfigFile = entries.some(entry => entry.filename === 'config.json');
    const config = codeData?.config || strategy.config || {};
    if (!hasConfigFile) {
      entries.push({
        filename: 'config.json',
        content: JSON.stringify(config, null, 2),
        language: 'json',
        isGenerated: true,
      });
    }

    const entrypoint = codeData?.entrypoint;
    entries.sort((a, b) => {
      if (entrypoint && a.filename === entrypoint) return -1;
      if (entrypoint && b.filename === entrypoint) return 1;
      return a.filename.localeCompare(b.filename);
    });

    return entries;
  }, [codeData, strategy.config]);

  useEffect(() => {
    if (expandedSection || codeFiles.length === 0) return;
    setExpandedSection(codeFiles[0].filename);
  }, [codeFiles, expandedSection]);

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

  if (isLoading) {
    return (
      <div className="text-center py-12 text-gray-500">
        Loading strategy code...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-600">
        {error}
      </div>
    );
  }

  if (codeFiles.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No code files found for this strategy.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {codeFiles.map((file) => (
        <CodeSection
          key={file.filename}
          title={file.filename}
          subtitle={file.isGenerated ? 'Generated from strategy config' : 'Strategy file'}
          code={file.content}
          language={file.language}
          isExpanded={expandedSection === file.filename}
          onToggle={() => toggleSection(file.filename)}
          onCopy={() => copyToClipboard(file.content)}
          onEdit={() => openInChat(file.filename)}
          lastModified={file.isGenerated ? 'Generated' : 'From chat files'}
        />
      ))}
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

function getLanguageForFilename(filename: string) {
  const extension = filename.split('.').pop()?.toLowerCase();
  switch (extension) {
    case 'py':
      return 'python';
    case 'json':
      return 'json';
    case 'js':
      return 'javascript';
    case 'ts':
      return 'typescript';
    case 'md':
      return 'markdown';
    default:
      return 'text';
  }
}
