"""Executable script and entry point for researching SaaS applications."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from research_agent.adapters.composio_client import ComposioAdapter
from research_agent.adapters.documentation_search import DocumentationSearchAdapter
from research_agent.adapters.groq_client import GroqAdapter
from research_agent.config import (
    DEFAULT_GROQ_MODEL,
    OUTPUT_DIR,
    PROJECT_ROOT,
    Settings,
    check_missing_credentials,
    load_settings,
)
from research_agent.models import AppResearchRecord, SeedAppRecord
from research_agent.services.research_service import (
    ResearchService,
    get_seed_app,
    load_seed_dataset,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("research_agent.runner")

TARGET_TEST_APP_IDS = [1, 21, 61]  # Salesforce, Slack, GitHub


def initialize_research_service(
    cache_dir: Optional[Path] = None,
) -> tuple[ResearchService, bool]:
    """Initialize ResearchService checking live credentials availability.

    Returns:
        tuple[ResearchService, bool]: (service_instance, is_fully_configured_for_live)
    """
    settings: Optional[Settings] = None
    try:
        settings = load_settings()
        is_live = True
    except Exception as exc:
        logger.info("Live credentials not fully configured (%s). Running in graceful fallback mode.", exc)
        is_live = False

    doc_adapter = DocumentationSearchAdapter()
    composio_adapter = ComposioAdapter(
        api_key=settings.composio_api_key if settings else None
    )
    groq_adapter = GroqAdapter(
        api_key=settings.groq_api_key if settings else None,
        model=settings.groq_model if settings else DEFAULT_GROQ_MODEL,
    )

    service = ResearchService(
        doc_adapter=doc_adapter,
        composio_adapter=composio_adapter,
        groq_adapter=groq_adapter,
        cache_dir=cache_dir or (OUTPUT_DIR / "research_results"),
    )
    return service, is_live


def research_single_app(
    app_id_or_name: int | str,
    force_refresh: bool = False,
    allow_fallback: bool = True,
    cache_dir: Optional[Path] = None,
) -> AppResearchRecord:
    """Research a single application by ID or name."""
    service, is_live = initialize_research_service(cache_dir=cache_dir)
    seed_app = get_seed_app(app_id_or_name)
    logger.info("Processing target app: %s (ID %d)", seed_app.name, seed_app.id)

    record = service.research_app(
        seed_app=seed_app,
        force_refresh=force_refresh,
        allow_fallback=allow_fallback or not is_live,
    )
    return record


def run_research_on_test_targets(
    force_refresh: bool = False,
    allow_fallback: bool = True,
    cache_dir: Optional[Path] = None,
) -> list[AppResearchRecord]:
    """Execute research on the three designated test targets: Salesforce (1), Slack (21), and GitHub (61)."""
    service, is_live = initialize_research_service(cache_dir=cache_dir)
    results: list[AppResearchRecord] = []

    print("\n" + "=" * 70)
    print("COMPOSIO RESEARCH AGENT - TEST TARGET EXECUTION")
    print(f"Target Applications: Salesforce (1), Slack (21), GitHub (61)")
    print(f"Live Configuration Status: {'LIVE' if is_live else 'OFFLINE / FALLBACK'}")
    print("=" * 70 + "\n")

    for app_id in TARGET_TEST_APP_IDS:
        seed_app = get_seed_app(app_id)
        print(f"\n--- [App {seed_app.id}/100] {seed_app.name} ({seed_app.category.value}) ---")
        print(f"Website: {seed_app.website}")
        print(f"Doc Hint: {seed_app.documentation_hint}")

        record = service.research_app(
            seed_app=seed_app,
            force_refresh=force_refresh,
            allow_fallback=allow_fallback or not is_live,
        )
        results.append(record)

        print(f"Verdict:             {record.buildability_verdict.value.upper()}")
        print(f"Category:            {record.category.value}")
        print(f"Auth Methods:        {', '.join(a.value for a in record.auth_methods)}")
        print(f"Self-Service Access: {record.self_service_access.value}")
        if record.developer_access_tier:
            print(f"Developer Tier:      {record.developer_access_tier.value}")
        if record.production_access_tier:
            print(f"Production Tier:     {record.production_access_tier.value}")
        print(f"API Types:           {', '.join(t.value for t in record.api_types)}")
        print(f"API Breadth:         {record.api_breadth.value}")
        print(f"MCP Availability:    {record.mcp_availability.value}")
        print(f"Composio Toolkit:    {record.has_composio_integration} (slug: {record.composio_toolkit_slug})")
        print(f"Primary Blocker:     {record.primary_blocker.value}")
        print(f"Confidence Level:    {record.confidence_level.value}")
        if record.provenance:
            print(f"Provenance Mode:     {record.provenance.execution_mode.value} (Live docs: {record.provenance.documentation_live_fetched}, Live LLM: {record.provenance.llm_inference_executed})")
        print(f"Cached JSON:         {service.get_cache_path(seed_app)}")

    print("\n" + "=" * 70)
    print(f"COMPLETED {len(results)}/3 TEST TARGETS SUCCESSFULLY")
    print("=" * 70 + "\n")

    return results


def main() -> int:
    """CLI entry point for research agent execution."""
    parser = argparse.ArgumentParser(
        description="Composio Research Agent - Investigate SaaS applications for AI agent toolkits."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--test-targets",
        action="store_true",
        help="Run research exclusively on the 3 designated test targets: Salesforce (1), Slack (21), GitHub (61).",
    )
    group.add_argument(
        "--app-id",
        type=int,
        help="Research a specific application by seed dataset ID (1-100).",
    )
    group.add_argument(
        "--app-name",
        type=str,
        help="Research a specific application by official name.",
    )

    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass cached research records and re-run live discovery.",
    )
    parser.add_argument(
        "--disallow-fallback",
        action="store_true",
        help="Fail strictly if live credentials are not present.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Custom directory to store research result JSON files.",
    )

    args = parser.parse_args()
    allow_fallback = not args.disallow_fallback

    try:
        if args.test_targets:
            run_research_on_test_targets(
                force_refresh=args.force_refresh,
                allow_fallback=allow_fallback,
                cache_dir=args.output_dir,
            )
        elif args.app_id is not None:
            record = research_single_app(
                app_id_or_name=args.app_id,
                force_refresh=args.force_refresh,
                allow_fallback=allow_fallback,
                cache_dir=args.output_dir,
            )
            print(record.model_dump_json(indent=2))
        elif args.app_name is not None:
            record = research_single_app(
                app_id_or_name=args.app_name,
                force_refresh=args.force_refresh,
                allow_fallback=allow_fallback,
                cache_dir=args.output_dir,
            )
            print(record.model_dump_json(indent=2))
        return 0
    except Exception as exc:
        logger.error("Research execution failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
