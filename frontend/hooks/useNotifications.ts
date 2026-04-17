'use client';

import { useState, useCallback, useRef } from 'react';

export function useNotifications() {
  const [permission, setPermission] = useState<NotificationPermission | 'unsupported'>(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) return 'unsupported';
    return Notification.permission;
  });
  const promptedRef = useRef(false);

  const requestPermission = useCallback(async () => {
    if (permission === 'unsupported' || permission === 'denied') return false;
    if (permission === 'granted') return true;

    // Only prompt once per session
    if (promptedRef.current) return false;
    promptedRef.current = true;

    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      return result === 'granted';
    } catch {
      return false;
    }
  }, [permission]);

  const sendNotification = useCallback((title: string, body: string) => {
    if (permission !== 'granted' || !document.hidden) return;
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
