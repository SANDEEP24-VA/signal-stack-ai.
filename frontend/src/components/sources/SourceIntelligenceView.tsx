import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertCircle,
  Archive,
  Building2,
  CheckCircle2,
  Compass,
  ExternalLink,
  Eye,
  Filter,
  Globe,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Users,
  X,
  XCircle,
} from 'lucide-react';
import {
  approveCompetitor,
  approveSource,
  archiveCompetitor,
  createCompetitor,
  createSource,
  deleteSource,
  discoverCompetitors,
  discoverSources,
  fetchCompanies,
  fetchCompetitors,
  fetchSources,
  fetchSourceSummary,
  pauseSource,
  probeSource,
  rejectCompetitor,
  rejectSource,
  resumeSource,
} from '../../services/api';
import {
  Company,
  Competitor,
  IntelligenceSource,
  SourceSummaryStats,
} from '../../types';

export const SourceIntelligenceView: React.FC = () => {
  // Company Selection
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);

  // Data State
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [sources, setSources] = useState<IntelligenceSource[]>([]);
  const [summary, setSummary] = useState<SourceSummaryStats | null>(null);

  // Filters & Tabs
  const [activeTab, setActiveTab] = useState<'sources' | 'competitors'>('sources');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [relationshipFilter, setRelationshipFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modals & Inspection
  const [inspectedCompetitor, setInspectedCompetitor] = useState<Competitor | null>(null);
  const [inspectedSource, setInspectedSource] = useState<IntelligenceSource | null>(null);
  const [addCompetitorOpen, setAddCompetitorOpen] = useState<boolean>(false);
  const [addSourceOpen, setAddSourceOpen] = useState<boolean>(false);

  // New Competitor Form
  const [newCompName, setNewCompName] = useState<string>('');
  const [newCompWebsite, setNewCompWebsite] = useState<string>('');
  const [newCompRel, setNewCompRel] = useState<string>('DIRECT');
  const [newCompRationale, setNewCompRationale] = useState<string>('');

  // New Source Form
  const [newSourceName, setNewSourceName] = useState<string>('');
  const [newSourceUrl, setNewSourceUrl] = useState<string>('');
  const [newSourceCat, setNewSourceCat] = useState<string>('MARKET');
  const [newSourceType, setNewSourceType] = useState<string>('WEBSITE');
  const [newSourceWhy, setNewSourceWhy] = useState<string>('');

  // UI Status
  const [loading, setLoading] = useState<boolean>(false);
  const [discoveringComp, setDiscoveringComp] = useState<boolean>(false);
  const [discoveringSource, setDiscoveringSource] = useState<boolean>(false);
  const [probingId, setProbingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // 1. Initial Load: Fetch Companies
  useEffect(() => {
    async function loadCompanies() {
      try {
        setLoading(true);
        const data = await fetchCompanies();
        setCompanies(data);
        if (data.length > 0 && !selectedCompanyId) {
          setSelectedCompanyId(data[0].id);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load monitored companies.');
      } finally {
        setLoading(false);
      }
    }
    loadCompanies();
  }, []);

  // 2. Load Competitors & Sources when company changes
  const loadCompanyIntelligence = useCallback(async (companyId: number) => {
    try {
      setLoading(true);
      setError(null);
      const [compData, srcData, sumData] = await Promise.all([
        fetchCompetitors(companyId),
        fetchSources(companyId),
        fetchSourceSummary(companyId),
      ]);
      setCompetitors(compData);
      setSources(srcData);
      setSummary(sumData);
    } catch (err: any) {
      setError(err.message || 'Failed to load sources and competitors.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCompanyId) {
      loadCompanyIntelligence(selectedCompanyId);
    }
  }, [selectedCompanyId, loadCompanyIntelligence]);

  // Trigger Competitor Discovery
  const handleDiscoverCompetitors = async () => {
    if (!selectedCompanyId) return;
    try {
      setDiscoveringComp(true);
      setError(null);
      setSuccessNotice(null);
      const newComps = await discoverCompetitors(selectedCompanyId, true);
      setSuccessNotice(`Discovered ${newComps.length} competitor candidate(s).`);
      await loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message || 'Competitor discovery failed.');
    } finally {
      setDiscoveringComp(false);
    }
  };

  // Trigger Source Discovery
  const handleDiscoverSources = async () => {
    if (!selectedCompanyId) return;
    try {
      setDiscoveringSource(true);
      setError(null);
      setSuccessNotice(null);
      const newSrcs = await discoverSources(selectedCompanyId, true);
      setSuccessNotice(`Discovered ${newSrcs.length} intelligence source candidate(s).`);
      await loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message || 'Source discovery failed.');
    } finally {
      setDiscoveringSource(false);
    }
  };

  // Competitor Governance Actions
  const handleApproveCompetitor = async (id: number) => {
    try {
      await approveCompetitor(id);
      setSuccessNotice('Competitor marked as APPROVED.');
      if (selectedCompanyId) loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRejectCompetitor = async (id: number) => {
    try {
      await rejectCompetitor(id);
      setSuccessNotice('Competitor marked as REJECTED.');
      if (selectedCompanyId) loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleArchiveCompetitor = async (id: number) => {
    try {
      await archiveCompetitor(id);
      setSuccessNotice('Competitor ARCHIVED.');
      if (selectedCompanyId) loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message);
    }
  };

  // Source Governance Actions
  const handleApproveSource = async (id: number) => {
    try {
      await approveSource(id);
      setSuccessNotice('Source APPROVED for continuous monitoring.');
      if (selectedCompanyId) loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRejectSource = async (id: number) => {
    try {
      await rejectSource(id, 'User rejected from dashboard');
      setSuccessNotice('Source marked as REJECTED.');
      if (selectedCompanyId) loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleTogglePauseSource = async (source: IntelligenceSource) => {
    try {
      if (source.status === 'PAUSED') {
        await resumeSource(source.id);
        setSuccessNotice('Source monitoring RESUMED.');
      } else {
        await pauseSource(source.id);
        setSuccessNotice('Source monitoring PAUSED.');
      }
      if (selectedCompanyId) loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteSource = async (id: number) => {
    try {
      await deleteSource(id);
      setSuccessNotice('Source removed from registry.');
      if (selectedCompanyId) loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleProbeHealth = async (id: number) => {
    try {
      setProbingId(id);
      const log = await probeSource(id);
      setSuccessNotice(`Health check: ${log.status} (HTTP ${log.http_status || 'N/A'}) in ${log.response_time_ms || 0}ms.`);
      if (selectedCompanyId) loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message || 'Probe failed.');
    } finally {
      setProbingId(null);
    }
  };

  // Submit Manual Competitor
  const handleCreateCompetitor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompanyId || !newCompName.trim() || !newCompWebsite.trim()) return;
    try {
      await createCompetitor(selectedCompanyId, {
        name: newCompName.trim(),
        website: newCompWebsite.trim(),
        relationship_type: newCompRel,
        discovery_rationale: newCompRationale.trim(),
      });
      setAddCompetitorOpen(false);
      setNewCompName('');
      setNewCompWebsite('');
      setNewCompRationale('');
      setSuccessNotice('Competitor manually added and approved.');
      loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message || 'Failed to add competitor.');
    }
  };

  // Submit Manual Source
  const handleCreateSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompanyId || !newSourceName.trim() || !newSourceUrl.trim()) return;
    try {
      await createSource(selectedCompanyId, {
        name: newSourceName.trim(),
        canonical_url: newSourceUrl.trim(),
        category: newSourceCat,
        source_type: newSourceType,
        why_it_matters: newSourceWhy.trim(),
      });
      setAddSourceOpen(false);
      setNewSourceName('');
      setNewSourceUrl('');
      setNewSourceWhy('');
      setSuccessNotice('Source manually registered and approved.');
      loadCompanyIntelligence(selectedCompanyId);
    } catch (err: any) {
      setError(err.message || 'Failed to add source.');
    }
  };

  const selectedCompany = companies.find((c) => c.id === selectedCompanyId);

  // Filtered Competitors
  const filteredCompetitors = competitors.filter((c) => {
    const matchesStatus = statusFilter === 'ALL' || c.review_status === statusFilter;
    const matchesRel = relationshipFilter === 'ALL' || c.relationship_type === relationshipFilter;
    const matchesQuery =
      !searchQuery ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.canonical_domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.discovery_rationale.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesRel && matchesQuery;
  });

  // Filtered Sources
  const filteredSources = sources.filter((s) => {
    const matchesCat = categoryFilter === 'ALL' || s.category === categoryFilter;
    const matchesStatus = statusFilter === 'ALL' || s.status === statusFilter;
    const matchesQuery =
      !searchQuery ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.why_it_matters.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesStatus && matchesQuery;
  });

  return (
    <div className="space-y-6">
      {/* 1. TOP HEADER */}
      <div className="flex flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Compass className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">Source Intelligence & Competitor Registry</h1>
              <span className="rounded-full bg-cyan-500/10 px-2.5 py-0.5 text-xs font-semibold text-cyan-400 border border-cyan-500/20">
                Task 4 Engine
              </span>
            </div>
            <p className="text-sm text-slate-400">
              Evidence-grounded competitor discovery and multi-channel public source governance for{' '}
              <strong className="text-slate-200">{selectedCompany?.name || 'Company'}</strong>.
            </p>
          </div>
        </div>

        {/* Company Selector & Global Triggers */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-1.5">
            <Building2 className="h-4 w-4 text-slate-400" />
            <select
              value={selectedCompanyId || ''}
              onChange={(e) => setSelectedCompanyId(Number(e.target.value))}
              className="bg-transparent text-sm font-medium text-slate-200 focus:outline-none"
            >
              {companies.map((comp) => (
                <option key={comp.id} value={comp.id} className="bg-slate-900 text-slate-200">
                  {comp.name} ({comp.normalized_domain})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleDiscoverCompetitors}
            disabled={discoveringComp || loading}
            className="flex items-center gap-1.5 rounded-lg border border-purple-500/30 bg-purple-500/10 px-3.5 py-2 text-xs font-semibold text-purple-300 hover:bg-purple-500/20 disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {discoveringComp ? 'Discovering Competitors...' : 'Discover Competitors (AI)'}
          </button>

          <button
            onClick={handleDiscoverSources}
            disabled={discoveringSource || loading}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-cyan-500/20 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${discoveringSource ? 'animate-spin' : ''}`} />
            {discoveringSource ? 'Discovering Sources...' : 'Discover Sources (Multi-Channel)'}
          </button>
        </div>
      </div>

      {/* FEEDBACK BANNERS */}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-400" />
          <div className="flex-1">{error}</div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200">
            Dismiss
          </button>
        </div>
      )}

      {successNotice && (
        <div className="flex items-center gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-emerald-400" />
          <div className="flex-1">{successNotice}</div>
          <button onClick={() => setSuccessNotice(null)} className="text-emerald-400 hover:text-emerald-200">
            Dismiss
          </button>
        </div>
      )}

      {/* 2. OVERVIEW KPI CARDS */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-md">
            <div className="text-xs text-slate-400">Total Sources</div>
            <div className="mt-1 text-2xl font-bold text-white">{summary.total_sources}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Across 4 categories</div>
          </div>

          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 backdrop-blur-md">
            <div className="text-xs text-emerald-400">Approved Sources</div>
            <div className="mt-1 text-2xl font-bold text-emerald-400">{summary.approved}</div>
            <div className="text-[11px] text-emerald-500/80 mt-0.5">Active monitoring</div>
          </div>

          <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 backdrop-blur-md">
            <div className="text-xs text-amber-400">Pending Review</div>
            <div className="mt-1 text-2xl font-bold text-amber-400">{summary.pending}</div>
            <div className="text-[11px] text-amber-500/80 mt-0.5">Discovered candidates</div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-md">
            <div className="text-xs text-slate-400">Paused / Rejected</div>
            <div className="mt-1 text-2xl font-bold text-slate-300">{summary.paused + summary.rejected}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">{summary.paused} paused • {summary.rejected} rejected</div>
          </div>

          <div className="rounded-xl border border-purple-500/30 bg-purple-500/5 p-4 backdrop-blur-md">
            <div className="text-xs text-purple-400">Competitor Candidates</div>
            <div className="mt-1 text-2xl font-bold text-purple-400">{summary.competitors_count}</div>
            <div className="text-[11px] text-purple-500/80 mt-0.5">{summary.approved_competitors} approved</div>
          </div>

          <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-4 backdrop-blur-md">
            <div className="text-xs text-cyan-400">Market & Regulatory</div>
            <div className="mt-1 text-2xl font-bold text-cyan-400">{summary.by_category.MARKET || 0}</div>
            <div className="text-[11px] text-cyan-500/80 mt-0.5">Gov & industry portals</div>
          </div>
        </div>
      )}

      {/* 3. SECTION TABS & CONTROLS */}
      <div className="flex flex-col gap-4 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setActiveTab('sources'); setStatusFilter('ALL'); }}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition-all ${
              activeTab === 'sources'
                ? 'bg-slate-800 text-cyan-400 border border-slate-700 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Globe className="h-4 w-4" />
            Intelligence Sources ({sources.length})
          </button>

          <button
            onClick={() => { setActiveTab('competitors'); setStatusFilter('ALL'); }}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition-all ${
              activeTab === 'competitors'
                ? 'bg-slate-800 text-purple-400 border border-slate-700 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Users className="h-4 w-4" />
            Competitors & Substitutes ({competitors.length})
          </button>
        </div>

        {/* Search & Manual Add Buttons */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder={`Search ${activeTab}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-48 sm:w-64 rounded-lg border border-slate-800 bg-slate-950 pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
          </div>

          {activeTab === 'sources' ? (
            <button
              onClick={() => setAddSourceOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700"
            >
              <Plus className="h-3.5 w-3.5 text-cyan-400" /> Add Source
            </button>
          ) : (
            <button
              onClick={() => setAddCompetitorOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700"
            >
              <Plus className="h-3.5 w-3.5 text-purple-400" /> Add Competitor
            </button>
          )}
        </div>
      </div>

      {/* 4. TAB 1: INTELLIGENCE SOURCES TABLE & GOVERNANCE */}
      {activeTab === 'sources' && (
        <div className="space-y-4">
          {/* Category & Status Filter Pills */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            {/* Category Filter */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-slate-500 mr-1 flex items-center gap-1">
                <Filter className="h-3 w-3" /> Category:
              </span>
              {['ALL', 'CUSTOMERS', 'COMPETITORS', 'MARKET', 'INTERNAL'].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                    categoryFilter === cat
                      ? cat === 'CUSTOMERS'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : cat === 'COMPETITORS'
                        ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                        : cat === 'MARKET'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                        : cat === 'INTERNAL'
                        ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                        : 'bg-slate-700 text-white'
                      : 'bg-slate-950 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Status Filter */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-slate-500 mr-1">Status:</span>
              {['ALL', 'PENDING_APPROVAL', 'APPROVED', 'PAUSED', 'REJECTED'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                    statusFilter === st ? 'bg-slate-700 text-white' : 'bg-slate-950 text-slate-400 hover:text-slate-300'
                  }`}
                >
                  {st.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Sources List */}
          {filteredSources.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-10 text-center">
              <Globe className="mx-auto h-10 w-10 text-slate-600 mb-2" />
              <p className="text-sm font-medium text-slate-300">No intelligence sources found matching criteria.</p>
              <p className="text-xs text-slate-500 mt-1">
                Click "Discover Sources (Multi-Channel)" to automatically uncover regulatory, competitor, and customer sources.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/70 backdrop-blur-md">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-950/60 text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Source Name & Domain</th>
                    <th className="py-3 px-3">Category</th>
                    <th className="py-3 px-3">Type</th>
                    <th className="py-3 px-3">Credibility</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3">Last Health Check</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredSources.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-200">{s.name}</div>
                        <a
                          href={s.canonical_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-[11px] text-cyan-400 hover:underline mt-0.5"
                        >
                          {s.domain}
                          <ExternalLink className="h-2.5 w-2.5" />
                        </a>
                      </td>

                      <td className="py-3 px-3">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                            s.category === 'CUSTOMERS'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : s.category === 'COMPETITORS'
                              ? 'bg-purple-500/20 text-purple-300'
                              : s.category === 'MARKET'
                              ? 'bg-cyan-500/20 text-cyan-300'
                              : 'bg-blue-500/20 text-blue-300'
                          }`}
                        >
                          {s.category}
                        </span>
                      </td>

                      <td className="py-3 px-3">
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300 font-mono">
                          {s.source_type}
                        </span>
                      </td>

                      <td className="py-3 px-3">
                        <div className="flex items-center gap-1.5">
                          <div className="h-1.5 w-12 rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className="h-full bg-cyan-400"
                              style={{ width: `${s.credibility_score * 100}%` }}
                            />
                          </div>
                          <span className="text-[11px] font-semibold text-slate-300">
                            {(s.credibility_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                            s.status === 'APPROVED'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : s.status === 'PENDING_APPROVAL' || s.status === 'DISCOVERED'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : s.status === 'PAUSED'
                              ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                              : 'bg-red-500/10 text-red-400 border border-red-500/20'
                          }`}
                        >
                          {s.status.replace('_', ' ')}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-slate-400 text-[11px]">
                        {s.last_successful_crawl ? (
                          <div className="text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" />
                            HTTP {s.http_status || 200}
                          </div>
                        ) : s.last_error ? (
                          <div className="text-red-400 flex items-center gap-1 truncate max-w-[120px]" title={s.last_error}>
                            <XCircle className="h-3 w-3 flex-shrink-0" />
                            {s.last_error}
                          </div>
                        ) : (
                          <span className="text-slate-500">Unprobed</span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Inspect Modal Trigger */}
                          <button
                            onClick={() => setInspectedSource(s)}
                            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
                            title="Inspect Evidence & Rationale"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </button>

                          {/* Probe Health */}
                          <button
                            onClick={() => handleProbeHealth(s.id)}
                            disabled={probingId === s.id}
                            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-cyan-400"
                            title="Probe URL Reachability"
                          >
                            <RefreshCw className={`h-3.5 w-3.5 ${probingId === s.id ? 'animate-spin text-cyan-400' : ''}`} />
                          </button>

                          {/* Approval / Rejection Controls */}
                          {s.status !== 'APPROVED' ? (
                            <button
                              onClick={() => handleApproveSource(s.id)}
                              className="rounded bg-emerald-600/20 px-2 py-1 text-[11px] font-semibold text-emerald-400 hover:bg-emerald-600/30"
                            >
                              Approve
                            </button>
                          ) : (
                            <button
                              onClick={() => handleTogglePauseSource(s)}
                              className="rounded bg-slate-800 px-2 py-1 text-[11px] font-semibold text-slate-300 hover:bg-slate-700"
                            >
                              Pause
                            </button>
                          )}

                          {s.status === 'PAUSED' && (
                            <button
                              onClick={() => handleTogglePauseSource(s)}
                              className="rounded bg-emerald-600/20 px-2 py-1 text-[11px] font-semibold text-emerald-400 hover:bg-emerald-600/30"
                            >
                              Resume
                            </button>
                          )}

                          {s.status !== 'REJECTED' && (
                            <button
                              onClick={() => handleRejectSource(s.id)}
                              className="rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-amber-400"
                              title="Reject Source"
                            >
                              <XCircle className="h-3.5 w-3.5" />
                            </button>
                          )}

                          <button
                            onClick={() => handleDeleteSource(s.id)}
                            className="rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-red-400"
                            title="Delete Source"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 5. TAB 2: COMPETITORS & SUBSTITUTES */}
      {activeTab === 'competitors' && (
        <div className="space-y-4">
          {/* Relationship Filter */}
          <div className="flex items-center gap-1.5 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <span className="text-xs font-medium text-slate-500 mr-2 flex items-center gap-1">
              <Filter className="h-3 w-3" /> Relationship:
            </span>
            {['ALL', 'DIRECT', 'INDIRECT', 'SUBSTITUTE'].map((rel) => (
              <button
                key={rel}
                onClick={() => setRelationshipFilter(rel)}
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  relationshipFilter === rel
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200'
                }`}
              >
                {rel}
              </button>
            ))}
          </div>

          {/* Competitor Cards Grid */}
          {filteredCompetitors.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-10 text-center">
              <Users className="mx-auto h-10 w-10 text-slate-600 mb-2" />
              <p className="text-sm font-medium text-slate-300">No competitors registered for this company.</p>
              <p className="text-xs text-slate-500 mt-1">
                Click "Discover Competitors (AI)" to automatically detect rivals and substitutes from verified company facts.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredCompetitors.map((comp) => (
                <div
                  key={comp.id}
                  className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-lg backdrop-blur-md flex flex-col justify-between"
                >
                  <div>
                    {/* Header: Name, Pill, Domain */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <h3 className="font-bold text-white text-base">{comp.name}</h3>
                        <a
                          href={comp.website}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-xs text-purple-400 hover:underline mt-0.5"
                        >
                          {comp.canonical_domain}
                          <ExternalLink className="h-2.5 w-2.5" />
                        </a>
                      </div>

                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                          comp.relationship_type === 'DIRECT'
                            ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                            : comp.relationship_type === 'INDIRECT'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                        }`}
                      >
                        {comp.relationship_type}
                      </span>
                    </div>

                    {/* Rationale Excerpt */}
                    <p className="text-xs text-slate-300 line-clamp-3 my-3 leading-relaxed">
                      {comp.discovery_rationale}
                    </p>

                    {/* Overlap Tags */}
                    {comp.products_services && comp.products_services.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {comp.products_services.slice(0, 3).map((p, idx) => (
                          <span key={idx} className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                            {p}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Actions & Status */}
                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        comp.review_status === 'APPROVED'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : comp.review_status === 'CANDIDATE'
                          ? 'bg-amber-500/20 text-amber-400'
                          : comp.review_status === 'REJECTED'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {comp.review_status}
                    </span>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => setInspectedCompetitor(comp)}
                        className="rounded p-1 text-slate-400 hover:text-white"
                        title="View Full Profile & Evidence"
                      >
                        <Eye className="h-4 w-4" />
                      </button>

                      {comp.review_status !== 'APPROVED' && (
                        <button
                          onClick={() => handleApproveCompetitor(comp.id)}
                          className="rounded bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-emerald-500"
                        >
                          Approve
                        </button>
                      )}

                      {comp.review_status !== 'REJECTED' && (
                        <button
                          onClick={() => handleRejectCompetitor(comp.id)}
                          className="rounded p-1 text-slate-400 hover:text-amber-400"
                          title="Reject Competitor"
                        >
                          <XCircle className="h-4 w-4" />
                        </button>
                      )}

                      {comp.review_status !== 'ARCHIVED' && (
                        <button
                          onClick={() => handleArchiveCompetitor(comp.id)}
                          className="rounded p-1 text-slate-400 hover:text-slate-200"
                          title="Archive"
                        >
                          <Archive className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 6. INSPECT SOURCE MODAL */}
      {inspectedSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <Globe className="h-5 w-5 text-cyan-400" />
                <h3 className="font-bold text-white text-base">Intelligence Source Audit Details</h3>
              </div>
              <button onClick={() => setInspectedSource(null)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs text-slate-300">
              <div>
                <span className="font-bold text-slate-400 block mb-1">Source Name & URL:</span>
                <div className="text-sm font-semibold text-white">{inspectedSource.name}</div>
                <a
                  href={inspectedSource.canonical_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan-400 hover:underline break-all"
                >
                  {inspectedSource.canonical_url}
                </a>
              </div>

              <div className="grid grid-cols-2 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-500 block">Category:</span>
                  <span className="font-bold text-slate-200">{inspectedSource.category}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Source Type:</span>
                  <span className="font-bold text-slate-200">{inspectedSource.source_type}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Credibility Rating:</span>
                  <span className="font-bold text-cyan-400">{(inspectedSource.credibility_score * 100).toFixed(0)}% Authoritative</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Discovery Method:</span>
                  <span className="font-bold text-slate-200">{inspectedSource.discovery_method}</span>
                </div>
              </div>

              <div>
                <span className="font-bold text-slate-400 block mb-1">Strategic Relevance (Why It Matters):</span>
                <p className="bg-slate-950 p-3 rounded-lg border border-slate-800 leading-relaxed text-slate-200">
                  {inspectedSource.why_it_matters}
                </p>
              </div>

              <div>
                <span className="font-bold text-slate-400 block mb-1">Signals Exposed (Intelligence Type):</span>
                <p className="text-slate-200">{inspectedSource.intelligence_type}</p>
              </div>

              {inspectedSource.supporting_evidence && inspectedSource.supporting_evidence.length > 0 && (
                <div>
                  <span className="font-bold text-slate-400 block mb-1">Supporting Discovery Evidence:</span>
                  <pre className="bg-slate-950 p-3 rounded border border-slate-800 text-[11px] font-mono text-slate-400 overflow-x-auto max-h-32">
                    {JSON.stringify(inspectedSource.supporting_evidence, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="mt-5 pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setInspectedSource(null)}
                className="rounded bg-slate-800 px-4 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. INSPECT COMPETITOR MODAL */}
      {inspectedCompetitor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-purple-400" />
                <h3 className="font-bold text-white text-base">Competitor Intelligence Profile</h3>
              </div>
              <button onClick={() => setInspectedCompetitor(null)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs text-slate-300">
              <div>
                <div className="text-lg font-bold text-white">{inspectedCompetitor.name}</div>
                <a
                  href={inspectedCompetitor.website}
                  target="_blank"
                  rel="noreferrer"
                  className="text-purple-400 hover:underline"
                >
                  {inspectedCompetitor.website}
                </a>
              </div>

              <div className="grid grid-cols-2 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-500 block">Relationship Type:</span>
                  <span className="font-bold text-purple-300">{inspectedCompetitor.relationship_type}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Candidate Confidence:</span>
                  <span className="font-bold text-slate-200">{(inspectedCompetitor.confidence * 100).toFixed(0)}%</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Discovery Method:</span>
                  <span className="font-bold text-slate-200">{inspectedCompetitor.discovery_method}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Review State:</span>
                  <span className="font-bold text-slate-200">{inspectedCompetitor.review_status}</span>
                </div>
              </div>

              <div>
                <span className="font-bold text-slate-400 block mb-1">Commercial Discovery Rationale:</span>
                <p className="bg-slate-950 p-3 rounded-lg border border-slate-800 leading-relaxed text-slate-200">
                  {inspectedCompetitor.discovery_rationale}
                </p>
              </div>

              {inspectedCompetitor.products_services && inspectedCompetitor.products_services.length > 0 && (
                <div>
                  <span className="font-bold text-slate-400 block mb-1">Products & Services:</span>
                  <div className="flex flex-wrap gap-1">
                    {inspectedCompetitor.products_services.map((p, idx) => (
                      <span key={idx} className="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-5 pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setInspectedCompetitor(null)}
                className="rounded bg-slate-800 px-4 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8. MODAL: ADD COMPETITOR MANUALLY */}
      {addCompetitorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <form onSubmit={handleCreateCompetitor} className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <h3 className="font-bold text-white text-base mb-4">Register Verified Competitor</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Competitor Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. IDP Education"
                  value={newCompName}
                  onChange={(e) => setNewCompName(e.target.value)}
                  className="w-full rounded bg-slate-950 p-2 text-slate-200 border border-slate-800 focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Official Website URL *</label>
                <input
                  type="url"
                  required
                  placeholder="https://idp.com"
                  value={newCompWebsite}
                  onChange={(e) => setNewCompWebsite(e.target.value)}
                  className="w-full rounded bg-slate-950 p-2 text-slate-200 border border-slate-800 focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Relationship Type</label>
                <select
                  value={newCompRel}
                  onChange={(e) => setNewCompRel(e.target.value)}
                  className="w-full rounded bg-slate-950 p-2 text-slate-200 border border-slate-800 focus:border-purple-500 focus:outline-none"
                >
                  <option value="DIRECT">DIRECT (Direct product & regional overlap)</option>
                  <option value="INDIRECT">INDIRECT (Adjacent model or segment)</option>
                  <option value="SUBSTITUTE">SUBSTITUTE (Self-service / DIY alternative)</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Rationale / Notes</label>
                <textarea
                  rows={2}
                  placeholder="Why does this enterprise compete with the target company?"
                  value={newCompRationale}
                  onChange={(e) => setNewCompRationale(e.target.value)}
                  className="w-full rounded bg-slate-950 p-2 text-slate-200 border border-slate-800 focus:border-purple-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAddCompetitorOpen(false)}
                className="rounded px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="rounded bg-purple-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-purple-500"
              >
                Save Competitor
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 9. MODAL: ADD SOURCE MANUALLY */}
      {addSourceOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <form onSubmit={handleCreateSource} className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <h3 className="font-bold text-white text-base mb-4">Register Intelligence Source</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Source Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. UK Visas & Immigration"
                  value={newSourceName}
                  onChange={(e) => setNewSourceName(e.target.value)}
                  className="w-full rounded bg-slate-950 p-2 text-slate-200 border border-slate-800 focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Canonical URL *</label>
                <input
                  type="url"
                  required
                  placeholder="https://www.gov.uk/student-visa"
                  value={newSourceUrl}
                  onChange={(e) => setNewSourceUrl(e.target.value)}
                  className="w-full rounded bg-slate-950 p-2 text-slate-200 border border-slate-800 focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">Category</label>
                  <select
                    value={newSourceCat}
                    onChange={(e) => setNewSourceCat(e.target.value)}
                    className="w-full rounded bg-slate-950 p-2 text-slate-200 border border-slate-800 focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="MARKET">MARKET</option>
                    <option value="CUSTOMERS">CUSTOMERS</option>
                    <option value="COMPETITORS">COMPETITORS</option>
                    <option value="INTERNAL">INTERNAL</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Source Type</label>
                  <select
                    value={newSourceType}
                    onChange={(e) => setNewSourceType(e.target.value)}
                    className="w-full rounded bg-slate-950 p-2 text-slate-200 border border-slate-800 focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="WEBSITE">WEBSITE</option>
                    <option value="REGULATORY">REGULATORY</option>
                    <option value="NEWS_FEED">NEWS_FEED</option>
                    <option value="CASE_STUDY">CASE_STUDY</option>
                    <option value="SITEMAP">SITEMAP</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Why It Matters (Strategic Relevance)</label>
                <textarea
                  rows={2}
                  placeholder="What type of executive warning or market opportunity does this source reveal?"
                  value={newSourceWhy}
                  onChange={(e) => setNewSourceWhy(e.target.value)}
                  className="w-full rounded bg-slate-950 p-2 text-slate-200 border border-slate-800 focus:border-cyan-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAddSourceOpen(false)}
                className="rounded px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="rounded bg-cyan-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500"
              >
                Save Source
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
