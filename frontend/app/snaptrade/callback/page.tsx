'use client';

import { useEffect } from 'react';

export default function SnapTradeCallbackPage() {
  useEffect(() => {
    const message = { type: 'SNAPTRADE_CONNECTION', success: true };
    const origin = window.location.origin;

    if (window.opener) {
      try { window.opener.parent.postMessage(message, origin); } catch {}
      try { window.opener.postMessage(message, origin); } catch {}
      window.close();
    } else if (window.parent !== window) {
      window.parent.postMessage(message, origin);
    }
  }, []);

  return (
    <div className="flex items-center justify-center min-h-screen bg-white">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-gray-200 border-t-emerald-500 rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-500">Finishing connection...</p>
      </div>
    </div>
  );
}
