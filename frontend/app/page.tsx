'use client';

import AuthGate from '@/components/PasswordGate';
import AppLayout from '@/components/layout/AppLayout';
import ChatView from '@/components/chat/ChatView';
import FilesView from '@/components/files/FilesView';
import { NavigationProvider } from '@/contexts/NavigationContext';
import { ChatModeProvider } from '@/contexts/ChatModeContext';
import { useState, useEffect } from 'react';

export default function Home() {
  const [chatId, setChatId] = useState<string>('');

  useEffect(() => {
    // Generate or retrieve chat ID
    let id = localStorage.getItem('current_chat_id');
    if (!id) {
      id = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('current_chat_id', id);
    }
    setChatId(id);
  }, []);

  return (
    <AuthGate>
      <NavigationProvider>
        <ChatModeProvider>
          <main className="min-h-screen bg-gray-50">
            <AppLayout
              strategiesView={
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📈</div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-2">Strategies Coming Soon</h3>
                    <p className="text-gray-600">Build and manage trading strategies</p>
                  </div>
                </div>
              }
              chatView={<ChatView />}
              filesView={chatId ? <FilesView chatId={chatId} /> : <div>Loading...</div>}
              analyticsView={
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📊</div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-2">Analytics Coming Soon</h3>
                    <p className="text-gray-600">Performance dashboard and trade journal</p>
                  </div>
                </div>
              }
            />
          </main>
        </ChatModeProvider>
      </NavigationProvider>
    </AuthGate>
  );
}
