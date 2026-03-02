'use client';

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '@/contexts/AuthContext';
import { skillsApi, type CatalogSkill, type SkillFile } from '@/lib/api';
import { skillsCache } from '@/lib/skillsCache';

// ── Helpers ───────────────────────────────────────────────────────────────────

function extractMarkdownContent(content: string): string {
  if (content.trim().startsWith('---')) {
    const lines = content.split('\n');
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim() === '---') return lines.slice(i + 1).join('\n').trim();
    }
  }
  return content;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Toggle({ enabled, onToggle, size = 'md' }: { enabled: boolean; onToggle: () => void; size?: 'sm' | 'md' }) {
  const track = size === 'sm' ? 'h-4 w-7' : 'h-5 w-9';
  const knob = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5';
  const on = size === 'sm' ? 'translate-x-3.5' : 'translate-x-5';
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onToggle(); }}
      className={`relative inline-flex ${track} items-center rounded-full transition-colors focus:outline-none flex-shrink-0 ${
        enabled ? 'bg-green-500' : 'bg-gray-200'
      }`}
    >
      <span className={`inline-block ${knob} transform rounded-full bg-white shadow transition-transform ${
        enabled ? on : 'translate-x-1'
      }`} />
    </button>
  );
}

function SkillEmoji({ skill, size = 'md' }: { skill: CatalogSkill; size?: 'sm' | 'md' }) {
  const box = size === 'sm' ? 'w-8 h-8 text-lg' : 'w-10 h-10 text-xl';
  if (skill.emoji) {
    return (
      <div className={`${box} rounded-xl bg-gray-100 flex items-center justify-center flex-shrink-0`}>
        <span>{skill.emoji}</span>
      </div>
    );
  }
  const icon = size === 'sm' ? 'w-4 h-4' : 'w-5 h-5';
  return (
    <div className={`${box} rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0`}>
      <svg className={`${icon} text-white`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    </div>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="prose prose-slate max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-bold text-gray-900 mt-6 mb-4 pb-3 border-b border-gray-200">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-semibold text-gray-800 mt-6 mb-3">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-semibold text-gray-700 mt-5 mb-2">{children}</h3>,
          code: ({ children, className }) => {
            const isInline = !className?.includes('language-');
            return isInline ? (
              <code className="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded text-sm font-mono border border-gray-200">{children}</code>
            ) : (
              <pre className="bg-gray-900 text-gray-100 p-4 rounded-xl overflow-x-auto my-4 shadow-lg">
                <code className="text-sm font-mono leading-relaxed">{children}</code>
              </pre>
            );
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-xl border border-gray-200">
              <table className="min-w-full">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="px-4 py-2.5 bg-gray-50 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">{children}</th>,
          td: ({ children }) => <td className="px-4 py-2.5 text-sm text-gray-900 border-b border-gray-100">{children}</td>,
          tr: ({ children }) => <tr className="hover:bg-gray-50 transition-colors">{children}</tr>,
          blockquote: ({ children }) => <blockquote className="border-l-4 border-blue-400 pl-4 py-2 my-4 bg-blue-50/50 rounded-r-lg text-gray-700 italic">{children}</blockquote>,
          ul: ({ children }) => <ul className="list-disc list-outside ml-5 space-y-1.5 my-3 text-gray-700">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-outside ml-5 space-y-1.5 my-3 text-gray-700">{children}</ol>,
          p: ({ children }) => <p className="text-gray-700 leading-7 my-3">{children}</p>,
          a: ({ children, href }) => <a href={href} className="text-blue-600 hover:text-blue-800 hover:underline font-medium">{children}</a>,
          hr: () => <hr className="my-6 border-gray-200" />,
          li: ({ children }) => <li className="leading-7">{children}</li>,
        }}
      >
        {extractMarkdownContent(content)}
      </ReactMarkdown>
    </div>
  );
}

