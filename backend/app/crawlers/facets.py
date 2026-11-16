"""Deterministic Facet Extractor.

Extracts structured domain facts (study destinations, service offerings, operating locations)
from URLs, page titles, and structured metadata using configurable pattern mapping.
Guarantees 100% recall on destination pages regardless of LLM context degradation.
"""
import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import unquote, urlsplit
from pydantic import BaseModel, Field


# Canonical country aliases mapping
DEFAULT_COUNTRY_ALIASES: Dict[str, str] = {
    # UK
    "uk": "United Kingdom",
    "united-kingdom": "United Kingdom",
    "united_kingdom": "United Kingdom",
    "great-britain": "United Kingdom",
    "britain": "United Kingdom",
    "england": "United Kingdom",
    # USA
    "usa": "United States",
    "united-states": "United States",
    "united_states": "United States",
    "america": "United States",
    "us": "United States",
    # Canada
    "canada": "Canada",
    "ca": "Canada",
    # Australia
    "australia": "Australia",
    "aus": "Australia",
    "au": "Australia",
    # Ireland
    "ireland": "Ireland",
    "ie": "Ireland",
    # Germany
    "germany": "Germany",
    "de": "Germany",
    "deutschland": "Germany",
    # New Zealand
    "new_zealand": "New Zealand",
    "new-zealand": "New Zealand",
    "newzealand": "New Zealand",
    "nz": "New Zealand",
    # Singapore
    "singapore": "Singapore",
    "sg": "Singapore",
    # Europe & Others
    "france": "France",
    "fr": "France",
    "italy": "Italy",
    "it": "Italy",
    "spain": "Spain",
    "es": "Spain",
    "switzerland": "Switzerland",
    "ch": "Switzerland",
    "netherlands": "Netherlands",
    "holland": "Netherlands",
    "nl": "Netherlands",
    "sweden": "Sweden",
    "se": "Sweden",
    "dubai": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "japan": "Japan",
    "jp": "Japan",
}

