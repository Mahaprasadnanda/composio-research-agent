"""Groq LLM adapter for structured schema extraction from retrieved documentation evidence."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

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
    ResearchStatus,
    SelfServiceAccess,
    VerificationStatus,
)
from research_agent.config import DEFAULT_GROQ_MODEL

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
INITIAL_BACKOFF = 1.5

EXTRACTION_SYSTEM_PROMPT = """You are an expert AI software engineer analyzing SaaS developer platforms to determine if an autonomous AI agent toolkit can be built for the application.

Analyze the provided documentation and Composio ecosystem context strictly according to the evidence provided.

Return a valid JSON object matching the following specification:
{
  "app_name": string (official name),
  "category": string (MUST be one of: "crm", "customer_support", "communication", "marketing", "ecommerce", "analytics", "developer_tools", "project_management", "finance_accounting", "other"),
  "description": string (concise one-line functional summary, 15-200 characters),
  "auth_methods": list of strings (allowed: "oauth2", "api_key", "basic_auth", "bearer_token", "session_cookie", "webhook_secret", "custom_header", "none", "unknown"),
  "self_service_access": string (MUST be one of: "free_self_service", "free_trial_self_service", "paid_subscription", "admin_approval", "partnership", "contact_sales", "closed", "unknown"),
  "developer_access_tier": string or null (developer/sandbox environment tier, e.g. "free_self_service"),
  "production_access_tier": string or null (customer production environment tier, e.g. "paid_subscription"),
  "access_requirements": string (exact requirement to get API access, e.g. "Free tier self-serve" or "Requires Team plan ($25/mo)"),
  "api_types": list of strings (allowed: "rest", "graphql", "grpc", "webhook_only", "soap", "none", "unknown"),
  "api_breadth": string (MUST be one of: "comprehensive", "moderate", "limited", "minimal", "none", "unknown"),
  "mcp_availability": string (MUST be one of: "official", "community", "composio", "none", "unknown"),
  "has_composio_integration": boolean (true if native integration exists in Composio catalog),
  "composio_toolkit_slug": string or null (toolkit slug in Composio),
  "buildability_verdict": string (MUST be one of: "buildable", "conditionally_buildable", "blocked", "unknown"),
  "primary_blocker": string (MUST be one of: "none", "no_public_api", "paywall_restricted", "contact_sales_required", "partnership_required", "admin_approval_gate", "complex_proprietary_auth", "restricted_scopes", "rate_limit_restricted", "documentation_incomplete", "other"),
  "blocker_details": string or null (explanation if blocked or conditionally buildable),
  "evidence_urls": list of strings (canonical URLs cited from the evidence),
  "evidence_excerpts": list of strings (verbatim quotes directly supporting auth, access, and API breadth),
  "confidence_level": string ("high", "medium", "low"),
  "uncertainty_notes": string or null (notes on ambiguities, conflicting docs, or unverified claims)
}

