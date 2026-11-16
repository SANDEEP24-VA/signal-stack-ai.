from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class CrawlResult(BaseModel):
    url: str
    status_code: int
    raw_html: Optional[str] = None
    extracted_text: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseCrawler(ABC):
    """Abstract Base Class for web crawlers and content extractors."""

    @abstractmethod
    async def fetch(self, url: str) -> CrawlResult:
        """Fetch and extract web document."""
        pass
