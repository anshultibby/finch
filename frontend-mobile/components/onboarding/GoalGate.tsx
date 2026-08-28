/**
 * GoalGate (mobile) — when a signed-in user has no active goal, present the
 * onboarding full-screen before they use the app. Soft gate: onboarding is
 * skippable and a skip is remembered per-user (SecureStore), so a user who just
 * wants in isn't re-prompted every launch. Fail-open: any error checking or
 * saving never blocks access (mobile allows guest browsing, so this only
 * triggers once a real user with no goal is present).
 */
import React, { useEffect, useState } from 'react';
import { Modal, Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { useAuth } from '@/contexts/AuthContext';
import { goalApi, type SetGoalRequest } from '@/lib/api';
import GoalOnboarding from './GoalOnboarding';

const skipKey = (userId: string) => `finch-goal-wizard-skipped-${userId}`;

async function getSkipped(userId: string): Promise<boolean> {
  try {
    if (Platform.OS === 'web') return (typeof window !== 'undefined' && window.localStorage.getItem(skipKey(userId))) === '1';
    return (await SecureStore.getItemAsync(skipKey(userId))) === '1';
  } catch { return false; }
}
async function setSkipped(userId: string) {
  try {
    if (Platform.OS === 'web') { if (typeof window !== 'undefined') window.localStorage.setItem(skipKey(userId), '1'); return; }
    await SecureStore.setItemAsync(skipKey(userId), '1');
  } catch { /* best effort */ }
}

export default function GoalGate() {
  const { user } = useAuth();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!user) { setShow(false); return; }
    let cancelled = false;
    (async () => {
      if (await getSkipped(user.id)) { if (!cancelled) setShow(false); return; }
      try {
        const g = await goalApi.getGoal(user.id);
        if (!cancelled) setShow(g == null);
      } catch { /* fail open */ }
    })();
    return () => { cancelled = true; };
  }, [user]);

  const handleDone = async (goal: SetGoalRequest) => {
    try { if (user) await goalApi.setGoal(user.id, goal); } catch { /* proceed anyway */ }
    setShow(false);
  };

  const handleSkip = async () => {
    if (user) await setSkipped(user.id);
    setShow(false);
  };

  return (
    <Modal visible={show} animationType="slide" presentationStyle="fullScreen" onRequestClose={() => { /* not dismissable */ }}>
      <GoalOnboarding onDone={handleDone} onSkip={handleSkip} />
    </Modal>
  );
}
