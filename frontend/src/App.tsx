import { useEffect, useState, useCallback } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardOverview } from './components/dashboard/DashboardOverview';
import { CompanyIntelligenceView } from './components/companies/CompanyIntelligenceView';
import { FounderInterviewView } from './components/interview/FounderInterviewView';
import { SourceIntelligenceView } from './components/sources/SourceIntelligenceView';
import { ModulePlaceholder } from './components/dashboard/ModulePlaceholder';
import { fetchSystemHealth } from './services/api';
import { SystemHealth } from './types';

export function App() {
  const [currentTab, setCurrentTab] = useState<string>('overview');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchSystemHealth();
      setHealth(data);
    } catch {
      // Graceful offline state when backend is not yet started
      setHealth({
        status: 'offline',
        service: 'Signal Stack AI Backend',
        version: '0.1.0',
        environment: 'development',
        timestamp: new Date().toISOString(),
        database: { connected: false, type: 'sqlite' },
        ai_providers: {
          gemini: { configured: false, model: 'gemini-1.5-flash' },
          ollama: { configured: false, model: 'llama3.2' },
        },
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  return (
    <AppLayout
      currentTab={currentTab}
      onSelectTab={setCurrentTab}
      health={health}
      loading={loading}
      onRefresh={loadHealth}
    >
      {currentTab === 'overview' && (
        <DashboardOverview
          health={health}
          loading={loading}
          onNavigateTab={setCurrentTab}
        />
      )}

      {currentTab === 'companies' && (
        <CompanyIntelligenceView />
      )}

      {currentTab === 'interview' && (
        <FounderInterviewView />
      )}

      {currentTab === 'signals' && (
        <ModulePlaceholder
          title="Raw Signal Feeds & Ingestion"
          description="Inspect live signal stream, category classifications, and relevance threshold filters."
          moduleName="signals"
        />
      )}

      {currentTab === 'briefings' && (
        <ModulePlaceholder
          title="Executive Intelligence Briefings"
          description="Generate, review, and export AI-synthesized strategic executive intelligence briefings."
          moduleName="briefings"
        />
      )}

      {currentTab === 'crawlers' && (
        <SourceIntelligenceView />
      )}

      {currentTab === 'settings' && (
        <ModulePlaceholder
          title="Platform Configuration & AI Providers"
          description="Configure Gemini API credentials, local Ollama endpoints, scheduling frequencies, and CORS parameters."
          moduleName="settings"
        />
      )}
    </AppLayout>
  );
}

export default App;
