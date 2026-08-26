/**
 * GoalGate (mobile) — when a signed-in user has no active goal, present the
 * onboarding full-screen before they use the app. Fail-open: any error checking
 * or saving never blocks access (mobile allows guest browsing, so this only
 * triggers once a real user with no goal is present).
 */
import React, { useEffect, useState } from 'react';
import { Modal } from 'react-native';
import { useAuth } from '@/contexts/AuthContext';
import { goalApi, type SetGoalRequest } from '@/lib/api';
import GoalOnboarding from './GoalOnboarding';

export default function GoalGate() {
  const { user } = useAuth();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!user) { setShow(false); return; }
    let cancelled = false;
    goalApi.getGoal(user.id)
      .then(g => { if (!cancelled) setShow(g == null); })
      .catch(() => { /* fail open */ });
    return () => { cancelled = true; };
  }, [user]);

  const handleDone = async (goal: SetGoalRequest) => {
    try { if (user) await goalApi.setGoal(user.id, goal); } catch { /* proceed anyway */ }
    setShow(false);
  };

  return (
    <Modal visible={show} animationType="slide" presentationStyle="fullScreen" onRequestClose={() => { /* not dismissable */ }}>
      <GoalOnboarding onDone={handleDone} />
    </Modal>
  );
}
