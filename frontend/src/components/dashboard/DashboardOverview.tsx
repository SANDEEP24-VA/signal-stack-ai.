import React from 'react';
import { SystemHealth } from '../../types';
import { SystemReadinessCard } from './SystemReadinessCard';
import { EmptyIntelligenceState } from './EmptyIntelligenceState';
import { Code2, Server, Database, Sparkles, Workflow } from 'lucide-react';

interface DashboardOverviewProps {
  health: SystemHealth | null;
  loading: boolean;
  onNavigateTab: (tabId: string) => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  health,
  loading,
  onNavigateTab,
}) => {
  return (
    <div className="space-y-8">
      {/* Platform Header Hero */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-2 gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium mb-3">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Signal Stack AI • Core Operational Starter
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Company Intelligence & Executive Briefing
          </h1>
          <p className="mt-1 text-sm text-slate-400 max-w-2xl">
            Autonomous multi-source signal ingestion, strategic analysis, and executive briefing synthesis
            powered by Gemini and local Ollama provider abstractions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateTab('companies')}
            className="rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 transition-colors"
          >
            Manage Targets
          </button>
          <button
            onClick={() => onNavigateTab('crawlers')}
            className="rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-sm font-semibold text-slate-200 hover:bg-slate-800 hover:text-white transition-colors"
          >
            Source Intelligence
          </button>
        </div>
      </div>

      {/* Live Foundation Readiness */}
      <SystemReadinessCard health={health} loading={loading} />

      {/* Primary Workspace View - Empty Intelligence State (No fake stats) */}
      <EmptyIntelligenceState onConfigureCompany={() => onNavigateTab('companies')} />

      {/* Core Technology Architecture Stack */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm">
        <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
          <Workflow className="h-4 w-4 text-emerald-400" />
          Configured Technology Architecture
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200 mb-1">
              <Code2 className="h-4 w-4 text-cyan-400" />
              Frontend Layer
            </div>
            <p className="text-xs text-slate-400">
              React 18 + TypeScript + Vite 5 + Tailwind CSS with responsive executive SaaS UI layout.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200 mb-1">
              <Server className="h-4 w-4 text-emerald-400" />
              Backend Layer
            </div>
            <p className="text-xs text-slate-400">
              Python FastAPI with structured error handling, CORS security, and modular REST routers.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200 mb-1">
              <Database className="h-4 w-4 text-amber-400" />
              Database & Storage
            </div>
            <p className="text-xs text-slate-400">
              SQLite relational database with SQLAlchemy 2.0 ORM sessions and schema migrations foundation.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200 mb-1">
              <Sparkles className="h-4 w-4 text-purple-400" />
              Intelligence & Crawling
            </div>
            <p className="text-xs text-slate-400">
              Dual Gemini/Ollama provider abstraction, HTTPX, Trafilatura, Feedparser, and APScheduler.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
