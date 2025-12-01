'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

export type View = 'strategies' | 'chat' | 'files' | 'analytics';

interface NavigationContextType {
  currentView: View;
  navigateTo: (view: View) => void;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

export function NavigationProvider({ children }: { children: ReactNode }) {
  const [currentView, setCurrentView] = useState<View>('strategies');

  const navigateTo = (view: View) => {
    setCurrentView(view);
  };

  return (
    <NavigationContext.Provider value={{ currentView, navigateTo }}>
      {children}
    </NavigationContext.Provider>
  );
}

export function useNavigation() {
  const context = useContext(NavigationContext);
  if (context === undefined) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
}

