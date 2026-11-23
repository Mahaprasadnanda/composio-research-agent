"""Data models and schema definitions for Composio Research Agent.

Defines typed Pydantic models and classification enums representing research
findings for SaaS applications and their readiness for AI agent toolkit integration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AppCategory(str, Enum):
    """Broad functional category of the SaaS application."""

    CRM = "crm"
    COMMUNICATION = "communication"
    DEVELOPER_TOOLS = "developer_tools"
    PRODUCTIVITY = "productivity"
    PROJECT_MANAGEMENT = "project_management"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    FINANCE_ACCOUNTING = "finance_accounting"
    HR_RECRUITING = "hr_recruiting"
    CUSTOMER_SUPPORT = "customer_support"
    ECOMMERCE = "ecommerce"
    DESIGN_CREATIVE = "design_creative"
    SECURITY_COMPLIANCE = "security_compliance"
    DATABASE_STORAGE = "database_storage"
    OTHER = "other"


class AuthMethod(str, Enum):
    """Authentication mechanism supported for programmatic API access."""

    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
    SESSION_COOKIE = "session_cookie"
    WEBHOOK_SECRET = "webhook_secret"
    CUSTOM_HEADER = "custom_header"
    NONE = "none"
    UNKNOWN = "unknown"


class SelfServiceAccess(str, Enum):
    """Classification of how developers acquire API credentials."""

    FREE_SELF_SERVICE = "free_self_service"
    FREE_TRIAL_SELF_SERVICE = "free_trial_self_service"
    PAID_SUBSCRIPTION = "paid_subscription"
    ADMIN_APPROVAL = "admin_approval"
    PARTNERSHIP = "partnership"
    CONTACT_SALES = "contact_sales"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class ApiType(str, Enum):
    """Architectural style of the public API."""

    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    WEBHOOK_ONLY = "webhook_only"
    SOAP = "soap"
    NONE = "none"
    UNKNOWN = "unknown"


class ApiBreadth(str, Enum):
    """Estimated coverage and surface area of the public API."""

    COMPREHENSIVE = "comprehensive"
    MODERATE = "moderate"
    LIMITED = "limited"
    MINIMAL = "minimal"
    NONE = "none"
    UNKNOWN = "unknown"


class McpAvailability(str, Enum):
    """Current Model Context Protocol (MCP) server ecosystem status."""

    OFFICIAL = "official"
    COMMUNITY = "community"
    COMPOSIO = "composio"
    NONE = "none"
    UNKNOWN = "unknown"


class BuildabilityVerdict(str, Enum):
    """Assessment of whether an AI agent toolkit can be built."""

    BUILDABLE = "buildable"
    CONDITIONALLY_BUILDABLE = "conditionally_buildable"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class PrimaryBlocker(str, Enum):
    """Primary bottleneck preventing or impeding agent toolkit integration."""

    NONE = "none"
    NO_PUBLIC_API = "no_public_api"
    PAYWALL_RESTRICTED = "paywall_restricted"
    CONTACT_SALES_REQUIRED = "contact_sales_required"
    PARTNERSHIP_REQUIRED = "partnership_required"
    ADMIN_APPROVAL_GATE = "admin_approval_gate"
    COMPLEX_PROPRIETARY_AUTH = "complex_proprietary_auth"
    RESTRICTED_SCOPES = "restricted_scopes"
    RATE_LIMIT_RESTRICTED = "rate_limit_restricted"
    DOCUMENTATION_INCOMPLETE = "documentation_incomplete"
    OTHER = "other"


class ResearchStatus(str, Enum):
    """Lifecycle state of the research investigation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfidenceLevel(str, Enum):
    """Confidence score of the automated research agent's finding."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(str, Enum):
    """Human audit verification status."""

    UNVERIFIED = "unverified"
    HUMAN_VERIFIED = "human_verified"
    FLAGGED_FOR_REVIEW = "flagged_for_review"


class EvidenceItem(BaseModel):
    """Structured documentation evidence supporting research claims."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str = Field(description="Direct URL to official documentation or developer portal.")
    title: Optional[str] = Field(default=None, description="Page or section title.")
    excerpt: str = Field(description="Verbatim excerpt or key quote from the documentation.")
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when evidence was fetched.",
    )