RULES:
1. ONLY cite URLs and verbatim excerpts present in the provided documentation text. Never invent URLs or quotes.
2. If documentation is unavailable or inaccessible, set buildability_verdict to "blocked" or "unknown" and confidence_level to "low".
3. Distinguish clearly between official vendor MCP servers (e.g. vendor-published remote/local MCP server), community MCP servers, and Composio integrations. If a vendor maintains an official MCP server (e.g. Slack mcp.slack.com), set mcp_availability to "official", and record has_composio_integration separately.
4. Distinguish between developer/sandbox access (e.g. Salesforce Developer Edition free self-service) and production enterprise licensing.
5. Output ONLY the JSON object. Do not include markdown preamble or conversational text.
"""


class GroqAdapter:
    """Client wrapper for Groq inference with structured JSON output and bounded retries."""

    is_configured: bool = False

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GROQ_MODEL,
        max_retries: int = MAX_RETRIES,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self._client: Any = None
        self.is_configured = bool(api_key and not api_key.startswith("your_"))

        if self.is_configured:
            try:
                from groq import Groq

                self._client = Groq(api_key=self.api_key, timeout=self.timeout)
            except Exception as exc:
                logger.warning("Failed to initialize Groq client: %s", exc)
                self.is_configured = False

    def extract_app_research(
        self,
        app_name: str,
        category_hint: str,
        documentation_snippets: list[dict[str, str]],
        composio_info: Optional[dict[str, Any]] = None,
    ) -> AppResearchRecord:
        """Execute structured LLM extraction on documentation evidence."""
        if not self.is_configured or self._client is None:
            raise RuntimeError(
                "Groq client is not configured. Set GROQ_API_KEY in .env to run live extraction."
            )

        # Build context payload
        evidence_block = ""
        for i, doc in enumerate(documentation_snippets, 1):
            evidence_block += (
                f"\n--- SOURCE {i} ({doc.get('url', 'Unknown URL')}) ---\n"
                f"Title: {doc.get('title', 'N/A')}\n"
                f"Content:\n{doc.get('content', '')}\n"
            )

        composio_block = ""
        if composio_info:
            composio_block = (
                f"\n--- COMPOSIO TOOLKIT INTEGRATION DATA ---\n"
                f"Integrated in Composio: {composio_info.get('is_integrated')}\n"
                f"Toolkit Slug: {composio_info.get('slug')}\n"
                f"Tools Count: {composio_info.get('available_tools_count')}\n"
                f"MCP Supported: {composio_info.get('mcp_supported')}\n"
                f"Sample Tools: {json.dumps(composio_info.get('sample_tools', []))}\n"
            )

        user_prompt = (
            f"Target Application: {app_name}\n"
            f"Assigned Category: {category_hint}\n"
            f"{composio_block}\n"
            f"Documentation Evidence:\n{evidence_block}\n\n"
            f"Analyze the above evidence and output the JSON research record."
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "Calling Groq (%s) for %s [attempt %d/%d]",
                    self.model,
                    app_name,
                    attempt,
                    self.max_retries,
                )
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )

                raw_content = response.choices[0].message.content
                if not raw_content:
                    raise ValueError("Groq returned empty response body.")

                data = json.loads(raw_content)

                # Ensure required fields conform to schema
                record = self._parse_and_validate_record(app_name, data, documentation_snippets)
                return record

            except Exception as exc:
                last_error = exc
                err_msg = str(exc)
                logger.warning(
                    "Groq extraction attempt %d failed for %s: %s",
                    attempt,
                    app_name,
                    err_msg,
                )
                # Exponential backoff on rate limits or network issues
                if attempt < self.max_retries:
                    sleep_time = INITIAL_BACKOFF * (2 ** (attempt - 1))
                    time.sleep(sleep_time)

        raise RuntimeError(
            f"Groq extraction failed after {self.max_retries} attempts: {last_error}"
        )

    def _parse_and_validate_record(
        self,
        app_name: str,
        data: dict[str, Any],
        docs: list[dict[str, str]],
    ) -> AppResearchRecord:
        """Validate and construct AppResearchRecord from model JSON."""
        # Normalize category
        cat_str = str(data.get("category", "other")).lower()
        try:
            category = AppCategory(cat_str)
        except ValueError:
            category = AppCategory.OTHER

        # Normalize auth methods
        raw_auth = data.get("auth_methods", [])
        auth_methods: list[AuthMethod] = []
        for m in raw_auth:
            try:
                auth_methods.append(AuthMethod(str(m).lower()))
            except ValueError:
                pass
        if not auth_methods:
            auth_methods = [AuthMethod.UNKNOWN]

        # Normalize self-service access
        try:
            self_service = SelfServiceAccess(str(data.get("self_service_access", "unknown")).lower())
        except ValueError:
            self_service = SelfServiceAccess.UNKNOWN

        # Normalize API types
        raw_api_types = data.get("api_types", ["rest"])
        api_types: list[ApiType] = []
        for at in raw_api_types:
            try:
                api_types.append(ApiType(str(at).lower()))
            except ValueError:
                pass
        if not api_types:
            api_types = [ApiType.REST]

        # Normalize API breadth
        try:
            breadth = ApiBreadth(str(data.get("api_breadth", "unknown")).lower())
        except ValueError:
            breadth = ApiBreadth.UNKNOWN

        # Normalize MCP availability
        try:
            mcp_avail = McpAvailability(str(data.get("mcp_availability", "unknown")).lower())
        except ValueError:
            mcp_avail = McpAvailability.UNKNOWN

        # Normalize buildability verdict
        try:
            verdict = BuildabilityVerdict(str(data.get("buildability_verdict", "unknown")).lower())
        except ValueError:
            verdict = BuildabilityVerdict.UNKNOWN

        # Normalize primary blocker
        try:
            blocker = PrimaryBlocker(str(data.get("primary_blocker", "none")).lower())
        except ValueError:
            blocker = PrimaryBlocker.NONE

        # Normalize confidence level
        try:
            confidence = ConfidenceLevel(str(data.get("confidence_level", "medium")).lower())
        except ValueError:
            confidence = ConfidenceLevel.MEDIUM

        # Evidence URLs & excerpts
        evidence_urls = [str(u) for u in data.get("evidence_urls", []) if u]
        if not evidence_urls:
            evidence_urls = [d["url"] for d in docs if d.get("url")]

        evidence_excerpts = [str(e) for e in data.get("evidence_excerpts", []) if e]

        # Build structured EvidenceItems
        evidence_items: list[EvidenceItem] = []
        for excerpt in evidence_excerpts:
            evidence_items.append(
                EvidenceItem(
                    url=evidence_urls[0] if evidence_urls else "https://example.com",
                    excerpt=excerpt,
                )
            )

        # Normalize developer and production access tiers
        dev_tier: Optional[SelfServiceAccess] = None
        raw_dev = data.get("developer_access_tier")
        if raw_dev:
            try:
                dev_tier = SelfServiceAccess(str(raw_dev).lower())
            except ValueError:
                pass

        prod_tier: Optional[SelfServiceAccess] = None
        raw_prod = data.get("production_access_tier")
        if raw_prod:
            try:
                prod_tier = SelfServiceAccess(str(raw_prod).lower())
            except ValueError:
                pass

        # Composio integration flags
        has_composio = bool(data.get("has_composio_integration", False))
        composio_slug = data.get("composio_toolkit_slug")

        return AppResearchRecord(
            app_name=app_name,
            category=category,
            description=str(data.get("description", f"SaaS platform for {app_name}")),
            auth_methods=auth_methods,
            self_service_access=self_service,
            developer_access_tier=dev_tier,
            production_access_tier=prod_tier,
            access_requirements=str(data.get("access_requirements", "")),
            api_types=api_types,
            api_breadth=breadth,
            mcp_availability=mcp_avail,
            has_composio_integration=has_composio,
            composio_toolkit_slug=str(composio_slug) if composio_slug else None,
            buildability_verdict=verdict,
            primary_blocker=blocker,
            blocker_details=data.get("blocker_details"),
            evidence_urls=evidence_urls,
            evidence_excerpts=evidence_excerpts,
            evidence_items=evidence_items,
            research_status=ResearchStatus.COMPLETED,
            confidence_level=confidence,
            uncertainty_notes=data.get("uncertainty_notes"),
            verification_status=VerificationStatus.UNVERIFIED,
        )
