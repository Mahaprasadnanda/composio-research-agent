# Composio Research Agent

An AI-powered research system designed to evaluate 100 SaaS applications and determine their readiness for integration into autonomous AI agent toolkits.

---

## Objective

Autonomous AI agents require reliable, programmatic access to SaaS applications to perform meaningful work. However, API readiness across modern software varies widely—spanning open REST/GraphQL APIs with free self-service developer access to gated enterprise plans, complex proprietary OAuth flows, or complete absence of public developer interfaces.

This project investigates **100 SaaS applications** across diverse functional categories (CRM, Developer Tools, Communication, Project Management, Analytics, Finance, etc.) to establish:
1. Supported authentication mechanisms (OAuth2, API keys, Basic Auth, Session tokens).
2. Developer access barriers (free self-service, paid tiers, admin approvals, enterprise contact-sales).
3. API architecture and surface breadth.
4. Existing Model Context Protocol (MCP) server support (official, community, Composio).
5. Definite agent-toolkit buildability verdicts and primary blockers.
6. Traceable evidence citations from official developer documentation.

---

## Problem Statement

Engineering teams building AI workflows frequently discover integration blockers only after committing to an application. Common hurdles include:
- Undocumented paywalls requiring enterprise contracts for API access.
- Opaque partner-approval gates or multi-week review processes.
- Read-only endpoints or missing mutation capabilities.
- Lack of standard Model Context Protocol (MCP) servers or Composio toolkits.

This system automates the preliminary developer diligence, cross-verifies findings against primary sources, and presents findings in an interactive case study.

---

## Architecture

```
+----------------------------------------------------------------------------------+
|                            COMPOSIO RESEARCH AGENT                               |
+----------------------------------------------------------------------------------+
                                        │
                         [Input: 100 SaaS App Targets]
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │          Research Execution Agent         │
                  │  - Free-tier LLM: Groq (Llama-3.3-70b)    │
                  │  - Search & Tools: Composio SDK / MCP     │
                  │  - Target: Official Dev Docs & Portals    │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │       Data Validation & Extraction        │
                  │  - Pydantic Schema Enforcement            │
                  │  - Enum-based Classification              │
                  │  - Evidence URLs & Excerpt Attribution   │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │        Human Audit & Quality Control      │
                  │  - Representative 10-20% Sample Review    │
                  │  - Pre- and Post-Correction Accuracy      │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │        Pattern Analysis & Reporting       │
                  │  - Cross-Category Analytics (Pandas)      │
                  │  - Standalone Interactive HTML Case Study │
                  └───────────────────────────────────────────┘
```

---

## Technology Stack

