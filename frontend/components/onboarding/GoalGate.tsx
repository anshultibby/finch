'use client';

/**
 * GoalGate — sits between auth and the app. If the signed-in user has no active
 * goal yet, it shows the conversational GoalWizard first and persists the result
 * (PUT /goal) before letting them into the app. Fail-open: any error checking or
 * saving the goal never blocks access to Finch.
 */
import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { goalApi, type SetGoalRequest } from '@/lib/api';
import GoalWizard from './GoalWizard';

export default function GoalGate({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [checked, setChecked] = useState(false);
  const [needsGoal, setNeedsGoal] = useState(false);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
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

  // AuthGate only mounts us once authenticated. While we check for a goal, hold
  // the app back so we don't flash the dashboard and then swap to the wizard.
  if (user && !checked) return null;
  if (needsGoal) return <GoalWizard onComplete={handleComplete} />;
  return <>{children}</>;
}
