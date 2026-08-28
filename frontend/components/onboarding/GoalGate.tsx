'use client';

/**
 * GoalGate — sits between auth and the app. If the signed-in user has no active
 * goal yet, it offers the MeetFinch onboarding and persists the result
 * (PUT /goal). Soft gate: the wizard is skippable and a skip is remembered
 * per-user (localStorage), so a user who just wants in isn't walled on every
 * load. MissionCockpit still nudges them to set a mission later. Fail-open: any
 * error checking or saving the goal never blocks access to Finch.
 */
import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { goalApi, type SetGoalRequest } from '@/lib/api';
import MeetFinch from './MeetFinch';

const skipKey = (userId: string) => `finch:goal-wizard-skipped:${userId}`;

export default function GoalGate({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [checked, setChecked] = useState(false);
  const [needsGoal, setNeedsGoal] = useState(false);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      // A user who skipped onboarding shouldn't be re-prompted every load.
      let skipped = false;
      try { skipped = localStorage.getItem(skipKey(user.id)) === '1'; } catch { /* SSR / privacy mode */ }
      if (skipped) { if (!cancelled) { setNeedsGoal(false); setChecked(true); } return; }
      try {
        const goal = await goalApi.getGoal(user.id);
        if (!cancelled) setNeedsGoal(goal == null);
      } catch {
        if (!cancelled) setNeedsGoal(false); // fail open — never lock the user out
      } finally {
        if (!cancelled) setChecked(true);
      }
    })();
    return () => { cancelled = true; };
  }, [user]);

  const handleComplete = async (goal: SetGoalRequest) => {
    try {
      if (user) await goalApi.setGoal(user.id, goal);
    } catch {
      /* best effort — proceed into the app even if the save fails */
    }
    setNeedsGoal(false);
  };

  const handleSkip = () => {
    try { if (user) localStorage.setItem(skipKey(user.id), '1'); } catch { /* best effort */ }
    setNeedsGoal(false);
  };

  // AuthGate only mounts us once authenticated. While we check for a goal, hold
  // the app back so we don't flash the dashboard and then swap to the wizard.
  if (user && !checked) return null;
  if (needsGoal) return <MeetFinch onComplete={handleComplete} onSkip={handleSkip} />;
  return <>{children}</>;
}
