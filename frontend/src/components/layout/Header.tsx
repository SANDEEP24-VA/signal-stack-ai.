import React from 'react';
import { Menu, RefreshCw, ShieldCheck, Server } from 'lucide-react';
import { SystemHealth } from '../../types';

interface HeaderProps {
  currentTab: string;
  onOpenMobile: () => void;
  health: SystemHealth | null;
  loading: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onOpenMobile,
  health,
  loading,
  onRefresh,
}) => {
  const titles: Record<string, string> = {
    overview: 'Executive Dashboard & Platform State',
    companies: 'Target Company Intelligence',
    signals: 'Raw Signal Ingestion Streams',
    briefings: 'Executive Intelligence Briefings',
    crawlers: 'Web Crawlers & Document Extraction',
    settings: 'Configuration & AI Providers',
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-800 bg-slate-950/80 px-6 backdrop-blur-md">
      <div className="flex items-center gap-4">
        <button
          onClick={onOpenMobile}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-lg font-semibold text-white tracking-tight">
            {titles[currentTab] || 'Platform Dashboard'}
          </h1>
          <p className="text-xs text-slate-400 hidden sm:block">
            Signal Stack AI Core Environment • Enterprise Intelligence Engine
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Environment pill */}
        <div className="hidden md:flex items-center gap-1.5 rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs font-mono text-slate-300">
          <Server className="h-3.5 w-3.5 text-slate-400" />
          <span>env: {health?.environment || 'development'}</span>
        </div>

        {/* Health status indicator */}
        <div className="flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/90 px-3 py-1 text-xs">
          <ShieldCheck
            className={`h-4 w-4 ${
              health?.status === 'healthy' ? 'text-emerald-400' : 'text-amber-400'
            }`}
          />
          <span className="font-medium text-slate-200 hidden sm:inline">
            {health?.status === 'healthy' ? 'Core Engine Online' : 'Connecting to Core...'}
          </span>
        </div>

        {/* Manual Refresh Trigger */}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors disabled:opacity-50"
          title="Refresh system status"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
        </button>
      </div>
    </header>
  );
};
