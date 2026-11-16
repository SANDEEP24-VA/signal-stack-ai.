"""Production-grade, SSRF-protected website research engine with complete crawl accounting."""
import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set
from urllib.parse import urlsplit

import httpx
from sqlalchemy.orm import Session

from app.crawlers.extractor import ContentExtractor
from app.crawlers.robots import RobotsManager
from app.crawlers.sitemap import SitemapDiscoverer
from app.crawlers.url_utils import (
    is_internal_link,
    normalize_domain,
    normalize_url,
    validate_ip_security,
    validate_url_syntax,
)
from app.database.models import (
    Company,
    DiscoveredUrl,
    DiscoveredUrlStatus,
    ResearchPage,
    ResearchRun,
)

logger = logging.getLogger(__name__)


class WebsiteResearchEngine:
    """Production-grade, SSRF-protected website research engine with complete crawl accounting."""

    def __init__(
        self,
        max_pages: int = 12,
        max_depth: int = 2,
        timeout: float = 15.0,
        max_response_size: int = 2 * 1024 * 1024,  # 2 MB
        max_redirects: int = 3,
        rate_limit_delay: float = 1.0,
        user_agent: str = "SignalStackAI-Bot/1.0 (+https://signalstack.ai/bot; bot@signalstack.ai)",
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.max_response_size = max_response_size
        self.max_redirects = max_redirects
        self.rate_limit_delay = rate_limit_delay
        self.user_agent = user_agent

    async def execute_research(
        self,
        company: Company,
        research_run: ResearchRun,
        db: Session,
    ) -> List[ResearchPage]:
        """
        Execute full website research workflow with exact crawl accounting:
        - Pages discovered
        - Pages fetched
        - Pages failed
        - Pages skipped (limit, robots, duplicate, out-of-scope)
        Enforces invariant:
        pages_discovered = fetched + failed + skipped_limit + skipped_robots + skipped_duplicate + skipped_out_of_scope
        """
        seed_url = company.website
        base_domain = company.normalized_domain

        logger.info(f"Starting research run {research_run.id} for {company.name} ({base_domain}) [max_pages={self.max_pages}]")

        # Validate seed URL syntax and SSRF security
        valid_syntax, syntax_err = validate_url_syntax(seed_url)
        if not valid_syntax:
            research_run.status = "FAILED"
            research_run.error_message = f"Invalid seed website URL: {syntax_err}"
            research_run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return []

        host = urlsplit(seed_url).hostname or base_domain
        is_safe_ip, ip_err = validate_ip_security(host)
        if not is_safe_ip:
            research_run.status = "FAILED"
            research_run.error_message = f"SSRF Security Violation: {ip_err}"
            research_run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return []

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # URL accounting registry: maps normalized URL -> DiscoveredUrl instance
        now = datetime.now(timezone.utc)
        url_registry: Dict[str, DiscoveredUrl] = {}
        extracted_pages: List[ResearchPage] = []
        crawled_urls: Set[str] = set()

        # Seed URL initialization
        norm_seed = normalize_url(seed_url)
        url_registry[norm_seed] = DiscoveredUrl(
            research_run_id=research_run.id,
            url=norm_seed,
            status=DiscoveredUrlStatus.PENDING.value,
            depth=0,
            priority=100,
            created_at=now,
            updated_at=now,
        )

        queue: List[dict] = [{"url": norm_seed, "depth": 0, "priority": 100}]

        transport = httpx.AsyncHTTPTransport(retries=1)
        async with httpx.AsyncClient(
            transport=transport,
            headers=headers,
            timeout=self.timeout,
            follow_redirects=False,
        ) as client:
            # 1. Fetch robots.txt
            robots_mgr = RobotsManager(user_agent="SignalStackAI-Bot")
            await robots_mgr.fetch_and_parse(seed_url, client)

            # 2. Discover sitemaps
            sitemap_disco = SitemapDiscoverer(base_domain, client)
            try:
                sitemap_links = await sitemap_disco.discover_urls(seed_url, robots_mgr.sitemaps)
                for s_url in sitemap_links:
                    norm_s = normalize_url(s_url)
                    if norm_s in url_registry:
                        continue

                    # Check domain scope
                    if not is_internal_link(norm_s, base_domain):
                        url_registry[norm_s] = DiscoveredUrl(
                            research_run_id=research_run.id,
                            url=norm_s,
                            status=DiscoveredUrlStatus.SKIPPED_OUT_OF_SCOPE.value,
                            depth=1,
                            priority=0,
                            error_message="External domain out of scope",
                            created_at=now,
                            updated_at=now,
                        )
                        continue

                    # Check robots.txt
                    if not robots_mgr.can_fetch(norm_s):
                        url_registry[norm_s] = DiscoveredUrl(
                            research_run_id=research_run.id,
                            url=norm_s,
                            status=DiscoveredUrlStatus.SKIPPED_ROBOTS.value,
                            depth=1,
                            priority=0,
                            error_message="Disallowed by robots.txt",
                            created_at=now,
                            updated_at=now,
                        )
                        continue

                    # Valid internal sitemap link
                    p = 20
                    lower_s = norm_s.lower()
                    from app.crawlers.extractor import PRIORITY_KEYWORDS
                    if any(k in lower_s for k in PRIORITY_KEYWORDS):
                        p += 40

                    url_registry[norm_s] = DiscoveredUrl(
                        research_run_id=research_run.id,
                        url=norm_s,
                        status=DiscoveredUrlStatus.PENDING.value,
                        depth=1,
                        priority=p,
                        created_at=now,
                        updated_at=now,
                    )
                    queue.append({"url": norm_s, "depth": 1, "priority": p})
            except Exception as e:
                logger.warning(f"Sitemap discovery notice: {e}")

            # 3. Breadth-First Crawl Loop
            while queue and len(crawled_urls) < self.max_pages:
                queue.sort(key=lambda x: x["priority"], reverse=True)
                item = queue.pop(0)
                current_url = item["url"]
                depth = item["depth"]

                record = url_registry.get(current_url)

                if current_url in crawled_urls:
                    if record and record.status == DiscoveredUrlStatus.PENDING.value:
                        record.status = DiscoveredUrlStatus.SKIPPED_DUPLICATE.value
                        record.updated_at = datetime.now(timezone.utc)
                    continue

                # Check robots.txt permission
                if not robots_mgr.can_fetch(current_url):
                    logger.info(f"Skipping robots.txt disallowed URL: {current_url}")
                    if record:
                        record.status = DiscoveredUrlStatus.SKIPPED_ROBOTS.value
                        record.error_message = "Disallowed by robots.txt"
                        record.updated_at = datetime.now(timezone.utc)
                    continue

                # Rate limiting delay
                if crawled_urls:
                    await asyncio.sleep(self.rate_limit_delay)

                logger.info(f"Fetching [{len(crawled_urls) + 1}/{self.max_pages}] (depth {depth}): {current_url}")

                fetch_res = await self._safe_fetch(client, current_url, base_domain)

                if not fetch_res["success"]:
                    if record:
                        record.status = DiscoveredUrlStatus.FAILED.value
                        record.error_message = str(fetch_res.get("error"))
                        record.updated_at = datetime.now(timezone.utc)
                    logger.warning(f"Failed to fetch {current_url}: {fetch_res['error']}")
                    continue

                crawled_urls.add(current_url)

                # Extract content
                html = fetch_res["html"]
                status_code = fetch_res["status_code"]
                final_url = fetch_res["final_url"]

                title, text, canonical, content_hash = ContentExtractor.extract(html, final_url)

                # Check for insufficient text
                if not text or len(text.strip()) < 40:
                    if record:
                        record.status = DiscoveredUrlStatus.FAILED.value
                        record.error_message = f"Insufficient text ({len(text) if text else 0} chars)"
                        record.updated_at = datetime.now(timezone.utc)
                    logger.info(f"Page {final_url} had insufficient text.")
                    continue

                # Successfully fetched and extracted
                if record:
                    record.status = DiscoveredUrlStatus.FETCHED.value
                    record.updated_at = datetime.now(timezone.utc)

                # Content deduplication and storage
                existing_page = (
                    db.query(ResearchPage)
                    .filter(
                        ResearchPage.company_id == company.id,
                        ResearchPage.url == final_url,
                    )
                    .first()
                )

                if existing_page and existing_page.content_hash == content_hash:
                    existing_page.last_seen_at = now
                    existing_page.crawled_at = now
                    existing_page.research_run_id = research_run.id
                    existing_page.http_status = status_code
                    if title:
                        existing_page.title = title
                    db_page = existing_page
                else:
                    db_page = ResearchPage(
                        company_id=company.id,
                        research_run_id=research_run.id,
                        url=final_url,
                        canonical_url=canonical,
                        title=title or "Untitled Page",
                        extracted_text=text,
                        content_hash=content_hash,
                        http_status=status_code,
                        first_seen_at=now,
                        last_seen_at=now,
                        crawled_at=now,
                    )
                    db.add(db_page)

                db.flush()
                extracted_pages.append(db_page)

                # Discover new internal links if depth permits
                if depth < self.max_depth and len(url_registry) < 100:
                    internal_links = ContentExtractor.discover_links(html, final_url, base_domain)
                    for link_url, link_score in internal_links:
                        norm_link = normalize_url(link_url)
                        if norm_link not in url_registry:
                            if not is_internal_link(norm_link, base_domain):
                                url_registry[norm_link] = DiscoveredUrl(
                                    research_run_id=research_run.id,
                                    url=norm_link,
                                    status=DiscoveredUrlStatus.SKIPPED_OUT_OF_SCOPE.value,
                                    depth=depth + 1,
                                    priority=0,
                                    error_message="External link",
                                    created_at=now,
                                    updated_at=now,
                                )
                            elif not robots_mgr.can_fetch(norm_link):
                                url_registry[norm_link] = DiscoveredUrl(
                                    research_run_id=research_run.id,
                                    url=norm_link,
                                    status=DiscoveredUrlStatus.SKIPPED_ROBOTS.value,
                                    depth=depth + 1,
                                    priority=0,
                                    error_message="Disallowed by robots.txt",
                                    created_at=now,
                                    updated_at=now,
                                )
                            else:
                                url_registry[norm_link] = DiscoveredUrl(
                                    research_run_id=research_run.id,
                                    url=norm_link,
                                    status=DiscoveredUrlStatus.PENDING.value,
                                    depth=depth + 1,
                                    priority=link_score,
                                    created_at=now,
                                    updated_at=now,
                                )
                                queue.append({
                                    "url": norm_link,
                                    "depth": depth + 1,
                                    "priority": link_score,
                                })

            # 4. End of Crawl: Handle pages remaining in queue (SKIPPED_LIMIT)
            # Any discovered URL still PENDING was excluded purely due to the max_pages cap
            for rec in url_registry.values():
                if rec.status == DiscoveredUrlStatus.PENDING.value:
                    rec.status = DiscoveredUrlStatus.SKIPPED_LIMIT.value
                    rec.error_message = f"Skipped: reached maximum crawl limit ({self.max_pages} pages)"
                    rec.updated_at = datetime.now(timezone.utc)

        # 5. Calculate mutually exclusive accounting counters
        fetched_count = sum(1 for r in url_registry.values() if r.status == DiscoveredUrlStatus.FETCHED.value)
        failed_count = sum(1 for r in url_registry.values() if r.status == DiscoveredUrlStatus.FAILED.value)
        skipped_limit_count = sum(1 for r in url_registry.values() if r.status == DiscoveredUrlStatus.SKIPPED_LIMIT.value)
        skipped_robots_count = sum(1 for r in url_registry.values() if r.status == DiscoveredUrlStatus.SKIPPED_ROBOTS.value)
        skipped_dup_count = sum(1 for r in url_registry.values() if r.status == DiscoveredUrlStatus.SKIPPED_DUPLICATE.value)
        skipped_scope_count = sum(1 for r in url_registry.values() if r.status == DiscoveredUrlStatus.SKIPPED_OUT_OF_SCOPE.value)
        discovered_count = len(url_registry)

        # Enforce and validate invariant: discovered == sum(all statuses)
        total_accounted = (
            fetched_count
            + failed_count
            + skipped_limit_count
            + skipped_robots_count
            + skipped_dup_count
            + skipped_scope_count
        )
        assert discovered_count == total_accounted, (
            f"Crawl accounting mismatch! Discovered {discovered_count} != Accounted {total_accounted} "
            f"(fetched={fetched_count}, failed={failed_count}, limit={skipped_limit_count}, "
            f"robots={skipped_robots_count}, dup={skipped_dup_count}, scope={skipped_scope_count})"
        )

        research_run.pages_discovered = discovered_count
        research_run.pages_fetched = fetched_count
        research_run.pages_failed = failed_count
        research_run.pages_skipped_limit = skipped_limit_count
        research_run.pages_skipped_robots = skipped_robots_count
        research_run.pages_skipped_duplicate = skipped_dup_count
        research_run.pages_skipped_out_of_scope = skipped_scope_count

        # Persist individual DiscoveredUrl records
        for rec in url_registry.values():
            db.add(rec)

        if not extracted_pages:
            research_run.status = "FAILED"
            research_run.error_message = (
                f"Crawled {len(crawled_urls)} pages but could not extract content from any page. "
                "The site may be unreachable, blocking bot User-Agents, or completely JavaScript-rendered."
            )
        elif failed_count > 0:
            research_run.status = "COMPLETED_WITH_WARNINGS"
        else:
            research_run.status = "COMPLETED"

        db.commit()
        logger.info(
            f"Research run {research_run.id} crawl finished: discovered={discovered_count}, "
            f"fetched={fetched_count}, failed={failed_count}, skipped_limit={skipped_limit_count}, "
            f"skipped_robots={skipped_robots_count}, skipped_dup={skipped_dup_count}, "
            f"skipped_scope={skipped_scope_count}"
        )
        return extracted_pages

    async def _safe_fetch(
        self,
        client: httpx.AsyncClient,
        url: str,
        base_domain: str,
    ) -> Dict:
        """Safely fetch a URL with SSRF checks on every redirect hop, size limits, and timeouts."""
        current_url = url
        redirect_count = 0

        while redirect_count <= self.max_redirects:
            # 1. Validate syntax
            valid_syntax, err = validate_url_syntax(current_url)
            if not valid_syntax:
                return {"success": False, "error": f"Invalid syntax: {err}"}

            # 2. Check internal domain
            if not is_internal_link(current_url, base_domain):
                return {"success": False, "error": f"Refusing to follow external URL: {current_url}"}

            # 3. Validate IP for SSRF
            parsed = urlsplit(current_url)
            host = parsed.hostname or base_domain
            is_safe, ip_err = validate_ip_security(host)
            if not is_safe:
                return {"success": False, "error": f"SSRF blocked: {ip_err}"}

            # 4. Stream response to enforce size limits
            try:
                async with client.stream("GET", current_url) as response:
                    # Check redirect
                    if response.status_code in (301, 302, 303, 307, 308):
                        redirect_location = response.headers.get("Location")
                        if not redirect_location:
                            return {"success": False, "error": "Redirect without Location header"}

                        current_url = normalize_url(redirect_location, base_url=current_url)
                        redirect_count += 1
                        continue

                    if response.status_code != 200:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                            "status_code": response.status_code,
                        }

                    # Check Content-Type (must be HTML or text)
                    content_type = response.headers.get("Content-Type", "").lower()
                    if content_type and not any(ct in content_type for ct in ("text/html", "application/xhtml", "text/plain")):
                        return {"success": False, "error": f"Unsupported Content-Type: {content_type}"}

                    # Read body with max_response_size enforcement
                    chunks = []
                    bytes_read = 0
                    async for chunk in response.aiter_bytes():
                        bytes_read += len(chunk)
                        if bytes_read > self.max_response_size:
                            return {"success": False, "error": "Response exceeded maximum 2 MB limit"}
                        chunks.append(chunk)

                    body_bytes = b"".join(chunks)
                    encoding = response.encoding or "utf-8"
                    try:
                        html = body_bytes.decode(encoding, errors="replace")
                    except Exception:
                        html = body_bytes.decode("utf-8", errors="replace")

                    return {
                        "success": True,
                        "html": html,
                        "status_code": response.status_code,
                        "final_url": current_url,
                    }

            except httpx.TimeoutException:
                return {"success": False, "error": f"Request timed out after {self.timeout}s"}
            except httpx.RequestError as e:
                return {"success": False, "error": f"Request failed: {e}"}
            except Exception as e:
                return {"success": False, "error": f"Unexpected fetch error: {e}"}

        return {"success": False, "error": f"Exceeded maximum redirects ({self.max_redirects})"}
