'use client';

import { useState, useCallback, useEffect } from 'react';

export function useNotifications() {
  const [permission, setPermission] = useState<NotificationPermission | 'unsupported'>(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) return 'unsupported';
    return Notification.permission;
  });

  // Request permission once on mount so the very first long task can notify.
  // The browser shows the prompt immediately — user can grant or dismiss.
  useEffect(() => {
    if (permission !== 'default') return;
    Notification.requestPermission().then(result => setPermission(result)).catch(() => {});
  }, [permission]);

  const requestPermission = useCallback(async () => {
    if (permission === 'unsupported' || permission === 'denied') return false;
    if (permission === 'granted') return true;
    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      return result === 'granted';
    } catch {
      return false;
    }
  }, [permission]);

  const sendNotification = useCallback((title: string, body: string) => {
    if (permission !== 'granted') return;
    try {
      const notif = new Notification(title, {
        body,
        icon: '/favicon.ico',
        tag: 'finch-chat-complete',
      });
      notif.onclick = () => {
        window.focus();
        notif.close();
      };
    } catch {
      // Notification API not available in this context
    }
  }, [permission]);

  return { permission, requestPermission, sendNotification };
}
