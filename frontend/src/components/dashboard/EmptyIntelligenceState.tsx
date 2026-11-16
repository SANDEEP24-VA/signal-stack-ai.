import React from 'react';
import { Building2, Plus, ArrowRight, Shield, Globe, Sparkles } from 'lucide-react';

interface EmptyIntelligenceStateProps {
  onConfigureCompany?: () => void;
}

export const EmptyIntelligenceState: React.FC<EmptyIntelligenceStateProps> = ({
  onConfigureCompany,
}) => {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center backdrop-blur-sm">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-800/80 border border-slate-700/60 text-slate-300 mb-4 shadow-inner">
        <Building2 className="h-7 w-7 text-emerald-400" />
      </div>

      <h3 className="text-lg font-semibold text-white tracking-tight">
        No Company Intelligence Profiles Active
      </h3>
      <p className="mx-auto mt-2 max-w-lg text-sm text-slate-400">
        Signal Stack AI continuously aggregates external signals, press releases, hiring trends,
        regulatory filings, and market shifts for configured targets to compile executive briefings.
      </p>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4 text-left max-w-3xl mx-auto">
        <div className="rounded-lg border border-slate-800/80 bg-slate-950/60 p-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1.5">
            <Globe className="h-4 w-4" />
            1. Source Ingestion
          </div>
          <p className="text-xs text-slate-400">
            Configure target company domains, RSS feeds, and official newsrooms for automated Trafilatura and Feedparser ingestion.
          </p>
        </div>

        <div className="rounded-lg border border-slate-800/80 bg-slate-950/60 p-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400 mb-1.5">
            <Shield className="h-4 w-4" />
            2. Signal Extraction
          </div>
          <p className="text-xs text-slate-400">
            Raw documents are normalized, de-duplicated, and filtered for executive relevance without noisy social noise.
          </p>
        </div>

        <div className="rounded-lg border border-slate-800/80 bg-slate-950/60 p-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-purple-400 mb-1.5">
            <Sparkles className="h-4 w-4" />
            3. AI Executive Briefing
          </div>
          <p className="text-xs text-slate-400">
            Gemini and Ollama providers summarize strategic signals into high-impact, actionable intelligence briefs.
          </p>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={onConfigureCompany}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-500 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add First Company Target
        </button>
        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <span>View API Specification</span>
          <ArrowRight className="h-4 w-4" />
        </a>
      </div>
    </div>
  );
};
