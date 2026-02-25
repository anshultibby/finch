// Simple in-memory cache for skills to avoid repeated API calls
import type { Skill, GlobalSkill } from './api';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

const CACHE_TTL_MS = 30000; // 30 seconds - keeps data fresh but avoids hammering the API

class SkillsCache {
  private userSkills: Map<string, CacheEntry<Skill[]>> = new Map();
  private storeSkills: Map<string, CacheEntry<GlobalSkill[]>> = new Map();
  private globalSkillsList: CacheEntry<GlobalSkill[]> | null = null;

  // Get cached user skills if fresh
  getUserSkills(userId: string): Skill[] | null {
    const entry = this.userSkills.get(userId);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
      this.userSkills.delete(userId);
      return null;
    }
    return entry.data;
  }

  // Cache user skills
  setUserSkills(userId: string, skills: Skill[]) {
    this.userSkills.set(userId, { data: skills, timestamp: Date.now() });
  }

  // Get cached store skills by category
  getStoreSkills(category?: string): GlobalSkill[] | null {
    const key = category || '__all__';
    const entry = this.storeSkills.get(key);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
      this.storeSkills.delete(key);
      return null;
    }
    return entry.data;
  }

  // Cache store skills
  setStoreSkills(category: string | undefined, skills: GlobalSkill[]) {
    const key = category || '__all__';
    this.storeSkills.set(key, { data: skills, timestamp: Date.now() });
  }

  // Invalidate cache for a user (call after create/update/delete/install)
  invalidateUser(userId: string) {
    this.userSkills.delete(userId);
  }

  // Invalidate all user caches
  invalidateAllUsers() {
    this.userSkills.clear();
  }

  // Invalidate store cache
  invalidateStore() {
    this.storeSkills.clear();
    this.globalSkillsList = null;
  }
}

export const skillsCache = new SkillsCache();
