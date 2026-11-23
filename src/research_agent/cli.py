"""Top-level CLI entry point for Composio Research Agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from research_agent.use_cases.run_batch_research import (
    execute_batch_research,
    parse_id_list,
    parse_name_list,
)
from research_agent.use_cases.run_single_research import (
    research_single_app,
    run_research_on_test_targets,
)


def build_parser() -> argparse.ArgumentParser:
    """Build unified CLI argument parser supporting single and batch modes."""
    parser = argparse.ArgumentParser(
        prog="research_agent",
        description="Composio Research Agent - Automated research pipeline for SaaS AI agent toolkits.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Execution mode: batch or single")

    # ------------------------------------------------------------------------
    # Subcommand: batch
    # ------------------------------------------------------------------------
    batch_parser = subparsers.add_parser(
        "batch",
        help="Execute batch research over 100 applications or a selected subset.",
    )
    batch_parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of applications to process per batch chunk (default: 10).",
    )
    batch_parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help="Comma-separated application IDs to research (e.g. '1,21,61').",
    )
    batch_parser.add_argument(
        "--names",
        type=str,
        default=None,
        help="Comma-separated application names to research (e.g. 'Slack,GitHub').",
    )
    batch_parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Reuse existing completed research records from cache (default: True).",
    )
    batch_parser.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        help="Do not resume; process all specified applications.",
    )
    batch_parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force regeneration of research records even if cached.",
    )
    batch_parser.add_argument(
        "--disallow-fallback",
        action="store_true",
        help="Disallow offline fallback fixtures; fail strictly if live credentials are not present.",
    )
    batch_parser.add_argument(
        "--allow-fallback",
        action="store_true",
        default=True,
        help="Allow explicitly labelled offline fallback records (default: True).",
    )
    batch_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Custom output directory for research results and consolidated datasets.",
    )
    batch_parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay in seconds between applications (for live rate-limit pacing).",
    )

    # ------------------------------------------------------------------------
    # Subcommand: analytics
    # ------------------------------------------------------------------------
    analytics_parser = subparsers.add_parser(
        "analytics",
        help="Execute offline analytics, data reconciliation, category statistics, and generate HTML case study.",
    )
    analytics_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Custom output directory containing research data (default: PROJECT_ROOT/output).",
    )
    analytics_parser.add_argument(
        "--reports-dir",
        type=Path,
        default=None,
        help="Custom directory to write HTML case study (default: PROJECT_ROOT/reports).",
    )
    analytics_parser.add_argument(
        "--seed-path",
        type=Path,
        default=None,
        help="Custom path to seed_apps.json (default: PROJECT_ROOT/data/raw/seed_apps.json).",
    )

    # ------------------------------------------------------------------------
    # Subcommand: verify
    # ------------------------------------------------------------------------
    verify_parser = subparsers.add_parser(
        "verify",
        help="Execute ground-truth verification audit over the 15-app sample and generate audit reports.",
    )
    verify_parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Custom directory containing research result JSON files (default: PROJECT_ROOT/output/research_results).",
    )
    verify_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Custom directory to write verification JSON/CSV reports (default: PROJECT_ROOT/output/verification).",
    )
    verify_parser.add_argument(
        "--docs-dir",
        type=Path,
        default=None,
        help="Custom directory to write verification Markdown summary (default: PROJECT_ROOT/docs).",
    )

    # ------------------------------------------------------------------------
    # Top-level / single arguments (for backwards compatibility)
    # ------------------------------------------------------------------------
    single_group = parser.add_argument_group("Single & Test Target Options")
    single_group.add_argument(
        "--test-targets",
        action="store_true",
        help="Run research exclusively on the 3 designated test targets: Salesforce (1), Slack (21), GitHub (61).",
    )
    single_group.add_argument(
        "--app-id",
        type=int,
        help="Research a specific application by seed dataset ID (1-100).",
    )
    single_group.add_argument(
        "--app-name",
        type=str,
        help="Research a specific application by official name.",
    )
    single_group.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass cached research records and re-run live discovery.",
    )
    single_group.add_argument(
        "--disallow-fallback",
        action="store_true",
        help="Fail strictly if live credentials are not present.",
    )
    single_group.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Custom directory to store research result JSON files.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    allow_fallback = not getattr(args, "disallow_fallback", False)

    try:
        if args.command == "batch":
            target_ids = parse_id_list(args.ids) if args.ids else None
            target_names = parse_name_list(args.names) if args.names else None
            execute_batch_research(
                batch_size=args.batch_size,
                target_ids=target_ids,
                target_names=target_names,
                resume=args.resume,
                force_refresh=args.force_refresh,
                allow_fallback=allow_fallback,
                output_dir=args.output_dir,
                inter_app_delay=args.delay,
            )
            return 0

        if args.command == "analytics":
            from research_agent.services.analytics_service import run_full_analytics

            result = run_full_analytics(
                output_dir=args.output_dir,
                reports_dir=args.reports_dir,
                seed_path=args.seed_path,
            )
            reconcil = result["reconciliation"]
            overall_files = result["overall_summary"]["all_available_outputs"]
            prov_stats = overall_files.get("provenance_and_verification", {})
            build_stats = overall_files.get("buildability_summary", {})
            comp_stats = overall_files.get("composio_ecosystem", {})

            print("\n======================================================================")
            print("COMPOSIO RESEARCH AGENT - ANALYTICS & CASE STUDY COMPLETE")
            print("======================================================================")
            print(f"Seed Applications:        {reconcil.get('seed_applications_count', 0)}")
            print(f"Consolidated Records:     {reconcil.get('consolidated_dataset_records_count', 0)}")
            print(f"Individual Result Files:  {reconcil.get('individual_result_files_count', 0)}")
            print(f"Total Unique Researched:  {len(reconcil.get('unique_ids_across_all_outputs', []))}")
            print(f"Live Verified Rate:       {prov_stats.get('live_verified_percentage', 0.0)}%")
            print(f"Buildable Rate:           {build_stats.get('percentages', {}).get('buildable', 0.0)}%")
            print(f"Composio Toolkit Rate:    {comp_stats.get('toolkit_discovery_rate', 0.0)}%")
            print(f"MCP Session Success:      {comp_stats.get('mcp_session_success_rate_of_discovered', 0.0)}%")
            print("\nGenerated Output Artifacts:")
            for name, path in result.get("generated_files", {}).items():
                print(f"  - {name}: {path}")
            print("======================================================================\n")
            return 0

        if args.command == "verify":
            from research_agent.services.verification_service import VerificationService

            svc = VerificationService(results_dir=args.results_dir)
            files = svc.save_reports(output_dir=args.output_dir, docs_dir=args.docs_dir)
            audit = svc.evaluate_audit()
            stats = audit["summary_statistics"]

            print("\n======================================================================")
            print("COMPOSIO RESEARCH AGENT - VERIFICATION AUDIT COMPLETE")
            print("======================================================================")
            print(f"Sample Applications:      {stats.get('sample_size')}")
            print(f"Total Fields Evaluated:   {stats.get('total_evaluated_fields')}")
            print(f"Exact Match Rate:         {stats.get('overall_field_exact_match_rate')}%")
            print(f"Post-Correction Accuracy: {stats.get('overall_post_correction_accuracy')}%")
            print(f"Composio Discovery Match: {stats.get('composio_discovery_agreement_rate')}%")
            print(f"Verdict Agreement Rate:   {stats.get('verdict_agreement_rate')}%")
            print("\nGenerated Verification Artifacts:")
            for name, path in files.items():
                print(f"  - {name}: {path}")
            print("======================================================================\n")
            return 0

        # Handle top-level single / test-target flags
        if getattr(args, "test_targets", False):
            run_research_on_test_targets(
                force_refresh=args.force_refresh,
                allow_fallback=allow_fallback,
                cache_dir=args.output_dir,
            )
            return 0
        elif getattr(args, "app_id", None) is not None:
            record = research_single_app(
                app_id_or_name=args.app_id,
                force_refresh=args.force_refresh,
                allow_fallback=allow_fallback,
                cache_dir=args.output_dir,
            )
            print(record.model_dump_json(indent=2))
            return 0
        elif getattr(args, "app_name", None) is not None:
            record = research_single_app(
                app_id_or_name=args.app_name,
                force_refresh=args.force_refresh,
                allow_fallback=allow_fallback,
                cache_dir=args.output_dir,
            )
            print(record.model_dump_json(indent=2))
            return 0

        # No command or flag passed: print help
        parser.print_help()
        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
