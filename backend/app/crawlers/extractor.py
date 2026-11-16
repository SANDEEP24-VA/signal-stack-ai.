import hashlib
import logging
import re
from typing import List, Optional, Set, Tuple
from bs4 import BeautifulSoup
import trafilatura

from app.crawlers.url_utils import is_internal_link, normalize_url

logger = logging.getLogger(__name__)

# Keywords for prioritizing key business intelligence pages
PRIORITY_KEYWORDS = [
    "about",
    "company",
    "products",
    "product",
    "services",
    "solutions",
    "solution",
    "industries",
    "industry",
    "platform",
    "features",
    "pricing",
    "contact",
    "overview",
    "mission",
    "team",
    "leadership",
    "customers",
    "case-studies",
    "who-we-are",
]


class ContentExtractor:
    """Extracts clean text, titles, canonical URLs, and internal links from HTML."""

    @staticmethod
    def extract(html: str, page_url: str) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
        """
        Extract title, main text, canonical URL, and content SHA-256 hash.
        Returns: (title, text, canonical_url, content_hash)
        """
        if not html or not html.strip():
            return None, None, None, hashlib.sha256(b"").hexdigest()

        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract title
        title: Optional[str] = None
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)

        # 2. Extract canonical URL
        canonical_url: Optional[str] = None
        canon_tag = soup.find("link", rel=lambda r: r and "canonical" in r.lower())
        if canon_tag and canon_tag.get("href"):
            try:
                canonical_url = normalize_url(canon_tag["href"], base_url=page_url)
            except Exception:
                canonical_url = canon_tag["href"].strip()

        # 3. Extract clean text using Trafilatura
        text = trafilatura.extract(
            html,
            url=page_url,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )

        # 4. Fallback to BeautifulSoup if Trafilatura extracted nothing
        if not text or len(text.strip()) < 50:
            # Strip noise elements
            for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
                tag.decompose()
            raw_text = soup.get_text(separator=" ", strip=True)
            # Collapse whitespace
            text = re.sub(r"\s+", " ", raw_text).strip()

        clean_text = text if text and text.strip() else ""
        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

        return title, clean_text, canonical_url, content_hash

    @staticmethod
    def discover_links(html: str, page_url: str, base_domain: str) -> List[Tuple[str, int]]:
        """
        Extract internal links and score their priority.
        Returns a list of (normalized_url, priority_score) sorted by descending priority.
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        seen: Set[str] = set()
        scored_links: List[Tuple[str, int]] = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Ignore empty, javascript, mailto, tel, fragments
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                continue

            try:
                norm_url = normalize_url(href, base_url=page_url)
            except Exception:
                continue

            if norm_url in seen:
                continue

            if not is_internal_link(norm_url, base_domain):
                continue

            # Skip binary / non-HTML assets
            lower_url = norm_url.lower()
            if any(lower_url.endswith(ext) for ext in (
                ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
                ".pdf", ".zip", ".tar", ".gz", ".exe", ".dmg",
                ".css", ".js", ".mp4", ".mp3", ".woff", ".woff2"
            )):
                continue

            seen.add(norm_url)

            # Score priority based on URL keywords and anchor text
            score = 10  # base score
            link_text = a.get_text(strip=True).lower()

            for kw in PRIORITY_KEYWORDS:
                if kw in lower_url:
                    score += 50
                if kw in link_text:
                    score += 30

            # Penalize deep or query-heavy paths
            if "?" in norm_url:
                score -= 15
            path_depth = norm_url.count("/")
            if path_depth > 5:
                score -= 10

            scored_links.append((norm_url, score))

        # Sort by priority descending
        scored_links.sort(key=lambda x: x[1], reverse=True)
        return scored_links
