'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { skillsApi, type CatalogSkill } from '@/lib/api';
import { skillsCache } from '@/lib/skillsCache';

export default function SkillsPanel() {
  const { user } = useAuth();
  const [skills, setSkills] = useState<CatalogSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.id) return;
    const cached = skillsCache.getCatalogSkills(user.id);
    if (cached) {
      setSkills(cached);
      setLoading(false);
      return;
    }
    setLoading(true);
    skillsApi.listCatalog(user.id)
      .then(data => {
        setSkills(data);
        skillsCache.setCatalogSkills(user.id, data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user?.id]);

  const toggle = async (skill: CatalogSkill) => {
    if (!user?.id || toggling) return;
    setToggling(skill.name);
    try {
      const updated = await skillsApi.toggleCatalogSkill(user.id, skill.name, !skill.enabled);
      setSkills(prev => prev.map(s => s.name === updated.name ? updated : s));
      skillsCache.invalidateUser(user.id);
    } catch {}
    finally { setToggling(null); }
  };

  const grouped = skills.reduce<Record<string, CatalogSkill[]>>((acc, s) => {
    const cat = s.category || 'other';
    (acc[cat] = acc[cat] || []).push(s);
    return acc;
  }, {});

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center px-6 py-4 border-b border-gray-200 flex-shrink-0">
        <h2 className="text-base font-semibold text-gray-900">Skills</h2>
        <span className="ml-2 text-xs text-gray-400">{skills.filter(s => s.enabled).length} active</span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-5">
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
          </div>
        ) : skills.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-16">
            <div className="text-4xl mb-3">💡</div>
            <p className="text-sm text-gray-500">No skills available.</p>
          </div>
        ) : (
          Object.entries(grouped).map(([category, items]) => (
            <div key={category}>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-1 capitalize">{category}</p>
              <div className="space-y-1">
                {items.map(skill => (
                  <div
                    key={skill.name}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-gray-100 hover:border-gray-200 hover:bg-gray-50 transition-all"
                  >
                    <span className="text-xl flex-shrink-0">{skill.emoji || '🔧'}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{skill.name}</p>
                      <p className="text-xs text-gray-400 truncate mt-0.5">{skill.description}</p>
                    </div>
                    <button
                      onClick={() => toggle(skill)}
                      disabled={toggling === skill.name}
                      className={`relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full transition-colors focus:outline-none disabled:opacity-50 ${
                        skill.enabled ? 'bg-blue-600' : 'bg-gray-200'
                      }`}
                    >
                      <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                        skill.enabled ? 'translate-x-5' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
