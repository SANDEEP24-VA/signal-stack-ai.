import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Building2,
  ExternalLink,
  Plus,
  Play,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  FileText,
  Layers,
  Edit3,
  Globe,
  Quote,
  Sparkles,
  HelpCircle,
  X,
} from 'lucide-react';
import {
  Company,
  CompanyFact,
  CompanyProfile,
  ResearchPage,
  ResearchRun,
} from '../../types';
import {
  createCompany,
  fetchCompanies,
  fetchCompanyFacts,
  fetchCompanyPages,
  fetchCompanyProfile,
  fetchResearchRun,
  fetchResearchRuns,
  startResearch,
  updateCompanyProfile,
} from '../../services/api';

export const CompanyIntelligenceView: React.FC = () => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [loadingCompanies, setLoadingCompanies] = useState<boolean>(true);

  // Active Company Data
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [facts, setFacts] = useState<CompanyFact[]>([]);
  const [pages, setPages] = useState<ResearchPage[]>([]);
  const [activeRun, setActiveRun] = useState<ResearchRun | null>(null);
  const [loadingData, setLoadingData] = useState<boolean>(false);

  // UI Navigation Tabs
  const [activeTab, setActiveTab] = useState<'profile' | 'evidence' | 'pages' | 'edit'>('profile');
  const [evidenceFilter, setEvidenceFilter] = useState<'ALL' | 'VERIFIED_FACT' | 'ASSUMPTION' | 'UNKNOWN'>('ALL');

  // Register Modal State
  const [showRegisterModal, setShowRegisterModal] = useState<boolean>(false);
  const [newCompanyName, setNewCompanyName] = useState<string>('');
  const [newCompanyWebsite, setNewCompanyWebsite] = useState<string>('');
  const [newCompanyIndustry, setNewCompanyIndustry] = useState<string>('');
  const [registering, setRegistering] = useState<boolean>(false);
  const [registerError, setRegisterError] = useState<string | null>(null);

  // Edit Profile Form State
  const [editIndustry, setEditIndustry] = useState<string>('');
  const [editBusinessModel, setEditBusinessModel] = useState<string>('');
  const [editPositioning, setEditPositioning] = useState<string>('');
  const [editProducts, setEditProducts] = useState<string>('');
  const [editCustomers, setEditCustomers] = useState<string>('');
  const [editProblems, setEditProblems] = useState<string>('');
  const [editMarkets, setEditMarkets] = useState<string>('');
  const [savingEdit, setSavingEdit] = useState<boolean>(false);
  const [editSuccessMsg, setEditSuccessMsg] = useState<string | null>(null);

  // Research Trigger State
  const [startingResearch, setStartingResearch] = useState<boolean>(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load companies
  const loadCompanies = useCallback(async (selectId?: number) => {
    setLoadingCompanies(true);
    try {
      const data = await fetchCompanies();
      setCompanies(data);
      if (data.length > 0) {
        if (selectId && data.some((c) => c.id === selectId)) {
          setSelectedCompanyId(selectId);
        } else if (!selectedCompanyId || !data.some((c) => c.id === selectedCompanyId)) {
          setSelectedCompanyId(data[0].id);
        }
      } else {
        setSelectedCompanyId(null);
      }
    } catch (err: any) {
      console.error('Failed to load companies:', err);
    } finally {
      setLoadingCompanies(false);
    }
  }, [selectedCompanyId]);

  useEffect(() => {
    loadCompanies();
  }, [loadCompanies]);

  // Load details for selected company
  const loadCompanyData = useCallback(async (companyId: number) => {
    setLoadingData(true);
    try {
      // 1. Fetch research runs to get latest status
      const runs = await fetchResearchRuns(companyId);
      if (runs.length > 0) {
        setActiveRun(runs[0]);
      } else {
        setActiveRun(null);
      }

      // 2. Fetch Profile
      try {
        const p = await fetchCompanyProfile(companyId);
        setProfile(p);
        setEditIndustry(p.industry || '');
        setEditBusinessModel(p.business_model || '');
        setEditPositioning(p.positioning || '');
        setEditProducts(p.products_services?.join(', ') || '');
        setEditCustomers(p.target_customers?.join(', ') || '');
        setEditProblems(p.customer_problems?.join(', ') || '');
        setEditMarkets(p.geographical_markets?.join(', ') || '');
      } catch {
        setProfile(null);
      }

      // 3. Fetch Facts
      try {
        const f = await fetchCompanyFacts(companyId);
        setFacts(f);
      } catch {
        setFacts([]);
      }

      // 4. Fetch Pages
      try {
        const pgs = await fetchCompanyPages(companyId);
        setPages(pgs);
      } catch {
        setPages([]);
      }
    } finally {
      setLoadingData(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCompanyId) {
      loadCompanyData(selectedCompanyId);
    } else {
      setProfile(null);
      setFacts([]);
      setPages([]);
      setActiveRun(null);
    }
  }, [selectedCompanyId, loadCompanyData]);

  // Polling for active research run
  useEffect(() => {
    if (activeRun && (activeRun.status === 'PENDING' || activeRun.status === 'RUNNING')) {
      pollingRef.current = setInterval(async () => {
        if (!selectedCompanyId || !activeRun) return;
        try {
          const updated = await fetchResearchRun(selectedCompanyId, activeRun.id);
          setActiveRun(updated);
          if (updated.status === 'COMPLETED' || updated.status === 'COMPLETED_WITH_WARNINGS' || updated.status === 'FAILED') {
            if (pollingRef.current) clearInterval(pollingRef.current);
            // Refresh full company intelligence
            loadCompanyData(selectedCompanyId);
            loadCompanies(selectedCompanyId);
          }
        } catch (e) {
          console.error('Polling error:', e);
        }
      }, 2000);
    }

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [activeRun, selectedCompanyId, loadCompanyData, loadCompanies]);

  // Trigger Research
  const handleStartResearch = async () => {
    if (!selectedCompanyId || startingResearch) return;
    setStartingResearch(true);
    try {
      const run = await startResearch(selectedCompanyId);
      setActiveRun(run);
      // Switch to profile or evidence tab to watch results
      setActiveTab('profile');
    } catch (err: any) {
      alert(`Could not start research: ${err.message}`);
    } finally {
      setStartingResearch(false);
    }
  };

  // Register New Company
  const handleRegisterCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegistering(true);
    setRegisterError(null);

    try {
      const created = await createCompany({
        name: newCompanyName,
        website: newCompanyWebsite,
        industry: newCompanyIndustry || undefined,
      });

      setShowRegisterModal(false);
      setNewCompanyName('');
      setNewCompanyWebsite('');
      setNewCompanyIndustry('');
      await loadCompanies(created.id);
    } catch (err: any) {
      setRegisterError(err.message || 'Registration failed');
    } finally {
      setRegistering(false);
    }
  };

  // Save Profile Edits
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompanyId) return;
    setSavingEdit(true);
    setEditSuccessMsg(null);

    const parseList = (str: string) =>
      str
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

    try {
      const updated = await updateCompanyProfile(selectedCompanyId, {
        industry: editIndustry,
        business_model: editBusinessModel,
        positioning: editPositioning,
        products_services: parseList(editProducts),
        target_customers: parseList(editCustomers),
        customer_problems: parseList(editProblems),
        geographical_markets: parseList(editMarkets),
      });

      setProfile(updated);
      setEditSuccessMsg(`Profile v${updated.profile_version} saved successfully!`);
      setTimeout(() => setEditSuccessMsg(null), 4000);
    } catch (err: any) {
      alert(`Failed to save profile: ${err.message}`);
    } finally {
      setSavingEdit(false);
    }
  };

  const selectedCompany = companies.find((c) => c.id === selectedCompanyId);

  // Filtered facts
  const filteredFacts = facts.filter((f) => {
    if (evidenceFilter === 'ALL') return true;
    return f.classification === evidenceFilter;
  });

  const verifiedCount = facts.filter((f) => f.classification === 'VERIFIED_FACT').length;
  const assumptionCount = facts.filter((f) => f.classification === 'ASSUMPTION').length;
  const unknownCount = facts.filter((f) => f.classification === 'UNKNOWN').length;

  return (
    <div className="space-y-6">
      {/* Top Header / Company Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 uppercase tracking-wider mb-1">
            <Building2 className="h-4 w-4" />
            Company Intelligence Engine
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            {selectedCompany ? selectedCompany.name : 'Target Companies'}
            {profile && (
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                v{profile.profile_version}
              </span>
            )}
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Company Dropdown */}
          {companies.length > 0 && (
            <select
              value={selectedCompanyId || ''}
              onChange={(e) => setSelectedCompanyId(Number(e.target.value))}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm text-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-medium"
            >
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.normalized_domain})
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => setShowRegisterModal(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 hover:text-white transition-colors"
          >
            <Plus className="h-4 w-4 text-emerald-400" />
            Register Company
          </button>

          {selectedCompany && (
            <button
              onClick={handleStartResearch}
              disabled={
                startingResearch ||
                activeRun?.status === 'PENDING' ||
                activeRun?.status === 'RUNNING'
              }
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 transition-colors disabled:opacity-50"
            >
              {activeRun?.status === 'PENDING' || activeRun?.status === 'RUNNING' ? (
                <>
                  <RotateCw className="h-4 w-4 animate-spin" />
                  Research in Progress...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Start AI Research
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Empty State: No Companies Registered */}
      {!loadingCompanies && companies.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-800 border border-slate-700 text-slate-300 mb-4">
            <Building2 className="h-7 w-7 text-emerald-400" />
          </div>
          <h2 className="text-lg font-semibold text-white">No Target Companies Registered</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">
            Register your first corporate intelligence target by providing its official website URL to
            initiate autonomous crawling, content extraction, and AI synthesis.
          </p>
          <button
            onClick={() => setShowRegisterModal(true)}
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-500 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Register Company Now
          </button>
        </div>
      )}

      {selectedCompany && (
        <>
          {/* Target Company Metadata Card */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs text-slate-400 font-mono">Domain:</span>
              <span className="text-xs font-mono font-medium text-slate-200 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                {selectedCompany.normalized_domain}
              </span>
              <a
                href={selectedCompany.website}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 font-medium"
              >
                {selectedCompany.website} <ExternalLink className="h-3 w-3" />
              </a>
              {selectedCompany.industry && (
                <span className="text-xs text-slate-300 bg-slate-800 px-2.5 py-1 rounded border border-slate-700/60">
                  {selectedCompany.industry}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              <span>Registered: {new Date(selectedCompany.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          {/* Active Research Execution Banner */}
          {activeRun && (
            <div
              className={`rounded-xl border p-5 transition-all ${
                activeRun.status === 'RUNNING' || activeRun.status === 'PENDING'
                  ? 'border-emerald-500/40 bg-emerald-950/20'
                  : activeRun.status === 'FAILED'
                  ? 'border-rose-500/40 bg-rose-950/20'
                  : 'border-slate-800 bg-slate-900/40'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
                <div className="flex items-center gap-2.5">
                  {activeRun.status === 'RUNNING' || activeRun.status === 'PENDING' ? (
                    <RotateCw className="h-4 w-4 animate-spin text-emerald-400" />
                  ) : activeRun.status === 'FAILED' ? (
                    <AlertTriangle className="h-4 w-4 text-rose-400" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  )}
                  <span className="text-sm font-semibold text-white">
                    Research Run #{activeRun.id} —{' '}
                    <span
                      className={
                        activeRun.status === 'COMPLETED'
                          ? 'text-emerald-400'
                          : activeRun.status === 'FAILED'
                          ? 'text-rose-400'
                          : 'text-amber-400'
                      }
                    >
                      {activeRun.status}
                    </span>
                  </span>
                </div>

                <div className="text-xs text-slate-400 flex items-center gap-3">
                  <span>
                    Started: {new Date(activeRun.started_at).toLocaleTimeString()}
                  </span>
                  {activeRun.completed_at && (
                    <span>
                      Completed: {new Date(activeRun.completed_at).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-3 text-xs">
                <div>
                  <span className="text-slate-400">Pages Discovered:</span>
                  <div className="text-sm font-semibold text-white font-mono mt-0.5">
                    {activeRun.pages_discovered}
                  </div>
                </div>
                <div>
                  <span className="text-slate-400">Pages Extracted:</span>
                  <div className="text-sm font-semibold text-emerald-400 font-mono mt-0.5">
                    {activeRun.pages_fetched}
                  </div>
                </div>
                <div>
                  <span className="text-slate-400">Pages Failed:</span>
                  <div className="text-sm font-semibold text-slate-300 font-mono mt-0.5">
                    {activeRun.pages_failed}
                  </div>
                </div>
                <div>
                  <span className="text-slate-400">AI Analysis Status:</span>
                  <div className="text-sm font-semibold text-purple-400 font-mono mt-0.5">
                    {activeRun.ai_analysis_status || 'Pending'}
                  </div>
                </div>
              </div>

              {activeRun.error_message && (
                <div className="mt-3 rounded-lg border border-rose-800/60 bg-rose-950/40 p-3 text-xs text-rose-300">
                  <span className="font-semibold">Notice:</span> {activeRun.error_message}
                </div>
              )}
            </div>
          )}

          {/* Module Sub-Tabs */}
          <div className="flex border-b border-slate-800 space-x-1">
            <button
              onClick={() => setActiveTab('profile')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'profile'
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="h-4 w-4" />
              Strategic Profile
            </button>
            <button
              onClick={() => setActiveTab('evidence')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'evidence'
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <ShieldCheck className="h-4 w-4" />
              Evidence & Facts ({facts.length})
            </button>
            <button
              onClick={() => setActiveTab('pages')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'pages'
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="h-4 w-4" />
              Crawled Pages ({pages.length})
            </button>
            <button
              onClick={() => setActiveTab('edit')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'edit'
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Edit3 className="h-4 w-4" />
              Edit Profile
            </button>
          </div>

          {/* TAB 1: STRATEGIC INTELLIGENCE PROFILE */}
          {activeTab === 'profile' && (
            <div className="space-y-6">
              {!profile && !loadingData && (
                <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-8 text-center">
                  <FileText className="mx-auto h-8 w-8 text-slate-500 mb-2" />
                  <h3 className="text-base font-semibold text-white">No Intelligence Profile Available</h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                    Click "Start AI Research" above to crawl {selectedCompany.name}'s public web pages and generate an evidence-verified executive profile.
                  </p>
                </div>
              )}

              {profile && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Left Column: Core Positioning & Model */}
                  <div className="lg:col-span-2 space-y-6">
                    {/* Positioning Card */}
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        Market Positioning & Value Proposition
                      </h3>
                      <p className="text-sm font-medium text-slate-100 leading-relaxed">
                        {profile.positioning || 'Positioning details pending analysis.'}
                      </p>
                    </div>

                    {/* Business Model & Industry */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                          Industry Sector
                        </div>
                        <div className="text-sm font-medium text-white">
                          {profile.industry || 'Not specified'}
                        </div>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                          Business Model
                        </div>
                        <div className="text-sm font-medium text-white">
                          {profile.business_model || 'Not specified'}
                        </div>
                      </div>
                    </div>

                    {/* Products and Services */}
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                        Products & Service Offerings
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {profile.products_services?.length > 0 ? (
                          profile.products_services.map((item, idx) => (
                            <span
                              key={idx}
                              className="rounded-lg border border-emerald-800/50 bg-emerald-950/60 px-3 py-1.5 text-xs font-medium text-emerald-300"
                            >
                              {item}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500">None extracted yet</span>
                        )}
                      </div>
                    </div>

                    {/* Customer Problems Addressed */}
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                        Customer Problems Solved
                      </h3>
                      <ul className="space-y-2 text-xs text-slate-300">
                        {profile.customer_problems?.length > 0 ? (
                          profile.customer_problems.map((prob, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-emerald-400 mt-0.5">•</span>
                              <span>{prob}</span>
                            </li>
                          ))
                        ) : (
                          <span className="text-slate-500">No specific problem statements identified</span>
                        )}
                      </ul>
                    </div>
                  </div>

                  {/* Right Column: Markets, Revenue, Unknowns */}
                  <div className="space-y-6">
                    {/* Target Customers */}
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                        Target Customers & ICP
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {profile.target_customers?.length > 0 ? (
                          profile.target_customers.map((cust, idx) => (
                            <span
                              key={idx}
                              className="rounded-lg border border-cyan-800/50 bg-cyan-950/60 px-2.5 py-1 text-xs font-medium text-cyan-300"
                            >
                              {cust}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500">Not identified</span>
                        )}
                      </div>
                    </div>

                    {/* Geographical Markets */}
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                        Geographical Markets
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {profile.geographical_markets?.length > 0 ? (
                          profile.geographical_markets.map((geo, idx) => (
                            <span
                              key={idx}
                              className="rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs text-slate-300"
                            >
                              {geo}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500">Global / Not specified</span>
                        )}
                      </div>
                    </div>

                    {/* Revenue Streams */}
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                        Revenue Streams
                      </h3>
                      <ul className="space-y-1.5 text-xs text-slate-300">
                        {profile.revenue_streams?.length > 0 ? (
                          profile.revenue_streams.map((rev, idx) => (
                            <li key={idx} className="flex items-start gap-1.5">
                              <span className="text-cyan-400">✓</span>
                              <span>{rev}</span>
                            </li>
                          ))
                        ) : (
                          <span className="text-slate-500">Not publicly disclosed</span>
                        )}
                      </ul>
                    </div>

                    {/* Unknown Information Card */}
                    <div className="rounded-xl border border-slate-800/90 bg-slate-950/80 p-6">
                      <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <HelpCircle className="h-3.5 w-3.5" />
                        Explicit Knowledge Gaps (Unknowns)
                      </h3>
                      <ul className="space-y-1.5 text-xs text-slate-400">
                        {profile.unknown_information?.length > 0 ? (
                          profile.unknown_information.map((unk, idx) => (
                            <li key={idx} className="flex items-start gap-1.5">
                              <span className="text-amber-500">?</span>
                              <span>{unk}</span>
                            </li>
                          ))
                        ) : (
                          <span className="text-slate-500">No explicit gaps recorded</span>
                        )}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: EVIDENCE & TRACEABILITY PANEL */}
          {activeTab === 'evidence' && (
            <div className="space-y-6">
              {/* Evidence Filters Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => setEvidenceFilter('ALL')}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                      evidenceFilter === 'ALL'
                        ? 'bg-slate-700 text-white'
                        : 'bg-slate-900 text-slate-400 hover:text-white'
                    }`}
                  >
                    All Evidence ({facts.length})
                  </button>
                  <button
                    onClick={() => setEvidenceFilter('VERIFIED_FACT')}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                      evidenceFilter === 'VERIFIED_FACT'
                        ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700'
                        : 'bg-slate-900 text-slate-400 hover:text-emerald-300'
                    }`}
                  >
                    Verified Facts ({verifiedCount})
                  </button>
                  <button
                    onClick={() => setEvidenceFilter('ASSUMPTION')}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                      evidenceFilter === 'ASSUMPTION'
                        ? 'bg-amber-900/60 text-amber-300 border border-amber-700'
                        : 'bg-slate-900 text-slate-400 hover:text-amber-300'
                    }`}
                  >
                    Assumptions ({assumptionCount})
                  </button>
                  <button
                    onClick={() => setEvidenceFilter('UNKNOWN')}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                      evidenceFilter === 'UNKNOWN'
                        ? 'bg-purple-900/60 text-purple-300 border border-purple-700'
                        : 'bg-slate-900 text-slate-400 hover:text-purple-300'
                    }`}
                  >
                    Unknowns ({unknownCount})
                  </button>
                </div>

                <div className="text-xs text-slate-400">
                  Strict evidence rules enforced: Verbatim match required for verification.
                </div>
              </div>

              {filteredFacts.length === 0 ? (
                <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-12 text-center text-slate-400 text-sm">
                  No facts match the selected filter.
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredFacts.map((fact) => (
                    <div
                      key={fact.id}
                      className={`rounded-xl border p-5 transition-colors ${
                        fact.classification === 'VERIFIED_FACT'
                          ? 'border-emerald-900/50 bg-emerald-950/10'
                          : fact.classification === 'ASSUMPTION'
                          ? 'border-amber-900/50 bg-amber-950/10'
                          : 'border-slate-800 bg-slate-900/30'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${
                            fact.classification === 'VERIFIED_FACT'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : fact.classification === 'ASSUMPTION'
                              ? 'bg-amber-950 text-amber-400 border border-amber-800'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {fact.classification === 'VERIFIED_FACT' && <CheckCircle2 className="h-3 w-3" />}
                          {fact.classification === 'ASSUMPTION' && <AlertTriangle className="h-3 w-3" />}
                          {fact.classification.replace('_', ' ')}
                        </span>

                        <span className="text-[11px] text-slate-400 font-mono">
                          Category: {fact.category}
                        </span>
                      </div>

                      <div className="text-sm font-medium text-white mb-3">
                        {fact.statement}
                      </div>

                      {/* Supporting Evidence Snippet */}
                      {fact.evidence_snippet && (
                        <div className="rounded-lg border border-emerald-900/60 bg-emerald-950/30 p-3 text-xs text-emerald-200 mb-3 flex items-start gap-2.5">
                          <Quote className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                          <div className="italic">
                            "{fact.evidence_snippet}"
                          </div>
                        </div>
                      )}

                      {/* Source Link */}
                      {fact.source_url && (
                        <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
                          <a
                            href={fact.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-slate-300 hover:text-emerald-400 transition-colors"
                          >
                            <Globe className="h-3.5 w-3.5 text-slate-400" />
                            <span className="truncate max-w-md">
                              {fact.source_title || fact.source_url}
                            </span>
                            <ExternalLink className="h-3 w-3 ml-1" />
                          </a>
                          <span className="text-[11px] text-slate-400">
                            Verified on {new Date(fact.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: CRAWLED EVIDENCE WEBPAGES */}
          {activeTab === 'pages' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-400 pb-2">
                All public documents discovered and crawled from {selectedCompany.normalized_domain}.
              </div>

              {pages.length === 0 ? (
                <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-12 text-center text-slate-400 text-sm">
                  No crawled pages recorded yet.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider text-[11px] border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-3">Page Title & URL</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Text Length</th>
                        <th className="px-4 py-3">Content Hash</th>
                        <th className="px-4 py-3">Crawled Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
                      {pages.map((p) => (
                        <tr key={p.id} className="hover:bg-slate-900/40 transition-colors">
                          <td className="px-4 py-3">
                            <div className="font-semibold text-white mb-0.5">{p.title || 'Untitled'}</div>
                            <a
                              href={p.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-mono text-[11px]"
                            >
                              <span className="truncate max-w-sm">{p.url}</span>
                              <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          </td>
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                              HTTP {p.http_status || 200}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-slate-300">
                            {p.text_length.toLocaleString()} chars
                          </td>
                          <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                            {p.content_hash ? `${p.content_hash.slice(0, 10)}...` : 'N/A'}
                          </td>
                          <td className="px-4 py-3 text-slate-400">
                            {new Date(p.crawled_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: EDIT PROFILE (FOUNDER / ANALYST OVERRIDES) */}
          {activeTab === 'edit' && (
            <form onSubmit={handleSaveProfile} className="space-y-6 max-w-3xl">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-semibold text-white">
                    Founder / Executive Intelligence Overrides
                  </h3>
                  <span className="text-xs text-slate-400">
                    Current Version: v{profile?.profile_version || 1}
                  </span>
                </div>

                {editSuccessMsg && (
                  <div className="rounded-lg bg-emerald-950 border border-emerald-800 p-3 text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    <span>{editSuccessMsg}</span>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Industry Sector
                  </label>
                  <input
                    type="text"
                    value={editIndustry}
                    onChange={(e) => setEditIndustry(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="e.g. EdTech / Higher Education"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Business Model
                  </label>
                  <input
                    type="text"
                    value={editBusinessModel}
                    onChange={(e) => setEditBusinessModel(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="e.g. Marketplace recruitment platform"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Market Positioning
                  </label>
                  <textarea
                    rows={3}
                    value={editPositioning}
                    onChange={(e) => setEditPositioning(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="Core strategic positioning statement..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Products & Services (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={editProducts}
                    onChange={(e) => setEditProducts(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="Course Finder, Visa Guidance, University Connect"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Target Customers (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={editCustomers}
                    onChange={(e) => setEditCustomers(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="International Students, Universities, High Schools"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Customer Problems Addressed (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={editProblems}
                    onChange={(e) => setEditProblems(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="Application complexity, High agency fees"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Geographical Markets (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={editMarkets}
                    onChange={(e) => setEditMarkets(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="India, United Kingdom, USA, Canada"
                  />
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={savingEdit}
                    className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 transition-colors disabled:opacity-50"
                  >
                    {savingEdit ? (
                      <>
                        <RotateCw className="h-4 w-4 animate-spin" />
                        Saving Profile...
                      </>
                    ) : (
                      'Save & Increment Version'
                    )}
                  </button>
                </div>
              </div>
            </form>
          )}
        </>
      )}

      {/* REGISTER COMPANY MODAL */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Building2 className="h-5 w-5 text-emerald-400" />
                Register Intelligence Target
              </h3>
              <button
                onClick={() => setShowRegisterModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {registerError && (
              <div className="mb-4 rounded-lg bg-rose-950/70 border border-rose-800 p-3 text-xs text-rose-300 flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <span>{registerError}</span>
              </div>
            )}

            <form onSubmit={handleRegisterCompany} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Company Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newCompanyName}
                  onChange={(e) => setNewCompanyName(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  placeholder="e.g. MeetUniversity"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Official Website URL <span className="text-rose-400">*</span>
                </label>
                <input
                  type="url"
                  required
                  value={newCompanyWebsite}
                  onChange={(e) => setNewCompanyWebsite(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none font-mono text-xs"
                  placeholder="https://www.meetuniversity.com"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Must be HTTP or HTTPS. Domain will be normalized automatically.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Industry / Sector (Optional)
                </label>
                <input
                  type="text"
                  value={newCompanyIndustry}
                  onChange={(e) => setNewCompanyIndustry(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  placeholder="e.g. Higher Education / EdTech"
                />
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={registering}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {registering ? (
                    <>
                      <RotateCw className="h-3.5 w-3.5 animate-spin" />
                      Registering...
                    </>
                  ) : (
                    'Save Company Target'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
