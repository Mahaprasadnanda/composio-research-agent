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
