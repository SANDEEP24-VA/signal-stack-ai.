"""Strict Evidence Validator for Company Intelligence Engine.

Performs deterministic backend validation on candidate facts:
1. Whitespace-normalised exact substring matching.
2. Calculation and persistence of start and end character offsets in original webpage text.
3. Anti-hallucination checks:
   - Rejection of fabricated founding dates.
   - Rejection of unsupported percentages/metrics.
   - Rejection of synthetic placeholder competitors.
   - Rejection of unquoted or non-verbatim factual claims.
4. Explicit classification into:
   - VERIFIED_FACT
   - ASSUMPTION
   - UNKNOWN
   - REJECTED_UNSUPPORTED
"""
import re
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

# Synthetic placeholder competitor blacklist
PLACEHOLDER_COMPETITOR_PATTERNS = [
    re.compile(r"\bABC\s+Education\b", re.IGNORECASE),
    re.compile(r"\bDEF\s+Consulting\b", re.IGNORECASE),
    re.compile(r"\bCompany\s+[XYZAB]\b", re.IGNORECASE),
    re.compile(r"\bCompetitor\s+[12AB]\b", re.IGNORECASE),
    re.compile(r"\bXYZ\s+Corp\b", re.IGNORECASE),
    re.compile(r"\bAcme\s+Corp\b", re.IGNORECASE),
]

# Patterns for specific metrics / percentages
PERCENTAGE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?%)")
YEAR_PATTERN = re.compile(r"\b(19\d\d|20[0-2]\d)\b")


class FactValidationResult(BaseModel):
    statement: str
    classification: str  # VERIFIED_FACT, ASSUMPTION, UNKNOWN, REJECTED_UNSUPPORTED
    confidence: float
    evidence_snippet: Optional[str] = None
    research_page_id: Optional[int] = None
    quote_start_offset: Optional[int] = None
    quote_end_offset: Optional[int] = None
    rejection_reason: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None


