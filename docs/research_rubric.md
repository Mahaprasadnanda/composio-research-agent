# SaaS Evaluation Rubric for AI Agent Toolkit Integration

This document defines the official, standardized research rubric for evaluating 100 SaaS applications to determine their feasibility, access gating, surface breadth, and overall buildability as AI agent toolkits.

---

## 1. Principles and Methodology

The evaluation operates on rigorous technical evidence standards:
1. **Primary Source Hierarchy:** Official developer documentation, API reference guides, developer terms of service, and official pricing/plan matrices take precedence over third-party blog posts, aggregators, or marketing landing pages.
2. **Separation of Authentication from Access Acquisition:** Authentication defines *how credentials are exchanged programmatically* (e.g. OAuth2, API key). Access acquisition defines *what commercial, administrative, or contractual hurdles exist to obtain those credentials* (e.g. free self-service vs. enterprise contact-sales).
3. **No Inference Without Attribution:** Every assigned classification must cite a specific documentation URL and supporting verbatim excerpt.
4. **Presumption of Uncertainty over False Negatives:** The absence of a search result does not prove non-existence. When public documentation cannot be located or verified, the system must assign `Unknown` or `Insufficient Evidence` rather than fabricating negative claims.

---

## 2. Research Dimensions and Classifications

### Dimension A: Authentication Methods

Applications may support multiple authentication mechanisms depending on the API endpoint or product line. All documented, public programmatic methods should be recorded.

| Classification | Technical Criteria | Example Evidence Requirement |
| :--- | :--- | :--- |
| **OAuth2** | Supports RFC 6749 authorization code, client credentials, PKCE, or implicit grant flows. Developer can register client IDs and redirect URIs. | Official docs describing authorization URL, token endpoint, client ID, client secret, or OAuth scopes. |
| **API Key** | Static token or secret key generated via developer portal or account settings, passed via request header (e.g. `X-API-Key`, `Authorization: ApiKey ...`) or query parameter. | Documentation specifying key generation in dashboard and header format. |
| **Basic Authentication** | HTTP Basic Auth scheme using username/password or username/API token encoded in Base64 within `Authorization: Basic ...` header. | API reference explicitly stating HTTP Basic Auth with Base64 encoding. |
| **Bearer / Token Authentication** | Non-OAuth long-lived personal access tokens (PAT), JWT tokens, or session bearer tokens passed via `Authorization: Bearer <token>`. | Docs detailing personal access token creation in user profile settings. |
| **Session / Cookie** | Authentication requires maintaining stateful browser cookies or session IDs (e.g. session-based internal APIs). Typically indicates lack of standard machine-to-machine developer auth. | Documentation indicating reliance on cookie headers or session IDs. |
| **Other** | Custom signature algorithms (e.g. AWS Signature v4, HMAC-SHA256 request signing), mutual TLS (mTLS), or proprietary challenge-response schemes. | Specification of cryptographic signature creation over HTTP headers. |
| **Unknown** | Documentation is inaccessible, conflicting, or lacks explicit authentication specifications. | Absence of discoverable developer auth guide. |

---

### Dimension B: Self-Service Access & Credential Acquisition

This dimension measures the administrative and financial friction developers face to obtain API keys or register an application.

