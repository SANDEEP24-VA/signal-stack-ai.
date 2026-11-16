import React from 'react';
import { Layers, ShieldAlert } from 'lucide-react';

interface ModulePlaceholderProps {
  title: string;
  description: string;
  moduleName: string;
}

export const ModulePlaceholder: React.FC<ModulePlaceholderProps> = ({
  title,
  description,
  moduleName,
}) => {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800 border border-slate-700 text-slate-300 mb-4">
        <Layers className="h-6 w-6 text-emerald-400" />
      </div>
      <h2 className="text-lg font-semibold text-white tracking-tight">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">{description}</p>
      <div className="mt-6 inline-flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/80 px-4 py-2 text-xs font-mono text-slate-400">
        <ShieldAlert className="h-4 w-4 text-emerald-400" />
        <span>Module {moduleName} scaffolded and awaiting domain model integration</span>
      </div>
    </div>
  );
};