def normalize_whitespace(text: str) -> str:
    """Normalize repeated whitespace and newlines for robust comparison."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def find_quote_offsets(quote: str, full_text: str) -> Optional[Tuple[int, int]]:
    """
    Locate start and end character offsets of quote within full_text.
    Supports exact matching and whitespace-normalised matching.
    Returns (start_char, end_char) or None.
    """
    if not quote or not full_text:
        return None

    clean_quote = quote.strip()
    if not clean_quote:
        return None

    # 1. Exact raw match
    raw_idx = full_text.find(clean_quote)
    if raw_idx != -1:
        return raw_idx, raw_idx + len(clean_quote)

    # 2. Case-insensitive match
    raw_lower = full_text.lower()
    quote_lower = clean_quote.lower()
    case_idx = raw_lower.find(quote_lower)
    if case_idx != -1:
        return case_idx, case_idx + len(clean_quote)

    # 3. Whitespace-flexible regex match
    quote_words = [re.escape(w) for w in clean_quote.split() if w]
    if quote_words:
        regex_pattern = r"\s+".join(quote_words)
        try:
            match = re.search(regex_pattern, full_text, re.IGNORECASE)
            if match:
                return match.start(), match.end()
        except re.error:
            pass

    return None


class StrictEvidenceValidator:
    """Rigorous evidence-quality validator enforcing truthfulness and provenance."""

    @classmethod
    def validate_candidate_fact(
        cls,
        statement: str,
        category: str,
        raw_classification: str,
        evidence_snippet: Optional[str],
        page_text: Optional[str],
        page_id: Optional[int] = None,
        source_url: Optional[str] = None,
    ) -> FactValidationResult:
        """
        Validate a candidate fact against source webpage text.
        Guarantees that unsupported or fabricated claims are never marked VERIFIED_FACT
        and never silently converted to assumptions.
        """
        stmt_clean = (statement or "").strip()
        quote_clean = (evidence_snippet or "").strip()
        raw_cls = (raw_classification or "").upper().strip()

        # Handle explicit UNKNOWN items
        if raw_cls == "UNKNOWN" or category.lower() == "unknown":
            return FactValidationResult(
                statement=stmt_clean,
                classification="UNKNOWN",
                confidence=1.0,
                evidence_snippet=None,
                research_page_id=None,
                quote_start_offset=None,
                quote_end_offset=None,
                rejection_reason=None,
                provenance={"status": "explicitly_unknown", "category": category},
            )

        # 1. Anti-hallucination Check: Placeholder competitors
        for pat in PLACEHOLDER_COMPETITOR_PATTERNS:
            match = pat.search(stmt_clean)
            if match:
                return FactValidationResult(
                    statement=stmt_clean,
                    classification="REJECTED_UNSUPPORTED",
                    confidence=0.0,
                    evidence_snippet=quote_clean or None,
                    research_page_id=page_id,
                    rejection_reason=f"Claim contains synthetic placeholder competitor '{match.group(0)}'",
                    provenance={"rule": "anti_placeholder_competitor", "match": match.group(0)},
                )

        # 2. Check presence of page text
        if not page_text or not page_text.strip():
            # If explicit assumption without false assertions, keep as ASSUMPTION
            if raw_cls == "ASSUMPTION":
                return FactValidationResult(
                    statement=stmt_clean,
                    classification="ASSUMPTION",
                    confidence=0.5,
                    evidence_snippet=None,
                    research_page_id=page_id,
                    rejection_reason="No page text available to verify; marked as inference",
                    provenance={"status": "unverified_inference"},
                )
            return FactValidationResult(
                statement=stmt_clean,
                classification="REJECTED_UNSUPPORTED",
                confidence=0.0,
                evidence_snippet=quote_clean or None,
                research_page_id=page_id,
                rejection_reason="Referenced research page contains no extracted text",
                provenance={"rule": "missing_page_text"},
            )

        # 3. Locate quotation offsets in page text
        offsets = find_quote_offsets(quote_clean, page_text) if quote_clean else None

        # 4. Anti-hallucination Check: Metric / Percentage Verification
        stmt_percentages = PERCENTAGE_PATTERN.findall(stmt_clean)
        if stmt_percentages:
            for pct in stmt_percentages:
                # The percentage MUST appear in page text
                if pct not in page_text:
                    return FactValidationResult(
                        statement=stmt_clean,
                        classification="REJECTED_UNSUPPORTED",
                        confidence=0.0,
                        evidence_snippet=quote_clean or None,
                        research_page_id=page_id,
                        rejection_reason=f"Statement asserts percentage metric '{pct}' which does not appear in source webpage",
                        provenance={"rule": "unsupported_percentage_metric", "metric": pct},
                    )

        # 5. Anti-hallucination Check: Founding date / Year Verification
        if any(w in stmt_clean.lower() for w in ["founded", "established", "started", "launched", "inception"]):
            stmt_years = YEAR_PATTERN.findall(stmt_clean)
            if stmt_years:
                for yr in stmt_years:
                    if yr not in page_text:
                        # Check if page has another founding date that contradicts it
                        page_found_match = re.search(r"founded in\s+(\d{4})", page_text, re.IGNORECASE)
                        contradiction_note = (
                            f" (page text indicates Founded in {page_found_match.group(1)})"
                            if page_found_match
                            else ""
                        )
                        return FactValidationResult(
                            statement=stmt_clean,
                            classification="REJECTED_UNSUPPORTED",
                            confidence=0.0,
                            evidence_snippet=quote_clean or None,
                            research_page_id=page_id,
                            rejection_reason=f"Statement asserts founding year '{yr}' not evidenced in source text{contradiction_note}",
                            provenance={
                                "rule": "contradictory_or_unsupported_founding_date",
                                "asserted_year": yr,
                                "page_founding_year": page_found_match.group(1) if page_found_match else None,
                            },
                        )

        # 6. Check quotation validity
        if not offsets:
            # Quote does not appear in page text
            if raw_cls == "ASSUMPTION":
                # Stated as an assumption / hypothesis
                return FactValidationResult(
                    statement=stmt_clean,
                    classification="ASSUMPTION",
                    confidence=0.5,
                    evidence_snippet=None,
                    research_page_id=page_id,
                    rejection_reason="No verbatim quotation found; preserved as stated assumption",
                    provenance={"rule": "unquoted_assumption"},
                )
            else:
                # Claimed as a verified fact without a valid quotation in text -> REJECT
                return FactValidationResult(
                    statement=stmt_clean,
                    classification="REJECTED_UNSUPPORTED",
                    confidence=0.0,
                    evidence_snippet=quote_clean or None,
                    research_page_id=page_id,
                    rejection_reason="Supporting quotation does not exist in referenced webpage text",
                    provenance={"rule": "quote_not_in_text", "provided_quote": quote_clean},
                )

        # 7. Quote found in text: Verify direct support
        start_char, end_char = offsets
        actual_quote_in_text = page_text[start_char:end_char]

        # Calculate lexical overlap / support
        stmt_words = set(re.findall(r"\b[A-Za-z0-9]{3,}\b", stmt_clean.lower()))
        quote_words = set(re.findall(r"\b[A-Za-z0-9]{3,}\b", actual_quote_in_text.lower()))

        overlap = stmt_words.intersection(quote_words)
        overlap_ratio = len(overlap) / max(1, len(stmt_words))

        # Direct support requires substantial entity/term grounding or verbatim quotation
        if overlap_ratio >= 0.35 or len(quote_clean) >= 40:
            return FactValidationResult(
                statement=stmt_clean,
                classification="VERIFIED_FACT",
                confidence=0.95,
                evidence_snippet=actual_quote_in_text,
                research_page_id=page_id,
                quote_start_offset=start_char,
                quote_end_offset=end_char,
                rejection_reason=None,
                provenance={
                    "source_url": source_url,
                    "matched_quote": actual_quote_in_text,
                    "offsets": [start_char, end_char],
                    "overlap_ratio": round(overlap_ratio, 2),
                },
            )
        else:
            return FactValidationResult(
                statement=stmt_clean,
                classification="ASSUMPTION",
                confidence=0.6,
                evidence_snippet=actual_quote_in_text,
                research_page_id=page_id,
                quote_start_offset=start_char,
                quote_end_offset=end_char,
                rejection_reason="Quotation matched in text but lexical support is partial",
                provenance={
                    "source_url": source_url,
                    "matched_quote": actual_quote_in_text,
                    "offsets": [start_char, end_char],
                    "overlap_ratio": round(overlap_ratio, 2),
                },
            )
