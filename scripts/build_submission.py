"""Build and package the complete submission deliverables."""

from pathlib import Path
import shutil
import json

root = Path(__file__).resolve().parent.parent
submission_dir = root / "submission"
submission_dir.mkdir(parents=True, exist_ok=True)
records_dir = submission_dir / "records"
records_dir.mkdir(parents=True, exist_ok=True)

out_dir = root / "output"
analytics_dir = out_dir / "analytics"
results_dir = out_dir / "research_results"
verification_dir = out_dir / "verification"

# 1. Copy consolidated dataset
shutil.copy2(out_dir / "research_dataset.json", submission_dir / "research_dataset.json")

# 2. Copy all 63 records
for f in sorted(results_dir.glob("*.json")):
    shutil.copy2(f, records_dir / f.name)

# 3. Copy analytics artifacts
shutil.copy2(analytics_dir / "data_reconciliation.json", submission_dir / "data_reconciliation.json")
shutil.copy2(analytics_dir / "analytics_summary.json", submission_dir / "analytics_summary.json")
shutil.copy2(analytics_dir / "category_analysis.json", submission_dir / "category_analysis.json")
shutil.copy2(analytics_dir / "insights.json", submission_dir / "insights.json")

# 4. Copy verification artifacts
shutil.copy2(verification_dir / "verification_sample.json", submission_dir / "verification_sample.json")
shutil.copy2(verification_dir / "verification_report.json", submission_dir / "verification_report.json")
shutil.copy2(verification_dir / "verification_report.csv", submission_dir / "verification_report.csv")

print(f"Copied data artifacts. Records in submission/records: {len(list(records_dir.glob('*.json')))}")
