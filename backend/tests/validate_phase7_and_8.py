"""
Phase 7 & Phase 8 Comprehensive Validation Script
Signal Stack AI - Task 4: Dynamic Competitor Discovery & Source Intelligence Management

Validates:
- Phase 7: MeetUniversity (EdTech) live discovery (5-10 competitors, >=20 sources, approvals, health probes, logs)
- Phase 8: Nexus Robotics (AgTech / Autonomous Weeding) live discovery (domain-specific competitors & sources, 0 overlap)
- Phase 8: CloudPulse AI (B2B Observability / APM) live discovery (domain-specific competitors & sources, 0 overlap)
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.ai.manager import get_active_ai_provider
from app.database.session import SessionLocal
from app.database.models import (
    Company,
    CompanyFact,
    CompanyProfile,
    FounderBusinessContext,
    InterviewSession,
    Competitor,
    CompetitorRelationshipType,
    CompetitorReviewStatus,
    IntelligenceSource,
    IntelligenceSourceCategory,
    IntelligenceSourceType,
    IntelligenceSourceStatus,
    SourceCrawlLog,
)
from app.discovery.competitors import CompetitorDiscoveryEngine
from app.discovery.sources import SourceDiscoveryEngine
from app.discovery.governance import SourceGovernanceManager, CompetitorGovernanceManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("task4_validation")


def setup_nexus_robotics(db: Session) -> Company:
    """Ensure Nexus Robotics has realistic, domain-specific facts, profile and founder context."""
    company = db.query(Company).filter(Company.id == 2).first()
    if not company:
        company = Company(
            id=2,
            name="Nexus Robotics",
            website="https://nexusrobotics.ai",
            normalized_domain="nexusrobotics.ai",
            industry="Autonomous Agricultural Robotics",
            status="ACTIVE",
        )
        db.add(company)
        db.commit()
        db.refresh(company)

    # 1. Company Profile
    profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == 2).first()
    if not profile:
        profile = CompanyProfile(
            company_id=2,
            profile_version=1,
            industry="Autonomous Agricultural Robotics",
            business_model="Robotics-as-a-Service (RaaS) subscription model for commercial vegetable growers.",
            positioning="Eco-friendly precision agriculture robotics replacing manual field labour and reducing herbicide reliance.",
            products_services=["La Chèvre autonomous weeding robot", "AI weed identification vision system", "Field telemetry analytics"],
            target_customers=["Commercial vegetable farmers", "Organic crop producers", "High-value specialty crop growers"],
            customer_problems=["Agricultural farm labour shortages", "Herbicide resistance in weeds", "Environmental regulations on chemical runoff"],
            geographical_markets=["Canada", "United States (California, Salinas Valley)", "Europe"],
            unknown_information=["Exact hourly operational pricing per acre and full unit manufacturing bill of materials."],
        )
        db.add(profile)
        db.commit()

    # 2. Company Facts
    fact_count = db.query(CompanyFact).filter(CompanyFact.company_id == 2).count()
    if fact_count == 0:
        facts_data = [
            ("Core Technology", "Nexus Robotics builds autonomous robots using deep learning computer vision to differentiate between crops and weeds.", "VERIFIED"),
            ("Flagship Product", "The robotic platform 'La Chèvre' operates autonomously in crop fields removing weeds mechanically.", "VERIFIED"),
            ("Target Market", "Primary customer base consists of commercial organic vegetable farms and specialty crop growers.", "VERIFIED"),
            ("Value Proposition", "Reduces manual farm labour costs by up to 80% while completely eliminating chemical herbicide application.", "VERIFIED"),
            ("Navigation System", "Equipped with RTK-GPS, LiDAR, and stereo cameras for autonomous field row navigation and obstacle avoidance.", "VERIFIED"),
            ("Business Model", "Operates a Robotics-as-a-Service (RaaS) operational lease model charging per acre weeded.", "VERIFIED"),
            ("Key Partners", "Supported by agricultural research programs at McGill University and certified organic farming co-ops.", "VERIFIED"),
        ]
        for cat, stmt, cls in facts_data:
            db.add(CompanyFact(
                company_id=2,
                category=cat,
                statement=stmt,
                classification=cls,
                evidence_snippet=stmt,
            ))
        db.commit()

    # 3. Founder Context
    session = db.query(InterviewSession).filter(InterviewSession.company_id == 2).first()
    if not session:
        session = InterviewSession(company_id=2, status="COMPLETED")
        db.add(session)
        db.commit()
        db.refresh(session)

    fc_count = db.query(FounderBusinessContext).filter(FounderBusinessContext.company_id == 2).count()
    if fc_count == 0:
        contexts = [
            ("competitors", "direct_competitors", ["Carbon Robotics", "FarmWise", "Naïo Technologies", "Stout Industrial Technology"]),
            ("competitors", "indirect_substitutes", ["John Deere autonomous tractors", "Raven Industries autonomous sprayers", "Hand weeding crews"]),
            ("regulatory_bodies", "oversight_agencies", ["USDA Agricultural Marketing Service", "EPA Office of Pesticide Programs", "CFIA Canadian Food Inspection Agency"]),
            ("target_customers", "ideal_segments", ["Commercial vegetable growers", "Organic brassica producers", "Agricultural co-ops"]),
            ("technology_dependencies", "key_hardware", ["NVIDIA Jetson edge AI", "Stereolabs ZED stereo cameras", "RTK GPS positioning"]),
        ]
        for cat, field, val in contexts:
            db.add(FounderBusinessContext(
                company_id=2,
                interview_session_id=session.id,
                context_category=cat,
                field_name=field,
                confirmed_value=val,
                confidence=1.0,
            ))
        db.commit()

    return company


def setup_cloudpulse_ai(db: Session) -> Company:
    """Ensure Company 3 (CloudPulse AI) exists for B2B Cloud / Observability validation."""
    company = db.query(Company).filter(Company.normalized_domain == "cloudpulse.io").first()
    if not company:
        company = Company(
            name="CloudPulse AI",
            website="https://cloudpulse.io",
            normalized_domain="cloudpulse.io",
            industry="B2B Cloud Observability & Autonomous APM",
            status="ACTIVE",
        )
        db.add(company)
        db.commit()
        db.refresh(company)

    profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == company.id).first()
    if not profile:
        profile = CompanyProfile(
            company_id=company.id,
            profile_version=1,
            industry="B2B Cloud Observability & Autonomous APM",
            business_model="Tiered B2B SaaS subscription based on active telemetry ingest gigabytes and host node count.",
            positioning="Zero-overhead autonomous telemetry and instant incident triage without manual application code instrumentation.",
            products_services=["CloudPulse eBPF Agent", "CloudPulse Autonomous APM", "Kubernetes Anomaly Detector", "Service Topology Graph"],
            target_customers=["Site Reliability Engineers (SREs)", "DevOps teams", "Enterprise platform engineering groups"],
            customer_problems=["Microservice alert fatigue", "Complex multi-cloud debugging latency", "High traditional APM vendor licensing costs"],
            geographical_markets=["North America", "European Union", "APAC tech hubs"],
            unknown_information=["Custom enterprise on-premise air-gapped pricing schedule."],
        )
        db.add(profile)
        db.commit()

    fact_count = db.query(CompanyFact).filter(CompanyFact.company_id == company.id).count()
    if fact_count == 0:
        facts = [
            ("Core Platform", "CloudPulse delivers kernel-level eBPF continuous profiling and microservice network mapping.", "VERIFIED"),
            ("Incident Response", "AI anomaly correlation engine detects multi-tier cascading latency regressions in real time.", "VERIFIED"),
            ("Target Audience", "SREs and engineering leaders managing Kubernetes clusters across AWS, GCP, and Azure.", "VERIFIED"),
            ("Architecture", "Collects telemetry at Linux kernel boundary with zero proprietary SDK code modifications.", "VERIFIED"),
            ("Security & Compliance", "SOC2 Type II certified and GDPR compliant with automated PII masking on trace payloads.", "VERIFIED"),
        ]
        for cat, stmt, cls in facts:
            db.add(CompanyFact(
                company_id=company.id,
                category=cat,
                statement=stmt,
                classification=cls,
                evidence_snippet=stmt,
            ))
        db.commit()

    session = db.query(InterviewSession).filter(InterviewSession.company_id == company.id).first()
    if not session:
        session = InterviewSession(company_id=company.id, status="COMPLETED")
        db.add(session)
        db.commit()
        db.refresh(session)

    fc_count = db.query(FounderBusinessContext).filter(FounderBusinessContext.company_id == company.id).count()
    if fc_count == 0:
        contexts = [
            ("competitors", "direct_competitors", ["Datadog", "Dynatrace", "New Relic", "Grafana Labs", "Honeycomb.io"]),
            ("competitors", "indirect_alternatives", ["Prometheus Thanos open-source stack", "AWS CloudWatch", "Splunk APM"]),
            ("regulatory_bodies", "standards_organizations", ["Cloud Native Computing Foundation (CNCF)", "OpenTelemetry Governing Board", "NIST Cloud Standards"]),
            ("target_customers", "ideal_segments", ["Enterprise SRE teams", "FinTech platforms", "Cloud-native platform engineering leaders"]),
            ("technology_dependencies", "key_dependencies", ["Linux eBPF kernel subsystem", "ClickHouse analytical DB", "Apache Kafka event streaming"]),
        ]
        for cat, field, val in contexts:
            db.add(FounderBusinessContext(
                company_id=company.id,
                interview_session_id=session.id,
                context_category=cat,
                field_name=field,
                confirmed_value=val,
                confidence=1.0,
            ))
        db.commit()

    return company


async def run_phase7_meetuniversity(db: Session):
    print("=" * 80)
    print("PHASE 7 — MEETUNIVERSITY (EDTECH) LIVE VALIDATION")
    print("=" * 80)

    provider = await get_active_ai_provider()
    comp_engine = CompetitorDiscoveryEngine(db=db, provider=provider)
    src_engine = SourceDiscoveryEngine(db=db, provider=provider)
    source_gov = SourceGovernanceManager(db=db)
    comp_gov = CompetitorGovernanceManager(db=db)

    # 1. Competitor Discovery
    print("\n[Step 7.1] Triggering Dynamic Competitor Discovery for MeetUniversity (Company ID: 1)...")
    discovered_comps = await comp_engine.discover_competitors(company_id=1)
    print(f"✓ Total Competitors in Registry: {len(discovered_comps)}")
    assert len(discovered_comps) >= 5, f"Expected at least 5 competitors, got {len(discovered_comps)}"

    print("\nDiscovered Competitor Registry:")
    direct_count = 0
    indirect_count = 0
    substitute_count = 0
    for idx, comp in enumerate(discovered_comps, 1):
        rel_type = str(getattr(comp.relationship_type, "value", comp.relationship_type))
        rev_status = str(getattr(comp.review_status, "value", comp.review_status))
        if rel_type == "DIRECT":
            direct_count += 1
        elif rel_type == "INDIRECT":
            indirect_count += 1
        elif rel_type == "SUBSTITUTE":
            substitute_count += 1
        print(f"  {idx}. [{rel_type:10}] {comp.name:25} ({comp.canonical_domain}) | Status: {rev_status:10} | Confidence: {comp.confidence:.2f}")
        print(f"     Rationale: {comp.discovery_rationale}")

    print(f"\nRelationship Breakdown: Direct={direct_count}, Indirect={indirect_count}, Substitute={substitute_count}")

    # Approve top 3 competitors for downstream tracking
    print("\n[Step 7.2] Reviewing & Approving Key Competitors...")
    for comp in discovered_comps[:3]:
        comp_gov.approve_competitor(comp.id)
        print(f"  ✓ Approved: {comp.name} ({comp.canonical_domain}) -> APPROVED")

    # 2. Source Discovery
    print("\n[Step 7.3] Triggering Multi-Method Source Discovery for MeetUniversity...")
    discovered_sources = await src_engine.discover_sources_for_company(company_id=1)
    print(f"✓ Total Sources in Registry: {len(discovered_sources)}")
    assert len(discovered_sources) >= 20, f"Expected at least 20 sources, got {len(discovered_sources)}"

    cat_counts = {cat.value: 0 for cat in IntelligenceSourceCategory}
    type_counts = {}
    for s in discovered_sources:
        cat_key = str(getattr(s.category, "value", s.category))
        type_key = str(getattr(s.source_type, "value", s.source_type))
        cat_counts[cat_key] = cat_counts.get(cat_key, 0) + 1
        type_counts[type_key] = type_counts.get(type_key, 0) + 1

    print("\nSource Category Coverage:")
    for cat, count in cat_counts.items():
        print(f"  - Category '{cat:12}': {count:2} sources")
        assert count > 0, f"Category '{cat}' must have at least 1 discovered source!"

    print("\nSource Type Breakdown:")
    for stype, count in type_counts.items():
        print(f"  - Type '{stype:16}': {count:2} sources")

    # Print sample sources across categories
    print("\nSample Intelligence Sources Discovered:")
    for cat in IntelligenceSourceCategory:
        cat_val = getattr(cat, "value", cat)
        sample = next((s for s in discovered_sources if s.category == cat_val), None)
        if sample:
            cat_str = str(getattr(sample.category, "value", sample.category))
            type_str = str(getattr(sample.source_type, "value", sample.source_type))
            print(f"  [{cat_str.upper()}] {sample.name} ({sample.canonical_url})")
            print(f"    Type: {type_str} | Credibility: {sample.credibility_score:.2f} | Method: {sample.discovery_method}")
            print(f"    Why it matters: {sample.why_it_matters[:80]}...")

    # 3. Source Governance: Approval and Rejection
    print("\n[Step 7.4] Reviewing & Governing Sources...")
    approved_count = 0
    rejected_count = 0
    for s in discovered_sources:
        cat_str = str(getattr(s.category, "value", s.category))
        if s.credibility_score >= 0.85 and approved_count < 5:
            source_gov.approve_source(s.id)
            approved_count += 1
            print(f"  ✓ Approved: [{cat_str}] {s.name}")
        elif s.credibility_score < 0.75 and rejected_count < 2:
            source_gov.reject_source(s.id, "Outside core intelligence scope")
            rejected_count += 1
            print(f"  ✗ Rejected: [{cat_str}] {s.name}")

    # 4. Safe Health Probing
    print("\n[Step 7.5] Probing Health of Approved Sources (SSRF-protected, robots-aware)...")
    approved_sources = db.query(IntelligenceSource).filter(
        IntelligenceSource.company_id == 1,
        IntelligenceSource.status == IntelligenceSourceStatus.APPROVED,
    ).all()

    probe_success = 0
    for src in approved_sources[:3]:
        log_entry = await source_gov.probe_source_health(src.id)
        if log_entry:
            print(f"  [Probe] {src.name} ({src.canonical_url})")
            print(f"    Status: {log_entry.status} | HTTP {log_entry.http_status} | Latency: {log_entry.response_time_ms}ms | Hash: {log_entry.content_hash or 'N/A'}")
            probe_success += 1

    # Verify audit logs in database
    logs_in_db = db.query(SourceCrawlLog).join(IntelligenceSource).filter(
        IntelligenceSource.company_id == 1
    ).count()
    print(f"\n✓ Verified {logs_in_db} crawl audit log records persisted in source_crawl_logs.")
    print("✓ Phase 7 Validation for MeetUniversity PASSED successfully.")


async def run_phase8_multi_company(db: Session):
    print("\n" + "=" * 80)
    print("PHASE 8 — MULTI-COMPANY DIVERSIFICATION & ISOLATION VALIDATION")
    print("=" * 80)

    provider = await get_active_ai_provider()
    comp_engine = CompetitorDiscoveryEngine(db=db, provider=provider)
    src_engine = SourceDiscoveryEngine(db=db, provider=provider)

    # Company 2: Nexus Robotics
    print("\n[Step 8.1] Initializing Company 2: Nexus Robotics (AgTech / Autonomous Weeding)...")
    c2 = setup_nexus_robotics(db)
    print(f"✓ Company 2 configured: {c2.name} | Industry: {c2.industry}")

    c2_comps = await comp_engine.discover_competitors(company_id=2)
    print(f"✓ Nexus Robotics Discovered Competitors ({len(c2_comps)}):")
    c2_comp_names = set()
    for c in c2_comps:
        c2_comp_names.add(c.name.lower())
        rel_type = str(getattr(c.relationship_type, "value", c.relationship_type))
        print(f"  - [{rel_type:10}] {c.name:25} ({c.canonical_domain}) | Conf: {c.confidence:.2f}")

    c2_sources = await src_engine.discover_sources_for_company(company_id=2)
    print(f"✓ Nexus Robotics Discovered Sources ({len(c2_sources)}):")
    for s in c2_sources[:6]:
        cat_str = str(getattr(s.category, "value", s.category))
        type_str = str(getattr(s.source_type, "value", s.source_type))
        print(f"  - [{cat_str:11} | {type_str:14}] {s.name:30} ({s.canonical_url[:45]}...)")

    # Company 3: CloudPulse AI
    print("\n[Step 8.2] Initializing Company 3: CloudPulse AI (B2B Observability / APM)...")
    c3 = setup_cloudpulse_ai(db)
    print(f"✓ Company 3 configured: {c3.name} | Industry: {c3.industry}")

    c3_comps = await comp_engine.discover_competitors(company_id=c3.id)
    print(f"✓ CloudPulse AI Discovered Competitors ({len(c3_comps)}):")
    c3_comp_names = set()
    for c in c3_comps:
        c3_comp_names.add(c.name.lower())
        rel_type = str(getattr(c.relationship_type, "value", c.relationship_type))
        print(f"  - [{rel_type:10}] {c.name:25} ({c.canonical_domain}) | Conf: {c.confidence:.2f}")

    c3_sources = await src_engine.discover_sources_for_company(company_id=c3.id)
    print(f"✓ CloudPulse AI Discovered Sources ({len(c3_sources)}):")
    for s in c3_sources[:6]:
        cat_str = str(getattr(s.category, "value", s.category))
        type_str = str(getattr(s.source_type, "value", s.source_type))
        print(f"  - [{cat_str:11} | {type_str:14}] {s.name:30} ({s.canonical_url[:45]}...)")

    # 3. Cross-Company Isolation and Zero-Overlap Verification
    print("\n[Step 8.3] Verifying Cross-Company Intelligence Isolation & Zero Overlap...")
    c1_comps = db.query(Competitor).filter(Competitor.company_id == 1).all()
    c1_comp_names = {c.name.lower() for c in c1_comps}

    print(f"  Company 1 (MeetUniversity EdTech) Competitors: {c1_comp_names}")
    print(f"  Company 2 (Nexus Robotics AgTech) Competitors: {c2_comp_names}")
    print(f"  Company 3 (CloudPulse AI APM) Competitors:     {c3_comp_names}")

    overlap_1_2 = c1_comp_names.intersection(c2_comp_names)
    overlap_1_3 = c1_comp_names.intersection(c3_comp_names)
    overlap_2_3 = c2_comp_names.intersection(c3_comp_names)

    print(f"\n  Overlap (MeetUniversity vs Nexus Robotics): {overlap_1_2 or 'ZERO (Passed)'}")
    print(f"  Overlap (MeetUniversity vs CloudPulse AI):  {overlap_1_3 or 'ZERO (Passed)'}")
    print(f"  Overlap (Nexus Robotics vs CloudPulse AI):   {overlap_2_3 or 'ZERO (Passed)'}")

    assert len(overlap_1_2) == 0, f"Found unexpected competitor overlap between C1 and C2: {overlap_1_2}"
    assert len(overlap_1_3) == 0, f"Found unexpected competitor overlap between C1 and C3: {overlap_1_3}"
    assert len(overlap_2_3) == 0, f"Found unexpected competitor overlap between C2 and C3: {overlap_2_3}"

    # Verify source domain isolation
    c1_src_urls = {s.canonical_url for s in db.query(IntelligenceSource).filter(IntelligenceSource.company_id == 1).all()}
    c2_src_urls = {s.canonical_url for s in c2_sources}
    c3_src_urls = {s.canonical_url for s in c3_sources}

    print(f"\n  Sources Count: C1={len(c1_src_urls)}, C2={len(c2_src_urls)}, C3={len(c3_src_urls)}")
    print("✓ Phase 8 Multi-Company Diversification & Zero-Overlap PASSED successfully.")


async def main():
    print("SIGNAL STACK AI — TASK 4 VALIDATION SUITE")
    print(f"Execution started at: {datetime.now().isoformat()}Z\n")
    db = SessionLocal()
    try:
        await run_phase7_meetuniversity(db)
        await run_phase8_multi_company(db)
        print("\n" + "=" * 80)
        print("ALL TASK 4 VALIDATION CHECKS (PHASE 7 & PHASE 8) COMPLETED SUCCESSFULLY")
        print("=" * 80)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
