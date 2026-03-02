'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { skillsApi, type CatalogSkill } from '@/lib/api';
import { skillsCache } from '@/lib/skillsCache';

interface SkillsMenuProps {
  selectedSkillNames: string[];
  onSkillsChange: (names: string[]) => void;
  variant?: 'compact' | 'full';
}

export default function SkillsMenu({ selectedSkillNames, onSkillsChange, variant = 'full' }: SkillsMenuProps) {
  const { user } = useAuth();
  const [catalog, setCatalog] = useState<CatalogSkill[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) return;
    const cached = skillsCache.getCatalogSkills(user.id);
    if (cached) setCatalog(cached);
    skillsApi.listCatalog(user.id).then(data => {
      setCatalog(data);
      skillsCache.setCatalogSkills(user.id, data);
    }).catch(() => {});
  }, [user]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setIsOpen(false);
    };
    if (isOpen) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  // Skills that are always-on (enabled in DB)
  const alwaysOnSkills = useMemo(
    () => catalog.filter(s => s.enabled),
    [catalog]
  );

  // Skills manually added for this message only (not already always-on)
  const manualSkills = useMemo(
    () => selectedSkillNames
      .map(name => catalog.find(s => s.name === name))
      .filter((s): s is CatalogSkill => !!s && !s.enabled),
    [catalog, selectedSkillNames]
  );

  // Skills available to add manually (not enabled, not already manually selected)
  const addableSkills = useMemo(
    () => catalog.filter(s => !s.enabled && !selectedSkillNames.includes(s.name)),
    [catalog, selectedSkillNames]
  );

  const toggleManual = (skill: CatalogSkill) => {
    if (selectedSkillNames.includes(skill.name)) {
      onSkillsChange(selectedSkillNames.filter(n => n !== skill.name));
    } else {
      onSkillsChange([...selectedSkillNames, skill.name]);
      setIsOpen(false);
    }
  };

  const clearManual = () => onSkillsChange([]);

  const hasAnySkills = alwaysOnSkills.length > 0 || addableSkills.length > 0 || manualSkills.length > 0;
  if (!hasAnySkills) return null;

  const buttonSize = variant === 'compact' ? 'w-7 h-7' : 'w-8 h-8';

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {/* Always-on pills */}
      {alwaysOnSkills.map(skill => (
        <span
          key={skill.name}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-green-50 text-green-700 border border-green-200"
          title="Always enabled"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
          <span className="truncate max-w-[100px]">{skill.name}</span>
        </span>
      ))}

      {/* Manually added pills */}
      {manualSkills.map(skill => (
        <span
          key={skill.name}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-blue-50 text-blue-700 border border-blue-200"
        >
          <span className="truncate max-w-[100px]">{skill.name}</span>
          <button
            onClick={() => toggleManual(skill)}
            className="hover:opacity-70 ml-0.5"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </span>
      ))}

      {/* Add button */}
      {addableSkills.length > 0 && (
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className={`flex items-center justify-center ${buttonSize} rounded-lg transition-all ${
              isOpen ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
            title="Add skill for this message"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>

          {isOpen && (
            <div className="absolute bottom-full left-0 mb-2 w-56 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
              <div className="py-1">
                <div className="px-3 py-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wide">Add for this message</div>
                {addableSkills.map(skill => (
                  <button
                    key={skill.name}
                    onClick={() => toggleManual(skill)}
                    className="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center gap-2.5 transition-colors"
                  >
                    <div className="w-6 h-6 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 text-sm">
                      {skill.emoji ?? (
                        <svg className="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                      )}
                    </div>
                    <span className="text-sm text-gray-700 truncate">{skill.name}</span>
                  </button>
                ))}

                {manualSkills.length > 0 && (
                  <>
                    <div className="my-1 border-t border-gray-100" />
                    <button
                      onClick={clearManual}
                      className="w-full text-left px-3 py-2 hover:bg-red-50 text-red-500 flex items-center gap-2 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span className="text-sm">Clear added</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
