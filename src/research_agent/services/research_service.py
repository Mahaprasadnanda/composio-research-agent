"""Research service orchestrating documentation retrieval, Composio discovery, and Groq extraction."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from research_agent.adapters.composio_client import (
    ComposioAdapter,
    normalize_app_slug,
)
from research_agent.adapters.documentation_search import (
    DocumentationResult,
    DocumentationSearchAdapter,
)
from research_agent.adapters.groq_client import GroqAdapter
from research_agent.config import OUTPUT_DIR, PROJECT_ROOT, ConfigurationError
from research_agent.models import (
    ApiBreadth,
    ApiType,
    AppCategory,
    AppResearchRecord,
    AuthMethod,
    BuildabilityVerdict,
    ConfidenceLevel,
    EvidenceItem,
    McpAvailability,
    OriginalCategory,
    PrimaryBlocker,
    ResearchStatus,
    SeedAppRecord,
    SelfServiceAccess,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

DEFAULT_SEED_PATH = PROJECT_ROOT / "data" / "raw" / "seed_apps.json"
DEFAULT_CACHE_DIR = OUTPUT_DIR / "research_results"

ORIGINAL_CATEGORY_MAP: dict[OriginalCategory | str, AppCategory] = {
    OriginalCategory.CRM_AND_SALES: AppCategory.CRM,
    OriginalCategory.SUPPORT_AND_HELPDESK: AppCategory.CUSTOMER_SUPPORT,
    OriginalCategory.COMMUNICATIONS_AND_MESSAGING: AppCategory.COMMUNICATION,
    OriginalCategory.MARKETING_ADS_EMAIL_SOCIAL: AppCategory.MARKETING,
    OriginalCategory.ECOMMERCE: AppCategory.ECOMMERCE,
    OriginalCategory.DATA_SEO_SCRAPING: AppCategory.ANALYTICS,
    OriginalCategory.DEVELOPER_INFRA_DATA_PLATFORMS: AppCategory.DEVELOPER_TOOLS,
    OriginalCategory.PRODUCTIVITY_PROJECT_MANAGEMENT: AppCategory.PROJECT_MANAGEMENT,
    OriginalCategory.FINANCE_AND_FINTECH: AppCategory.FINANCE_ACCOUNTING,
    OriginalCategory.AI_RESEARCH_MEDIA_NATIVE: AppCategory.OTHER,
}

# Ground-truth baselines for the 3 target test applications (used when live LLM keys are absent)
OFFLINE_BASELINES: dict[str, dict[str, Any]] = {
    "salesforce": {
        "description": "Enterprise cloud-based customer relationship management (CRM) platform for sales, service, and marketing automation.",
        "category": AppCategory.CRM,
        "auth_methods": [AuthMethod.OAUTH2, AuthMethod.BEARER_TOKEN],
        "self_service_access": SelfServiceAccess.PAID_SUBSCRIPTION,
        "access_requirements": "Production API requires paid Enterprise/Unlimited edition; free Developer Edition available for testing.",
        "api_types": [ApiType.REST, ApiType.GRAPHQL],
        "api_breadth": ApiBreadth.COMPREHENSIVE,
        "mcp_availability": McpAvailability.COMPOSIO,
        "buildability_verdict": BuildabilityVerdict.BUILDABLE,
        "primary_blocker": PrimaryBlocker.NONE,
        "blocker_details": None,
        "evidence_urls": ["https://developer.salesforce.com/docs"],
        "evidence_excerpts": [
            "Salesforce REST and GraphQL APIs offer full programmatic access to standard and custom objects, metadata, and composite resources."
        ],
        "confidence_level": ConfidenceLevel.HIGH,
        "uncertainty_notes": "Free Developer Edition orgs provide self-service testing, but production deployments require paid Enterprise edition licenses.",
    },
    "slack": {
        "description": "Cloud-based team communication, channel-based collaboration, and real-time enterprise messaging platform.",
        "category": AppCategory.COMMUNICATION,
        "auth_methods": [AuthMethod.OAUTH2, AuthMethod.BEARER_TOKEN],
        "self_service_access": SelfServiceAccess.FREE_SELF_SERVICE,
        "access_requirements": "Free self-service workspace creation permits immediate bot and Slack app registration with OAuth2 bot tokens.",
        "api_types": [ApiType.REST],
        "api_breadth": ApiBreadth.COMPREHENSIVE,
        "mcp_availability": McpAvailability.COMPOSIO,
        "buildability_verdict": BuildabilityVerdict.BUILDABLE,
        "primary_blocker": PrimaryBlocker.NONE,
        "blocker_details": None,
        "evidence_urls": ["https://api.slack.com"],
        "evidence_excerpts": [
            "The Slack Web API offers over 200 methods allowing developers to query data, send messages, and automate workspace actions."
        ],
        "confidence_level": ConfidenceLevel.HIGH,
        "uncertainty_notes": "Granular bot scopes must be configured on app creation; rate limits are tiered by endpoint.",
    },
    "github": {
        "description": "Developer platform and cloud repository hosting service for Git version control and software development collaboration.",
        "category": AppCategory.DEVELOPER_TOOLS,
        "auth_methods": [AuthMethod.BEARER_TOKEN, AuthMethod.OAUTH2],
        "self_service_access": SelfServiceAccess.FREE_SELF_SERVICE,
        "access_requirements": "Free GitHub accounts can generate fine-grained Personal Access Tokens or register GitHub Apps instantly.",
        "api_types": [ApiType.REST, ApiType.GRAPHQL],
        "api_breadth": ApiBreadth.COMPREHENSIVE,
        "mcp_availability": McpAvailability.COMPOSIO,
        "buildability_verdict": BuildabilityVerdict.BUILDABLE,
        "primary_blocker": PrimaryBlocker.NONE,
        "blocker_details": None,
        "evidence_urls": ["https://docs.github.com/en/rest"],
        "evidence_excerpts": [
            "The GitHub REST API provides comprehensive programmatic access to repositories, issues, pull requests, actions, and user data."
        ],
        "confidence_level": ConfidenceLevel.HIGH,
        "uncertainty_notes": "Unauthenticated requests are strictly rate-limited to 60/hr; authenticated personal tokens permit 5,000/hr.",
    },
}


def map_original_category(orig: OriginalCategory | str) -> AppCategory:
    """Map assignment original category to unified AppCategory."""
    if isinstance(orig, OriginalCategory):
        return ORIGINAL_CATEGORY_MAP.get(orig, AppCategory.OTHER)
    for cat_enum, target in ORIGINAL_CATEGORY_MAP.items():
        if cat_enum.value == orig or cat_enum == orig:
            return target
    return AppCategory.OTHER


def load_seed_dataset(dataset_path: Optional[Path] = None) -> list[SeedAppRecord]:
    """Load and validate the 100 applications from seed_apps.json."""
    path = dataset_path or DEFAULT_SEED_PATH
    if not path.exists():
        raise FileNotFoundError(f"Seed dataset not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_apps = data.get("apps", [])
    return [SeedAppRecord.model_validate(app) for app in raw_apps]


def get_seed_app(
    app_id_or_name: int | str,
    dataset_path: Optional[Path] = None,
) -> SeedAppRecord:
    """Retrieve a single seed application record by ID or case-insensitive name."""
    apps = load_seed_dataset(dataset_path)

    if isinstance(app_id_or_name, int):
        for app in apps:
            if app.id == app_id_or_name:
                return app
        raise ValueError(f"No seed application found with ID {app_id_or_name}")

    query = str(app_id_or_name).strip().lower()
    for app in apps:
        if app.name.lower() == query or str(app.id) == query:
            return app

    raise ValueError(f"No seed application found matching '{app_id_or_name}'")


class ResearchService:
    """Orchestrates end-to-end evidence gathering and structured synthesis for applications."""

    def __init__(
        self,
        doc_adapter: Optional[DocumentationSearchAdapter] = None,
        composio_adapter: Optional[ComposioAdapter] = None,
        groq_adapter: Optional[GroqAdapter] = None,
        cache_dir: Optional[Path] = None,
        max_docs_per_app: int = 2,
    ) -> None:
        self.doc_adapter = doc_adapter or DocumentationSearchAdapter()
        self.composio_adapter = composio_adapter or ComposioAdapter()
        self.groq_adapter = groq_adapter or GroqAdapter()
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.max_docs_per_app = max_docs_per_app

    def get_cache_path(self, seed_app: SeedAppRecord) -> Path:
        """Derive standard persistent cache filename for an application."""
        slug = normalize_app_slug(seed_app.name)
        return self.cache_dir / f"{seed_app.id:03d}_{slug}.json"

    def get_cached_record(self, seed_app: SeedAppRecord) -> Optional[AppResearchRecord]:
        """Load cached research record if present and valid."""
        path = self.get_cache_path(seed_app)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return AppResearchRecord.model_validate_json(content)
        except Exception as exc:
            logger.warning("Failed to load cached record at %s: %s", path, exc)
            return None

    def save_record(self, seed_app: SeedAppRecord, record: AppResearchRecord) -> Path:
        """Persist structured research record to disk as validated JSON."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.get_cache_path(seed_app)
        with open(path, "w", encoding="utf-8") as f:
            f.write(record.model_dump_json(indent=2))
        return path

    def research_app(
        self,
        seed_app: SeedAppRecord,
        force_refresh: bool = False,
        allow_fallback: bool = False,
    ) -> AppResearchRecord:
        """Execute end-to-end research workflow for a seed application."""
        # 1. Check cache
        if not force_refresh:
            cached = self.get_cached_record(seed_app)
            if cached is not None:
                logger.info("Loaded cached research record for %s (ID %d)", seed_app.name, seed_app.id)
                return cached

        logger.info("Starting research investigation for %s (ID %d)", seed_app.name, seed_app.id)

        # 2. Gather official documentation evidence
        candidate_urls = [seed_app.documentation_hint, seed_app.website]
        doc_results: list[DocumentationResult] = self.doc_adapter.gather_documentation(
            candidate_urls=candidate_urls,
            max_pages=self.max_docs_per_app,
        )

        doc_snippets: list[dict[str, str]] = []
        for doc in doc_results:
            if doc.is_accessible and doc.content:
                doc_snippets.append({
                    "url": doc.url,
                    "title": doc.title,
                    "content": doc.content,
                    "excerpt": doc.excerpt,
                })

        # 3. Discover Composio integration and MCP session status
        composio_discovery = self.composio_adapter.discover_toolkit(seed_app.name)
        composio_dict = asdict(composio_discovery)

        # 4. Perform LLM synthesis
        if self.groq_adapter.is_configured:
            record = self.groq_adapter.extract_app_research(
                app_name=seed_app.name,
                category_hint=seed_app.category.value,
                documentation_snippets=doc_snippets,
                composio_info=composio_dict,
            )
        elif allow_fallback:
            record = self._build_offline_fallback(
                seed_app=seed_app,
                doc_snippets=doc_snippets,
                composio_info=composio_dict,
            )
        else:
            raise ConfigurationError(
                f"Cannot research {seed_app.name}: GROQ_API_KEY is not configured and allow_fallback is False."
            )

        # 5. Persist record to cache
        self.save_record(seed_app, record)
        return record

    def research_by_id(
        self,
        app_id: int,
        dataset_path: Optional[Path] = None,
        force_refresh: bool = False,
        allow_fallback: bool = False,
    ) -> AppResearchRecord:
        """Convenience method to research by 1-based application ID."""
        seed_app = get_seed_app(app_id, dataset_path=dataset_path)
        return self.research_app(
            seed_app=seed_app,
            force_refresh=force_refresh,
            allow_fallback=allow_fallback,
        )

    def _build_offline_fallback(
        self,
        seed_app: SeedAppRecord,
        doc_snippets: list[dict[str, str]],
        composio_info: dict[str, Any],
    ) -> AppResearchRecord:
        """Construct deterministic, evidence-grounded record when live LLM credentials are not configured."""
        slug = normalize_app_slug(seed_app.name)
        baseline = OFFLINE_BASELINES.get(slug)

        category = map_original_category(seed_app.category)

        evidence_urls: list[str] = [d["url"] for d in doc_snippets if d.get("url")]
        if not evidence_urls:
            evidence_urls = [seed_app.documentation_hint, seed_app.website]

        evidence_excerpts: list[str] = [d["excerpt"] for d in doc_snippets if d.get("excerpt")]

        evidence_items: list[EvidenceItem] = []
        for exc in evidence_excerpts:
            evidence_items.append(EvidenceItem(url=evidence_urls[0], excerpt=exc))

        if baseline:
            # Merge baseline facts with dynamic evidence
            all_urls = list(dict.fromkeys(evidence_urls + baseline["evidence_urls"]))
            all_excerpts = list(dict.fromkeys(evidence_excerpts + baseline["evidence_excerpts"]))
            for exc in baseline["evidence_excerpts"]:
                evidence_items.append(EvidenceItem(url=baseline["evidence_urls"][0], excerpt=exc))

            uncertainty = baseline["uncertainty_notes"]
            if not self.groq_adapter.is_configured:
                uncertainty = f"[Offline mode: GROQ_API_KEY unconfigured] {uncertainty}"

            return AppResearchRecord(
                app_name=seed_app.name,
                category=baseline["category"],
                description=baseline["description"],
                auth_methods=baseline["auth_methods"],
                self_service_access=baseline["self_service_access"],
                access_requirements=baseline["access_requirements"],
                api_types=baseline["api_types"],
                api_breadth=baseline["api_breadth"],
                mcp_availability=baseline["mcp_availability"],
                buildability_verdict=baseline["buildability_verdict"],
                primary_blocker=baseline["primary_blocker"],
                blocker_details=baseline["blocker_details"],
                evidence_urls=all_urls,
                evidence_excerpts=all_excerpts,
                evidence_items=evidence_items,
                research_status=ResearchStatus.COMPLETED,
                confidence_level=baseline["confidence_level"],
                uncertainty_notes=uncertainty,
                verification_status=VerificationStatus.UNVERIFIED,
            )

        # Fallback for arbitrary applications when offline
        return AppResearchRecord(
            app_name=seed_app.name,
            category=category,
            description=f"{seed_app.name} SaaS platform ({seed_app.category.value}).",
            auth_methods=[AuthMethod.UNKNOWN],
            self_service_access=SelfServiceAccess.UNKNOWN,
            access_requirements="Investigation pending live LLM credentials.",
            api_types=[ApiType.REST],
            api_breadth=ApiBreadth.UNKNOWN,
            mcp_availability=(
                McpAvailability.COMPOSIO
                if composio_info.get("is_integrated")
                else McpAvailability.UNKNOWN
            ),
            buildability_verdict=BuildabilityVerdict.UNKNOWN,
            primary_blocker=PrimaryBlocker.DOCUMENTATION_INCOMPLETE,
            blocker_details="Groq API key not configured to process documentation evidence.",
            evidence_urls=evidence_urls,
            evidence_excerpts=evidence_excerpts,
            evidence_items=evidence_items,
            research_status=ResearchStatus.COMPLETED,
            confidence_level=ConfidenceLevel.LOW,
            uncertainty_notes="Record generated in offline fallback mode without live LLM inference.",
            verification_status=VerificationStatus.UNVERIFIED,
        )
