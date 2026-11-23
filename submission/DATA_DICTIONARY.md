# Composio SaaS Research Agent — Data Dictionary & Schema Specification

**Version:** 1.0.0  
**Repository:** [Mahaprasadnanda/composio-research-agent](https://github.com/Mahaprasadnanda/composio-research-agent)  
**Schema Definition:** [src/research_agent/models.py](file:///c:/Users/mail2/OneDrive/Desktop/Composio/src/research_agent/models.py)

---

## 1. Overview & Architectural Hierarchy

The Composio SaaS Research Agent systematically investigates SaaS applications across 10 functional categories to determine their feasibility for autonomous AI agent toolkits, live Composio SDK toolkits, and remote Model Context Protocol (MCP) session creation.

Every output record adheres strictly to typed Pydantic V2 schemas (`extra="forbid"`) with end-to-end evidence traceability, timestamped citations, and immutable execution provenance.

```
SeedAppRecord (data/raw/seed_apps.json)
       │
       ▼
ResearchService (Web Scraper + Groq LLM + Composio SDK)
       │
       ├─► AppResearchRecord (output/research_results/<id>_<app>.json)
       │       ├── EvidenceItem[]
       │       └── ResearchProvenance (ExecutionMode, Sources, Truncation)
       │
       └─► ResearchDataset (output/research_dataset.json)
               └── BatchRunSummary (output/batch_run_summary.json)
```

---

## 2. Core Record Specification (`AppResearchRecord`)

Each application researched by the pipeline is represented by an `AppResearchRecord` containing 24 typed fields:

| Field Name | Type | Allowed / Example Values | Description |
| :--- | :--- | :--- | :--- |
| `app_name` | `str` | e.g. `"Slack"`, `"Shopify"` | Official vendor or product name from the seed dataset. |
| `category` | `AppCategory` (enum) | `crm`, `customer_support`, `communication`, etc. | Broad functional domain categorization. |
| `description` | `str` | Text up to 500 characters | Concise summary of the application's core capabilities. |
| `auth_methods` | `list[AuthMethod]` | `["oauth2"]`, `["api_key", "bearer_token"]` | Publicly documented authentication mechanisms for API access. |
| `self_service_access` | `SelfServiceAccess` | `free_self_service`, `paid_subscription`, etc. | General developer onboarding tier for API credentials. |
| `developer_access_tier` | `Optional[SelfServiceAccess]` | `free_self_service`, `enterprise_only`, `None` | Access tier specifically for sandbox/test environments. |
| `production_access_tier` | `Optional[SelfServiceAccess]` | `paid_subscription`, `enterprise_only` | Access tier required for customer production data. |
| `access_requirements` | `str` | e.g. `"Free internal integration token"` | Specific prerequisites (e.g. billing plan, business verification). |
| `api_types` | `list[ApiType]` | `["rest"]`, `["graphql"]`, `["rest", "grpc"]` | Architectural styles supported by the vendor's APIs. |
| `api_breadth` | `ApiBreadth` | `comprehensive`, `moderate`, `limited`, `unknown` | Estimated functional coverage of the public API surface. |
| `mcp_availability` | `McpAvailability` | `official`, `community`, `composio`, `none`, `unknown` | Model Context Protocol server status in vendor/open-source ecosystems. |
| `has_composio_integration`| `bool` | `True`, `False` | Whether an official toolkit exists in the Composio catalog. |
| `composio_toolkit_slug` | `Optional[str]` | `"slack"`, `"github"`, `None` | Normalized identifier used by the Composio SDK router. |
| `buildability_verdict` | `BuildabilityVerdict` | `buildable`, `conditionally_buildable`, `blocked`, `unknown` | Feasibility assessment for building autonomous agent toolkits today. |
| `primary_blocker` | `PrimaryBlocker` | `none`, `admin_approval_gate`, `contact_sales_required`, etc. | Primary technical, commercial, or operational hurdle. |
| `blocker_details` | `Optional[str]` | Free text explanation | Specific explanation if blocked or conditionally buildable. |
| `evidence_urls` | `list[str]` | `["https://api.slack.com/authentication"]` | Verifiable HTTP URLs of scraped developer documentation. |
| `evidence_excerpts` | `list[str]` | `["Generate a Bot User OAuth Token..."]` | Verbatim text excerpts extracted from retrieved documentation. |
| `evidence_items` | `list[EvidenceItem]` | List of structured objects | Timestamped citations binding each excerpt to its retrieval URL. |
| `research_status` | `ResearchStatus` | `completed`, `failed`, `pending` | Lifecycle status of the automated investigation. |
| `confidence_level` | `ConfidenceLevel` | `high`, `medium`, `low` | LLM and pipeline confidence score in the findings. |
| `uncertainty_notes` | `Optional[str]` | Free text notes | Explicit caveats regarding ambiguous or truncated documentation. |
| `provenance` | `ResearchProvenance` | Embedded provenance object | Detailed boundary tracking of live vs offline evidence sources. |
| `created_at` / `updated_at`| `datetime` | ISO 8601 UTC timestamp | Record creation and last-modified timestamps. |

---

## 3. Execution Provenance Specification (`ResearchProvenance`)

The `provenance` block enforces the project's central research-integrity requirement: **preventing false live claims**.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `execution_mode` | `ExecutionMode` | High-level execution classification: `live`, `partial_live`, `offline_fallback`, `mocked`. |
| `doc_execution_source` | `ExecutionSource` | Source of documentation content: `real_network`, `simulated`, `fixture`, `mocked`. |
| `llm_execution_source` | `ExecutionSource` | Source of structured extraction: `real_network`, `simulated`, `fixture`, `mocked`. |
| `composio_execution_source`| `ExecutionSource` | Source of Composio catalog lookup: `real_network`, `simulated`, `fixture`, `mocked`. |
| `documentation_live_fetched` | `bool` | `True` only if an actual outbound HTTP request succeeded. |
| `documentation_urls_attempted`| `list[str]` | Complete list of target documentation URLs probed. |
| `documentation_urls_succeeded`| `list[str]` | URLs that returned HTTP 200 with extractable content. |
| `documentation_truncated` | `bool` | `True` if raw HTML exceeded token budget and was truncated. |
| `documentation_truncation_notes`| `Optional[str]` | Details of character retention (e.g. `"Retained 12000 of 33549 chars"`). |
| `llm_inference_attempted` | `bool` | Whether an inference call was dispatched to Groq. |
| `llm_inference_executed` | `bool` | Whether Groq returned a valid structured JSON response. |
| `llm_model` | `str` | Exact model identifier used (e.g. `"openai/gpt-oss-120b"`). |
| `llm_error` | `Optional[str]` | Raw error response if Groq failed (e.g. HTTP 413 or 429). |
| `composio_adapter_configured` | `bool` | Whether `COMPOSIO_API_KEY` was valid and non-placeholder. |
| `composio_discovery_attempted`| `bool` | Whether a real network call was dispatched to Composio API. |
| `composio_discovery_succeeded`| `bool` | Whether the Composio API returned HTTP 200. |
| `composio_toolkit_found` | `bool` | Whether the application toolkit was located in the catalog. |
| `composio_mcp_session_attempted`| `bool` | Whether remote MCP session creation was initiated. |
| `composio_mcp_session_created` | `bool` | Whether Composio returned a valid hosted MCP session. |
| `composio_mcp_endpoint_returned`| `bool` | Whether a usable SSE/HTTP MCP endpoint URL was provided. |
| `composio_mcp_endpoint` | `Optional[str]` | Exact MCP session endpoint URL. |
| `composio_mcp_session_error` | `Optional[str]` | Diagnostic error string if session creation was rejected. |
| `live_verified` | `bool` | **Verification Invariant:** `True` if and only if documentation, Groq, and Composio were all executed over real network with zero mocks. |

---

## 4. Enumeration Definitions

### `BuildabilityVerdict`
- `buildable`: Documented REST/GraphQL API with self-service developer access. Toolkit can be built immediately.
- `conditionally_buildable`: Public API exists, but access is gated by developer token approval, partner contracts, or paid enterprise subscriptions.
- `blocked`: No public developer API, consumer web-only app, closed proprietary protocol, or contact sales required.
- `unknown`: Documentation was inaccessible due to Cloudflare anti-bot blocks, paywalls, or incomplete portal data.

### `PrimaryBlocker`
- `none`: No significant technical or administrative obstacles.
- `no_public_api`: Vendor does not publish a developer API.
- `contact_sales_required`: Custom pricing and sales contract required before API keys are issued.
- `admin_approval_gate`: Application review or developer token approval required (e.g. Google Ads, Meta Ads).
- `partnership_required`: Formal certified partner program enrollment mandatory.
- `paywall_restricted`: High-tier enterprise plan required to enable API access.
- `documentation_incomplete`: Developer documentation lacks critical authentication or endpoint details.
- `complex_proprietary_auth`: Non-standard cryptographic signing or proprietary session schemes.

### `ExecutionMode`
- `live`: All research stages executed via real external network calls.
- `partial_live`: Real LLM and Composio calls, but documentation was blocked or restricted.
- `offline_fallback`: Pre-recorded ground-truth baseline fixture used without network calls.
- `mocked`: Generated via test double or unit test mock.

### `ExecutionSource`
- `real_network`: Outbound HTTP request dispatched to genuine external API.
- `simulated`: Test double simulating successful response.
- `fixture`: Static JSON fixture loaded from local disk.
- `mocked`: Mock or MagicMock instance.

---

## 5. Composio Remote MCP Error Taxonomy

When initiating hosted remote MCP sessions via `composio.sessions.create(toolkits=[slug], mcp=True)`, 7 toolkits failed out of 40 discovered (82.5% success rate). All 7 failures share a single root cause:

| Error Classification | HTTP Code | Diagnostic Pattern | Impacted Toolkits |
| :--- | :---: | :--- | :--- |
| `required_auth_configuration_missing` | `400 Bad Request` | `"The following toolkits require auth configs but none exist and cannot be auto-created: <slug>. Please specify them in auth_configs."` | Podio (`podio`), Help Scout (`help_scout`), Zoho Cliq (`zoho_cliq`), Lark (`lark`), LinkedIn Ads (`linkedin_ads`), Threads (`threads`), Shopify (`shopify`). |

**Architectural Takeaway:** Remote MCP session routing in Composio is deterministic. 33 toolkits support anonymous zero-config routing, while 7 toolkits with strict provider security policies require explicit user credentials before router provisioning.
