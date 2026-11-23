"""Documentation research adapter for discovering and fetching official developer documentation."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx

# Keywords used to extract high-relevance documentation snippets
RELEVANCE_KEYWORDS = [
    "authentication",
    "oauth",
    "api key",
    "bearer",
    "pricing",
    "rate limit",
    "rest api",
    "graphql",
    "endpoints",
    "developer",
    "mcp",
    "model context protocol",
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 ComposioResearchBot/1.0"
)


@dataclass(frozen=True)
class DocumentationResult:
    """Encapsulates retrieved documentation content and access metadata."""

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


def clean_html_to_text(html_content: str, max_chars: int = 15000) -> tuple[str, str]:
    """Convert raw HTML to clean textual representation, extracting title and body.

    Returns:
        tuple[str, str]: (extracted_title, cleaned_body_text)
    """
    # Extract title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    title = html.unescape(title_match.group(1)).strip() if title_match else ""

    # Remove script, style, nav, footer, and svg elements
    text = re.sub(r"<(script|style|nav|footer|svg|noscript)[^>]*>.*?</\1>", " ", html_content, flags=re.IGNORECASE | re.DOTALL)
    # Replace block tags with newlines
    text = re.sub(r"<(p|div|h[1-6]|li|tr|br|hr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[TRUNCATED FOR LENGTH]"

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
        max_chars_per_doc: int = 15000,
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
                    )

                content_type = response.headers.get("content-type", "").lower()
                raw_text = response.text

                if "html" in content_type:
                    title, cleaned = clean_html_to_text(raw_text, max_chars=self.max_chars_per_doc)
                else:
                    title = f"Document at {urlparse(url).netloc}"
                    cleaned = raw_text[: self.max_chars_per_doc]

                snippet = extract_relevant_snippet(cleaned)

                return DocumentationResult(
                    url=str(response.url),
                    title=title or f"Developer Documentation ({urlparse(url).netloc})",
                    content=cleaned,
                    excerpt=snippet,
                    status_code=response.status_code,
                    is_accessible=True,
                )

        except httpx.TimeoutException:
            return DocumentationResult(
                url=url,
                is_accessible=False,
                error_message=f"Connection timed out after {self.timeout}s.",
            )
        except httpx.RequestError as exc:
            return DocumentationResult(
                url=url,
                is_accessible=False,
                error_message=f"Network error while reaching destination: {type(exc).__name__}",
            )
        except Exception as exc:
            return DocumentationResult(
                url=url,
                is_accessible=False,
                error_message=f"Unexpected error retrieving documentation: {str(exc)}",
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
