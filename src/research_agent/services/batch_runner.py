"""Batch research runner orchestrating multi-application research pipelines."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from research_agent.config import OUTPUT_DIR, ConfigurationError
from research_agent.models import (
    AppResearchRecord,
    BatchRunSummary,
    BuildabilityVerdict,
    ExecutionMode,
    FailedAppSummary,
    ResearchDataset,
    SeedAppRecord,
)
from research_agent.services.research_service import ResearchService, load_seed_dataset

logger = logging.getLogger("research_agent.batch_runner")

DEFAULT_BATCH_SIZE = 10
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 1.0


def is_transient_error(exc: BaseException) -> bool:
    """Determine whether an error is transient and eligible for bounded retry.

    Transient errors:
        - Network connection drops, resets, DNS failures
        - HTTP/socket timeouts
        - HTTP 429 rate limit or quota delays
        - HTTP 500, 502, 503, 504 remote server errors

    Permanent errors (fail-fast, do not retry):
        - Missing or invalid credentials (ConfigurationError, 401 Unauthorized)
        - Schema / validation errors (ValidationError, ValueError)
        - Missing resource (404 Not Found)
        - Forbidden / permission denied (403 Forbidden without rate limit)
    """
    if isinstance(exc, (ConfigurationError, KeyError)):
        return False

    err_msg = str(exc).lower()

    # Fail fast on authentication or credential errors
    if "unauthorized" in err_msg or "401" in err_msg or "invalid api key" in err_msg:
        return False
    if "not found" in err_msg and "404" in err_msg:
        return False
    if "validation error" in err_msg or "valueerror" in err_msg:
        return False

    # Transient error indicators
    transient_indicators = [
        "timeout",
        "timed out",
        "connection",
        "rate limit",
        "429",
        "500",
        "502",
        "503",
        "504",
        "server error",
        "temporarily unavailable",
    ]
    if any(ind in err_msg for ind in transient_indicators):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True

    return False


class BatchResearchRunner:
    """Orchestrates structured research over batches of seed applications.

    Supports:
        - Configurable batch sizing and deterministic sequential processing
        - Resuming interrupted runs via cache inspection
        - Selective target execution by application IDs or names
        - Bounded exponential-backoff retries for transient network/rate-limit errors
        - Immediate fail-fast on permanent authentication or configuration errors
        - Checkpoint persistence of individual records and consolidated datasets
        - Comprehensive execution metrics and failure summaries
    """

    def __init__(
        self,
        research_service: ResearchService,
        seed_dataset: Optional[list[SeedAppRecord]] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_retries_per_app: int = DEFAULT_MAX_RETRIES,
        initial_backoff_seconds: float = DEFAULT_INITIAL_BACKOFF,
        inter_app_delay_seconds: float = 0.0,
        output_dir: Optional[Path] = None,
    ) -> None:
        self.service = research_service
        self.all_seed_apps = seed_dataset if seed_dataset is not None else load_seed_dataset()
        self.batch_size = max(1, batch_size)
        self.max_retries_per_app = max(1, max_retries_per_app)
        self.initial_backoff_seconds = max(0.1, initial_backoff_seconds)
        self.inter_app_delay_seconds = max(0.0, inter_app_delay_seconds)
        self.output_dir = output_dir or OUTPUT_DIR

    def resolve_target_apps(
        self,
        app_ids: Optional[list[int]] = None,
        app_names: Optional[list[str]] = None,
    ) -> list[SeedAppRecord]:
        """Filter seed applications by explicit IDs or case-insensitive names, preserving ID order."""
        if not app_ids and not app_names:
            return sorted(self.all_seed_apps, key=lambda a: a.id)

        selected: dict[int, SeedAppRecord] = {}

        if app_ids:
            id_set = set(app_ids)
            for app in self.all_seed_apps:
                if app.id in id_set:
                    selected[app.id] = app

        if app_names:
            clean_names = {n.strip().lower() for n in app_names if n.strip()}
            for app in self.all_seed_apps:
                if app.name.lower() in clean_names:
                    selected[app.id] = app

        return [selected[k] for k in sorted(selected.keys())]

    def run_batch(
        self,
        target_app_ids: Optional[list[int]] = None,
        target_app_names: Optional[list[str]] = None,
        resume: bool = True,
        force_refresh: bool = False,
        allow_fallback: bool = True,
        on_app_completed: Optional[Callable[[SeedAppRecord, AppResearchRecord, bool], None]] = None,
    ) -> tuple[ResearchDataset, BatchRunSummary]:
        """Execute the batch research workflow on designated seed applications."""
        target_apps = self.resolve_target_apps(
            app_ids=target_app_ids,
            app_names=target_app_names,
        )

        total_count = len(target_apps)
        if total_count == 0:
            raise ValueError("No matching applications found for the specified targets.")

        started_at = datetime.now(timezone.utc)
        logger.info(
            "Starting batch research run for %d applications (batch_size=%d, resume=%s, force_refresh=%s)",
            total_count,
            self.batch_size,
            resume,
            force_refresh,
        )

        successful_records: list[AppResearchRecord] = []
        failed_apps: list[FailedAppSummary] = []
        newly_researched_count = 0
        cached_count = 0

        # Chunk applications into batches
        app_batches = [
            target_apps[i : i + self.batch_size]
            for i in range(0, total_count, self.batch_size)
        ]

        total_processed = 0

        try:
            for batch_idx, batch in enumerate(app_batches, start=1):
                logger.info(
                    "--- [Batch %d/%d] Processing %d applications (apps %d to %d) ---",
                    batch_idx,
                    len(app_batches),
                    len(batch),
                    total_processed + 1,
                    total_processed + len(batch),
                )

                for app in batch:
                    total_processed += 1
                    logger.info("[%d/%d] Inspecting %s (ID %d)", total_processed, total_count, app.name, app.id)

                    # 1. Resume / Cache check
                    if resume and not force_refresh:
                        cached_record = self.service.get_cached_record(app)
                        if cached_record is not None:
                            logger.info(
                                "  -> Cache hit for %s (ID %d). Loaded existing record (mode: %s, verified: %s)",
                                app.name,
                                app.id,
                                cached_record.provenance.execution_mode.value if cached_record.provenance else "unknown",
                                cached_record.provenance.live_verified if cached_record.provenance else False,
                            )
                            successful_records.append(cached_record)
                            cached_count += 1
                            if on_app_completed:
                                on_app_completed(app, cached_record, True)
                            continue

                    # 2. Execute research with bounded exponential backoff
                    record: Optional[AppResearchRecord] = None
                    last_error: Optional[Exception] = None

                    for attempt in range(1, self.max_retries_per_app + 1):
                        try:
                            record = self.service.research_app(
                                seed_app=app,
                                force_refresh=force_refresh,
                                allow_fallback=allow_fallback,
                            )
                            break
                        except Exception as exc:
                            last_error = exc
                            if not is_transient_error(exc) or attempt == self.max_retries_per_app:
                                logger.warning(
                                    "  -> Permanent error or retry exhausted for %s on attempt %d/%d: %s",
                                    app.name,
                                    attempt,
                                    self.max_retries_per_app,
                                    exc,
                                )
                                break
                            backoff = self.initial_backoff_seconds * (2 ** (attempt - 1))
                            logger.info(
                                "  -> Transient error on %s (attempt %d/%d): %s. Backing off %.1fs...",
                                app.name,
                                attempt,
                                self.max_retries_per_app,
                                exc,
                                backoff,
                            )
                            time.sleep(backoff)

                    # 3. Handle research outcome
                    if record is not None:
                        successful_records.append(record)
                        newly_researched_count += 1
                        logger.info(
                            "  -> Completed research for %s: verdict=%s, mode=%s, verified=%s",
                            app.name,
                            record.buildability_verdict.value,
                            record.provenance.execution_mode.value if record.provenance else "unknown",
                            record.provenance.live_verified if record.provenance else False,
                        )
                        if on_app_completed:
                            on_app_completed(app, record, False)
                    else:
                        err_text = str(last_error) if last_error else "Unknown execution error"
                        failed_apps.append(
                            FailedAppSummary(
                                app_id=app.id,
                                app_name=app.name,
                                error=err_text,
                            )
                        )
                        logger.error("  -> Research FAILED for %s (ID %d): %s", app.name, app.id, err_text)

                    # Optional inter-app delay for live rate-limit pacing
                    if self.inter_app_delay_seconds > 0:
                        time.sleep(self.inter_app_delay_seconds)

                # Persist batch checkpoint
                self._persist_checkpoint(
                    records=successful_records,
                    failed_apps=failed_apps,
                    total_applications=total_count,
                    newly_researched_count=newly_researched_count,
                    cached_count=cached_count,
                    started_at=started_at,
                )

        except KeyboardInterrupt:
            logger.warning("Batch research run interrupted by user! Persisting checkpoint of completed records...")
            self._persist_checkpoint(
                records=successful_records,
                failed_apps=failed_apps,
                total_applications=total_count,
                newly_researched_count=newly_researched_count,
                cached_count=cached_count,
                started_at=started_at,
            )
            raise

        completed_at = datetime.now(timezone.utc)
        duration_seconds = round((completed_at - started_at).total_seconds(), 2)

        dataset, summary = self._build_outputs(
            records=successful_records,
            failed_apps=failed_apps,
            total_applications=total_count,
            newly_researched_count=newly_researched_count,
            cached_count=cached_count,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
        )

        # Final persistence
        self._save_final_outputs(dataset, summary)

        logger.info(
            "Batch run finished in %.1fs: %d total, %d newly researched, %d cached, %d failed",
            duration_seconds,
            total_count,
            newly_researched_count,
            cached_count,
            len(failed_apps),
        )

        return dataset, summary

    def _build_outputs(
        self,
        records: list[AppResearchRecord],
        failed_apps: list[FailedAppSummary],
        total_applications: int,
        newly_researched_count: int,
        cached_count: int,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
    ) -> tuple[ResearchDataset, BatchRunSummary]:
        """Construct validated ResearchDataset and BatchRunSummary Pydantic models."""
        dataset = ResearchDataset(
            version="0.1.0",
            target_count=total_applications,
            records=records,
            created_at=completed_at,
        )

        # Aggregate counts by execution mode
        counts_by_mode: dict[str, int] = {m.value: 0 for m in ExecutionMode}
        for rec in records:
            if rec.provenance:
                mode_str = rec.provenance.execution_mode.value
                counts_by_mode[mode_str] = counts_by_mode.get(mode_str, 0) + 1

        # Aggregate counts by verdict
        counts_by_verdict: dict[str, int] = {v.value: 0 for v in BuildabilityVerdict}
        for rec in records:
            verdict_str = rec.buildability_verdict.value
            counts_by_verdict[verdict_str] = counts_by_verdict.get(verdict_str, 0) + 1

        # Aggregate counts by category
        counts_by_category: dict[str, int] = {}
        for rec in records:
            cat_str = rec.category.value
            counts_by_category[cat_str] = counts_by_category.get(cat_str, 0) + 1

        summary = BatchRunSummary(
            total_applications=total_applications,
            newly_researched_count=newly_researched_count,
            cached_count=cached_count,
            failed_count=len(failed_apps),
            counts_by_execution_mode=counts_by_mode,
            counts_by_buildability_verdict=counts_by_verdict,
            counts_by_category=counts_by_category,
            failed_apps=failed_apps,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
        )

        return dataset, summary

    def _persist_checkpoint(
        self,
        records: list[AppResearchRecord],
        failed_apps: list[FailedAppSummary],
        total_applications: int,
        newly_researched_count: int,
        cached_count: int,
        started_at: datetime,
    ) -> None:
        """Persist intermediate consolidated dataset and run summary to disk."""
        now = datetime.now(timezone.utc)
        duration = round((now - started_at).total_seconds(), 2)
        dataset, summary = self._build_outputs(
            records=records,
            failed_apps=failed_apps,
            total_applications=total_applications,
            newly_researched_count=newly_researched_count,
            cached_count=cached_count,
            started_at=started_at,
            completed_at=now,
            duration_seconds=duration,
        )
        self._save_final_outputs(dataset, summary)

    def _save_final_outputs(
        self,
        dataset: ResearchDataset,
        summary: BatchRunSummary,
    ) -> None:
        """Write research_dataset.json and batch_run_summary.json to the output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        dataset_path = self.output_dir / "research_dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            f.write(dataset.model_dump_json(indent=2))

        summary_path = self.output_dir / "batch_run_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary.model_dump_json(indent=2))

        logger.debug("Persisted dataset to %s and summary to %s", dataset_path, summary_path)
