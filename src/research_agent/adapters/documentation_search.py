"""Documentation research adapter for discovering and fetching official developer documentation."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx

from research_agent.models import ExecutionSource

# Default conservative character budget per document (~1,250 tokens)
DEFAULT_MAX_CHARS_PER_DOC = 5000

# Extended keywords for relevance scoring and semantic section prioritization
RELEVANCE_KEYWORDS = [
    "authentication",
    "oauth",
    "oauth2",
    "api key",
    "bearer",
    "personal access token",
    "jwt",
    "client secret",
    "client id",
    "credentials",
    "scopes",
    "permissions",
    "authorization",
    "rest api",
    "graphql",
    "webhook",
    "endpoints",
    "rate limit",
    "pagination",
    "base url",
    "methods",
    "developer account",
    "developer edition",
    "free trial",
    "sandbox",
    "enterprise",
    "pricing",
    "subscription",
    "approval",
    "mcp",
    "model context protocol",
]

# Weighted priority mapping for semantic documentation section selection
PRIORITY_KEYWORDS = {
    "oauth": 6,
    "oauth2": 6,
    "authentication": 6,
    "api key": 5,
    "bearer": 5,
    "personal access token": 5,
    "jwt": 5,
    "client secret": 5,
    "client id": 5,
    "credentials": 5,
    "scopes": 5,
    "permissions": 5,
    "authorization": 5,
    "rest api": 5,
    "graphql": 5,
    "webhook": 4,
    "endpoints": 4,
    "rate limit": 5,
    "pagination": 4,
    "base url": 4,
    "methods": 4,
    "developer account": 5,
    "developer edition": 5,
    "free trial": 4,
    "sandbox": 5,
    "enterprise": 4,
    "pricing": 4,
    "subscription": 4,
    "approval": 5,
    "mcp": 6,
    "model context protocol": 6,
}

TAGS_TO_REMOVE_REGEX = re.compile(
    r"<(script|style|nav|header|footer|aside|svg|noscript|iframe|form|button|select|option|input|textarea|dialog|canvas)[^>]*>.*?</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)

ELEMENTS_BY_CLASS_OR_ID_TO_REMOVE = re.compile(
    r"<div[^>]*(?:class|id)=[\"'][^\"']*(?:sidebar|navbar|navigation|site-header|site-footer|menu|toc|breadcrumbs|cookie|consent|banner|modal|announcement|search-modal)[^\"']*[\"'][^>]*>.*?</div\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)

BOILERPLATE_LINE_PATTERNS = [
    re.compile(r"^skip to (main )?content", re.IGNORECASE),
    re.compile(r"^(accept|reject|manage) (all )?cookies", re.IGNORECASE),
    re.compile(r"^cookie (policy|settings|notice|banner)", re.IGNORECASE),
    re.compile(r"^all rights reserved", re.IGNORECASE),
    re.compile(r"^copyright (©|\(c\))", re.IGNORECASE),
    re.compile(r"^was this (page|article) helpful", re.IGNORECASE),
    re.compile(r"^edit this page( on github)?", re.IGNORECASE),
    re.compile(r"^(privacy policy|terms of service|terms of use)", re.IGNORECASE),
    re.compile(r"^back to top", re.IGNORECASE),
    re.compile(r"^[•·\-\|\s]+$"),
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 ComposioResearchBot/1.0"
)


@dataclass(frozen=True)
class DocumentationResult:
    """Encapsulates retrieved documentation content, access metadata, and token truncation details."""

    url: str
    title: str = ""
    content: str = ""
    excerpt: str = ""
    status_code: int = 0
    is_accessible: bool = False
    error_message: Optional[str] = None
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    execution_source: ExecutionSource = ExecutionSource.SIMULATED
    is_live_network: bool = False
    is_truncated: bool = False
    original_chars: int = 0
    cleaned_chars: int = 0
    truncation_notes: Optional[str] = None


def preprocess_documentation_html(
    html_content: str,
    max_chars: int = DEFAULT_MAX_CHARS_PER_DOC,
) -> tuple[str, str, bool, int, int, Optional[str]]:
    """Convert raw HTML to clean text with boilerplate removal, section prioritization, and truncation metadata.

    Args:
        html_content: Raw HTML text retrieved over HTTP.
        max_chars: Maximum character budget to retain for this document.

    Returns:
        tuple[str, str, bool, int, int, Optional[str]]:
            (title, cleaned_text, is_truncated, original_length, cleaned_length, truncation_notes)
    """
    # 1. Extract title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    title = html.unescape(title_match.group(1)).strip() if title_match else ""

    # 2. Strip unwanted tags with their contents
    text = TAGS_TO_REMOVE_REGEX.sub(" ", html_content)
    # Strip common navigation / sidebar / cookie containers
    text = ELEMENTS_BY_CLASS_OR_ID_TO_REMOVE.sub(" ", text)

    # 3. Replace heading block tags with markdown-style indicators
    text = re.sub(r"<h1[^>]*>", "\n\n# ", text, flags=re.IGNORECASE)
    text = re.sub(r"<h2[^>]*>", "\n\n## ", text, flags=re.IGNORECASE)
    text = re.sub(r"<h[3-6][^>]*>", "\n\n### ", text, flags=re.IGNORECASE)
    # Replace other block tags with double newlines
    text = re.sub(r"<(p|div|li|tr|br|hr)[^>]*>", "\n\n", text, flags=re.IGNORECASE)

    # 4. Remove all remaining tags and decode entities
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)

    # 5. Filter boilerplate lines and normalize whitespace
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            cleaned_lines.append("")
            continue
        if any(pat.search(line_stripped) for pat in BOILERPLATE_LINE_PATTERNS):
            continue
        line_clean = re.sub(r"[ \t]+", " ", line_stripped)
        cleaned_lines.append(line_clean)

    full_cleaned_text = "\n".join(cleaned_lines)
    full_cleaned_text = re.sub(r"\n\s*\n+", "\n\n", full_cleaned_text).strip()
    raw_cleaned_len = len(full_cleaned_text)

    if raw_cleaned_len <= max_chars:
        return title, full_cleaned_text, False, raw_cleaned_len, raw_cleaned_len, None

    # 6. Budget exceeded: Prioritize semantic sections
    sections = [s.strip() for s in full_cleaned_text.split("\n\n") if s.strip()]
    if not sections:
        return title, "", False, 0, 0, None

    banner_template = "\n\n...[DOCUMENTATION TRUNCATED TO FIT TOKEN BUDGET: ~{omitted} CHARS OMITTED]"
    # Estimate banner length (~75 chars)
    est_banner_len = 80
    content_budget = max(100, max_chars - est_banner_len)

    # Keep overview / intro paragraph (proportional to budget)
    intro_budget = min(len(sections[0]), max(150, content_budget // 3))
    intro_section = sections[0][:intro_budget]
    remaining_sections = sections[1:]

    # Score remaining sections
    scored_sections: list[tuple[int, int, str]] = []  # (score, original_index, section_text)
    for idx, sec in enumerate(remaining_sections):
        sec_lower = sec.lower()
        score = sum(weight for kw, weight in PRIORITY_KEYWORDS.items() if kw in sec_lower)
        scored_sections.append((score, idx, sec))

    priority_scored = [s for s in scored_sections if s[0] > 0]
    zero_scored = [s for s in scored_sections if s[0] == 0]

    available_budget = content_budget - len(intro_section)
    selected_indices: set[int] = set()
    current_chars = 0

    # First pass: allocate budget to positive-score API/Auth sections first
    for score, idx, sec in sorted(priority_scored, key=lambda x: (-x[0], x[1])):
        sec_len = len(sec) + 2
        if current_chars + sec_len <= available_budget:
            selected_indices.add(idx)
            current_chars += sec_len
        elif (available_budget - current_chars) > 60:
            selected_indices.add(idx)
            current_chars = available_budget
            break

    # Second pass: only if NO positive-score sections existed in document, fill from top
    if not priority_scored:
        for score, idx, sec in zero_scored:
            sec_len = len(sec) + 2
            if current_chars + sec_len <= available_budget:
                selected_indices.add(idx)
                current_chars += sec_len
            else:
                break

    assembled_parts = [intro_section]
    for idx, sec in enumerate(remaining_sections):
        if idx in selected_indices:
            current_total = len("\n\n".join(assembled_parts))
            rem_budget = content_budget - current_total - 2
            if rem_budget <= 0:
                break
            if len(sec) > rem_budget:
                if rem_budget > 30:
                    assembled_parts.append(sec[:rem_budget - 3] + "...")
                break
            else:
                assembled_parts.append(sec)

    body_text = "\n\n".join(assembled_parts).strip()
    omitted_chars = max(0, raw_cleaned_len - len(body_text))
    banner = f"\n\n...[DOCUMENTATION TRUNCATED TO FIT TOKEN BUDGET: ~{omitted_chars} CHARS OMITTED]"
    final_text = (body_text + banner).strip()

    trunc_notes = (
        f"Original documentation length was {raw_cleaned_len} chars. "
        f"Truncated to {len(final_text)} chars prioritizing authentication, endpoints, access tiers, and MCP."
    )
    return title, final_text, True, raw_cleaned_len, len(final_text), trunc_notes


def clean_html_to_text(html_content: str, max_chars: int = DEFAULT_MAX_CHARS_PER_DOC) -> tuple[str, str]:
    """Convert raw HTML to clean textual representation, extracting title and body.

    Returns:
        tuple[str, str]: (extracted_title, cleaned_body_text)
    """
    title, text, _, _, _, _ = preprocess_documentation_html(html_content, max_chars=max_chars)
    return title, text


def extract_relevant_snippet(text: str, max_length: int = 500) -> str:
    """Find the highest-relevance paragraph matching authentication or API keywords."""
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 40]
    best_paragraph = ""
    highest_score = -1

    for p in paragraphs:
        p_lower = p.lower()
        score = sum(1 for kw in RELEVANCE_KEYWORDS if kw in p_lower)
        if score > highest_score:
            highest_score = score
            best_paragraph = p

    if best_paragraph:
        snippet = best_paragraph[:max_length].strip()
        if len(best_paragraph) > max_length:
            snippet += "..."
        return snippet

    # Fallback to first non-empty block
    if text:
        return text[:max_length].strip()
    return ""


class DocumentationSearchAdapter:
    """Fetches, sanitizes, and extracts evidence from official developer documentation."""

    def __init__(
        self,
        timeout: float = 15.0,
        max_chars_per_doc: int = DEFAULT_MAX_CHARS_PER_DOC,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.timeout = timeout
        self.max_chars_per_doc = max_chars_per_doc
        self.user_agent = user_agent

    def fetch_url(self, url: str) -> DocumentationResult:
        """Retrieve and process documentation from a specific canonical URL."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers=headers,
                verify=True,
            ) as client:
                response = client.get(url)

                if response.status_code >= 400:
                    return DocumentationResult(
                        url=str(response.url),
                        status_code=response.status_code,
                        is_accessible=False,
                        error_message=(
                            f"HTTP {response.status_code} client/server error while accessing documentation."
                        ),
                        is_live_network=True,
                        execution_source=ExecutionSource.REAL_NETWORK,
                    )

                content_type = response.headers.get("content-type", "").lower()
                raw_text = response.text
                is_truncated = False
                original_chars = len(raw_text)
                cleaned_chars = len(raw_text)
                trunc_notes = None

                if "html" in content_type:
                    title, cleaned, is_truncated, original_chars, cleaned_chars, trunc_notes = (
                        preprocess_documentation_html(raw_text, max_chars=self.max_chars_per_doc)
                    )
                else:
                    title = f"Document at {urlparse(url).netloc}"
                    if len(raw_text) > self.max_chars_per_doc:
                        cleaned = raw_text[: self.max_chars_per_doc] + "\n...[TRUNCATED FOR LENGTH]"
                        is_truncated = True
                        cleaned_chars = len(cleaned)
                        trunc_notes = f"Plain document truncated from {len(raw_text)} to {len(cleaned)} chars."
                    else:
                        cleaned = raw_text

                snippet = extract_relevant_snippet(cleaned)

                return DocumentationResult(
                    url=str(response.url),
                    title=title or f"Developer Documentation ({urlparse(url).netloc})",
                    content=cleaned,
                    excerpt=snippet,
                    status_code=response.status_code,
                    is_accessible=True,
                    is_live_network=True,
                    execution_source=ExecutionSource.REAL_NETWORK,
                    is_truncated=is_truncated,
                    original_chars=original_chars,
                    cleaned_chars=cleaned_chars,
                    truncation_notes=trunc_notes,
                )

        except httpx.TimeoutException:
            return DocumentationResult(
                url=url,
                is_accessible=False,
                error_message=f"Connection timed out after {self.timeout}s.",
                is_live_network=True,
                execution_source=ExecutionSource.REAL_NETWORK,
            )
        except httpx.RequestError as exc:
            return DocumentationResult(
                url=url,
                is_accessible=False,
                error_message=f"Network error while reaching destination: {type(exc).__name__}",
                is_live_network=True,
                execution_source=ExecutionSource.REAL_NETWORK,
            )
        except Exception as exc:
            return DocumentationResult(
                url=url,
                is_accessible=False,
                error_message=f"Unexpected error retrieving documentation: {str(exc)}",
                is_live_network=True,
                execution_source=ExecutionSource.REAL_NETWORK,
            )

    def gather_documentation(
        self,
        candidate_urls: list[str],
        max_pages: int = 2,
    ) -> list[DocumentationResult]:
        """Fetch up to max_pages accessible documentation pages from the candidate list."""
        results: list[DocumentationResult] = []
        fetched_count = 0

        for url in candidate_urls:
            if not url or not url.startswith(("http://", "https://")):
                continue
            if fetched_count >= max_pages:
                break

            doc_result = self.fetch_url(url)
            results.append(doc_result)
            if doc_result.is_accessible:
                fetched_count += 1

        return results