| Classification | Definition | Evidence Criteria |
| :--- | :--- | :--- |
| **Free Self-Service** | Any user can create a free account or developer account and immediately generate API credentials or register an OAuth app without entering payment details or waiting for human review. | Official pricing page showing API access included in Free tier, or instant self-service developer portal signup. |
| **Free Trial / Self-Service** | Self-service signup provides a time-limited or credit-limited trial with full API access, allowing immediate testing without manual sales interaction. | Official trial terms confirming API access is active during the 14/30-day trial period. |
| **Paid Subscription Required** | Self-service signup is possible, but API access is gated behind a mandatory paid tier (e.g. Pro, Team, Business). Self-service checkout is available without speaking to sales. | Pricing table explicitly listing "API Access" under paid tiers, with self-service checkout available. |
| **Admin Approval Required** | Developer access is restricted to organization administrators, or requires an enterprise workspace admin to explicitly enable developer access/scopes before tokens can be generated. | Docs stating "Only Workspace Admins can create API tokens" or requiring internal IT ticket/approval. |
| **Partnership Required** | API access requires applying to a formal developer/technology partner program, signing a partner agreement, or passing third-party security certification. | Developer portal linking to a formal partner application form, marketplace vetting requirements, or formal review. |
| **Contact Sales** | API keys or enterprise endpoints cannot be purchased self-service; requires direct engagement with enterprise sales or bespoke contractual agreements. | Pricing page stating "Enterprise - Contact Sales" for API access, or missing self-serve signup. |
| **Closed / No Public API** | Platform does not expose any public, third-party developer API. Platform operates solely via closed proprietary web/mobile interfaces. | Official statement confirming no public API exists, or developer portal absence with explicit closed-ecosystem policy. |
| **Unknown** | Access requirements cannot be conclusively established from public documentation. | Pricing or developer portal information is gated or ambiguous. |

---

### Dimension C: API Surface & Architectural Style

#### Architectural Style

| Style | Description |
| :--- | :--- |
| **REST** | Standard HTTP RESTful API with resource-oriented endpoints returning JSON/XML. |
| **GraphQL** | Exposes a single `/graphql` endpoint supporting queries and mutations via GraphQL schema. |
| **Both** | Formally exposes and maintains both REST endpoints and a GraphQL schema for primary workflows. |
| **Other** | gRPC, SOAP/XML, Webhook-only, or CLI-only interface. |
| **No Documented Public API** | No discoverable public API documentation exists. |
| **Unknown** | Architectural style cannot be verified. |

#### API Breadth

| Classification | Surface Description | Typical Endpoint / Resource Scope |
| :--- | :--- | :--- |
| **Comprehensive** | Covers virtually all core domain objects with full CRUD (Create, Read, Update, Delete) capabilities, webhooks/event subscriptions, and granular query filters. | >50 endpoints, complete entity management, bulk APIs, webhooks. |
| **Moderate** | Covers primary common workflows (e.g. list, get, create), but lacks advanced configuration, bulk operations, or secondary object access. | 15–50 endpoints covering primary entities. |
| **Limited** | Read-only endpoints, or restricted to a very narrow use case (e.g. logging events, single-record lookup). | 5–15 endpoints with constrained mutation capability. |
| **Minimal** | Bare minimum interface; e.g. single webhook ingestion endpoint, ping API, or single-action trigger. | <5 endpoints or single specialized function. |
| **None** | No public API exists. | 0 endpoints. |
| **Unknown** | Surface breadth cannot be reliably quantified from available evidence. | Documentation incomplete or gated. |

---

### Dimension D: Model Context Protocol (MCP) Server Availability

This dimension identifies existing Model Context Protocol integrations across the ecosystem.

| Classification | Definition | Evidence Source |
| :--- | :--- | :--- |
| **Official Provider-Maintained MCP** | The SaaS vendor directly maintains, publishes, and supports an official MCP server (e.g. in their official GitHub organization or npm/PyPI namespace). | Official repository owned by SaaS vendor (e.g. `github.com/<vendor>/mcp-server`), official documentation reference. |
| **Community-Maintained MCP** | An open-source, third-party developer has created a public MCP server repository that interfaces with the SaaS application. | Public GitHub repository under third-party organization (e.g. `github.com/<user>/<app>-mcp`). |
| **Composio Integration / MCP** | The application is natively supported as a toolkit or MCP server in Composio's official catalog (`composio-core` / Composio MCP bridge). | Listed in Composio official toolkit directory (`composio.dev/tools` or Composio SDK catalog). |
| **No Known MCP Found** | Active search across official vendor repositories, GitHub MCP topics, and Composio catalog yielded no public MCP server implementation. | Comprehensive search performed; zero matching open-source or official servers. |
| **Unknown** | Search could not be completed or verified due to tooling limitations. | Gated discovery source. |

