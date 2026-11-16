from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import Company, ResearchPage, ResearchRun


def test_sha256_content_deduplication_and_history(db_session: Session):
    company = Company(
        name="Dedupe Tech",
        website="https://dedupe-tech.com",
        normalized_domain="dedupe-tech.com",
        status="ACTIVE",
    )
    db_session.add(company)
    db_session.flush()

    run1 = ResearchRun(company_id=company.id, status="COMPLETED")
    db_session.add(run1)
    db_session.flush()

    initial_text = "Dedupe Tech builds high-throughput real-time telemetry systems."
    initial_hash = ResearchPage.compute_hash(initial_text)

    page1 = ResearchPage(
        company_id=company.id,
        research_run_id=run1.id,
        url="https://dedupe-tech.com/about",
        title="About Dedupe Tech",
        extracted_text=initial_text,
        content_hash=initial_hash,
        http_status=200,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        crawled_at=datetime.now(timezone.utc),
    )
    db_session.add(page1)
    db_session.commit()

    # Verify initial snapshot
    pages_count = db_session.query(ResearchPage).filter(ResearchPage.company_id == company.id).count()
    assert pages_count == 1

    # Simulate Run 2: Same content crawled
    run2 = ResearchRun(company_id=company.id, status="COMPLETED")
    db_session.add(run2)
    db_session.flush()

    same_text_hash = ResearchPage.compute_hash(initial_text)
    assert same_text_hash == initial_hash

    # Check that identical content hash matches existing page
    existing = (
        db_session.query(ResearchPage)
        .filter(
            ResearchPage.company_id == company.id,
            ResearchPage.url == "https://dedupe-tech.com/about",
        )
        .first()
    )
    assert existing is not None
    assert existing.content_hash == same_text_hash

    # Update existing record's last_seen_at without creating a duplicate row
    now_run2 = datetime.now(timezone.utc)
    existing.last_seen_at = now_run2
    existing.research_run_id = run2.id
    db_session.commit()

    # Total pages should still be exactly 1
    total_pages = db_session.query(ResearchPage).filter(ResearchPage.company_id == company.id).count()
    assert total_pages == 1

    # Simulate Run 3: Content changed on website
    run3 = ResearchRun(company_id=company.id, status="COMPLETED")
    db_session.add(run3)
    db_session.flush()

    modified_text = "Dedupe Tech builds high-throughput telemetry and autonomous signal engines."
    modified_hash = ResearchPage.compute_hash(modified_text)
    assert modified_hash != initial_hash

    # When content has changed, create a new snapshot to preserve historical record
    page_version2 = ResearchPage(
        company_id=company.id,
        research_run_id=run3.id,
        url="https://dedupe-tech.com/about",
        title="About Dedupe Tech - 2026",
        extracted_text=modified_text,
        content_hash=modified_hash,
        http_status=200,
        first_seen_at=now_run2,
        last_seen_at=datetime.now(timezone.utc),
        crawled_at=datetime.now(timezone.utc),
    )
    db_session.add(page_version2)
    db_session.commit()

    # Total pages should now be 2, preserving historical evolution
    historical_pages = db_session.query(ResearchPage).filter(ResearchPage.company_id == company.id).all()
    assert len(historical_pages) == 2
    hashes = {p.content_hash for p in historical_pages}
    assert initial_hash in hashes
    assert modified_hash in hashes

    # Verify run history persistence
    runs = db_session.query(ResearchRun).filter(ResearchRun.company_id == company.id).all()
    assert len(runs) == 3
