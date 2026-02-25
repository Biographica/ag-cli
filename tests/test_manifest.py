"""Unit tests for the dataset manifest loader (ct.data.manifest)
and the ag species list CLI command.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from ct.cli import app
from ct.data.manifest import load_manifest, manifest_species, manifest_summary


# ---------------------------------------------------------------------------
# Shared manifest data
# ---------------------------------------------------------------------------

_MANIFEST_DATA: dict[str, Any] = {
    "dataset": "Test Dataset",
    "version": "2024-01",
    "description": "A test dataset for unit testing",
    "species_covered": [
        "Arabidopsis thaliana",
        "Oryza sativa",
    ],
    "files": [
        {"name": "data.parquet", "description": "Test data", "format": "parquet"},
    ],
}


# ---------------------------------------------------------------------------
# load_manifest tests
# ---------------------------------------------------------------------------


def test_load_manifest_yaml(tmp_path: Path):
    """load_manifest returns a parsed dict when manifest.yaml is present."""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(yaml.safe_dump(_MANIFEST_DATA), encoding="utf-8")

    result = load_manifest(tmp_path)

    assert result is not None
    assert result["dataset"] == "Test Dataset"
    assert result["version"] == "2024-01"
    assert "species_covered" in result
    assert "files" in result


def test_load_manifest_json_fallback(tmp_path: Path):
    """load_manifest falls back to manifest.json when manifest.yaml is absent."""
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(_MANIFEST_DATA), encoding="utf-8")

    result = load_manifest(tmp_path)

    assert result is not None
    assert result["dataset"] == "Test Dataset"
    assert "species_covered" in result


def test_load_manifest_yaml_preferred_over_json(tmp_path: Path):
    """When both manifest.yaml and manifest.json exist, YAML is preferred."""
    yaml_data = dict(_MANIFEST_DATA)
    yaml_data["dataset"] = "From YAML"
    json_data = dict(_MANIFEST_DATA)
    json_data["dataset"] = "From JSON"

    (tmp_path / "manifest.yaml").write_text(yaml.safe_dump(yaml_data), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps(json_data), encoding="utf-8")

    result = load_manifest(tmp_path)

    assert result is not None
    assert result["dataset"] == "From YAML"


def test_load_manifest_missing_returns_none(tmp_path: Path):
    """load_manifest returns None when directory has no manifest file."""
    result = load_manifest(tmp_path)
    assert result is None


def test_load_manifest_nonexistent_dir_returns_none():
    """load_manifest returns None for a path that doesn't exist — never raises."""
    result = load_manifest(Path("/nonexistent/path/that/does/not/exist"))
    assert result is None


# ---------------------------------------------------------------------------
# manifest_species tests
# ---------------------------------------------------------------------------


def test_manifest_species():
    """manifest_species extracts the species_covered list from a manifest."""
    species = manifest_species(_MANIFEST_DATA)
    assert species == ["Arabidopsis thaliana", "Oryza sativa"]


def test_manifest_species_missing_key():
    """manifest_species returns [] when species_covered key is absent."""
    species = manifest_species({"dataset": "No species key"})
    assert species == []


def test_manifest_species_empty_list():
    """manifest_species returns [] when species_covered is an empty list."""
    species = manifest_species({"species_covered": []})
    assert species == []


# ---------------------------------------------------------------------------
# manifest_summary tests
# ---------------------------------------------------------------------------


def test_manifest_summary():
    """manifest_summary returns a formatted multi-line string."""
    summary = manifest_summary(_MANIFEST_DATA)

    assert "Test Dataset" in summary
    assert "A test dataset for unit testing" in summary
    assert "Arabidopsis thaliana" in summary
    assert "Oryza sativa" in summary
    assert "data.parquet" in summary


def test_manifest_summary_format():
    """manifest_summary produces exactly 3 lines in the standard format."""
    summary = manifest_summary(_MANIFEST_DATA)
    lines = summary.split("\n")
    # Expect: "{dataset}: {description}", "Species: ...", "Files: ..."
    assert len(lines) == 3
    assert lines[0].startswith("Test Dataset:")
    assert lines[1].startswith("Species:")
    assert lines[2].startswith("Files:")


def test_manifest_summary_missing_species():
    """manifest_summary gracefully handles absent species_covered key."""
    data = {"dataset": "Minimal", "description": "desc", "files": []}
    summary = manifest_summary(data)
    assert "Species:" in summary
    assert "(none)" in summary


def test_manifest_summary_string_files():
    """manifest_summary handles files as plain strings (not dicts)."""
    data = {
        "dataset": "StringFiles",
        "description": "test",
        "species_covered": ["Arabidopsis thaliana"],
        "files": ["counts.tsv", "metadata.csv"],
    }
    summary = manifest_summary(data)
    assert "counts.tsv" in summary
    assert "metadata.csv" in summary


# ---------------------------------------------------------------------------
# CLI: ag species list
# ---------------------------------------------------------------------------

runner = CliRunner()

# Minimal fake registry for CLI test — avoids hitting the real YAML on disk
_FAKE_REGISTRY_FOR_CLI = [
    {
        "binomial": "Arabidopsis thaliana",
        "taxon_id": 3702,
        "common_names": ["arabidopsis", "thale cress"],
        "abbreviations": ["at"],
        "genome_build": "TAIR10",
    },
    {
        "binomial": "Oryza sativa",
        "taxon_id": 4530,
        "common_names": ["rice"],
        "abbreviations": ["os"],
        "genome_build": "IRGSP-1.0",
    },
]


def test_species_list_command():
    """ag species list exits 0 and renders expected table content."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY_FOR_CLI):
        result = runner.invoke(app, ["species", "list"])

    assert result.exit_code == 0, f"Non-zero exit: {result.output}"
    assert "Arabidopsis thaliana" in result.output
    assert "Taxon ID" in result.output
    assert "3702" in result.output
    assert "TAIR10" in result.output
