// Simple in-memory cache for catalog skills to avoid repeated API calls
import type { CatalogSkill } from './api';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

const CACHE_TTL_MS = 5000; // 5 seconds

class SkillsCache {
  private catalog: Map<string, CacheEntry<CatalogSkill[]>> = new Map();

  getCatalogSkills(userId: string): CatalogSkill[] | null {
    const entry = this.catalog.get(userId);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > CACHE_TTL_MS) { this.catalog.delete(userId); return null; }
    return entry.data;
  }

  setCatalogSkills(userId: string, skills: CatalogSkill[]) {
    this.catalog.set(userId, { data: skills, timestamp: Date.now() });
  }

  invalidateUser(userId: string) {
    this.catalog.delete(userId);
  }

  clearAll() {
    this.catalog.clear();
  }
}

export const skillsCache = new SkillsCache();

// @ts-ignore - expose for debugging
if (typeof window !== 'undefined') {
  (window as any).clearSkillsCache = () => skillsCache.clearAll();
}
