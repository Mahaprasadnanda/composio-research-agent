"""Tests for Pydantic research models and classification enums."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

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
    PrimaryBlocker,
    ResearchDataset,
    ResearchStatus,
    SelfServiceAccess,
    VerificationStatus,
)


def test_app_research_record_valid_construction():
    record = AppResearchRecord(
        app_name="SampleApp",
        category=AppCategory.DEVELOPER_TOOLS,
        description="Sample developer platform for automated workflows.",
        auth_methods=[AuthMethod.API_KEY, AuthMethod.OAUTH2],
        self_service_access=SelfServiceAccess.FREE_SELF_SERVICE,
        access_requirements="Free tier account with self-service key generation in dashboard.",
        api_types=[ApiType.REST],
        api_breadth=ApiBreadth.COMPREHENSIVE,
        mcp_availability=McpAvailability.COMPOSIO,
        buildability_verdict=BuildabilityVerdict.BUILDABLE,
        primary_blocker=PrimaryBlocker.NONE,
        evidence_urls=["https://example.com/docs/api"],
        evidence_excerpts=["Generate an API key under Account Settings > Developer."],
    )

    assert record.app_name == "SampleApp"
    assert record.category == AppCategory.DEVELOPER_TOOLS
    assert AuthMethod.API_KEY in record.auth_methods
    assert record.self_service_access == SelfServiceAccess.FREE_SELF_SERVICE
    assert record.buildability_verdict == BuildabilityVerdict.BUILDABLE
    assert record.research_status == ResearchStatus.PENDING
    assert record.confidence_level == ConfidenceLevel.MEDIUM
    assert record.verification_status == VerificationStatus.UNVERIFIED
    assert isinstance(record.created_at, datetime)


def test_app_research_record_missing_required_fields_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        # Omitting required app_name, category, description
        AppResearchRecord.model_validate({})

    errors = exc_info.value.errors()
    missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
    assert "app_name" in missing_fields
    assert "category" in missing_fields
    assert "description" in missing_fields


def test_app_research_record_forbids_extra_fields():
    with pytest.raises(ValidationError) as exc_info:
        AppResearchRecord(
            app_name="AppWithExtra",
            category=AppCategory.CRM,
            description="Test CRM description.",
            unexpected_field="disallowed",
        )
    assert any(e["type"] == "extra_forbidden" for e in exc_info.value.errors())


def test_evidence_item_valid():
    item = EvidenceItem(
        url="https://docs.sample.com/auth",
        title="Authentication Guide",
        excerpt="OAuth 2.0 with authorization code grant is supported.",
    )
    assert item.url == "https://docs.sample.com/auth"
    assert item.title == "Authentication Guide"
    assert "OAuth 2.0" in item.excerpt
    assert isinstance(item.retrieved_at, datetime)


def test_research_dataset_aggregations():
    rec1 = AppResearchRecord(
        app_name="App One",
        category=AppCategory.CRM,
        description="First CRM app.",
        buildability_verdict=BuildabilityVerdict.BUILDABLE,
        verification_status=VerificationStatus.HUMAN_VERIFIED,
    )
    rec2 = AppResearchRecord(
        app_name="App Two",
        category=AppCategory.CRM,
        description="Second CRM app.",
        buildability_verdict=BuildabilityVerdict.BLOCKED,
        primary_blocker=PrimaryBlocker.CONTACT_SALES_REQUIRED,
        verification_status=VerificationStatus.UNVERIFIED,
    )
    rec3 = AppResearchRecord(
        app_name="App Three",
        category=AppCategory.COMMUNICATION,
        description="Communication app.",
        buildability_verdict=BuildabilityVerdict.CONDITIONALLY_BUILDABLE,
        primary_blocker=PrimaryBlocker.PAYWALL_RESTRICTED,
        verification_status=VerificationStatus.UNVERIFIED,
    )

    dataset = ResearchDataset(records=[rec1, rec2, rec3])

    verdict_counts = dataset.summary_by_verdict()
    assert verdict_counts[BuildabilityVerdict.BUILDABLE.value] == 1
    assert verdict_counts[BuildabilityVerdict.BLOCKED.value] == 1
    assert verdict_counts[BuildabilityVerdict.CONDITIONALLY_BUILDABLE.value] == 1

    category_counts = dataset.summary_by_category()
    assert category_counts[AppCategory.CRM.value] == 2
    assert category_counts[AppCategory.COMMUNICATION.value] == 1

    verification_counts = dataset.summary_by_verification()
    assert verification_counts[VerificationStatus.HUMAN_VERIFIED.value] == 1
    assert verification_counts[VerificationStatus.UNVERIFIED.value] == 2
