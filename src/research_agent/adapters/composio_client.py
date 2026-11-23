"""Composio SDK adapter for toolkit discovery, tool inspection, and MCP session integration."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Known slugs for standard SaaS apps in Composio
SLUG_OVERRIDES: dict[str, str] = {
    "salesforce": "salesforce",
    "hubspot": "hubspot",
    "pipedrive": "pipedrive",
    "zoho crm": "zoho_crm",
    "zendesk": "zendesk",
    "intercom": "intercom",
    "freshdesk": "freshdesk",
    "slack": "slack",
    "twilio": "twilio",
    "discord": "discord",
    "telegram": "telegram",
    "google ads": "google_ads",
    "mailchimp": "mailchimp",
    "klaviyo": "klaviyo",
    "sendgrid": "sendgrid",
    "shopify": "shopify",
    "github": "github",
    "vercel": "vercel",
    "cloudflare": "cloudflare",
    "supabase": "supabase",
    "notion": "notion",
    "airtable": "airtable",
    "linear": "linear",
    "jira": "jira",
    "asana": "asana",
    "clickup": "clickup",
    "stripe": "stripe",
    "quickbooks": "quickbooks",
    "xero": "xero",
}


def normalize_app_slug(app_name: str) -> str:
    """Derive canonical Composio slug from application name."""
    clean = app_name.strip().lower()
    if clean in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[clean]
    # Remove content in parentheses, then replace non-alphanumerics with underscores
    clean = re.sub(r"\(.*?\)", "", clean)
    clean = re.sub(r"[^a-z0-9]+", "_", clean).strip("_")
    return clean


@dataclass(frozen=True)
class ComposioToolkitDiscovery:
    """Results from querying Composio catalog for application integration."""

    app_name: str
    slug: str
    is_integrated: bool
    toolkit_name: str = ""
    description: str = ""
    category: str = ""
    auth_schemes: list[str] = field(default_factory=list)
    available_tools_count: int = 0
    sample_tools: list[dict[str, Any]] = field(default_factory=list)

    # Explicit discovery outcome tracking
    discovery_attempted: bool = False
    discovery_succeeded: bool = False
    toolkit_found: bool = False

    # Explicit MCP session provenance
    session_creation_attempted: bool = False
    session_created: bool = False
    mcp_endpoint: Optional[str] = None
    mcp_supported: bool = False
    session_error: Optional[str] = None

    requires_connected_account: bool = False
    error: Optional[str] = None


class ComposioAdapter:
    """Interacts with Composio Python SDK for discovery and MCP enablement."""

    is_configured: bool = False

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key
        self._client: Any = None
        self.is_configured = bool(api_key and not api_key.startswith("your_"))

        if self.is_configured:
            try:
                from composio import Composio

                self._client = Composio(api_key=self.api_key)
            except Exception as exc:
                logger.warning("Failed to initialize Composio SDK client: %s", exc)
                self.is_configured = False

    def discover_toolkit(self, app_name: str) -> ComposioToolkitDiscovery:
        """Inspect Composio catalog to determine if application is supported."""
        slug = normalize_app_slug(app_name)

        if not self.is_configured or self._client is None:
            return ComposioToolkitDiscovery(
                app_name=app_name,
                slug=slug,
                is_integrated=False,
                discovery_attempted=False,
                discovery_succeeded=False,
                toolkit_found=False,
                error="Composio API key is not configured or SDK unavailable.",
            )

        try:
            # Query toolkit details
            toolkit = None
            try:
                toolkit = self._client.toolkits.get(slug=slug)
            except Exception as get_exc:
                err_text = str(get_exc).lower()
                # 404 / not found means query succeeded, but toolkit is not in catalog
                if "404" in err_text or "not found" in err_text:
                    return ComposioToolkitDiscovery(
                        app_name=app_name,
                        slug=slug,
                        is_integrated=False,
                        discovery_attempted=True,
                        discovery_succeeded=True,
                        toolkit_found=False,
                    )
                # Any other error (e.g. 401 unauthorized, timeout, 500) means query failed
                raise

            if not toolkit:
                return ComposioToolkitDiscovery(
                    app_name=app_name,
                    slug=slug,
                    is_integrated=False,
                    discovery_attempted=True,
                    discovery_succeeded=True,
                    toolkit_found=False,
                )

            name = getattr(toolkit, "name", "") or getattr(toolkit, "display_name", "") or slug
            desc = getattr(toolkit, "description", "") or ""
            cat = getattr(toolkit, "category", "") or ""
            auth_schemes: list[str] = []

            # Check auth configs
            if hasattr(toolkit, "auth_config_creation_fields"):
                auth_schemes.append("configurable_auth")
            if hasattr(toolkit, "auth_schemes") and getattr(toolkit, "auth_schemes"):
                auth_schemes.extend(str(s) for s in toolkit.auth_schemes)

            # Discover sample tools
            sample_tools: list[dict[str, Any]] = []
            try:
                tools_response = self._client.tools.get(user_id="research_agent", toolkits=[slug], limit=5)
                if tools_response:
                    items = getattr(tools_response, "items", tools_response)
                    if isinstance(items, list):
                        for item in items[:5]:
                            tool_name = getattr(item, "name", str(item))
                            tool_desc = getattr(item, "description", "")
                            sample_tools.append({"name": tool_name, "description": tool_desc})
            except Exception as tool_exc:
                logger.debug("Tool discovery query notice for %s: %s", slug, tool_exc)

            # Check MCP session creation explicitly
            mcp_endpoint: Optional[str] = None
            mcp_supported = False
            session_creation_attempted = True
            session_created = False
            session_error: Optional[str] = None

            try:
                session = self._client.sessions.create(
                    user_id="research_agent",
                    toolkits=[slug],
                    mcp=True,
                )
                if session is not None:
                    session_created = True
                    if hasattr(session, "mcp") and session.mcp:
                        endpoint = getattr(session.mcp, "url", None)
                        if endpoint:
                            mcp_endpoint = str(endpoint)
                            mcp_supported = True
            except Exception as mcp_exc:
                session_error = str(mcp_exc)
                logger.debug("MCP session setup for %s: %s", slug, mcp_exc)

            return ComposioToolkitDiscovery(
                app_name=app_name,
                slug=slug,
                is_integrated=True,
                toolkit_name=str(name),
                description=str(desc),
                category=str(cat),
                auth_schemes=auth_schemes,
                available_tools_count=len(sample_tools),
                sample_tools=sample_tools,
                discovery_attempted=True,
                discovery_succeeded=True,
                toolkit_found=True,
                session_creation_attempted=session_creation_attempted,
                session_created=session_created,
                mcp_endpoint=mcp_endpoint,
                mcp_supported=mcp_supported,
                session_error=session_error,
                requires_connected_account=True,
            )

        except Exception as exc:
            err_msg = str(exc)
            if "401" in err_msg or "unauthorized" in err_msg.lower():
                return ComposioToolkitDiscovery(
                    app_name=app_name,
                    slug=slug,
                    is_integrated=False,
                    discovery_attempted=True,
                    discovery_succeeded=False,
                    toolkit_found=False,
                    error="Unauthorized: COMPOSIO_API_KEY is invalid or expired.",
                )
            if "404" in err_msg or "not found" in err_msg.lower():
                return ComposioToolkitDiscovery(
                    app_name=app_name,
                    slug=slug,
                    is_integrated=False,
                    discovery_attempted=True,
                    discovery_succeeded=True,
                    toolkit_found=False,
                )
            return ComposioToolkitDiscovery(
                app_name=app_name,
                slug=slug,
                is_integrated=False,
                discovery_attempted=True,
                discovery_succeeded=False,
                toolkit_found=False,
                error=f"Composio query failed: {type(exc).__name__}",
            )
