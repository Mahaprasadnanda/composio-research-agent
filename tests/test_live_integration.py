"""Live integration tests for external APIs (Groq, Composio, live documentation).

These tests run ONLY when real, valid API credentials are provided in the environment or .env.
Otherwise, they are skipped cleanly to ensure unit test suites pass in offline/CI environments.
"""

from __future__ import annotations

import os

import pytest

from research_agent.adapters.composio_client import ComposioAdapter
from research_agent.adapters.documentation_search import DocumentationSearchAdapter
from research_agent.adapters.groq_client import GroqAdapter
from research_agent.config import check_missing_credentials, load_settings
from research_agent.models import ExecutionMode, ExecutionSource
from research_agent.services.research_service import ResearchService, get_seed_app

HAS_LIVE_CREDENTIALS = len(check_missing_credentials()) == 0


@pytest.mark.skipif(
    not HAS_LIVE_CREDENTIALS,
    reason="Live credentials (GROQ_API_KEY, COMPOSIO_API_KEY) not found in environment or .env.",
)
def test_live_groq_and_composio_research(tmp_path):
    """Execute live end-to-end research on GitHub (ID 61) using real Groq and Composio APIs."""
    settings = load_settings()

    doc_adapter = DocumentationSearchAdapter(timeout=10.0)
    composio_adapter = ComposioAdapter(api_key=settings.composio_api_key)
    groq_adapter = GroqAdapter(api_key=settings.groq_api_key, model=settings.groq_model)

    service = ResearchService(
        doc_adapter=doc_adapter,
        composio_adapter=composio_adapter,
        groq_adapter=groq_adapter,
        cache_dir=tmp_path / "live_cache",
    )

    seed_github = get_seed_app(61)
    record = service.research_app(seed_github, force_refresh=True)

    assert record.app_name == "GitHub"
    assert record.buildability_verdict is not None
    assert len(record.evidence_urls) > 0
    assert record.provenance is not None
    assert record.provenance.execution_mode == ExecutionMode.LIVE
    assert record.provenance.live_verified is True
    assert record.provenance.doc_execution_source == ExecutionSource.REAL_NETWORK
    assert record.provenance.llm_execution_source == ExecutionSource.REAL_NETWORK
    assert record.provenance.composio_execution_source == ExecutionSource.REAL_NETWORK


def test_documentation_adapter_live_fetching_accessible_public_site():
    """Verify DocumentationSearchAdapter can retrieve a lightweight public documentation page."""
    adapter = DocumentationSearchAdapter(timeout=8.0)
    # Using python.org or similar reliable static public domain
    res = adapter.fetch_url("https://httpbin.org/html")
    # If network is unavailable or restricted in environment, we gracefully verify error handling
    if res.is_accessible:
        assert res.status_code == 200
        assert len(res.content) > 0
        assert res.execution_source == ExecutionSource.REAL_NETWORK
        assert res.is_live_network is True
    else:
        assert res.error_message is not None
