'use client';

import React from 'react';
import { useRouter } from 'next/navigation';

export function EmptyState() {
  const router = useRouter();

  return (
    <div className="bg-white rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
      <div className="text-gray-400 text-6xl mb-4">🤖</div>
      <h3 className="text-2xl font-semibold text-gray-900 mb-2">No Strategies Yet</h3>
      <p className="text-gray-500 mb-6 max-w-md mx-auto">
        Create your first automated trading bot with AI assistance
      </p>
      <button
        onClick={() => router.push('/')}
        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium mb-6"
      >
        Create Strategy in Chat
      </button>
      
      <div className="mt-8 text-left max-w-sm mx-auto">
        <p className="text-sm text-gray-600 mb-3">Or check out examples:</p>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex items-center gap-2">
            <span>•</span>
            <span>Copy Top Traders</span>
          </li>
          <li className="flex items-center gap-2">
            <span>•</span>
            <span>Sports Betting Bot</span>
          </li>
          <li className="flex items-center gap-2">
            <span>•</span>
            <span>Congress Trading Bot</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