const FILE_TYPE_COLORS: Record<string, string> = {
  python: 'bg-blue-50 text-blue-700',
  markdown: 'bg-gray-100 text-gray-600',
  javascript: 'bg-yellow-50 text-yellow-700',
  typescript: 'bg-blue-50 text-blue-700',
  json: 'bg-orange-50 text-orange-700',
  yaml: 'bg-purple-50 text-purple-700',
  bash: 'bg-green-50 text-green-700',
  text: 'bg-gray-100 text-gray-600',
};

type VirtualFile = { id: string; filename: string; file_type: string | null; content: string };

function buildFileList(skill: CatalogSkill): VirtualFile[] {
  return [
    { id: '__skill_md__', filename: 'SKILL.md', file_type: 'markdown', content: skill.content },
    ...(skill.files ?? []).map((f: SkillFile) => ({ id: f.filename, filename: f.filename, file_type: f.file_type, content: f.content })),
  ];
}

// ── Detail panel (right pane) ─────────────────────────────────────────────────

function SkillDetail({
  skill,
  onToggle,
  toggling,
}: {
  skill: CatalogSkill;
  onToggle: (enabled: boolean) => void;
  toggling: boolean;
}) {
  const [selectedFileId, setSelectedFileId] = useState<string>('__skill_md__');
  const files = buildFileList(skill);
  const activeFile = files.find(f => f.id === selectedFileId) ?? files[0];

  // Reset to SKILL.md when skill changes
  useEffect(() => { setSelectedFileId('__skill_md__'); }, [skill.name]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <SkillEmoji skill={skill} />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base font-semibold text-gray-900">{skill.name}</h2>
              {skill.is_system && (
                <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-600 text-[10px] font-semibold rounded-full border border-indigo-100">System</span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              {skill.category && (
                <span className="text-xs text-gray-400 capitalize">{skill.category.replace(/_/g, ' ')}</span>
              )}
              {skill.homepage && (
                <a href={skill.homepage} target="_blank" rel="noopener noreferrer"
                  className="text-xs text-blue-500 hover:text-blue-700 transition-colors">
                  Docs ↗
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Toggle */}
        <div className="flex items-center gap-2.5 flex-shrink-0 ml-4">
          <span className={`text-sm font-medium ${skill.enabled ? 'text-green-700' : 'text-gray-400'}`}>
            {skill.enabled ? 'Enabled' : 'Disabled'}
          </span>
          <Toggle
            enabled={skill.enabled}
            onToggle={() => !toggling && onToggle(!skill.enabled)}
          />
        </div>
      </div>

      {/* Two-pane body: file tree + content */}
      <div className="flex flex-1 min-h-0">
        {/* File tree — only shown when multiple files */}
        {files.length > 1 && (
          <div className="w-48 border-r border-gray-100 flex-shrink-0 overflow-y-auto bg-gray-50/60 py-2">
            {files.map(file => (
              <button
                key={file.id}
                onClick={() => setSelectedFileId(file.id)}
                className={`w-full text-left flex items-center gap-2 px-3 py-2 transition-colors ${
                  activeFile?.id === file.id
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <svg className="w-3.5 h-3.5 flex-shrink-0 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-xs font-mono truncate">{file.filename}</span>
              </button>
            ))}
          </div>
        )}

        {/* File content */}
        <div className="flex-1 overflow-y-auto min-w-0">
          {activeFile && (
            activeFile.file_type === 'markdown' ? (
              <div className="px-7 py-6">
                <MarkdownRenderer content={activeFile.content} />
              </div>
            ) : (
              <div className="h-full">
                <div className="flex items-center gap-2 px-5 py-2.5 border-b border-gray-100 bg-gray-50/50">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ${FILE_TYPE_COLORS[activeFile.file_type ?? 'text'] ?? 'bg-gray-100 text-gray-600'}`}>
                    {activeFile.file_type ?? 'text'}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">{activeFile.filename}</span>
                </div>
                <pre className="p-5 text-xs font-mono text-gray-800 leading-relaxed overflow-x-auto whitespace-pre-wrap break-words">
                  {activeFile.content}
                </pre>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function SkillsPanel() {
  const { user } = useAuth();
  const [skills, setSkills] = useState<CatalogSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<CatalogSkill | null>(null);
  const [toggling, setToggling] = useState<Set<string>>(new Set()); // keyed by skill name
  const [search, setSearch] = useState('');

  useEffect(() => { if (user) load(); }, [user]);

  const load = async () => {
    if (!user) return;
    const cached = skillsCache.getCatalogSkills(user.id);
    if (cached) { setSkills(cached); setLoading(false); }
    try {
      const data = await skillsApi.listCatalog(user.id);
      setSkills(data);
      skillsCache.setCatalogSkills(user.id, data);
    } finally { setLoading(false); }
  };

  const handleToggle = async (skill: CatalogSkill, enabled: boolean) => {
    if (!user) return;
    setToggling(prev => { const next = new Set(prev); next.add(skill.name); return next; });

    // Optimistic update
    const update = (list: CatalogSkill[]) =>
      list.map(s => s.name === skill.name ? { ...s, enabled } : s);
    setSkills(prev => update(prev));
    if (selected?.name === skill.name) setSelected(s => s ? { ...s, enabled } : s);

    try {
      const updated = await skillsApi.toggleCatalogSkill(user.id, skill.name, enabled);
      const merge = (list: CatalogSkill[]) =>
        list.map(s => s.name === updated.name ? updated : s);
      setSkills(prev => merge(prev));
      skillsCache.invalidateUser(user.id);
      if (selected?.name === updated.name) setSelected(updated);
    } finally {
      setToggling(prev => { const next = new Set(prev); next.delete(skill.name); return next; });
    }
  };

  const filteredSkills = skills.filter(s =>
    !search || s.name.toLowerCase().includes(search.toLowerCase()) || s.description.toLowerCase().includes(search.toLowerCase())
  );

  const enabledCount = skills.filter(s => s.enabled).length;


  return (
    <div className="flex flex-col h-full bg-white">
      {/* Panel header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0 bg-gray-50/50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-gray-900">Skills</h2>
            {!loading && (
              <p className="text-xs text-gray-400">
                {enabledCount} of {skills.length} enabled
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Left: skill list */}
        <div className="w-72 border-r border-gray-200 flex flex-col flex-shrink-0 bg-gray-50/30">
          {/* Search */}
          <div className="p-3 border-b border-gray-200">
            <div className="relative">
              <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search skills…"
                className="w-full pl-8 pr-3 py-1.5 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto py-2 px-2">
            {loading ? (
              <div className="space-y-2 px-1 pt-1">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-16 bg-gray-200 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : filteredSkills.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <p className="text-sm text-gray-500">No skills found</p>
              </div>
            ) : (
              <div className="space-y-1">
                {filteredSkills.map(skill => (
                  <button
                    key={skill.name}
                    onClick={() => setSelected(skill)}
                    className={`group w-full text-left px-3 py-2.5 rounded-xl transition-all flex items-center gap-3 ${
                      selected?.name === skill.name
                        ? 'bg-white shadow-sm ring-1 ring-gray-200'
                        : 'hover:bg-white hover:shadow-sm'
                    }`}
                  >
                    <SkillEmoji skill={skill} size="sm" />

                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-800 truncate">{skill.name}</p>
                      <p className="text-xs text-gray-400 truncate mt-0.5">{skill.description}</p>
                    </div>

                    <Toggle
                      enabled={skill.enabled}
                      onToggle={() => handleToggle(skill, !skill.enabled)}
                      size="sm"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: detail / empty state */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {selected ? (
            <SkillDetail
              skill={selected}
              onToggle={(enabled) => handleToggle(selected, enabled)}
              toggling={toggling.has(selected.name)}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-8">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center mb-4 ring-1 ring-blue-100">
                <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-gray-900">Select a skill</h3>
              <p className="text-sm text-gray-500 mt-1.5 max-w-xs">Toggle skills on to make them available in every chat, or pick them per message.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
