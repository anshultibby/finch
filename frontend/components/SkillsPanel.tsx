'use client';

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '@/contexts/AuthContext';
import { skillsApi, type Skill, type GlobalSkill } from '@/lib/api';
import { skillsCache } from '@/lib/skillsCache';

type Tab = 'mine' | 'store';

const EMPTY_FORM = { name: '', description: '', content: '', enabled: false };
const STORE_CATEGORIES = ['All', 'trading', 'research', 'analysis', 'risk', 'other'];

// Extract markdown content from skill content (strip YAML frontmatter)
function extractMarkdownContent(content: string): string {
  // Check if content starts with YAML frontmatter
  if (content.trim().startsWith('---')) {
    const lines = content.split('\n');
    let endIndex = -1;
    // Find the closing ---
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim() === '---') {
        endIndex = i;
        break;
      }
    }
    if (endIndex !== -1) {
      // Return everything after the frontmatter
      return lines.slice(endIndex + 1).join('\n').trim();
    }
  }
  return content;
}

// Markdown renderer component with nice styling
function MarkdownRenderer({ content }: { content: string }) {
  const cleanContent = extractMarkdownContent(content);

  return (
    <div className="prose prose-sm prose-slate max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-bold text-gray-900 mt-6 mb-4 pb-2 border-b border-gray-200">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-semibold text-gray-800 mt-5 mb-3">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-semibold text-gray-700 mt-4 mb-2">{children}</h3>,
          code: ({ children, className }) => {
            const isInline = !className?.includes('language-');
            return isInline ? (
              <code className="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded text-sm font-mono">{children}</code>
            ) : (
              <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto my-4">
                <code className="text-sm font-mono leading-relaxed">{children}</code>
              </pre>
            );
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full border border-gray-200 rounded-lg overflow-hidden">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="px-4 py-2 bg-gray-50 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">{children}</th>,
          td: ({ children }) => <td className="px-4 py-2 text-sm text-gray-900 border-b border-gray-100">{children}</td>,
          tr: ({ children }) => <tr className="hover:bg-gray-50">{children}</tr>,
          blockquote: ({ children }) => <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-4 bg-blue-50 text-gray-700 italic">{children}</blockquote>,
          ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-3 text-gray-700">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-3 text-gray-700">{children}</ol>,
          p: ({ children }) => <p className="text-gray-700 leading-relaxed my-2">{children}</p>,
          a: ({ children, href }) => <a href={href} className="text-blue-600 hover:text-blue-800 hover:underline">{children}</a>,
          hr: () => <hr className="my-6 border-gray-200" />,
        }}
      >
        {cleanContent}
      </ReactMarkdown>
    </div>
  );
}

function Toggle({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
        enabled ? 'bg-blue-600' : 'bg-gray-300'
      }`}
    >
      <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
        enabled ? 'translate-x-5' : 'translate-x-1'
      }`} />
    </button>
  );
}

