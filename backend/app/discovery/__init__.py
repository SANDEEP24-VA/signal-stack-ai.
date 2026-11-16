"""Dynamic Competitor Discovery and Source Intelligence Module."""
from app.discovery.competitors import CompetitorDiscoveryEngine
from app.discovery.governance import CompetitorGovernanceManager, SourceGovernanceManager
from app.discovery.sources import SourceDiscoveryEngine

__all__ = [
    "CompetitorDiscoveryEngine",
    "SourceDiscoveryEngine",
    "SourceGovernanceManager",
    "CompetitorGovernanceManager",
]
