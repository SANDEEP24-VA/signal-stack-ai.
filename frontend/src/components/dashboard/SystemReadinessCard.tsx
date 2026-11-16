import React from 'react';
import {
  CheckCircle2,
  Database,
  Cpu,
  Layers,
  Clock,
  ExternalLink,
  AlertTriangle
} from 'lucide-react';
import { SystemHealth } from '../../types';

interface SystemReadinessCardProps {
  health: SystemHealth | null;
  loading: boolean;
}

export const SystemReadinessCard: React.FC<SystemReadinessCardProps> = ({ health, loading }) => {
  const geminiConfigured = health?.ai_providers?.gemini?.configured ?? false;
  const ollamaConfigured = health?.ai_providers?.ollama?.configured ?? false;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-slate-800/80 gap-3">
        <div>
          <h2 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
            System Architecture & Foundation Readiness
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time status of backend services, database connections, and AI engine providers.
          </p>
        </div>
        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 font-medium"
        >
          FastAPI OpenAPI Docs <ExternalLink className="h-3 w-3" />
        </a>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-5">
        {/* API Server Card */}
        <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
              <Cpu className="h-4 w-4 text-emerald-400" />
              FastAPI Core
            </span>
            <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/50">
              v{health?.version || '0.1.0'}
            </span>
          </div>
          <div className="text-sm font-semibold text-white">
            {health?.status === 'healthy' ? 'Operational' : loading ? 'Checking...' : 'Degraded'}
          </div>
          <div className="text-xs text-slate-400 mt-1 font-mono">
            {health?.service || 'Signal Stack AI'}
          </div>
        </div>

        {/* Database Card */}
        <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
              <Database className="h-4 w-4 text-cyan-400" />
              Storage Engine
            </span>
            <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/50">
              {health?.database.type.toUpperCase() || 'SQLITE'}
            </span>
          </div>
          <div className="text-sm font-semibold text-white flex items-center gap-1.5">
            {health?.database.connected ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>Connected & Verified</span>
              </>
            ) : (
              <>
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                <span>Disconnected</span>
              </>
            )}
          </div>
          <div className="text-xs text-slate-400 mt-1 font-mono">
            SQLAlchemy 2.0 ORM
          </div>
        </div>

        {/* AI Provider Status Card */}
        <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
              <Layers className="h-4 w-4 text-purple-400" />
              AI Abstraction
            </span>
            <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/50">
              Provider Layer
            </span>
          </div>
          <div className="text-sm font-semibold text-white">
            Gemini & Ollama
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
            <span className={geminiConfigured ? 'text-emerald-400' : 'text-slate-500'}>
              • Gemini ({geminiConfigured ? 'Key active' : 'Awaiting key'})
            </span>
            <span className={ollamaConfigured ? 'text-emerald-400' : 'text-slate-500'}>
              • Ollama
            </span>
          </div>
        </div>

        {/* Crawlers & Scheduler Card */}
        <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
              <Clock className="h-4 w-4 text-amber-400" />
              Scheduler & Crawlers
            </span>
            <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/50">
              Ready
            </span>
          </div>
          <div className="text-sm font-semibold text-white">
            APScheduler & Trafilatura
          </div>
          <div className="text-xs text-slate-400 mt-1">
            HTTPX • Feedparser • BS4
          </div>
        </div>
      </div>
    </div>
  );
};