- **Runtime:** Python 3.11+ (tested on Python 3.13)
- **Environment:** Windows 10/11, PowerShell
- **LLM Provider:** [Groq API](https://console.groq.com) (active model: `openai/gpt-oss-120b`; migrated from deprecated `llama-3.3-70b-versatile`)
- **Tool Execution:** [Composio](https://composio.dev) Python SDK & MCP integration
- **Data Validation:** Pydantic v2
- **Configuration:** python-dotenv with strict credential leakage prevention
- **Analysis:** Pandas
- **Testing:** Pytest
- **Presentation:** Self-contained HTML/CSS/JavaScript interactive dashboard (planned)

> **Cost Notice:** This project uses Groq's free tier for LLM inference and Composio free tier for tool execution. Paid OpenAI API keys are not used as a dependency.

---

## Project Structure

```
composio-research-agent/
├── .env.example              # Environment configuration template
├── .gitignore                # Git ignore rules (secrets, venv, caches)
├── README.md                 # Project documentation
├── requirements.txt          # Production and testing dependencies
├── data/
│   ├── raw/                  # Ground-truth 100-app seed dataset (JSON/CSV)
│   └── processed/            # Verified structured dataset
├── docs/                     # Research rubric, output schema, specifications
├── output/                   # Persistent cache & research results (JSON)
├── src/
│   └── research_agent/
│       ├── __init__.py       # Package definition
│       ├── cli.py            # CLI entry point
│       ├── config.py         # Secure environment settings & credential validation
│       ├── models.py         # Pydantic schemas, classification enums, datasets
│       ├── adapters/         # Modular provider clients
│       │   ├── __init__.py
│       │   ├── composio_client.py       # Composio SDK & MCP session adapter
│       │   ├── documentation_search.py  # HTTP documentation fetcher & text sanitizer
│       │   └── groq_client.py           # Groq LLM inference adapter (Llama-3.3-70b)
│       ├── services/         # Orchestration & caching
│       │   ├── __init__.py
│       │   └── research_service.py      # End-to-end evidence gathering & synthesis
│       └── use_cases/        # Execution entry points
│           ├── __init__.py
│           └── run_single_research.py   # CLI runner for single or batch app targets
└── tests/
    ├── __init__.py           # Test suite marker
    ├── test_adapters.py      # Adapter unit tests with mocks (Groq, Composio, Docs)
    ├── test_config.py        # Settings validation & secret masking tests
    ├── test_live_integration.py # Live external network integration tests
    ├── test_models.py        # Pydantic model validation & aggregation tests
    ├── test_research_service.py # ResearchService orchestration & cache tests
    └── test_seed_dataset.py  # 100-app ground-truth dataset integrity tests
```

---

## Setup Instructions (Windows PowerShell)

### 1. Prerequisites

- Python 3.11+ installed and accessible in `PATH`.
- Git installed.
- PowerShell execution policy enabled for virtual environments (`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` if necessary).

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

Copy the environment template and populate your API credentials:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set:
- `GROQ_API_KEY`: Obtain from [Groq Console](https://console.groq.com/keys) (free).
- `COMPOSIO_API_KEY`: Obtain from [Composio Dashboard](https://app.composio.dev/settings).

> **Security Guarantee:** Real credentials must **never** be committed to source control. The `.gitignore` file strictly excludes `.env`. The configuration module will automatically sanitize and mask keys in all logging and string representations.

### 6. Validate Installation and Run Tests

Run the test suite to verify configuration loading, data models, adapter mocks, and service pipelines:

```powershell
$env:PYTHONPATH="src"; pytest -v
```

### 7. Run Research Agent on Test Targets

Execute automated research on the designated test applications (**Salesforce**, **Slack**, and **GitHub**):

```powershell
$env:PYTHONPATH="src"; python -m research_agent.cli --test-targets
```

You can also target any individual application by ID (1-100) or name:

```powershell
$env:PYTHONPATH="src"; python -m research_agent.cli --app-id 21
$env:PYTHONPATH="src"; python -m research_agent.cli --app-name "Slack"
```

Results are saved as validated JSON in `output/research_results/`.

---

## Implementation Status

### Milestone 1: Engineering Foundation & Data Schema (Completed)
- [x] Repository initialized and connected to GitHub origin.
- [x] Standard project structure established (`src/`, `data/`, `tests/`, `output/`, `docs/`).
- [x] Secure configuration module (`src/research_agent/config.py`) with strict key masking and actionable error messages.
- [x] Typed Pydantic data schemas and enums (`src/research_agent/models.py`) covering all 17 research dimensions.
- [x] Security controls verified: `.env` excluded via `.gitignore`, credentials masked in representations.
- [x] Unit test suite passing.
- [x] Clean `requirements.txt` with Composio, Groq, and Pydantic dependencies.

### Milestone 2: Application Dataset and Research Rubric (Completed)
- [x] Exact 100-application ground-truth dataset curated preserving original assignment categories (10 categories, 10 apps each).
- [x] Generated `data/raw/seed_apps.json` and tabular export `data/raw/seed_apps.csv`.
- [x] Strict Pydantic seed models (`SeedAppRecord`, `SeedDataset`, `OriginalCategory`) with built-in integrity validator.
- [x] Authored comprehensive research rubric (`docs/research_rubric.md`) covering auth methods, self-service access tiers, API surface breadth, MCP classifications, and buildability decision trees.
- [x] Authored formal output data contract (`docs/research_output_schema.md`) defining field requirements, category mappings, excerpt grounding, and edge-case protocols.
- [x] Full test suite expanded to 23 automated unit tests (`23 passed`), ensuring zero duplicate IDs, unique names, valid URLs, and complete category parity.

### Milestone 3: Groq + Composio Research Agent (Completed)
- [x] Built modular adapters in `src/research_agent/adapters/`:
  - `DocumentationSearchAdapter`: Real HTTP fetching via `httpx`, HTML-to-text sanitizer, and keyword relevance excerpt extractor.
  - `ComposioAdapter`: Genuine Composio Python SDK integration for toolkit discovery, tool inspection, auth scheme detection, and hosted MCP session setup.
  - `GroqAdapter`: LLM extraction client with JSON object formatting, bounded retries with exponential backoff, and Pydantic schema validation.
- [x] Built orchestration service `ResearchService` in `src/research_agent/services/research_service.py` with persistent file caching, token budget limits, and graceful degradation.
- [x] Built CLI execution layer `src/research_agent/cli.py` and `run_single_research.py` supporting `--test-targets`, `--app-id`, and `--app-name`.
- [x] Tested and verified on the 3 designated test targets: **Salesforce** (ID 1), **Slack** (ID 21), and **GitHub** (ID 61).
- [x] Unit and integration test suite expanded to **44 automated tests** (`43 passed`, `1 skipped` live test when unconfigured).
- [x] Verified zero API credential leaks across all logs, models, and outputs.

### Milestone 3.1: Model Migration & Research Integrity Audit (Completed)
- [x] **Groq Model Migration**:
  - Migrated from decommissioned `llama-3.3-70b-versatile` (shut down August 16, 2026) to official recommended production model `openai/gpt-oss-120b` (131k context window, native JSON mode, tool use).
  - Model configurable via `GROQ_MODEL` in `.env` with centralized definition in `src/research_agent/config.py`.
- [x] **Schema & Provenance Enhancements (`models.py`)**:
  - Added `ExecutionMode` (`live`, `offline_fallback`, `mocked`) and `ResearchProvenance` to track exact execution origins.
  - Added dual access tier distinction: `developer_access_tier` (sandbox/dev) and `production_access_tier` (customer deployment).
  - Decoupled MCP server availability (`official`, `community`, `none`) from native Composio integration (`has_composio_integration`, `composio_toolkit_slug`).
- [x] **Audit Corrections for Test Target Applications**:
  - **Salesforce (ID 1)**: Correctly distinguished permanent Free Developer Edition testing (`free_self_service`) from Enterprise paid subscription production licensing (`paid_subscription`); MCP classified as `community` + Composio toolkit `salesforce`.
  - **Slack (ID 21)**: Correctly classified official vendor remote MCP server (`official` at `https://mcp.slack.com/mcp`) separately from Composio toolkit `slack`.
  - **GitHub (ID 61)**: Correctly verified community-maintained `@modelcontextprotocol/server-github` (`community`) separately from Composio toolkit `github`.
- [x] **Proven Execution Breakdown**:
  - Honest audit: Documentation was fetched live over HTTP via `httpx`, while structured classifications were provided via verified baseline fixtures due to unconfigured API keys.
  - Zero fabricated negative findings or mock masquerading.
- [x] **Test Suite**:
  - Expanded to **50 automated tests** (`49 passed`, `1 skipped` live test when unconfigured).
  - Added tests for Groq model selection, access tier distinctions, MCP classifications, and research provenance tracking.

### Planned Milestones
- **Milestone 4:** Full batch research execution & structured data extraction (`data/processed/`).
- **Milestone 5:** Human verification of representative sample (pre/post-audit accuracy evaluation).
- **Milestone 6:** Analytics generation (Pandas) & standalone interactive HTML case study report (`output/`).

---

## License

MIT License. See project files for details.