---

### Dimension E: Agent-Toolkit Buildability Verdict

The buildability verdict synthesizes authentication, access friction, and API capabilities into an actionable recommendation for AI agent engineering teams.

```
                                    [SaaS Application Audit]
                                               │
                                 Does public API exist?
                                  ├── No ──> [BLOCKED: No Public API]
                                  └── Yes
                                       │
                         Is access gated by sales or partner review?
                          ├── Yes (Contact Sales / Partner) ──> [BLOCKED: Enterprise / Partner Gate]
                          └── No
                               │
                  Is API free or self-serve paid with adequate breadth?
                   ├── Free self-serve + Moderate/Comprehensive ──> [BUILDABLE]
                   ├── Paid self-serve or requires Admin setup ────> [CONDITIONALLY BUILDABLE]
                   └── Read-only / Minimal breadth / Rate walls ───> [CONDITIONALLY BUILDABLE / BLOCKED]
```

| Verdict | Definition | Typical Conditions |
| :--- | :--- | :--- |
| **Buildable** | An AI agent toolkit can be constructed immediately with self-service credentials and adequate API breadth. No human sales or partner blockers exist. | Free self-service or trial tier, standard OAuth2/API key, REST/GraphQL with Moderate or Comprehensive breadth. |
| **Conditionally Buildable** | An agent toolkit can technically be built, but requires operational prerequisites: paid subscription, organization admin approval, manual token generation, or limited mutation scope. | Paid subscription required, requires workspace admin token grant, complex OAuth app verification for production, or Moderate/Limited API breadth. |
| **Blocked** | An agent toolkit cannot be built or distributed by typical developers due to hard gating, prohibitive bureaucracy, or complete absence of an API. | Contact sales required, closed/no public API, mandatory formal partnership review, or read-only/minimal API insufficient for agentic actions. |
| **Insufficient Evidence** | Public documentation is inconclusive, gated behind client logins, or conflicting, preventing a defensible determination. | Documentation inaccessible or contradictory. |

---

## 3. Evidence Collection & Traceability Rules

Every record produced by the research agent must satisfy the following traceability standards:

1. **Direct Attribution:** Every research finding must include at least one direct, canonical URL (`evidence_urls`) to official developer documentation.
2. **Verbatim Excerpts:** Key claims must be substantiated with verbatim textual snippets (`evidence_excerpts`) extracted directly from the cited source (e.g. *"API access is available on Team and Enterprise plans"*).
3. **Temporal Anchoring:** Each evidence item must record a UTC retrieval timestamp (`retrieved_at`) to account for future documentation changes.
4. **Fact vs. Inference Separation:** Concrete statements directly stated in documentation (e.g. *"Uses OAuth 2.0"*) must be recorded as factual. Derived assessments (e.g. *"API breadth is Moderate based on 22 listed endpoints"*) must be explicitly annotated in `uncertainty_notes` or `blocker_details`.
5. **Handling Conflicting Sources:** When marketing materials and technical developer docs disagree (e.g. marketing says "Instant API access" but docs say "Partner approval required"), the technical developer documentation takes absolute precedence.

---

## 4. Confidence Score Rubric

| Confidence Level | Definition & Criteria |
| :--- | :--- |
| **High** | Primary official developer portal was directly retrieved and reviewed. Authentication, pricing tier, and API reference endpoints are unambiguous and current. |
| **Medium** | Developer documentation was accessed, but secondary aspects (such as exact plan pricing gating or rate limits) required cross-referencing pricing pages or terms of service. |
| **Low** | Official developer documentation was partially gated, required inference from secondary sources, or presented conflicting terms. Flagged for human review. |
