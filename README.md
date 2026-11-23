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
- **LLM Provider:** [Groq API](https://console.groq.com) (free tier: `llama-3.3-70b-versatile`)
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
│   ├── raw/                  # Raw crawl data and scraped documentation
│   └── processed/            # Verified structured dataset (JSON/CSV)
├── docs/                     # Architectural specs and documentation
├── output/                   # Final reports and generated HTML case study
├── src/
│   └── research_agent/
│       ├── __init__.py       # Package definition
│       ├── config.py         # Secure environment settings & credential validation
│       └── models.py         # Pydantic schemas, classification enums, datasets
└── tests/
    ├── __init__.py           # Test suite marker
    ├── test_config.py        # Settings validation & secret masking tests
    └── test_models.py        # Pydantic model validation & aggregation tests
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

### 6. Validate Installation

Run the test suite to verify configuration loading and data models:

```powershell
$env:PYTHONPATH="src"; pytest -v
```

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

### Planned Milestones
- **Milestone 3:** Groq LLM integration & Composio tool/MCP research execution agent.
- **Milestone 4:** Full batch research execution & structured data extraction (`data/processed/`).
- **Milestone 5:** Human verification of representative sample (pre/post-audit accuracy evaluation).
- **Milestone 6:** Analytics generation (Pandas) & standalone interactive HTML case study report (`output/`).

---

## License

MIT License. See project files for details.