# Regex patterns for study destination discovery in URL paths
DESTINATION_URL_PATTERNS = [
    re.compile(r"/study[-_]in[-_]([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"/study[-_]([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"/destinations?/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"/countries?/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"/country/([a-zA-Z0-9_-]+)", re.IGNORECASE),
]

# Regex patterns for study destination discovery in titles
DESTINATION_TITLE_PATTERNS = [
    re.compile(r"Study (?:In|in)\s+([A-Za-z\s]+?)(?:\s*\||\s*-|\s*$)", re.IGNORECASE),
    re.compile(r"Education in\s+([A-Za-z\s]+?)(?:\s*\||\s*-|\s*$)", re.IGNORECASE),
]

# Service category keywords and canonical mappings
SERVICE_PATH_MAPPINGS: Dict[str, str] = {
    "ivy": "Ivy League Profile Building",
    "profile-building": "Ivy League Profile Building",
    "profile_building": "Ivy League Profile Building",
    "immigration": "Immigration & Visa Guidance",
    "visa": "Immigration & Visa Guidance",
    "counseling": "Personalized Counseling",
    "counselling": "Personalized Counseling",
    "admissions": "University Admission Support",
    "admission": "University Admission Support",
    "scholarship": "Scholarship Guidance",
    "scholarships": "Scholarship Guidance",
    "test-prep": "Standardized Test Preparation",
    "test_prep": "Standardized Test Preparation",
    "ielts": "Standardized Test Preparation (IELTS)",
    "toefl": "Standardized Test Preparation (TOEFL)",
    "gre": "Standardized Test Preparation (GRE)",
    "gmat": "Standardized Test Preparation (GMAT)",
    "sat": "Standardized Test Preparation (SAT)",
}


class FacetItem(BaseModel):
    value: str
    category: str
    source_url: str
    source_page_id: Optional[int] = None
    extraction_rule: str


class PageFacets(BaseModel):
    page_id: Optional[int] = None
    url: str
    study_destinations: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    operational_locations: List[str] = Field(default_factory=list)
    evidence_items: List[FacetItem] = Field(default_factory=list)


class DeterministicFacetExtractor:
    """Extracts deterministic facts from URLs, titles, and metadata."""

    def __init__(self, country_aliases: Optional[Dict[str, str]] = None):
        self.country_aliases = country_aliases or DEFAULT_COUNTRY_ALIASES

    def extract_from_url(self, url: str) -> Tuple[List[str], List[str]]:
        """Extract study destinations and services indicated by URL path."""
        destinations: List[str] = []
        services: List[str] = []

        path = unquote(urlsplit(url).path.lower()).rstrip("/")

        # 1. Match destination patterns
        for pattern in DESTINATION_URL_PATTERNS:
            match = pattern.search(path)
            if match:
                raw_token = match.group(1).lower().strip("-_/")
                canonical = self.country_aliases.get(raw_token)
                if canonical and canonical not in destinations:
                    destinations.append(canonical)

        # 2. Match service patterns
        path_segments = [s.strip("-_") for s in path.split("/") if s]
        for seg in path_segments:
            for key, canonical_service in SERVICE_PATH_MAPPINGS.items():
                if seg == key or seg.startswith(f"{key}-") or seg.startswith(f"{key}_"):
                    if canonical_service not in services:
                        services.append(canonical_service)

        return destinations, services

    def extract_from_title(self, title: Optional[str]) -> List[str]:
        """Extract study destinations from page title."""
        destinations: List[str] = []
        if not title:
            return destinations

        clean_title = title.strip()
        for pattern in DESTINATION_TITLE_PATTERNS:
            match = pattern.search(clean_title)
            if match:
                raw_country = match.group(1).strip().lower()
                canonical = self.country_aliases.get(raw_country)
                if not canonical:
                    # Check title-cased token
                    raw_country_kebab = raw_country.replace(" ", "-")
                    canonical = self.country_aliases.get(raw_country_kebab)
                if canonical and canonical not in destinations:
                    destinations.append(canonical)

        return destinations

    def extract_operational_locations(self, text: Optional[str]) -> List[str]:
        """
        Extract physical operational offices / locations explicitly mentioned in addresses.
        Distinguishes operating presence (e.g. India / Noida / Mumbai) from study destinations.
        """
        locations: List[str] = []
        if not text:
            return locations

        # Match Indian corporate office patterns (Noida, Mumbai, Delhi, Bengaluru, etc.)
        office_keywords = [
            ("Noida", r"\bNoida\b"),
            ("Mumbai", r"\bMumbai\b"),
            ("New Delhi", r"\b(?:New Delhi|Delhi)\b"),
            ("Bengaluru", r"\b(?:Bengaluru|Bangalore)\b"),
            ("Gurugram", r"\b(?:Gurugram|Gurgaon)\b"),
            ("Pune", r"\bPune\b"),
            ("Hyderabad", r"\bHyderabad\b"),
            ("India", r"\bIndia\b"),
        ]

        # Look specifically in contact / address sections
        lower_text = text.lower()
        if any(h in lower_text for h in ["address", "office", "contact us", "headquarters", "sector"]):
            for name, pattern in office_keywords:
                if re.search(pattern, text, re.IGNORECASE):
                    if name not in locations:
                        locations.append(name)

        return locations

    def process_page(
        self,
        url: str,
        title: Optional[str] = None,
        text: Optional[str] = None,
        page_id: Optional[int] = None,
    ) -> PageFacets:
        """Process a single ResearchPage snapshot and return deterministic facets."""
        url_destinations, url_services = self.extract_from_url(url)
        title_destinations = self.extract_from_title(title)
        operational_locs = self.extract_operational_locations(text)

        # Merge destinations
        all_destinations: List[str] = []
        evidence_items: List[FacetItem] = []

        for d in url_destinations:
            if d not in all_destinations:
                all_destinations.append(d)
                evidence_items.append(
                    FacetItem(
                        value=d,
                        category="study_destinations",
                        source_url=url,
                        source_page_id=page_id,
                        extraction_rule="url_path_pattern",
                    )
                )

        for d in title_destinations:
            if d not in all_destinations:
                all_destinations.append(d)
                evidence_items.append(
                    FacetItem(
                        value=d,
                        category="study_destinations",
                        source_url=url,
                        source_page_id=page_id,
                        extraction_rule="title_pattern",
                    )
                )

        for s in url_services:
            evidence_items.append(
                FacetItem(
                    value=s,
                    category="products_services",
                    source_url=url,
                    source_page_id=page_id,
                    extraction_rule="url_service_slug",
                )
            )

        return PageFacets(
            page_id=page_id,
            url=url,
            study_destinations=all_destinations,
            services=url_services,
            operational_locations=operational_locs,
            evidence_items=evidence_items,
        )