// Skill Preview Modal for Store
function SkillPreviewModal({ skill, isOpen, onClose, onInstall, isInstalling, isInstalled }: {
  skill: GlobalSkill | null;
  isOpen: boolean;
  onClose: () => void;
  onInstall: () => void;
  isInstalling: boolean;
  isInstalled: boolean;
}) {
  if (!isOpen || !skill) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-indigo-600">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{skill.name}</h2>
              <div className="flex items-center gap-2 mt-1">
                {skill.is_official && (
                  <span className="px-2 py-0.5 bg-blue-500/30 text-blue-100 text-xs font-medium rounded-full">
                    Official
                  </span>
                )}
                {skill.category && (
                  <span className="text-blue-100 text-xs capitalize">{skill.category}</span>
                )}
                <span className="text-blue-100/70 text-xs">• {skill.install_count} installs</span>
              </div>
            </div>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white p-2 rounded-lg hover:bg-white/10 transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          <div className="p-6">
            {/* Description Section */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-2">Description</h3>
              <p className="text-gray-700 leading-relaxed bg-white p-4 rounded-xl border border-gray-200">
                {skill.description}
              </p>
            </div>

            {/* Instructions Section */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-2">Skill Instructions</h3>
              <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                <MarkdownRenderer content={skill.content} />
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-white flex items-center justify-between">
          <span className="text-sm text-gray-500">
            Previewing skill content before installation
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onInstall}
              disabled={isInstalled || isInstalling}
              className={`px-6 py-2 text-sm font-medium rounded-lg transition-all flex items-center gap-2 ${
                isInstalled
                  ? 'bg-green-100 text-green-700 cursor-default'
                  : isInstalling
                  ? 'bg-gray-100 text-gray-400 cursor-wait'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 shadow-md hover:shadow-lg'
              }`}
            >
              {isInstalled ? (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Installed
                </>
              ) : isInstalling ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Installing…
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Install Skill
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function MySkillsTab({ installedIds }: { installedIds: Set<string> }) {
  const { user } = useAuth();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Skill | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState(false);

  useEffect(() => { load(true); }, [user]); // Try cache first on mount
  useEffect(() => { if (installedIds.size > 0) load(false); }, [installedIds.size]); // Force refresh after install

  const load = async (useCache = false) => {
    if (!user) return;

    // Try cache first
    if (useCache) {
      const cached = skillsCache.getUserSkills(user.id);
      if (cached) {
        setSkills(cached);
        setLoading(false);
        return; // Fast path - no API call needed
      }
    }

    setLoading(true);
    try {
      const data = await skillsApi.list(user.id);
      setSkills(data);
      skillsCache.setUserSkills(user.id, data); // Update cache
    } finally {
      setLoading(false);
    }
  };

  const startNew = () => { setSelected(null); setIsNew(true); setForm(EMPTY_FORM); setError(null); setPreviewMode(false); };
  const selectSkill = (skill: Skill) => {
    setSelected(skill); setIsNew(false);
    setForm({ name: skill.name, description: skill.description, content: skill.content, enabled: skill.enabled });
    setError(null); setPreviewMode(false);
  };
  const cancel = () => { setSelected(null); setIsNew(false); setForm(EMPTY_FORM); setError(null); setPreviewMode(false); };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setSaving(true); setError(null);
    try {
      if (isNew) {
        const skill = await skillsApi.create(user.id, form);
        setSkills(prev => [skill, ...prev]);
        skillsCache.invalidateUser(user.id); // Invalidate cache
        selectSkill(skill); setIsNew(false);
      } else if (selected) {
        const skill = await skillsApi.update(user.id, selected.id, form);
        setSkills(prev => prev.map(s => s.id === skill.id ? skill : s));
        skillsCache.invalidateUser(user.id); // Invalidate cache
        setSelected(skill);
      }
    } catch { setError('Failed to save. Please try again.'); }
    finally { setSaving(false); }
  };

  const toggle = async (skill: Skill) => {
    if (!user) return;
    const updated = await skillsApi.update(user.id, skill.id, { enabled: !skill.enabled });
    setSkills(prev => prev.map(s => s.id === updated.id ? updated : s));
    skillsCache.invalidateUser(user.id); // Invalidate cache
    if (selected?.id === skill.id) setSelected(updated);
  };

  const remove = async (skill: Skill) => {
    if (!user || !confirm(`Delete "${skill.name}"?`)) return;
    await skillsApi.delete(user.id, skill.id);
    setSkills(prev => prev.filter(s => s.id !== skill.id));
    skillsCache.invalidateUser(user.id); // Invalidate cache
    if (selected?.id === skill.id) cancel();
  };

  const showEditor = isNew || selected !== null;

  return (
    <div className="flex flex-1 min-h-0">
      {/* Left: skill list */}
      <div className="w-56 border-r border-gray-100 flex flex-col flex-shrink-0">
        <div className="p-3">
          <button
            onClick={startNew}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Skill
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <p className="text-xs text-gray-400 text-center py-8">Loading…</p>
          ) : skills.length === 0 && !isNew ? (
            <div className="px-4 py-6 text-center">
              <p className="text-xs text-gray-400">No skills yet.</p>
              <button onClick={startNew} className="text-xs text-blue-600 hover:underline mt-1">Create your first skill</button>
            </div>
          ) : (
            <>
              {isNew && (
                <div className="mx-2 mb-1 px-3 py-2.5 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-xs font-medium text-blue-700 truncate">{form.name || 'Untitled Skill'}</p>
                  <p className="text-xs text-blue-500 mt-0.5">Unsaved</p>
                </div>
              )}
              {skills.map(skill => (
                <button
                  key={skill.id}
                  onClick={() => selectSkill(skill)}
                  className={`w-full text-left px-3 py-2.5 flex items-start gap-2 hover:bg-gray-50 transition-colors ${
                    selected?.id === skill.id && !isNew ? 'bg-gray-100' : ''
                  }`}
                >
                  <div className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${skill.enabled ? 'bg-green-500' : 'bg-gray-300'}`} />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{skill.name}</p>
                    {skill.source_id && <p className="text-xs text-gray-400">from store</p>}
                  </div>
                </button>
              ))}
            </>
          )}
        </div>
      </div>

      {/* Right: editor / preview */}
      <div className="flex-1 flex flex-col min-h-0">
        {!showEditor ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
            <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-700">Select a skill to edit</p>
            <p className="text-xs text-gray-400 mt-1 max-w-xs">Custom instructions injected into the agent when you use them in chat.</p>
            <button onClick={startNew} className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors">
              Create Skill
            </button>
          </div>
        ) : previewMode ? (
          /* Preview Mode with Markdown */
          <div className="flex flex-col flex-1 min-h-0">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-sm font-semibold text-gray-900">Preview: {form.name || 'Untitled'}</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPreviewMode(false)}
                  className="px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-800 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Back to Editor
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
              <div className="max-w-4xl mx-auto bg-white rounded-xl border border-gray-200 p-8 shadow-sm">
                <MarkdownRenderer content={form.content} />
              </div>
            </div>
          </div>
        ) : (
          /* Editor Mode */
          <form onSubmit={save} className="flex flex-col flex-1 min-h-0">
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-900">{isNew ? 'New Skill' : 'Edit Skill'}</h3>
                <div className="flex items-center gap-3">
                  {/* Preview Toggle */}
                  <button
                    type="button"
                    onClick={() => setPreviewMode(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-800 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    Preview
                  </button>
                  {selected && !isNew && (
                    <>
                      <div className="flex items-center gap-2">
                        <Toggle enabled={selected.enabled} onToggle={() => toggle(selected)} />
                        <span className="text-xs text-gray-500">{selected.enabled ? 'Always on' : 'Manual'}</span>
                      </div>
                      <button type="button" onClick={() => remove(selected)} className="text-xs text-red-400 hover:text-red-600 transition-colors">
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </div>

              {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Name</label>
                <input required maxLength={100} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="momentum-trader"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-400 mt-1">You'll pick this by name when starting a chat</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Description</label>
                <input required maxLength={1024} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                  placeholder="What it does and when to use it"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Instructions</label>
                <textarea required rows={13} value={form.content} onChange={e => setForm({ ...form, content: e.target.value })}
                  placeholder={`When analyzing any trade or setup:\n\n- Prioritize momentum: look for price above 20-day MA with volume > 2x average\n- Always state the entry trigger, stop loss, and target\n- Risk/reward must be at least 2:1`}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
                <p className="text-xs text-gray-400 mt-1">Injected verbatim into the agent's system prompt. Use Preview to see how it renders.</p>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-100 flex items-center gap-3 flex-shrink-0">
              <button type="submit" disabled={saving}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
                {saving ? 'Saving…' : isNew ? 'Create Skill' : 'Save Changes'}
              </button>
              <button type="button" onClick={cancel} className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function StoreTab({ onInstall }: { onInstall: (id: string) => void }) {
  const { user } = useAuth();
  const [skills, setSkills] = useState<GlobalSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('All');
  const [installing, setInstalling] = useState<Set<string>>(new Set());
  const [installed, setInstalled] = useState<Set<string>>(new Set());
  const [userSkillSources, setUserSkillSources] = useState<Set<string>>(new Set());

  // Preview modal state
  const [previewSkill, setPreviewSkill] = useState<GlobalSkill | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  useEffect(() => { load(true); loadUserSources(true); }, []);
  useEffect(() => { load(true); }, [category]);

  const load = async (useCache = false) => {
    // Try cache first
    if (useCache) {
      const cached = skillsCache.getStoreSkills(category === 'All' ? undefined : category);
      if (cached) {
        setSkills(cached);
        setLoading(false);
        return;
      }
    }

    setLoading(true);
    try {
      const data = await skillsApi.listStore(category === 'All' ? undefined : category);
      setSkills(data);
      skillsCache.setStoreSkills(category === 'All' ? undefined : category, data);
    } finally { setLoading(false); }
  };

  const loadUserSources = async (useCache = false) => {
    if (!user) return;

    // Try user skills cache first
    if (useCache) {
      const cached = skillsCache.getUserSkills(user.id);
      if (cached) {
        setUserSkillSources(new Set(cached.map(s => s.source_id).filter(Boolean) as string[]));
        return;
      }
    }

    const userSkills = await skillsApi.list(user.id);
    setUserSkillSources(new Set(userSkills.map(s => s.source_id).filter(Boolean) as string[]));
    skillsCache.setUserSkills(user.id, userSkills);
  };

  const install = async (skill: GlobalSkill) => {
    if (!user) return;
    setInstalling(prev => new Set([...prev, skill.id]));
    try {
      await skillsApi.install(user.id, skill.id);
      setInstalled(prev => new Set([...prev, skill.id]));
      setUserSkillSources(prev => new Set([...prev, skill.id]));
      skillsCache.invalidateUser(user.id); // Invalidate user skills cache
      onInstall(skill.id);
      setSkills(prev => prev.map(s => s.id === skill.id ? { ...s, install_count: s.install_count + 1 } : s));
    } catch (e: any) {
      if (e.message === 'already_installed') setInstalled(prev => new Set([...prev, skill.id]));
    } finally {
      setInstalling(prev => { const next = new Set(prev); next.delete(skill.id); return next; });
    }
  };

  const isInstalled = (id: string) => installed.has(id) || userSkillSources.has(id);

  const openPreview = (skill: GlobalSkill) => {
    setPreviewSkill(skill);
    setIsPreviewOpen(true);
  };

  const closePreview = () => {
    setIsPreviewOpen(false);
    setPreviewSkill(null);
  };

  const handleInstallFromPreview = async () => {
    if (!previewSkill) return;
    await install(previewSkill);
  };

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="px-6 py-3 border-b border-gray-100 flex gap-2 overflow-x-auto flex-shrink-0">
        {STORE_CATEGORIES.map(cat => (
          <button key={cat} onClick={() => setCategory(cat)}
            className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-colors capitalize ${
              category === cat ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading ? (
          <div className="grid grid-cols-2 gap-3">
            {[...Array(4)].map((_, i) => <div key={i} className="h-36 bg-gray-100 rounded-xl animate-pulse" />)}
          </div>
        ) : skills.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-16">
            <p className="text-sm text-gray-500">No skills in this category yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {skills.map(skill => (
              <div key={skill.id} className="border border-gray-200 rounded-xl p-4 hover:border-gray-300 hover:shadow-sm transition-all flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm font-semibold text-gray-900 truncate">{skill.name}</p>
                      {skill.is_official && (
                        <span className="flex-shrink-0 px-1.5 py-0.5 bg-blue-100 text-blue-700 text-[10px] font-semibold rounded-full">Official</span>
                      )}
                    </div>
                    {skill.category && <p className="text-xs text-gray-400 capitalize mt-0.5">{skill.category}</p>}
                  </div>
                </div>
                <p className="text-xs text-gray-600 line-clamp-2 flex-1">{skill.description}</p>
                <div className="flex items-center justify-between mt-auto pt-1">
                  <span className="text-xs text-gray-400">{skill.install_count} installs</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openPreview(skill)}
                      className="px-2 py-1 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                    >
                      Preview
                    </button>
                    <button
                      onClick={() => install(skill)}
                      disabled={isInstalled(skill.id) || installing.has(skill.id)}
                      className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors ${
                        isInstalled(skill.id) ? 'bg-green-100 text-green-700 cursor-default'
                        : installing.has(skill.id) ? 'bg-gray-100 text-gray-400 cursor-wait'
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                      }`}
                    >
                      {isInstalled(skill.id) ? '✓ Installed' : installing.has(skill.id) ? 'Installing…' : 'Install'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Skill Preview Modal */}
      <SkillPreviewModal
        skill={previewSkill}
        isOpen={isPreviewOpen}
        onClose={closePreview}
        onInstall={handleInstallFromPreview}
        isInstalling={previewSkill ? installing.has(previewSkill.id) : false}
        isInstalled={previewSkill ? isInstalled(previewSkill.id) : false}
      />
    </div>
  );
}

export default function SkillsPanel() {
  const [tab, setTab] = useState<Tab>('mine');
  const [installedIds, setInstalledIds] = useState<Set<string>>(new Set());

  const handleInstall = (id: string) => {
    setInstalledIds(prev => new Set([...prev, id]));
    setTab('mine');
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Panel header */}
      <div className="flex items-center gap-4 px-6 py-4 border-b border-gray-200 flex-shrink-0">
        <h2 className="text-base font-semibold text-gray-900">Skills</h2>
        <div className="flex bg-gray-100 rounded-lg p-0.5 gap-0.5">
          {(['mine', 'store'] as Tab[]).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                tab === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'mine' ? 'My Skills' : 'Store'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col flex-1 min-h-0">
        {tab === 'mine' && <MySkillsTab installedIds={installedIds} />}
        {tab === 'store' && <StoreTab onInstall={handleInstall} />}
      </div>
    </div>
  );
}