class ExecutionSource(str, Enum):
    """Origin of an operation result to ensure research integrity and prevent false live claims.

    REAL_NETWORK: Confirmed real external network execution against remote API or HTTP endpoints.
    SIMULATED: Produced by a local test double, stub, or simulation without network execution.
    FIXTURE: Loaded from static offline baseline fixtures or pre-recorded fallback data.
    MOCKED: Produced by dynamic mock framework objects (e.g. MagicMock, Mock).
    UNKNOWN: Unspecified or indeterminate execution origin (fails closed to unverified).
    """

    REAL_NETWORK = "real_network"
    SIMULATED = "simulated"
    FIXTURE = "fixture"
    MOCKED = "mocked"
    UNKNOWN = "unknown"


class ExecutionMode(str, Enum):
    """Operational mode reflecting the factual execution status of research pipelines.

    LIVE: All real external network operations (live HTTP documentation fetching, live Groq
        LLM extraction, and live Composio catalog discovery) were executed against real remote APIs
        using non-mock adapters and completed successfully.
    PARTIAL_LIVE: At least one real external network operation executed successfully (e.g. live HTTP
        documentation was retrieved), but one or more other operations were unconfigured, failed,
        or relied on fallback data.
    OFFLINE_FALLBACK: Zero live network operations were executed against external APIs; findings were
        constructed entirely from verified baseline fixtures.
    MOCKED: Executed within a test double / unit test environment utilizing mock adapters (e.g., MagicMock)
        or simulated test stubs.
    """

    LIVE = "live"
    PARTIAL_LIVE = "partial_live"
    OFFLINE_FALLBACK = "offline_fallback"
    MOCKED = "mocked"


