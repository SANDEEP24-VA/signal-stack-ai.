import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { SystemHealth } from '../../types';

interface AppLayoutProps {
  currentTab: string;
  onSelectTab: (tabId: string) => void;
  health: SystemHealth | null;
  loading: boolean;
  onRefresh: () => void;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentTab,
  onSelectTab,
  health,
  loading,
  onRefresh,
  children,
}) => {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar
        currentTab={currentTab}
        onSelectTab={onSelectTab}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        health={health}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          currentTab={currentTab}
          onOpenMobile={() => setMobileOpen(true)}
          health={health}
          loading={loading}
          onRefresh={onRefresh}
        />

        <main className="flex-1 overflow-y-auto px-6 py-8">
          <div className="mx-auto max-w-7xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
