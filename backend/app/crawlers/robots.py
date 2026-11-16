import logging
from typing import List
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import httpx

logger = logging.getLogger(__name__)


class RobotsManager:
    """Fetches and evaluates robots.txt rules for a domain."""

    def __init__(self, user_agent: str = "SignalStackAI-Bot"):
        self.user_agent = user_agent
        self.parser = RobotFileParser()
        self.sitemaps: List[str] = []
        self._fetched = False

    def parse_content(self, text: str) -> None:
        """Parse raw robots.txt content."""
        lines = text.splitlines()
        self.parser.parse(lines)
        self._fetched = True
        for line in lines:
            line_clean = line.strip()
            if line_clean.lower().startswith("sitemap:"):
                sitemap_url = line_clean.split(":", 1)[1].strip()
                if sitemap_url and sitemap_url not in self.sitemaps:
                    self.sitemaps.append(sitemap_url)

    async def fetch_and_parse(self, base_url: str, client: httpx.AsyncClient) -> None:
        """Fetch robots.txt for the given base URL."""
        parsed = urlsplit(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            response = await client.get(robots_url, timeout=10.0)
            if response.status_code == 200:
                self.parse_content(response.text)
            elif response.status_code in (401, 403):
                # Disallow all if access to robots.txt is forbidden
                self.parser.disallow_all = True
                self._fetched = True
            else:
                # 404 or other 4xx means no robots.txt restrictions
                self.parser.allow_all = True
                self._fetched = True
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt from {robots_url}: {e}")
            # If robots.txt cannot be fetched due to network error, default allow
            self.parser.allow_all = True
            self._fetched = True

    def can_fetch(self, url: str) -> bool:
        """Check if user_agent is permitted to crawl the given URL."""
        if not self._fetched:
            return True
        return self.parser.can_fetch(self.user_agent, url)