class ResearchProvenance(BaseModel):
    """Audit-grade provenance tracking the exact origin and verification level of research claims.

    Verification Invariant:
        live_verified is strictly True IF AND ONLY IF:
            1. execution_mode == ExecutionMode.LIVE (not mocked, simulated, partial, or fallback).
            2. doc_execution_source == ExecutionSource.REAL_NETWORK and documentation_live_fetched is True
               (at least one official URL retrieved over real HTTP 200).
            3. llm_execution_source == ExecutionSource.REAL_NETWORK and llm_inference_executed is True
               (real remote LLM inference completed successfully over the network).
            4. composio_execution_source == ExecutionSource.REAL_NETWORK and
               composio_discovery_attempted is True AND composio_discovery_succeeded is True
               (real Composio API catalog lookup completed successfully over the network).
            5. No operation or adapter is simulated, mocked, or from offline fixtures.
        If any of these conditions are False, live_verified MUST BE False. The system fails closed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_mode: ExecutionMode = Field(
        description="Factual execution mode: live, partial_live, offline_fallback, or mocked."
    )

    # Granular operation execution sources
    doc_execution_source: ExecutionSource = Field(
        default=ExecutionSource.UNKNOWN,
        description="Factual execution origin of documentation retrieval: real_network, simulated, fixture, mocked.",
    )
    llm_execution_source: ExecutionSource = Field(
        default=ExecutionSource.UNKNOWN,
        description="Factual execution origin of LLM inference: real_network, simulated, fixture, mocked.",
    )
    composio_execution_source: ExecutionSource = Field(
        default=ExecutionSource.UNKNOWN,
        description="Factual execution origin of Composio discovery: real_network, simulated, fixture, mocked.",
    )

    # Documentation retrieval provenance
    documentation_live_fetched: bool = Field(
        default=False,
        description="Whether official documentation pages were fetched live over HTTP during this run.",
    )
    documentation_urls_attempted: list[str] = Field(
        default_factory=list,
        description="URLs targeted for documentation retrieval.",
    )
    documentation_urls_succeeded: list[str] = Field(
        default_factory=list,
        description="URLs successfully retrieved with HTTP 200.",
    )

    # LLM extraction provenance
    llm_inference_attempted: bool = Field(
        default=False,
        description="Whether live LLM extraction was attempted.",
    )
    llm_inference_executed: bool = Field(
        default=False,
        description="Whether live remote LLM inference successfully returned structured findings.",
    )
    llm_model: Optional[str] = Field(
        default=None,
        description="Exact model identifier used for inference (e.g. 'openai/gpt-oss-120b').",
    )
    llm_error: Optional[str] = Field(
        default=None,
        description="Error details if LLM inference failed.",
    )

    # Composio discovery provenance
    composio_adapter_configured: bool = Field(
        default=False,
        description="Whether Composio adapter held a valid, non-placeholder API key.",
    )
    composio_discovery_attempted: bool = Field(
        default=False,
        description="Whether Composio catalog lookup was actually attempted over the network.",
    )
    composio_discovery_succeeded: bool = Field(
        default=False,
        description="Whether Composio catalog lookup succeeded (independent of toolkit presence).",
    )
    composio_toolkit_found: bool = Field(
        default=False,
        description="Whether the application toolkit was confirmed present in the Composio catalog.",
    )
    composio_discovery_error: Optional[str] = Field(
        default=None,
        description="Error details if Composio discovery request failed.",
    )

    # Composio MCP session provenance
    composio_mcp_session_attempted: bool = Field(
        default=False,
        description="Whether Composio hosted MCP session creation was attempted.",
    )
    composio_mcp_session_created: bool = Field(
        default=False,
        description="Whether Composio hosted MCP session was successfully created.",
    )
    composio_mcp_endpoint_returned: bool = Field(
        default=False,
        description="Whether a usable MCP endpoint URL was returned from the created session.",
    )
    composio_mcp_endpoint: Optional[str] = Field(
        default=None,
        description="The exact MCP session endpoint URL if returned.",
    )
    composio_mcp_session_error: Optional[str] = Field(
        default=None,
        description="Error details if Composio MCP session creation failed.",
    )

    # Verification Invariant
    live_verified: bool = Field(
        default=False,
        description="Strictly True ONLY when execution_mode is LIVE with live docs, live LLM, and live Composio discovery all successfully executed without mocks.",
    )
    notes: str = Field(
        default="",
        description="Human-readable provenance notes explaining source of findings.",
    )


class AppResearchRecord(BaseModel):
    """Pydantic model representing comprehensive research findings for a single SaaS application."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    app_name: str = Field(description="Official name of the SaaS application.")
    category: AppCategory = Field(description="Primary category classification.")
    description: str = Field(description="Concise one-line description of core capabilities.")

    # API & Authentication details
    auth_methods: list[AuthMethod] = Field(
        default_factory=list,
        description="List of supported authentication methods (OAuth2, API key, etc.).",
    )
    self_service_access: SelfServiceAccess = Field(
        default=SelfServiceAccess.UNKNOWN,
        description="Self-service access classification (free, paid, partnership, etc.).",
    )
    developer_access_tier: Optional[SelfServiceAccess] = Field(
        default=None,
        description="Access classification for developer/sandbox environment (e.g. free Developer Edition).",
    )
    production_access_tier: Optional[SelfServiceAccess] = Field(
        default=None,
        description="Access classification for customer production environment (e.g. paid Enterprise tier).",
    )
    access_requirements: str = Field(
        default="",
        description="Specific requirements to obtain API access (e.g. plan tier, verification).",
    )
    api_types: list[ApiType] = Field(
        default_factory=lambda: [ApiType.REST],
        description="API architecture types (REST, GraphQL, etc.).",
    )
    api_breadth: ApiBreadth = Field(
        default=ApiBreadth.UNKNOWN,
        description="Breadth of public API surface (comprehensive, moderate, limited, etc.).",
    )

    # Integration readiness
    mcp_availability: McpAvailability = Field(
        default=McpAvailability.UNKNOWN,
        description="Existing MCP server availability (official, community, composio, none).",
    )
    has_composio_integration: bool = Field(
        default=False,
        description="Whether a native integration toolkit exists in Composio.",
    )
    composio_toolkit_slug: Optional[str] = Field(
        default=None,
        description="Official slug of the toolkit in Composio.",
    )
    buildability_verdict: BuildabilityVerdict = Field(
        default=BuildabilityVerdict.UNKNOWN,
        description="Verdict on whether an agent toolkit can be constructed.",
    )
    primary_blocker: PrimaryBlocker = Field(
        default=PrimaryBlocker.NONE,
        description="Primary obstacle if integration is blocked or conditioned.",
    )
    blocker_details: Optional[str] = Field(
        default=None,
        description="Specific notes on blockers or licensing restrictions.",
    )

    # Evidence & Verification
    evidence_urls: list[str] = Field(
        default_factory=list,
        description="List of official documentation and reference URLs.",
    )
    evidence_excerpts: list[str] = Field(
        default_factory=list,
        description="Key supporting excerpts extracted from documentation.",
    )
    evidence_items: list[EvidenceItem] = Field(
        default_factory=list,
        description="Structured evidence items with timestamps and source excerpts.",
    )

    # Research metadata
    research_status: ResearchStatus = Field(
        default=ResearchStatus.PENDING,
        description="Status of the automated investigation.",
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Confidence level of the automated findings.",
    )
    uncertainty_notes: Optional[str] = Field(
        default=None,
        description="Unresolved questions, conflicting sources, or ambiguity notes.",
    )
    llm_execution_source: Optional[ExecutionSource] = Field(
        default=None,
        description="Explicit execution source of LLM extraction: real_network, simulated, fixture, mocked.",
    )
    provenance: Optional[ResearchProvenance] = Field(
        default=None,
        description="Detailed execution provenance, tracking live vs offline evidence sources.",
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Human audit status.",
    )
    verification_notes: Optional[str] = Field(
        default=None,
        description="Auditor notes if modified or verified during human evaluation.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation UTC timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update UTC timestamp.",
    )


