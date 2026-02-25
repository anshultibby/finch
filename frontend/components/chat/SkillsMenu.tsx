'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { skillsApi, type Skill } from '@/lib/api';
import { skillsCache } from '@/lib/skillsCache';

interface SkillsMenuProps {
  selectedSkillIds: string[];
  onSkillsChange: (ids: string[]) => void;
  variant?: 'compact' | 'full';
}

export default function SkillsMenu({ selectedSkillIds, onSkillsChange, variant = 'full' }: SkillsMenuProps) {
  const { user } = useAuth();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Load skills
  useEffect(() => {
    if (!user) return;
    const cached = skillsCache.getUserSkills(user.id);
    if (cached) setSkills(cached);
    skillsApi.list(user.id).then(data => {
      setSkills(data);
      skillsCache.setUserSkills(user.id, data);
    }).catch(() => {});
  }, [user]);

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  // Organize skills
  const { selectedSkills, availableSkills } = useMemo(() => {
    const selected = selectedSkillIds
      .map(id => skills.find(s => s.id === id))
      .filter((s): s is Skill => !!s);
    const available = skills.filter(s => !selectedSkillIds.includes(s.id));
    return { selectedSkills: selected, availableSkills: available };
  }, [skills, selectedSkillIds]);

  const toggleSkill = (skill: Skill) => {
    if (selectedSkillIds.includes(skill.id)) {
      onSkillsChange(selectedSkillIds.filter(id => id !== skill.id));
    } else {
      onSkillsChange([...selectedSkillIds, skill.id]);
      setIsOpen(false);
    }
  };

  const clearAll = () => onSkillsChange([]);

  if (skills.length === 0) return null;

  // Compact variant - just the plus button with pills beside it
  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        {/* Plus button */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className={`flex items-center justify-center w-7 h-7 rounded-lg transition-all ${
              isOpen ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
            title="Add skills"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>

          {/* Dropdown */}
          {isOpen && (
            <div className="absolute bottom-full left-0 mb-2 w-64 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
              <div className="py-1">
                <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Skills</div>

                {availableSkills.length === 0 && selectedSkills.length === 0 ? (
                  <div className="px-3 py-3 text-sm text-gray-400">No skills available</div>
                ) : (
                  <>
                    {selectedSkills.map(skill => (
                      <button key={skill.id} onClick={() => toggleSkill(skill)} className="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center gap-3">
                        <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span className="text-sm text-gray-900">{skill.name}</span>
                        {skill.enabled && <span className="text-[10px] text-green-600 bg-green-50 px-1 rounded">always</span>}
                      </button>
                    ))}

                    {selectedSkills.length > 0 && availableSkills.length > 0 && <div className="my-1 border-t border-gray-100" />}

                    {availableSkills.map(skill => (
                      <button key={skill.id} onClick={() => toggleSkill(skill)} className="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center gap-3">
                        <div className="w-4" />
                        <span className="text-sm text-gray-700">{skill.name}</span>
                        {skill.enabled && <span className="text-[10px] text-green-600 bg-green-50 px-1 rounded">always</span>}
                      </button>
                    ))}

                    {selectedSkills.length > 0 && (
                      <>
                        <div className="my-1 border-t border-gray-100" />
                        <button onClick={clearAll} className="w-full text-left px-3 py-2 hover:bg-red-50 text-red-600 flex items-center gap-3">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                          <span className="text-sm">Clear all</span>
                        </button>
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Selected pills */}
        {selectedSkills.map(skill => (
          <span
            key={skill.id}
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${
              skill.enabled ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-blue-50 text-blue-700 border border-blue-200'
            }`}
          >
            {skill.enabled && <span className="w-1 h-1 rounded-full bg-green-500" />}
            <span className="truncate max-w-[100px]">{skill.name}</span>
            <button onClick={() => toggleSkill(skill)} className="hover:opacity-70">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </span>
        ))}
      </div>
    );
  }

  // Full variant - pills below input (for ChatInput)
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Plus button */}
      <div className="relative" ref={menuRef}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={`flex items-center justify-center w-8 h-8 rounded-lg transition-all ${
            isOpen ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'
          }`}
          title="Add skills"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>

        {isOpen && (
          <div className="absolute bottom-full left-0 mb-2 w-64 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
            <div className="py-1">
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Skills</div>

              {availableSkills.length === 0 && selectedSkills.length === 0 ? (
                <div className="px-3 py-3 text-sm text-gray-400">No skills available</div>
              ) : (
                <>
                  {selectedSkills.map(skill => (
                    <button key={skill.id} onClick={() => toggleSkill(skill)} className="w-full text-left px-3 py-2.5 hover:bg-gray-50 flex items-center gap-3">
                      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-sm text-gray-900">{skill.name}</span>
                      {skill.enabled && <span className="text-[10px] text-green-600 bg-green-50 px-1.5 rounded">always</span>}
                    </button>
                  ))}

                  {selectedSkills.length > 0 && availableSkills.length > 0 && <div className="my-1 border-t border-gray-100" />}

                  {availableSkills.map(skill => (
                    <button key={skill.id} onClick={() => toggleSkill(skill)} className="w-full text-left px-3 py-2.5 hover:bg-gray-50 flex items-center gap-3">
                      <div className="w-4" />
                      <span className="text-sm text-gray-700">{skill.name}</span>
                      {skill.enabled && <span className="text-[10px] text-green-600 bg-green-50 px-1.5 rounded">always</span>}
                    </button>
                  ))}

                  {selectedSkills.length > 0 && (
                    <>
                      <div className="my-1 border-t border-gray-100" />
                      <button onClick={clearAll} className="w-full text-left px-3 py-2.5 hover:bg-red-50 text-red-600 flex items-center gap-3">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        <span className="text-sm">Clear all skills</span>
                      </button>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Selected pills */}
      {selectedSkills.map(skill => (
        <span
          key={skill.id}
          className={`inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full text-xs font-medium ${
            skill.enabled ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-blue-50 text-blue-700 border border-blue-200'
          }`}
        >
          {skill.enabled && <span className="w-1.5 h-1.5 rounded-full bg-green-500" />}
          <span className="truncate max-w-[120px]">{skill.name}</span>
          <button onClick={() => toggleSkill(skill)} className="p-0.5 rounded-full hover:bg-white/50 transition-colors">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </span>
      ))}
    </div>
  );
}
