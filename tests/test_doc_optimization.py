"""Unit tests for documentation token optimization, HTML preprocessing, and rate-limit handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from research_agent.adapters.documentation_search import (
    DEFAULT_MAX_CHARS_PER_DOC,
    DocumentationResult,
    DocumentationSearchAdapter,
    clean_html_to_text,
    preprocess_documentation_html,
)
from research_agent.adapters.groq_client import (
    DEFAULT_MAX_TOTAL_DOC_CHARS,
    GroqAdapter,
    LLMExecutionReceipt,
)
from research_agent.models import ExecutionSource, ResearchProvenance


def test_large_html_preprocessing_removes_chrome_and_boilerplate():
    """Verify HTML cleanup removes navigation, cookie banners, boilerplate, scripts, and styles."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>SaaS Platform API Reference</title>
        <style>.sidebar { color: red; }</style>
        <script>window.analytics = {};</script>
    </head>
    <body>
        <div class="site-header navbar">
            <a href="/">Home</a>
            <a href="/pricing">Pricing</a>
            <a href="/docs">Docs</a>
        </div>
        <div id="cookie-banner" class="cookie-consent">
            <p>We use cookies to improve your experience. Accept all cookies.</p>
            <button>Manage cookies</button>
        </div>
        <aside class="sidebar-nav">
            <ul>
                <li><a href="#intro">Introduction</a></li>
                <li><a href="#auth">Auth</a></li>
            </ul>
        </aside>
        <main>
            <p>Skip to main content</p>
            <h1>SaaS Platform Overview</h1>
            <p>SaaS Platform delivers enterprise customer management APIs for autonomous agents.</p>
            <h2>Authentication & Security</h2>
            <p>All API requests must include an OAuth2 Bearer token in the Authorization header.</p>
        </main>
        <footer>
            <p>Copyright © 2026 SaaS Inc. All rights reserved.</p>
            <p>Privacy Policy | Terms of Service</p>
        </footer>
    </body>
    </html>
    """

    title, cleaned, is_truncated, orig_len, clean_len, notes = preprocess_documentation_html(
        html_content, max_chars=5000
    )

    assert title == "SaaS Platform API Reference"
    assert "SaaS Platform delivers enterprise customer management APIs" in cleaned
    assert "OAuth2 Bearer token" in cleaned

    # Verify unwanted chrome and boilerplate are stripped
    assert "window.analytics" not in cleaned
    assert ".sidebar { color: red; }" not in cleaned
    assert "Accept all cookies" not in cleaned
    assert "Skip to main content" not in cleaned
    assert "All rights reserved" not in cleaned
    assert "Privacy Policy | Terms of Service" not in cleaned
    assert is_truncated is False


def test_semantic_section_prioritization_under_budget():
    """Verify high-priority API, auth, and rate limit sections are preserved when budget is constrained."""
    paragraphs = [
        "SaaS Engine is a cloud platform for business analytics and automated report generation.",
        "## Release Notes\nIn version 2.4 we updated our marketing logo and redesigned the web dashboard.",
        "## Office Locations\nWe have regional headquarters in San Francisco, London, Tokyo, and Sydney.",
        "## Authentication\nAuthenticate with OAuth2 authorization code grant or bearer tokens.",
        "## Endpoints & Rate Limits\nCore endpoints support 100 requests per minute with cursor pagination.",
        "## Developer Access\nDevelopers can register for a free sandbox account with full API capabilities.",
        "## Community Forum\nJoin our community Slack channel to chat with other hobbyist developers.",
    ]
    large_html = "<html><body>" + "".join(f"<p>{p}</p>" for p in paragraphs) + "</body></html>"

    # Enforce a small budget of 600 characters
    title, cleaned, is_truncated, orig_len, clean_len, notes = preprocess_documentation_html(
        large_html, max_chars=600
    )

    assert is_truncated is True
    assert orig_len > clean_len
    assert notes is not None
    assert "Truncated" in notes

    # Priority sections must be retained
    assert "OAuth2" in cleaned or "bearer tokens" in cleaned
    assert "Rate Limits" in cleaned or "Developer Access" in cleaned

    # Low priority fluff should be omitted
    assert "Office Locations" not in cleaned
    assert "redesigned the web dashboard" not in cleaned


def test_explicit_truncation_metadata_tracking():
    """Verify DocumentationResult populates explicit truncation flags and character counts."""
    large_text = "<html><body><h1>Doc</h1>" + ("<p>Text paragraph for sizing. " * 300) + "</body></html>"

    adapter = DocumentationSearchAdapter(max_chars_per_doc=500)
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com/api"
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.text = large_text
        mock_get.return_value = mock_resp

        result = adapter.fetch_url("https://example.com/api")

        assert result.is_accessible is True
        assert result.is_truncated is True
        assert result.original_chars > result.cleaned_chars
        assert result.cleaned_chars <= 650
        assert result.truncation_notes is not None
        assert "DOCUMENTATION TRUNCATED" in result.content


def test_groq_adapter_build_user_prompt_enforces_budget():
    """Verify GroqAdapter builds prompts strictly bounded by max_total_doc_chars."""
    adapter = GroqAdapter(api_key="gsk_test_key", max_total_doc_chars=1000)

    docs = [
        {"url": "https://api.test/docs1", "title": "Doc 1", "content": "A" * 2000},
        {"url": "https://api.test/docs2", "title": "Doc 2", "content": "B" * 2000},
    ]

    prompt = adapter._build_user_prompt(
        app_name="TestApp",
        category_hint="CRM",
        composio_info=None,
        documentation_snippets=docs,
        max_doc_chars=1000,
    )

    assert "TestApp" in prompt
    assert "CONTENT TRUNCATED TO FIT MODEL TOKEN BUDGET" in prompt
    # Each doc content should be roughly 500 chars (1000 // 2)
    assert len(prompt) < 2500


@patch("time.sleep")
def test_groq_adapter_dynamic_compression_on_413(mock_sleep):
    """Verify GroqAdapter dynamically compresses doc budget when encountering HTTP 413 and succeeds."""
    adapter = GroqAdapter(api_key="gsk_test_key", max_retries=3, max_total_doc_chars=10000)
    adapter._client = MagicMock()

    # Attempt 1: Fails with 413 Request too large
    # Attempt 2: Succeeds with valid response after compression
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content='{"app_name": "TestApp", "category": "crm", "description": "Test app", "buildability_verdict": "buildable", "auth_methods": ["oauth2"]}'
            )
        )
    ]
    mock_resp.usage = MagicMock(prompt_tokens=4000, completion_tokens=200)
    mock_resp.id = "chatcmpl_test123"

    error_413 = Exception(
        "Error code: 413 - {'error': {'message': 'Request too large for model `openai/gpt-oss-120b` on tokens per minute (TPM): Limit 8000, Requested 11000'}}"
    )

    adapter._client.chat.completions.create.side_effect = [error_413, mock_resp]

    docs = [{"url": "https://test.com", "title": "API Docs", "content": "Sample content"}]
    record = adapter.extract_app_research("TestApp", "CRM", docs)

    assert record.app_name == "TestApp"
    assert record.buildability_verdict.value == "buildable"
    assert adapter._client.chat.completions.create.call_count == 2
    assert adapter.last_execution_receipt is not None
    assert adapter.last_execution_receipt.is_live_network is True


@patch("time.sleep")
def test_groq_adapter_permanent_413_fails_fast(mock_sleep):
    """Verify GroqAdapter fails fast and does not retry permanently oversized payloads unchanged."""
    adapter = GroqAdapter(api_key="gsk_test_key", max_retries=1, max_total_doc_chars=2500)
    adapter._client = MagicMock()

    error_413 = Exception("Error code: 413 - Request too large on tokens per minute (TPM)")
    adapter._client.chat.completions.create.side_effect = error_413

    docs = [{"url": "https://test.com", "title": "API Docs", "content": "Sample content"}]
    with pytest.raises(RuntimeError) as exc_info:
        adapter.extract_app_research("TestApp", "CRM", docs)

    assert "413" in str(exc_info.value)
    # At minimum budget (2500), it should not loop through repeated attempts
    assert adapter._client.chat.completions.create.call_count == 1


def test_groq_adapter_429_parses_retry_after():
    """Verify _parse_retry_after extracts wait time from headers or text messages."""
    adapter = GroqAdapter(api_key="gsk_test_key")

    # Header parsing
    exc_with_header = MagicMock()
    exc_with_header.response = MagicMock(headers={"retry-after": "18"})
    assert adapter._parse_retry_after(exc_with_header) == 19.0

    # Text pattern parsing
    exc_with_msg = Exception("Rate limit exceeded. Please try again in 24.5s.")
    assert adapter._parse_retry_after(exc_with_msg) == 25.5

    # Capped at 60s max
    exc_with_huge_wait = Exception("Rate limit exceeded. Please try again in 120s.")
    assert adapter._parse_retry_after(exc_with_huge_wait) == 60.0


def test_provenance_records_documentation_truncation(tmp_path):
    """Verify ResearchService records documentation_truncated=True and truncation notes in provenance."""
    from research_agent.adapters.composio_client import ComposioAdapter, ComposioToolkitDiscovery
    from research_agent.adapters.documentation_search import DocumentationResult, DocumentationSearchAdapter
    from research_agent.adapters.groq_client import GroqAdapter
    from research_agent.models import AppResearchRecord, ExecutionSource
    from research_agent.services.research_service import ResearchService, get_seed_app

    mock_doc_adapter = MagicMock(spec=DocumentationSearchAdapter)
    mock_doc_adapter.gather_documentation.return_value = [
        DocumentationResult(
            url="https://example.com/api",
            title="API Docs",
            content="API content",
            is_accessible=True,
            is_truncated=True,
            original_chars=12000,
            cleaned_chars=5000,
            truncation_notes="Truncated 7000 chars.",
            execution_source=ExecutionSource.SIMULATED,
            is_live_network=False,
        )
    ]

    mock_composio = MagicMock(spec=ComposioAdapter)
    mock_composio.is_configured = True
    mock_composio.discover_toolkit.return_value = ComposioToolkitDiscovery(
        app_name="Salesforce",
        slug="salesforce",
        is_integrated=True,
        discovery_attempted=True,
        discovery_succeeded=True,
        toolkit_found=True,
        execution_source=ExecutionSource.SIMULATED,
        is_live_network=False,
    )

    mock_groq = MagicMock(spec=GroqAdapter)
    mock_groq.is_configured = True
    mock_groq.extract_app_research.return_value = AppResearchRecord(
        app_name="Salesforce",
        category="crm",
        description="CRM platform",
        buildability_verdict="buildable",
        llm_execution_source=ExecutionSource.SIMULATED,
    )

    service = ResearchService(
        doc_adapter=mock_doc_adapter,
        composio_adapter=mock_composio,
        groq_adapter=mock_groq,
        cache_dir=tmp_path / "cache",
    )

    seed_app = get_seed_app(1)
    record = service.research_app(seed_app, force_refresh=True, allow_fallback=True)

    assert record.provenance is not None
    assert record.provenance.documentation_truncated is True
    assert record.provenance.documentation_truncation_notes is not None
    assert "Truncated 7000 chars" in record.provenance.documentation_truncation_notes
