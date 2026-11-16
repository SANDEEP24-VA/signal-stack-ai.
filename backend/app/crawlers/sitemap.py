import logging
from typing import List, Set
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import httpx

from app.crawlers.url_utils import is_internal_link, normalize_url

logger = logging.getLogger(__name__)


class SitemapDiscoverer:
    """Discovers and parses XML sitemaps for target domain URLs."""

    def __init__(self, base_domain: str, client: httpx.AsyncClient):
        self.base_domain = base_domain
        self.client = client
        self.discovered_urls: Set[str] = set()

    async def discover_urls(self, seed_url: str, robots_sitemaps: List[str]) -> List[str]:
        """Try known sitemap locations and any declared in robots.txt."""
        candidates = list(robots_sitemaps)

        parsed = urlsplit(seed_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        standard_locations = [
            f"{origin}/sitemap.xml",
            f"{origin}/sitemap_index.xml",
            f"{origin}/sitemap/sitemap.xml",
        ]

        for loc in standard_locations:
            if loc not in candidates:
                candidates.append(loc)

        for sitemap_url in candidates:
            try:
                await self._fetch_and_parse_sitemap(sitemap_url, depth=0)
                if len(self.discovered_urls) >= 50:
                    break
            except Exception as e:
                logger.debug(f"Failed parsing sitemap {sitemap_url}: {e}")

        return list(self.discovered_urls)

    async def _fetch_and_parse_sitemap(self, sitemap_url: str, depth: int) -> None:
        if depth > 1:
            return

        try:
            resp = await self.client.get(sitemap_url, timeout=10.0)
            if resp.status_code != 200 or not resp.text:
                return

            # Parse XML
            root = ET.fromstring(resp.content)
            # Remove namespace if present
            for elem in root.iter():
                if "}" in elem.tag:
                    elem.tag = elem.tag.split("}", 1)[1]

            # Check if this is a sitemapindex
            if root.tag == "sitemapindex":
                for sitemap in root.findall("sitemap"):
                    loc = sitemap.find("loc")
                    if loc is not None and loc.text:
                        sub_url = loc.text.strip()
                        if is_internal_link(sub_url, self.base_domain):
                            await self._fetch_and_parse_sitemap(sub_url, depth=depth + 1)
            elif root.tag == "urlset":
                for url_elem in root.findall("url"):
                    loc = url_elem.find("loc")
                    if loc is not None and loc.text:
                        candidate = loc.text.strip()
                        if is_internal_link(candidate, self.base_domain):
                            self.discovered_urls.add(normalize_url(candidate))
        except Exception as e:
            logger.debug(f"Could not parse sitemap at {sitemap_url}: {e}")
