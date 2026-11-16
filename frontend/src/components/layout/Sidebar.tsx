import React from 'react';
import {
  Activity,
  BrainCircuit,
  Building2,
  FileText,
  Layers,
  Radio,
  Sliders,
  Terminal,
  X
} from 'lucide-react';
import { SystemHealth } from '../../types';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tabId: string) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  health: SystemHealth | null;
}

const NAV_ITEMS = [
  { id: 'overview', label: 'Executive Overview', icon: Activity },
  { id: 'companies', label: 'Monitored Companies', icon: Building2 },
  { id: 'interview', label: 'Founder AI Interview', icon: BrainCircuit, badge: 'Adaptive' },
  { id: 'crawlers', label: 'Source Intelligence', icon: Layers, badge: 'Task 4' },
  { id: 'signals', label: 'Signal Feeds', icon: Radio },
  { id: 'briefings', label: 'Executive Briefings', icon: FileText },
  { id: 'settings', label: 'Platform Settings', icon: Sliders },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  mobileOpen,
  onCloseMobile,
  health,
}) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-800 bg-slate-900/95 backdrop-blur-md transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-0 -translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-slate-800 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <Radio className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
                Signal Stack <span className="text-emerald-400 font-mono text-xs font-semibold px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-800/60">AI</span>
              </div>
              <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                Executive Intelligence
              </div>
            </div>
          </div>
          <button
            onClick={onCloseMobile}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mb-2 px-3 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
            Platform Modules
          </div>
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onSelectTab(item.id);
                    onCloseMobile();
                  }}
                  className={`group flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-slate-800 text-emerald-400 border border-slate-700/80 shadow-sm'
                      : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                  }`}
                >
                  <Icon
                    className={`h-4 w-4 transition-colors ${
                      isActive ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-200'
                    }`}
                  />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* System Engine Status Footer */}
        <div className="border-t border-slate-800/80 p-4">
          <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-xs">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="font-medium flex items-center gap-1.5">
                <Terminal className="h-3.5 w-3.5 text-slate-400" />
                Backend Status
              </span>
              <span
                className={`inline-flex items-center gap-1 text-[11px] font-semibold px-1.5 py-0.5 rounded ${
                  health?.status === 'healthy'
                    ? 'text-emerald-400 bg-emerald-950/60 border border-emerald-800/40'
                    : 'text-amber-400 bg-amber-950/60 border border-amber-800/40'
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    health?.status === 'healthy' ? 'bg-emerald-400' : 'bg-amber-400'
                  }`}
                />
                {health?.status ? health.status.toUpperCase() : 'CONNECTING'}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 space-y-1">
              <div className="flex justify-between">
                <span>Database:</span>
                <span className="text-slate-300 font-mono">
                  {health?.database.connected ? 'SQLite Connected' : 'Checking...'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Version:</span>
                <span className="text-slate-300 font-mono">{health?.version || '0.1.0'}</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