class ResearchDataset(BaseModel):
    """Container dataset model for the collection of SaaS research records."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="0.1.0", description="Schema version identifier.")
    target_count: int = Field(default=100, description="Target total application count.")
    records: list[AppResearchRecord] = Field(
        default_factory=list,
        description="List of researched application records.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Dataset initialization UTC timestamp.",
    )

    def summary_by_verdict(self) -> dict[str, int]:
        """Aggregate counts of applications by buildability verdict."""
        counts: dict[str, int] = {v.value: 0 for v in BuildabilityVerdict}
        for record in self.records:
            counts[record.buildability_verdict.value] += 1
        return counts

    def summary_by_category(self) -> dict[str, int]:
        """Aggregate counts of applications by category."""
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.category.value] = counts.get(record.category.value, 0) + 1
        return counts

    def summary_by_verification(self) -> dict[str, int]:
        """Aggregate counts of applications by verification status."""
        counts: dict[str, int] = {v.value: 0 for v in VerificationStatus}
        for record in self.records:
            counts[record.verification_status.value] += 1
        return counts


class OriginalCategory(str, Enum):
    """Original 10 category groupings from the Composio take-home assignment."""

    CRM_AND_SALES = "CRM and Sales"
    SUPPORT_AND_HELPDESK = "Support and Helpdesk"
    COMMUNICATIONS_AND_MESSAGING = "Communications and Messaging"
    MARKETING_ADS_EMAIL_SOCIAL = "Marketing, Ads, Email and Social"
    ECOMMERCE = "Ecommerce"
    DATA_SEO_SCRAPING = "Data, SEO and Scraping"
    DEVELOPER_INFRA_DATA_PLATFORMS = "Developer, Infra and Data platforms"
    PRODUCTIVITY_PROJECT_MANAGEMENT = "Productivity and Project Management"
    FINANCE_AND_FINTECH = "Finance and Fintech"
    AI_RESEARCH_MEDIA_NATIVE = "AI, Research and Media-native"


class SeedAppRecord(BaseModel):
    """Seed input record for one of the 100 SaaS applications to be researched."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1, le=100, description="Deterministic 1-100 identifier.")
    name: str = Field(description="Official name of the SaaS application.")
    category: OriginalCategory = Field(
        description="Original category designation from the assignment."
    )
    website: str = Field(description="Primary official website URL.")
    documentation_hint: str = Field(
        description="Documentation or developer portal hint URL."
    )
    research_status: ResearchStatus = Field(
        default=ResearchStatus.PENDING,
        description="Initial research status (pending).",
    )


class SeedDataset(BaseModel):
    """Collection container for all 100 seed application records."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="1.0.0", description="Dataset schema version identifier.")
    total_apps: int = Field(default=100, description="Total number of applications.")
    apps: list[SeedAppRecord] = Field(
        description="List of exactly 100 seed application records."
    )

    def validate_dataset_integrity(self) -> None:
        """Validate that the dataset meets all strict ground truth requirements."""
        if len(self.apps) != 100:
            raise ValueError(f"Expected exactly 100 apps, got {len(self.apps)}")

        ids = [a.id for a in self.apps]
        if len(set(ids)) != 100:
            raise ValueError("Duplicate application IDs detected")
        if set(ids) != set(range(1, 101)):
            raise ValueError("Application IDs must be consecutive integers 1 to 100")

        names = [a.name for a in self.apps]
        if len(set(names)) != 100:
            raise ValueError("Duplicate application names detected")

        # Verify category counts (exactly 10 per category)
        counts = self.category_distribution()
        for cat in OriginalCategory:
            if counts.get(cat.value, 0) != 10:
                raise ValueError(
                    f"Expected 10 apps in category '{cat.value}', got {counts.get(cat.value, 0)}"
                )

    def category_distribution(self) -> dict[str, int]:
        """Return application counts grouped by original category."""
        counts: dict[str, int] = {}
        for a in self.apps:
            counts[a.category.value] = counts.get(a.category.value, 0) + 1
        return counts

