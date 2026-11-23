# Composio SaaS Research Agent

An automated, evidence-grounded research pipeline evaluating **100 enterprise SaaS applications** across 10 functional categories to determine their readiness for autonomous AI agent toolkits, Composio SDK integration, and remote Model Context Protocol (MCP) router sessions.

---

## Table of Contents

- [Objective & Problem Statement](#objective--problem-statement)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Setup Instructions (Windows PowerShell)](#setup-instructions-windows-powershell)
- [CLI Usage](#cli-usage)
  - [1. Single Application Research](#1-single-application-research)
  - [2. Batch Research Pipeline](#2-batch-research-pipeline)
  - [3. Offline Analytics & HTML Case Study](#3-offline-analytics--html-case-study)
- [Evaluation Rubric & Decision Matrix](#evaluation-rubric--decision-matrix)
- [Dataset Reconciliation & Coverage](#dataset-reconciliation--coverage)
- [Analytical Findings & Key Insights](#analytical-findings--key-insights)
- [Viewing the HTML Case Study](#viewing-the-html-case-study)
- [Testing & Quality Verification](#testing--quality-verification)
- [Known Limitations & Integrity Caveats](#known-limitations--integrity-caveats)
- [License](#license)

---

## Objective & Problem Statement

Building reliable autonomous AI workflows requires programmatic, authenticated access to third-party SaaS services. However, integration readiness across software vendors varies widely:
- Many modern developer platforms offer open REST/GraphQL APIs with instant self-service developer access.
- Others enforce strict business verification, multi-week app reviews, administrative approval gates, or paywalls requiring high-tier enterprise contracts.
- Some platforms maintain official remote Model Context Protocol (MCP) servers (e.g. `mcp.slack.com`), while others rely on ecosystem toolkits (such as Composio), community servers, or have no public developer API whatsoever.

The **Composio SaaS Research Agent** automates developer diligence by:
1. Crawling official developer portals and documentation.
2. Sanitizing raw HTML into structured, token-budgeted text while prioritizing auth, endpoint, rate-limit, and access-tier sections.
3. Querying the live Composio Python SDK catalog to discover supported tools and test remote MCP router session creation.
4. Synthesizing structured Pydantic records using Groq's `openai/gpt-oss-120b` LLM.
5. Enforcing a strict **provenance verification invariant**—zero test doubles, simulated responses, or offline fixtures can claim live verification.
6. Generating cross-category analytics, dataset reconciliation reports, and a standalone interactive HTML case study.

---

## System Architecture

```
+--------------------------------------------------------------------------------------------------+
|                                    COMPOSIO RESEARCH AGENT                                       |
+--------------------------------------------------------------------------------------------------+
                                                 │
                                 [Input: 100 SaaS Seed Applications]
                                                 │
                                                 ▼
               ┌─────────────────────────────────────────────────────────────────┐
               │                  Phase 1: Evidence Acquisition                  │
               │  - DocumentationSearchAdapter: HTTPX live fetching              │
               │  - DOM Sanitization: Strips nav, header, footer, SVG, scripts   │
               │  - Semantic Scoring: Prioritizes OAuth2, tokens, endpoints, MCP │
               │  - Explicit Truncation Tracking in Provenance Metadata          │
               └─────────────────────────────────┬───────────────────────────────┘
                                                 │
                                                 ▼
               ┌─────────────────────────────────────────────────────────────────┐
               │                 Phase 2: Ecosystem Discovery                    │
               │  - ComposioAdapter: Composio Python SDK (toolkits.get)          │
               │  - Tool Inspection: Bounded tool name & description schemas     │
               │  - Remote MCP Sessions: sessions.create(toolkits=[slug], mcp)   │
               │  - Distinguishes vendor MCP vs Composio integration             │
               └─────────────────────────────────┬───────────────────────────────┘
                                                 │
                                                 ▼
               ┌─────────────────────────────────────────────────────────────────┐
               │             Phase 3: Structured LLM Synthesis & Audit           │
               │  - GroqAdapter: openai/gpt-oss-120b (JSON Object Mode)          │
               │  - Dynamic 413 Compression: Bounded prompt token budgets        │
               │  - Provenance Guard: Strict fail-closed verification invariant  │
               │  - Output: Typed AppResearchRecord models                       │
               └─────────────────────────────────┬───────────────────────────────┘
                                                 │
                                                 ▼
               ┌─────────────────────────────────────────────────────────────────┐
               │          Phase 4: Cross-Reconciliation & Analytics              │
               │  - AnalyticsService: Seed vs Consolidated vs File reconciliation│
               │  - Cross-Category Metrics: Breakdown across all 10 categories    │
               │  - Empirical Insights: Answering 9 core integration questions   │
               │  - Standalone HTML Dashboard: Fully functional offline browser  │
               └─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

- **Runtime:** Python 3.11+ (verified on Python 3.13)
- **Environment:** Windows PowerShell / Linux / macOS
- **LLM Inference:** [Groq API](https://console.groq.com) using `openai/gpt-oss-120b` (131k context, native JSON mode; migrated from deprecated `llama-3.3-70b-versatile`)
- **Tooling & MCP:** [Composio Python SDK](https://composio.dev) (`composio` v0.12+) with remote Model Context Protocol router sessions
- **HTTP Client:** `httpx` with timeout management and user-agent emulation
- **Data Validation:** Pydantic v2 (strict enums, immutable fields, forbidden extra inputs)
- **Configuration:** `python-dotenv` with credential sanitization and secret masking
- **Testing:** `pytest` (91 automated unit and integration tests)
- **Reporting:** Vanilla HTML5, CSS3, JavaScript (zero external runtime dependencies, 100% offline-compatible)

---

## Repository Structure

```
composio-research-agent/
├── .env.example                          # Environment template (keys strictly excluded from git)
├── .gitignore                            # Comprehensive ignore rules (secrets, venv, caches, output)
├── README.md                             # Project documentation & operational manual
├── requirements.txt                      # Project dependencies
├── data/
│   ├── raw/
│   │   ├── seed_apps.json                # Ground-truth 100 SaaS applications across 10 categories
│   │   └── seed_apps.csv                 # Tabular export of seed applications
│   └── processed/                        # Processed ground-truth reference files
├── docs/
│   ├── research_rubric.md                # Formal evaluation rubric and verdict definitions
│   └── research_output_schema.md         # Pydantic schema specifications and data contracts
├── output/                               # Local research outputs (git-ignored for security)
│   ├── research_results/                 # 63 individual validated application JSON files
│   ├── research_dataset.json             # Consolidated dataset of completed research records
│   ├── batch_run_summary.json            # Batch execution statistics and failure logs
│   └── analytics/                        # Structured analytics generated by CLI
│       ├── data_reconciliation.json      # Complete cross-source data reconciliation audit
│       ├── analytics_summary.json        # High-level metrics for consolidated and file scopes
│       ├── category_analysis.json        # Granular breakdown for all 10 SaaS categories
│       └── insights.json                 # Structured answers to 9 integration questions
├── reports/                              # Presentation deliverables
│   ├── case_study.html                   # Standalone interactive dashboard & research case study
│   └── assets/
│       ├── styles.css                    # Professional dark-mode responsive dashboard styling
│       └── dashboard.js                  # Client-side search, filtering, and table interactions
├── src/
│   └── research_agent/
│       ├── __init__.py                   # Package exports
│       ├── cli.py                        # Unified command-line interface (single, batch, analytics)
│       ├── config.py                     # Safe configuration loader with secret masking
│       ├── models.py                     # Strict Pydantic models, provenance schemas, and enums
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── composio_client.py        # Composio SDK catalog discovery and MCP session adapter
│       │   ├── documentation_search.py   # DOM sanitization, semantic section scoring & fetcher
│       │   └── groq_client.py            # Groq client with token budgeting and 413/429 recovery
│       ├── services/
│       │   ├── __init__.py
│       │   ├── analytics_service.py      # Reconciliation, category analytics & HTML generator
│       │   ├── batch_runner.py           # Resumable batch runner & checkpoint persistence
│       │   └── research_service.py       # Core research orchestration & strict provenance engine
│       └── use_cases/
│           ├── __init__.py
│           ├── run_batch_research.py     # Batch runner use-case entry point
│           └── run_single_research.py    # Single application research entry point
└── tests/
    ├── __init__.py
    ├── test_adapters.py                  # Adapter unit tests with mocks
    ├── test_analytics.py                 # Analytics, reconciliation, and HTML generation tests
    ├── test_batch_runner.py              # Batch runner, resume, cache, and error handling tests
    ├── test_config.py                    # Environment and secret masking tests
    ├── test_doc_optimization.py          # HTML preprocessing, token budgeting, and 413 recovery
    ├── test_live_integration.py          # Live network integration tests
    ├── test_models.py                    # Model validation and schema contract tests
    ├── test_research_service.py          # Orchestration, cache, and provenance invariant tests
    └── test_seed_dataset.py              # Ground-truth 100-app dataset integrity tests
```

---

## Setup Instructions (Windows PowerShell)

### 1. Prerequisites
- Python 3.11+ installed and on `PATH`.
- Git installed.
- PowerShell execution policy enabled for local scripts:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```

### 2. Clone and Navigate
```powershell
git clone https://github.com/Mahaprasadnanda/composio-research-agent.git
cd composio-research-agent
```

### 3. Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Configure Credentials
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Populate `.env` with your free API keys:
- `GROQ_API_KEY`: Obtain from [Groq Console](https://console.groq.com/keys).
- `COMPOSIO_API_KEY`: Obtain from [Composio Dashboard](https://app.composio.dev/settings).
- `GROQ_MODEL`: `openai/gpt-oss-120b` (default).

> **Security Guarantee:** Real credentials are **never** committed to version control. Keys are masked in memory and sanitized in logging representations.

---

## CLI Usage

The CLI supports single application research, multi-app batch research, and offline analytics.

### 1. Single Application Research

Research designated test targets (**Salesforce**, **Slack**, and **GitHub**):
```powershell
$env:PYTHONPATH="src"; python -m research_agent.cli --test-targets
```

Target any individual application by ID (1–100) or name:
```powershell
$env:PYTHONPATH="src"; python -m research_agent.cli --app-id 21
$env:PYTHONPATH="src"; python -m research_agent.cli --app-name "Slack"
```

Flags:
- `--force-refresh`: Bypass cache and perform fresh live research.
- `--disallow-fallback`: Fail strictly if live network calls fail (rejects offline fixtures).

---

### 2. Batch Research Pipeline

Run batch research over selected applications or the full 100-app seed dataset:
```powershell
# Research selected apps by ID with checkpoint resume
$env:PYTHONPATH="src"; python -m research_agent.cli batch --ids 1,21,41,71 --resume

# Research full dataset in chunks of 10 with inter-app pacing
$env:PYTHONPATH="src"; python -m research_agent.cli batch --batch-size 10 --delay 15.0 --resume
```

Flags:
- `--batch-size <int>`: Number of applications per checkpoint chunk (default: 10).
- `--ids <list>`: Comma-separated application IDs to research (e.g. `1,2,11,21`).
- `--names <list>`: Comma-separated application names (e.g. `"Slack,Shopify"`).
- `--resume` / `--no-resume`: Re-use existing completed cached records (default: `--resume`).
- `--delay <float>`: Pause in seconds between applications to respect rolling TPM windows.
- `--disallow-fallback`: Enforce strict live execution; fails on missing credentials or rate limits.

---

### 3. Offline Analytics & HTML Case Study

Generate data reconciliation audits, category statistics, analytical insights, and the interactive HTML case study **without making any live network calls**:

```powershell
$env:PYTHONPATH="src"; python -m research_agent.cli analytics
```

Output:
```
======================================================================
COMPOSIO RESEARCH AGENT - ANALYTICS & CASE STUDY COMPLETE
======================================================================
Seed Applications:        100
Consolidated Records:     60
Individual Result Files:  63
Total Unique Researched:  63
Live Verified Rate:       93.7%
Buildable Rate:           52.4%
Composio Toolkit Rate:    63.5%
MCP Session Success:      82.5%

Generated Output Artifacts:
  - reconciliation_json: output/analytics/data_reconciliation.json
  - summary_json: output/analytics/analytics_summary.json
  - category_analysis_json: output/analytics/category_analysis.json
  - insights_json: output/analytics/insights.json
  - html_case_study: reports/case_study.html
  - css_asset: reports/assets/styles.css
  - js_asset: reports/assets/dashboard.js
======================================================================
```

---

## Evaluation Rubric & Decision Matrix

| Buildability Verdict | Public API Requirement | Developer Access Tier | Composio / MCP Status | Operational Definition |
| :--- | :--- | :--- | :--- | :--- |
| **Buildable** | Documented REST or GraphQL API | Free self-service tier or developer sandbox | Composio toolkit available or standard HTTP endpoint | An autonomous agent toolkit can be built, authenticated, and deployed immediately without human-in-the-loop sales friction. |
| **Conditionally Buildable** | Documented public API exists | Paid enterprise subscription, partner review, or business verification required | Toolkit available, subject to scope/auth restrictions | Toolkit is technically feasible, but developers must pass bureaucratic, financial, or administrative verification gates. |
| **Blocked** | No public API or proprietary closed protocol | Closed ecosystem, contact-sales mandatory, or partnership required | No integration available | An agent toolkit cannot be built due to absent developer endpoints, paywalls, or hard vendor walls. |
| **Unknown** | Documentation inaccessible (403, 404, or paywall) | Ambiguous or unverified access requirements | Unverified | Evidence was insufficient to make a high-confidence determination. Requires human audit. |

---

## Dataset Reconciliation & Coverage

A strict cross-source reconciliation was performed comparing `data/raw/seed_apps.json` (100 apps), `output/research_dataset.json` (consolidated dataset), and `output/research_results/` (individual files):

```
+-----------------------------------------------------------------------------------+
| Total Seed Applications:             100 (10 categories, 10 applications each)    |
| Consolidated Dataset Records:        60 valid Pydantic records                    |
| Individual Result Files:             63 valid JSON files                          |
| Total Unique Researched:             63 applications (63.0% total coverage)       |
| Failed During Batch Execution:       4 applications (Groq 200k TPD limit reached) |
| Unattempted Seed Applications:       33 applications remaining in pipeline        |
| Duplicate Records:                   0 (in consolidated dataset and files)        |
| Invalid Records / JSON Parse Errors: 0                                            |
+-----------------------------------------------------------------------------------+
```

### Reconciliation Discrepancy Note
- Applications 1 through 64 were executed sequentially in the batch pipeline until Groq's daily free-tier token ceiling (**200,000 Tokens Per Day**) was reached at application 64. 60 applications completed and were written to `output/research_dataset.json`.
- 4 applications (ID 58 Sherlock, ID 60 Clay, ID 62 Vercel, ID 64 Cloudflare) recorded transient 429 rate limits in `output/batch_run_summary.json`.
- 3 additional applications (ID 71 Notion, ID 81 Stripe, ID 91 NotebookLM) exist as genuine, validated research records in `output/research_results/` from the earlier 10-app pilot run.
- Total unique researched applications across all output files is **63**.

### Execution Provenance Breakdown (63 Researched Applications)
- **Live Network Verified (`live`, `live_verified = True`):** **59 applications (93.7%)**
- **Partial Live Execution (`partial_live`, `live_verified = False`):** **4 applications (6.3%)**
  - *Note:* WhatsApp Business, Meta Ads, Threads (Meta), and Salesforce Commerce Cloud had blocked documentation scrapes (0 candidate URLs succeeded). While LLM extraction and Composio discovery executed live, they are strictly classified as `partial_live` to maintain research integrity.
- **Offline Fallback / Simulated Mock:** **0 applications (0.0%)**

### Category-Wise Distribution Matrix (63 Researched Applications)

| Category | Target | Researched | Buildable | Cond. Buildable | Blocked | Unknown | Composio Toolkits | MCP Sessions | Live Verified |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **CRM & Sales** | 10 | 10 | 5 | 4 | 0 | 1 | 8 (80.0%) | 7 (87.5%) | **10 (100.0%)** |
| **Support & Helpdesk** | 10 | 10 | 4 | 3 | 2 | 1 | 8 (80.0%) | 8 (100.0%) | **10 (100.0%)** |
| **Communications & Messaging** | 10 | 10 | 8 | 0 | 1 | 1 | 7 (70.0%) | 6 (85.7%) | **9 (90.0%)** |
| **Marketing, Ads & Social** | 10 | 10 | 2 | 4 | 4 | 0 | 7 (70.0%) | 5 (71.4%) | **8 (80.0%)** |
| **Ecommerce** | 10 | 10 | 5 | 1 | 3 | 1 | 5 (50.0%) | 3 (60.0%) | **9 (90.0%)** |
| **Developer, Infra & Data** | 10 | 2 | 2 | 0 | 0 | 0 | 1 (50.0%) | 1 (100.0%) | **2 (100.0%)** |
| **Data, SEO & Scraping** | 10 | 8 | 5 | 2 | 1 | 0 | 3 (37.5%) | 3 (100.0%) | **8 (100.0%)** |
| **Productivity & Projects** | 10 | 1 | 1 | 0 | 0 | 0 | 1 (100.0%) | 1 (100.0%) | **1 (100.0%)** |
| **Finance & Fintech** | 10 | 1 | 1 | 0 | 0 | 0 | 0 (0.0%) | 0 (0.0%) | **1 (100.0%)** |
| **AI & Media-native** | 10 | 1 | 0 | 0 | 1 | 0 | 0 (0.0%) | 0 (0.0%) | **1 (100.0%)** |
| **Total / Aggregate** | **100** | **63** | **33** | **14** | **12** | **4** | **40 (63.5%)** | **33 (82.5%)** | **59 (93.7%)** |

---

## Analytical Findings & Key Insights

Derived from [output/analytics/insights.json](file:///c:/Users/mail2/OneDrive/Desktop/Composio/output/analytics/insights.json):

1. **Strongest Integration Readiness:**
   - **Communications & Messaging** (80% buildable; Slack, Discord, Twilio, SendGrid provide instant bot registration and self-serve webhooks).
   - **Ecommerce** (50% buildable; Shopify, BigCommerce provide developer sandboxes).
   - **CRM & Sales** (50% buildable, 40% conditionally buildable; mature REST APIs, though Salesforce requires Developer Edition).
2. **Weakest Integration Readiness:**
   - **Marketing, Ads & Social** (only 20% buildable; Meta Ads, TikTok Ads require strict business verification, ad account reviews, and partner agreements).
3. **Public API Availability:**
   - **84.1%** of researched applications provide documented public REST or GraphQL APIs. Only 10 applications (e.g. NotebookLM) were identified with `no_public_api` as their primary blocker.
4. **Composio Toolkit Coverage:**
   - **63.5%** of researched applications (40/63) have native toolkits in the official Composio catalog.
5. **Composio MCP Session Conversion:**
   - **82.5%** of discovered toolkits (33/40) successfully initiated live remote MCP router sessions. Failures occurred only on toolkits requiring mandatory authentication configurations (e.g. Shopify, Attio) that cannot be created anonymously.
6. **Authentication Standards:**
   - OAuth2 dominates modern SaaS, followed by API Key Bearer tokens. Developer access frequently diverges between free permanent sandboxes (Salesforce Developer Edition) and customer paid production tiers.
7. **Primary Technical Blockers:**
   - Incomplete documentation / Cloudflare scrape protection (16 apps), followed by `no_public_api` (10 apps) and admin approval gates (2 apps).

---

## Viewing the HTML Case Study

The generated HTML case study is located at [reports/case_study.html](file:///c:/Users/mail2/OneDrive/Desktop/Composio/reports/case_study.html).

### Key Dashboard Features:
- **Responsive Dark/Light UI:** Built with modern CSS grid layouts, clear typography, and metric cards.
- **100% Offline Standalone:** The full analytics and application explorer dataset is embedded directly in the HTML document. It can be opened directly as a `file://` URL in Google Chrome, Microsoft Edge, Mozilla Firefox, or Safari without requiring a web server or backend API.
- **Interactive Application Research Explorer:**
  - Full-text search across application names and functional descriptions.
  - Dropdown filtering by Category (all 10 categories) and Buildability Verdict (`buildable`, `conditionally_buildable`, `blocked`, `unknown`).
  - Displays authentication methods, API types, Composio toolkit status, remote MCP session creation, and live verification provenance.
- **Visual Distribution Charts:** Clean, accessible SVG/CSS native bar charts representing buildability distributions, top authentication methods, and primary blockers.

### Opening the Report:
```powershell
# Open directly in default web browser from PowerShell
Start-Process reports\case_study.html
```

---

## Testing & Quality Verification

The test suite enforces schema validity, adapter mocking, secret masking, batch checkpointing, HTML generation, and the strict provenance invariant:

```powershell
$env:PYTHONPATH="src"; pytest -v
```

### Test Coverage (93 Total Tests):
- `tests/test_adapters.py` (14 tests): HTML cleaning, snippet extraction, HTTP fetching, slug normalization, Composio discovery mocks, Groq model selection.
- `tests/test_analytics.py` (13 tests): Reconciliation accuracy, missing/duplicate ID detection, category aggregations, verdict distributions, zero-network verification, exact 59 live-verified regression check, HTML generation, CLI execution.
- `tests/test_batch_runner.py` (13 tests): Batch chunking, resume behavior, cache bypass, checkpoint persistence, transient vs permanent retry limits.
- `tests/test_config.py` (11 tests): Secret masking in `repr`/`str`, placeholder detection, missing credential errors, model overrides.
- `tests/test_doc_optimization.py` (8 tests): Boilerplate removal, semantic section scoring, token budgeting, dynamic 413 compression, 429 retry-after parsing.
- `tests/test_live_integration.py` (2 tests): Live external HTTP documentation fetching and live Groq/Composio integration (with vendor quota handling).
- `tests/test_models.py` (5 tests): Pydantic validation, forbidden extra attributes, evidence items, dataset aggregations.
- `tests/test_research_service.py` (18 tests): Research orchestration, offline fallback, access-tier separation, strict provenance invariant (stubs strictly produce `MOCKED`).
- `tests/test_seed_dataset.py` (12 tests): 100-app ground-truth dataset integrity, consecutive IDs, unique names, category distribution, CSV parity.

**Test Result:** `92 passed, 1 skipped` (100% pass rate).

---

## Known Limitations & Integrity Caveats

1. **Groq Free-Tier Rate Limits:** The live batch research was paused after 64 applications due to Groq's daily free-tier cap (200,000 Tokens Per Day) on `openai/gpt-oss-120b`. Scaling to all 100 applications concurrently requires a developer or paid tier key.
2. **Cloudflare & Anti-Bot Gates:** Several developer portals (e.g. `developer.salesforce.com/docs`, Meta Ads) block basic HTTP clients with HTTP 403 Forbidden. While the agent falls back to homepage redirects or reports `partial_live`, production crawlers should incorporate headless browser rendering (Playwright/Puppeteer).
3. **Composio Mandatory Auth Configs:** 7 discovered toolkits (e.g. Shopify, Attio) returned HTTP 400 on `sessions.create(mcp=True)` because their tool router requires pre-configured user credentials. These toolkits are confirmed to exist, but their MCP sessions cannot be initialized anonymously.
4. **Manual Verification Requirement:** 14 records received `conditionally_buildable` and 4 received `unknown`. These classifications require human review of enterprise agreements and OAuth approval flows.

---

## License

MIT License. See project repository for details.
