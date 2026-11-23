# Composio SaaS Research Agent — Offline Reproducibility Guide

This guide provides step-by-step instructions to reproduce all analytics, data reconciliation, category statistics, ground-truth verification audit reports, and the interactive HTML case study **100% offline without live external API keys**.

---

## 1. System Requirements & Environment Setup

- **Python Version:** Python 3.11, 3.12, or 3.13
- **Operating System:** Windows, macOS, or Linux
- **External Dependencies:** None required for offline evaluation; all dependencies are self-contained in `requirements.txt`.

### Step 1: Clone and Set Up Virtual Environment

```bash
# Clone the repository
git clone https://github.com/Mahaprasadnanda/composio-research-agent.git
cd composio-research-agent

# Create and activate virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"

# On macOS/Linux:
source .venv/bin/activate
export PYTHONPATH="src"

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Reproducing Data Reconciliation & Analytics (Offline)

The analytics engine processes the 63 researched applications, calculates category-level matrices, and generates the responsive HTML dashboard completely offline.

```bash
# Run the analytics command
python -m research_agent.cli analytics
```

### Generated Artifacts:
- `output/analytics/data_reconciliation.json` — 100% cross-source dataset reconciliation.
- `output/analytics/analytics_summary.json` — High-level KPIs and metric distributions.
- `output/analytics/category_analysis.json` — 10-category breakdown matrix with zero double-counting.
- `output/analytics/insights.json` — Structured empirical findings for Questions 1–9.
- `reports/case_study.html` — Self-contained interactive report with embedded JSON.
- `reports/assets/styles.css` & `reports/assets/dashboard.js` — Offline presentation assets.

---

## 3. Reproducing the Benchmark-Based Ground-Truth Verification Audit (Offline)

The verification audit inspects the stratified 15-application sample against curated official vendor documentation benchmarks and developer portal references, computing pre- and post-correction accuracy metrics. This audit represents an internal benchmark-grounded evaluation rather than an external third-party human review.

```bash
# Run the verification audit command
python -m research_agent.cli verify
```

### Generated Artifacts:
- `output/verification/verification_sample.json` — The 15 selected audit applications.
- `output/verification/verification_report.json` — Complete field-by-field audit comparisons.
- `output/verification/verification_report.csv` — Spreadsheet tabular matrix (105 field evaluations).
- `docs/verification_audit_summary.md` — Executive Markdown summary of audit results.

---

## 4. Running the Automated Test Suite

The repository contains a 98-test automated suite covering data models, configuration safety, adapters, HTML preprocessing/token budgeting, batch orchestration, analytical reporting, and verification audits.

### Option A: Strictly Offline Test Suite (Guaranteed Zero Network Calls)
96 of the 98 tests run with strict mock isolation, guaranteeing zero outbound HTTP network calls:

```bash
# Execute the offline unit test suite
pytest -v --ignore=tests/test_live_integration.py
```

**Expected Result:**
```
96 passed in ~17-18s (100% pass rate)
```

### Option B: Full Test Suite (Including Live Integration Tests)
The full suite includes 2 integration tests in `tests/test_live_integration.py`:
- `test_documentation_adapter_live_fetching_accessible_public_site`: performs a real HTTP GET request to `https://httpbin.org/html` to test live documentation scraping.
- `test_live_groq_and_composio_research`: performs live end-to-end research on GitHub (ID 61) using real Groq and Composio APIs when valid credentials exist in `.env` (skips cleanly if credentials are missing or if external rate limits/429 occur).

```bash
# Execute the full pytest suite
pytest -v
```

**Expected Result:**
```
98 passed in ~25-30s (100% pass rate)
```
*(Note: If external Groq API rate limits are active, `test_live_groq_and_composio_research` will skip with `97 passed, 1 skipped`).*

---

## 5. Viewing the Interactive Case Study

Open `reports/case_study.html` in any modern web browser:

```powershell
# On Windows:
Start-Process "reports\case_study.html"

# On macOS:
open reports/case_study.html

# On Linux:
xdg-open reports/case_study.html
```

The report is completely standalone: it contains all analytics data inline in an `<script id="analytics-data">` element and requires no internet connection, external CDNs, or active local web servers.

---

## 6. Optional: Resuming Live Batch Research (Requires API Keys)

To resume live research for remaining unattempted applications (once Groq token quotas reset or using a paid dev-tier key):

1. Populate `.env`:
   ```env
   GROQ_API_KEY=gsk_...
   COMPOSIO_API_KEY=comp_...
   GROQ_MODEL=openai/gpt-oss-120b
   ```
2. Run batch execution with caching enabled:
   ```bash
   python -m research_agent.cli batch --batch-size 10 --resume --delay 1.0
   ```
