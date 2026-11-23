"""Unit tests validating ground-truth seed dataset integrity for all 100 applications."""

import csv
import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

from research_agent.config import PROJECT_ROOT
from research_agent.models import (
    OriginalCategory,
    ResearchStatus,
    SeedAppRecord,
    SeedDataset,
)

SEED_JSON_PATH = PROJECT_ROOT / "data" / "raw" / "seed_apps.json"
SEED_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "seed_apps.csv"


@pytest.fixture(scope="module")
def seed_data():
    """Load and return raw seed dataset JSON content."""
    assert SEED_JSON_PATH.exists(), f"Missing required file: {SEED_JSON_PATH}"
    with open(SEED_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_seed_json_structure_and_metadata(seed_data):
    """Verify top-level metadata and app array existence."""
    assert "total_apps" in seed_data
    assert seed_data["total_apps"] == 100
    assert "apps" in seed_data
    assert isinstance(seed_data["apps"], list)
    assert len(seed_data["apps"]) == 100


def test_seed_dataset_unique_consecutive_ids(seed_data):
    """Ensure all application IDs are strictly unique and span 1 to 100 consecutively."""
    ids = [app["id"] for app in seed_data["apps"]]
    assert len(ids) == 100
    assert len(set(ids)) == 100
    assert sorted(ids) == list(range(1, 101))


def test_seed_dataset_unique_application_names(seed_data):
    """Ensure all 100 application names are unique without duplicates."""
    names = [app["name"].strip() for app in seed_data["apps"]]
    assert len(names) == 100
    assert len(set(names)) == 100


def test_seed_dataset_category_distribution(seed_data):
    """Ensure all 10 official categories contain exactly 10 applications each."""
    expected_categories = {c.value for c in OriginalCategory}
    assert len(expected_categories) == 10

    counts = {}
    for app in seed_data["apps"]:
        cat = app["category"]
        assert cat in expected_categories, f"Unexpected category: {cat}"
        counts[cat] = counts.get(cat, 0) + 1

    assert len(counts) == 10
    for cat, count in counts.items():
        assert count == 10, f"Category '{cat}' has {count} apps; expected exactly 10"


def test_seed_dataset_valid_website_urls(seed_data):
    """Verify website fields are valid HTTP/HTTPS URLs with valid netloc domains."""
    for app in seed_data["apps"]:
        url = app["website"]
        assert url.startswith(("http://", "https://")), f"Invalid URL scheme for {app['name']}: {url}"
        parsed = urlparse(url)
        assert parsed.netloc, f"Missing netloc in website URL for {app['name']}: {url}"
        assert "." in parsed.netloc, f"Invalid domain name for {app['name']}: {url}"


def test_seed_dataset_all_records_initially_pending(seed_data):
    """Verify all records are initialized with research_status 'pending'."""
    for app in seed_data["apps"]:
        assert app["research_status"] == ResearchStatus.PENDING.value
        assert app["research_status"] == "pending"


def test_seed_dataset_required_fields_present_and_non_empty(seed_data):
    """Verify every record has id, name, category, website, and documentation_hint."""
    for app in seed_data["apps"]:
        assert isinstance(app["id"], int)
        assert app["name"].strip(), f"Empty name for record {app['id']}"
        assert app["category"].strip(), f"Empty category for record {app['id']}"
        assert app["website"].strip(), f"Empty website for record {app['id']}"
        assert app["documentation_hint"].strip(), f"Empty documentation_hint for record {app['id']}"


def test_seed_dataset_loads_through_pydantic_model(seed_data):
    """Verify dataset deserializes cleanly into typed Pydantic SeedDataset model."""
    dataset = SeedDataset.model_validate(seed_data)
    assert len(dataset.apps) == 100
    # Run model's built-in strict verification
    dataset.validate_dataset_integrity()

    distribution = dataset.category_distribution()
    assert len(distribution) == 10
    for cat_name, count in distribution.items():
        assert count == 10


def test_seed_apps_csv_parity(seed_data):
    """Verify CSV export exists and has exact 1:1 parity with seed_apps.json."""
    assert SEED_CSV_PATH.exists(), f"Missing required CSV export: {SEED_CSV_PATH}"
    with open(SEED_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 100
    for json_app, csv_row in zip(seed_data["apps"], rows):
        assert str(json_app["id"]) == csv_row["id"]
        assert json_app["name"] == csv_row["name"]
        assert json_app["category"] == csv_row["category"]
        assert json_app["website"] == csv_row["website"]
        assert json_app["documentation_hint"] == csv_row["documentation_hint"]
        assert json_app["research_status"] == csv_row["research_status"]
