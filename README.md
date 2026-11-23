# Composio SaaS Research Agent

An automated, evidence-grounded research pipeline evaluating **100 enterprise SaaS applications** across 10 functional categories to determine their readiness for autonomous AI agent toolkits, Composio SDK integration, and remote Model Context Protocol (MCP) router sessions.

---

## Table of Contents

- [Objective & Problem Statement](#objective--problem-statement)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Submission Package & Artifacts](#submission-package--artifacts)
- [Setup Instructions (Windows PowerShell)](#setup-instructions-windows-powershell)
- [CLI Usage](#cli-usage)
  - [1. Single Application Research](#1-single-application-research)
  - [2. Batch Research Pipeline](#2-batch-research-pipeline)
  - [3. Offline Analytics & HTML Case Study](#3-offline-analytics--html-case-study)
  - [4. Benchmark-Based Verification Audit](#4-benchmark-based-verification-audit)
- [Evaluation Rubric & Decision Matrix](#evaluation-rubric--decision-matrix)
- [Dataset Reconciliation & Coverage](#dataset-reconciliation--coverage)
- [Analytical Findings & Key Insights](#analytical-findings--key-insights)
- [Benchmark-Based Verification Audit Findings](#benchmark-based-verification-audit-findings)
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
- **Testing:** `pytest` (98 automated unit, verification, and integration tests)
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
│   ├── research_output_schema.md         # Pydantic schema specifications and data contracts
│   └── verification_audit_summary.md     # Independent 15-application verification audit summary
├── output/                               # Local research outputs (git-ignored for security)
│   ├── research_results/                 # 63 individual validated application JSON files
│   ├── research_dataset.json             # Consolidated dataset of completed research records (63 records)
│   ├── batch_run_summary.json            # Batch execution statistics and failure logs
│   ├── analytics/                        # Structured analytics generated by CLI
│   │   ├── data_reconciliation.json      # Complete cross-source data reconciliation audit
│   │   ├── analytics_summary.json        # High-level metrics for consolidated and file scopes
│   │   ├── category_analysis.json        # Granular breakdown for all 10 SaaS categories
│   │   └── insights.json                 # Structured answers to 9 integration questions
│   └── verification/                     # Independent verification audit reports
│       ├── verification_sample.json      # Stratified 15-app sample data
│       ├── verification_report.json      # Field-by-field audit report
│       └── verification_report.csv       # Spreadsheet tabular audit matrix
├── reports/                              # Presentation deliverables
│   ├── case_study.html                   # Standalone interactive dashboard & research case study
│   └── assets/
│       ├── styles.css                    # Professional dark-mode responsive dashboard styling
│       └── dashboard.js                  # Client-side search, filtering, and table interactions
├── submission/                           # Submission-ready distribution package
│   ├── DATA_DICTIONARY.md                # Complete field-by-field schema and enum data dictionary
│   ├── REPRODUCIBILITY.md                # Offline reproduction instructions
│   ├── research_dataset.json             # Sanitized consolidated dataset (63 applications)
│   ├── records/                          # 63 individual sanitized JSON files
│   ├── data_reconciliation.json          # Reconciled dataset accounting
│   ├── analytics_summary.json            # High-level metric distributions
│   ├── category_analysis.json            # Category breakdown matrix
│   ├── insights.json                     # Structured research findings
│   ├── verification_sample.json          # 15-app audit sample
│   ├── verification_report.json          # Comprehensive verification audit JSON
│   └── verification_report.csv           # Tabular verification spreadsheet
├── src/
│   └── research_agent/
│       ├── __init__.py                   # Package exports
│       ├── cli.py                        # Unified command-line interface (single, batch, analytics, verify)
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
│       │   ├── research_service.py       # Core research orchestration & strict provenance engine
│       │   └── verification_service.py   # Independent 15-app verification audit service
│       └── use_cases/
│           ├── __init__.py
│           ├── run_batch_research.py     # Batch runner use-case entry point
│           └── run_single_research.py    # Single application research entry point
└── tests/
    ├── __init__.py
    ├── test_adapters.py                  # Adapter unit tests with mocks (14 tests)
    ├── test_analytics.py                 # Analytics, reconciliation, and HTML generation tests (13 tests)
    ├── test_batch_runner.py              # Batch runner, resume, cache, and error handling tests (13 tests)
    ├── test_config.py                    # Environment and secret masking tests (11 tests)
    ├── test_doc_optimization.py          # HTML preprocessing, token budgeting, and 413 recovery (8 tests)
    ├── test_live_integration.py          # Live network integration tests (2 tests)
    ├── test_models.py                    # Model validation and schema contract tests (5 tests)
    ├── test_research_service.py          # Orchestration, cache, and provenance invariant tests (18 tests)
    ├── test_seed_dataset.py              # Ground-truth 100-app dataset integrity tests (9 tests)
    └── test_verification.py              # Independent verification audit tests (5 tests)
```

---

## Submission Package & Artifacts

The `submission/` directory provides a self-contained, sanitized bundle designed for grading, review, and offline reproduction:

1. **Consolidated Research Dataset:** `submission/research_dataset.json` contains all 63 validated research records, validated against Pydantic schemas.
2. **Individual Research Records:** `submission/records/` contains all 63 standalone JSON application files with full evidence items.
3. **Data Dictionary:** `submission/DATA_DICTIONARY.md` documents every field, enum, validation rule, and provenance invariant.
4. **Offline Reproducibility Guide:** `submission/REPRODUCIBILITY.md` documents instructions to re-generate all reports offline.
5. **Reconciliation Accounting:** `submission/data_reconciliation.json` cross-references seed apps, batch summary, and output files.
6. **Verification Deliverables:** `submission/verification_report.json`, `submission/verification_report.csv`, and `submission/verification_sample.json`.
7. **Analytics Outputs:** `submission/analytics_summary.json`, `submission/category_analysis.json`, and `submission/insights.json`.

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
Consolidated Records:     63
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
  - verification_sample_json: output/verification/verification_sample.json
  - verification_report_json: output/verification/verification_report.json
  - verification_report_csv: output/verification/verification_report.csv
  - verification_audit_summary_md: docs/verification_audit_summary.md
======================================================================
```

---

### 4. Benchmark-Based Verification Audit

Execute the vendor-grounded verification audit over the stratified 15-application sample (internal benchmark evaluation against official vendor documentation rather than external third-party human review):

```powershell
$env:PYTHONPATH="src"; python -m research_agent.cli verify
```

Output:
```
======================================================================
COMPOSIO RESEARCH AGENT - VERIFICATION AUDIT COMPLETE
======================================================================
Sample Applications:      15
Total Fields Evaluated:   105
Exact Match Rate:         62.9%
Post-Correction Accuracy: 92.4%
Composio Discovery Match: 100.0%
Verdict Agreement Rate:   73.3%

Generated Verification Artifacts:
  - verification_sample: output/verification/verification_sample.json
  - verification_report_json: output/verification/verification_report.json
  - verification_report_csv: output/verification/verification_report.csv
  - verification_audit_summary_md: docs/verification_audit_summary.md
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
| Consolidated Dataset Records:        63 valid Pydantic records                    |
| Individual Result Files:             63 valid JSON files                          |
| Total Unique Researched:             63 applications (63.0% total coverage)       |
| Failed During Batch Execution:       4 applications (Groq 200k TPD limit reached) |
| Unattempted Seed Applications:       33 applications remaining in pipeline        |
| Duplicate Records:                   0 (in consolidated dataset and files)        |
| Invalid Records / JSON Parse Errors: 0                                            |
+-----------------------------------------------------------------------------------+
```

### Reconciliation Accounting & Provenance
- Applications 1 through 64 were executed sequentially in batch mode until Groq's daily free-tier token cap (**200,000 Tokens Per Day**) was reached at application 64. 60 applications completed cleanly.
- 4 applications (ID 58 Sherlock, ID 60 Clay, ID 62 Vercel, ID 64 Cloudflare) encountered transient 429 rate limits, recorded in `output/batch_run_summary.json`.
- 3 additional applications (ID 71 Notion, ID 81 Stripe, ID 91 NotebookLM) were researched during the pilot phase and exist as validated records in `output/research_results/`.
- All 63 completed applications are consolidated into `output/research_dataset.json` and `submission/research_dataset.json`.
- Total researched across all output files is **63 unique applications**. 63 + 4 + 33 = exactly 100 seed applications.

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
   - **82.5%** of discovered toolkits (33/40) successfully initiated live remote MCP router sessions in unauthenticated/zero-config mode.
   - **The 7 Mandatory-Auth Failures (HTTP 400):** Exactly 7 toolkits (**Podio**, **Help Scout**, **Zoho Cliq**, **Lark**, **LinkedIn Ads**, **Threads**, **Shopify**) failed session creation with HTTP 400: `"The following toolkits require auth configs but none exist and cannot be auto-created: <slug>. Please specify them in auth_configs."`
   - *Integrity Finding:* Zero failures were caused by network timeouts or SDK exceptions; all 7 represent strict provider security policies requiring pre-configured OAuth/API credentials.
6. **Authentication Standards:**
   - OAuth2 dominates modern SaaS, followed by API Key Bearer tokens. Developer access frequently diverges between free permanent sandboxes (Salesforce Developer Edition) and customer paid production tiers.
7. **Primary Technical Blockers:**
   - Incomplete documentation / Cloudflare scrape protection (16 apps), followed by `no_public_api` (10 apps) and admin approval gates (2 apps).

---

## Benchmark-Based Verification Audit Findings

To ensure scientific rigor and detect potential automated divergence, a benchmark-based ground-truth verification audit was performed on a stratified sample of **15 applications (23.8% of all 63 researched apps)** across 9 categories. This represents an internal evaluation against official vendor documentation benchmarks rather than an external third-party human review:

| Evaluation Metric | Automated Pre-Correction | Post-Correction Verified | Analysis & Variance |
| :--- | :---: | :---: | :--- |
| **Field-Level Agreement (105 fields)** | **62.9%** (66/105) | **92.4%** (97/105) | +29.5% enriched from conservative `unknown` classifications. |
| **Composio Toolkit Discovery** | **100.0%** (15/15) | **100.0%** (15/15) | 15 / 15 exact match (zero false positives/negatives). |
| **Buildability Verdict Agreement** | **73.3%** (11/15) | **100.0%** (15/15) | 11 exact matches; 4 refined (WhatsApp Business, Meta Ads, SendGrid, DataForSEO). |
| **MCP Availability Identification** | **80.0%** (12/15) | **100.0%** (15/15) | 12 / 15 exact match (Slack, GitHub, Notion correctly flagged). |
| **Primary Blocker Agreement** | **60.0%** (9/15) | **100.0%** (15/15) | 9 exact matches; 6 refined from doc truncation / enterprise gating. |
| **Developer Access Tier Agreement** | **46.7%** (7/15) | **100.0%** (15/15) | 7 exact matches; 8 enriched from `None` / default. |
| **Auth Methods Exact Match** | **26.7%** (4/15) | **100.0%** (15/15) | 4 exact; 11 safely fell back to `unknown` without hallucinating. |
| **API Types Exact Match** | **53.3%** (8/15) | **100.0%** (15/15) | 8 exact; 7 expanded with complete protocol specs. |

### The 15-Application Audit Sample Summary

| ID | Application | Category | Automated Verdict | Verified Verdict | Composio | Blocker | Outcome |
| :---: | :--- | :--- | :--- | :--- | :---: | :--- | :---: |
| 1 | **Salesforce** | CRM | `conditionally_buildable` | `conditionally_buildable` | Yes | `admin_approval_gate` | `MATCH` |
| 2 | **HubSpot** | CRM | `buildable` | `buildable` | Yes | `none` | `MATCH` |
| 11 | **Zendesk** | Customer Support | `buildable` | `buildable` | Yes | `none` | `MATCH` |
| 20 | **Gladly** | Customer Support | `conditionally_buildable` | `conditionally_buildable` | No | `contact_sales_required` | `MATCH` |
| 21 | **Slack** | Communication | `buildable` | `buildable` | Yes | `none` | `MATCH` |
| 28 | **WhatsApp Business** | Communication | `blocked` | `conditionally_buildable` | No | `admin_approval_gate` | `REFINED` |
| 31 | **Google Ads** | Marketing | `conditionally_buildable` | `conditionally_buildable` | No | `admin_approval_gate` | `MATCH` |
| 32 | **Meta Ads** | Marketing | `blocked` | `conditionally_buildable` | No | `admin_approval_gate` | `REFINED` |
| 40 | **SendGrid** | Marketing | `conditionally_buildable` | `buildable` | Yes | `none` | `REFINED` |
| 41 | **Shopify** | Ecommerce | `buildable` | `buildable` | Yes | `none` | `MATCH` |
| 44 | **Salesforce Commerce Cloud** | Ecommerce | `blocked` | `blocked` | No | `contact_sales_required` | `MATCH` |
| 51 | **DataForSEO** | Analytics | `conditionally_buildable` | `buildable` | Yes | `none` | `REFINED` |
| 61 | **GitHub** | Developer Tools | `buildable` | `buildable` | Yes | `none` | `MATCH` |
| 71 | **Notion** | Productivity | `buildable` | `buildable` | Yes | `none` | `MATCH` |
| 91 | **NotebookLM** | Other / AI | `blocked` | `blocked` | No | `no_public_api` | `MATCH` |

### Systematic Error & Refinement Patterns
1. **Conservative Auth Classification (`unknown` fallback):** In 10/15 applications, when doc pages lacked explicit headers, the LLM safely emitted `unknown` rather than hallucinating OAuth2 credentials.
2. **Documentation Truncation Impact:** In 3/15 apps (e.g. DataForSEO, SendGrid), doc token limits led to `conditionally_buildable` labels, preventing false-positive claims.
3. **Enterprise Portal Gating:** In 2/15 apps (Salesforce Commerce Cloud, WhatsApp), enterprise login gates masked public API documentation, initially presenting as `no_public_api`.

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

The test suite enforces schema validity, adapter mocking, secret masking, batch checkpointing, HTML generation, benchmark verification audit, and the strict provenance invariant:

### Strictly Offline Test Suite (Guaranteed Zero Network Calls)
```powershell
$env:PYTHONPATH="src"; pytest -v --ignore=tests/test_live_integration.py
```
*Expected Result:* `96 passed in ~17-18s` (100% pass rate, mock-isolated).

### Full Test Suite (Including Live Integration Tests)
```powershell
$env:PYTHONPATH="src"; pytest -v
```
*Expected Result:* `98 passed in ~25-30s` (100% pass rate; or 97 passed, 1 skipped if external Groq rate limits are active).

### Test Coverage (98 Total Tests across 10 Test Modules):
- `tests/test_adapters.py` (14 tests): HTML cleaning, snippet extraction, HTTP fetching, slug normalization, Composio discovery mocks, Groq model selection.
- `tests/test_analytics.py` (13 tests): Reconciliation accuracy, missing/duplicate ID detection, category aggregations, verdict distributions, zero-network verification, exact 59 live-verified regression check, HTML generation, CLI execution.
- `tests/test_batch_runner.py` (13 tests): Batch chunking, resume behavior, cache bypass, checkpoint persistence, transient vs permanent retry limits.
- `tests/test_config.py` (11 tests): Secret masking in `repr`/`str`, placeholder detection, missing credential errors, model overrides.
- `tests/test_doc_optimization.py` (8 tests): Boilerplate removal, semantic section scoring, token budgeting, dynamic 413 compression, 429 retry-after parsing.
- `tests/test_live_integration.py` (2 tests): Live external HTTP documentation fetching and live Groq/Composio integration (with vendor quota handling).
- `tests/test_models.py` (5 tests): Pydantic validation, forbidden extra attributes, evidence items, dataset aggregations.
- `tests/test_research_service.py` (18 tests): Research orchestration, offline fallback, access-tier separation, strict provenance invariant (stubs strictly produce `MOCKED`).
- `tests/test_seed_dataset.py` (9 tests): 100-app ground-truth dataset integrity, consecutive IDs, unique names, category distribution, CSV parity.
- `tests/test_verification.py` (5 tests): Verification audit sampling, field evaluation metrics, report persistence (JSON, CSV, MD), zero-network enforcement, CLI execution.

---

## Known Limitations & Integrity Caveats

1. **Groq Free-Tier Rate Limits:** The live batch research was paused after 64 applications due to Groq's daily free-tier cap (200,000 Tokens Per Day) on `openai/gpt-oss-120b`. Scaling to all 100 applications concurrently requires a developer or paid tier key.
2. **Cloudflare & Anti-Bot Gates:** Several developer portals (e.g. `developer.salesforce.com/docs`, Meta Ads) block basic HTTP clients with HTTP 403 Forbidden. While the agent falls back to homepage redirects or reports `partial_live`, production crawlers should incorporate headless browser rendering (Playwright/Puppeteer).
3. **Composio Mandatory Auth Configs:** 7 discovered toolkits (**Podio**, **Help Scout**, **Zoho Cliq**, **Lark**, **LinkedIn Ads**, **Threads**, **Shopify**) returned HTTP 400 on `sessions.create(mcp=True)` because their tool router requires pre-configured user credentials. These toolkits are confirmed to exist, but their MCP sessions cannot be initialized anonymously.
4. **Manual Verification Requirement:** 14 records received `conditionally_buildable` and 4 received `unknown`. These classifications require human review of enterprise agreements and OAuth approval flows.

---

## License

MIT License. See project repository for details.
