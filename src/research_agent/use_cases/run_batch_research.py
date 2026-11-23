"""Use case for running batch research over multiple applications."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

from research_agent.config import OUTPUT_DIR, ConfigurationError
from research_agent.models import BatchRunSummary, ResearchDataset
from research_agent.services.batch_runner import BatchResearchRunner
from research_agent.use_cases.run_single_research import initialize_research_service

logger = logging.getLogger("research_agent.batch_runner")


def parse_id_list(raw_ids: Optional[str]) -> Optional[list[int]]:
    """Parse comma-separated string of application IDs (e.g. '1,21,61') into list of integers."""
    if not raw_ids:
        return None
    ids: list[int] = []
    for part in raw_ids.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            val = int(part)
            if val < 1 or val > 100:
                raise ValueError(f"Application ID {val} out of range (must be 1-100).")
            ids.append(val)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Invalid application ID: '{part}'. {exc}")
    return sorted(list(set(ids)))


def parse_name_list(raw_names: Optional[str]) -> Optional[list[str]]:
    """Parse comma-separated string of application names into list of strings."""
    if not raw_names:
        return None
    names = [part.strip() for part in raw_names.split(",") if part.strip()]
    return names if names else None


def execute_batch_research(
    batch_size: int = 10,
    target_ids: Optional[list[int]] = None,
    target_names: Optional[list[str]] = None,
    resume: bool = True,
    force_refresh: bool = False,
    allow_fallback: bool = True,
    output_dir: Optional[Path] = None,
    inter_app_delay: float = 0.0,
) -> tuple[ResearchDataset, BatchRunSummary]:
    """Initialize research service and execute batch pipeline."""
    out_dir = output_dir or OUTPUT_DIR
    cache_dir = out_dir / "research_results"
    service, is_live = initialize_research_service(cache_dir=cache_dir)

    if not is_live and not allow_fallback:
        raise ConfigurationError(
            "Live credentials not configured (missing or invalid GROQ_API_KEY / COMPOSIO_API_KEY) "
            "and offline fallback is disallowed (--disallow-fallback)."
        )

    runner = BatchResearchRunner(
        research_service=service,
        batch_size=batch_size,
        inter_app_delay_seconds=inter_app_delay,
        output_dir=out_dir,
    )

    dataset, summary = runner.run_batch(
        target_app_ids=target_ids,
        target_app_names=target_names,
        resume=resume,
        force_refresh=force_refresh,
        allow_fallback=allow_fallback,
    )

    print("\n" + "=" * 70)
    print("COMPOSIO RESEARCH AGENT - BATCH RUN COMPLETE")
    print("=" * 70)
    print(f"Total Applications:   {summary.total_applications}")
    print(f"Newly Researched:     {summary.newly_researched_count}")
    print(f"Loaded from Cache:    {summary.cached_count}")
    print(f"Failed:               {summary.failed_count}")
    print(f"Duration:             {summary.duration_seconds}s")
    print(f"Execution Modes:      {summary.counts_by_execution_mode}")
    print(f"Buildability Verdicts:{summary.counts_by_buildability_verdict}")
    print(f"Consolidated Dataset: {out_dir / 'research_dataset.json'}")
    print(f"Batch Summary:        {out_dir / 'batch_run_summary.json'}")
    if summary.failed_apps:
        print("\nFailed Applications:")
        for f in summary.failed_apps:
            print(f"  - App {f.app_id} ({f.app_name}): {f.error}")
    print("=" * 70 + "\n")

    return dataset, summary
