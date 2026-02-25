"""Unit tests for the @validate_species decorator (ct.tools._validation).

Each test creates a minimal mock tool function, applies the decorator, and
verifies the expected behaviour.  Real manifest.yaml files (either the
tests/fixtures/plantexp fixture or tmp_path-created files) are used — the
manifest and species resolution functions are NOT mocked so the full
integration chain is exercised.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from ct.tools._validation import validate_species


# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "plantexp"

# The plantexp fixture manifest covers: ["Arabidopsis thaliana", "Oryza sativa"]


# ---------------------------------------------------------------------------
# Helper mock tools
# ---------------------------------------------------------------------------

# Mode 1: explicit dataset_dir kwarg (default decorator usage)
@validate_species()
def _mock_tool(
    gene: str = "",
    species: str = "",
    dataset_dir: str = "",
    **kwargs,
) -> dict:
    """Minimal mock tool that returns fixed data."""
    return {"summary": f"Found data for {gene}", "data": [1, 2, 3]}


# Mode 2: dataset_kwarg resolution (decorator resolves name or absolute path → dir)
@validate_species(dataset_kwarg="dataset")
def _mock_tool_with_dataset_kwarg(
    gene: str = "",
    species: str = "",
    dataset: str = "",
    **kwargs,
) -> dict:
    """Minimal mock tool using the dataset kwarg resolution mode."""
    return {"summary": f"Found data for {gene}", "data": [1, 2, 3]}


# ---------------------------------------------------------------------------
# Test 1: species IS covered → no warning
# ---------------------------------------------------------------------------

def test_species_match_no_warning():
    """species='arabidopsis' on a dataset covering Arabidopsis → no warning."""
    result = _mock_tool(gene="AT1G01010", species="arabidopsis", dataset_dir=str(_FIXTURE_DIR))

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3]
    assert "species_warning" not in result, "No warning expected when species is covered"
    assert "mismatch" not in result["summary"].lower()
    assert "warning" not in result["summary"].lower()


# ---------------------------------------------------------------------------
# Test 2: species NOT covered → warning, data still returned
# ---------------------------------------------------------------------------

def test_species_mismatch_warns_not_blocks():
    """species='zea mays' on a dataset covering Arabidopsis + rice → warning, data returned."""
    result = _mock_tool(gene="ZM00001", species="zea mays", dataset_dir=str(_FIXTURE_DIR))

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3], "Data must still be returned on mismatch"
    assert "species_warning" in result, "species_warning key must be present"
    assert "zea mays" in result["species_warning"].lower() or "mismatch" in result["species_warning"].lower()
    assert result["summary"].startswith(result["species_warning"]), (
        "Warning must be prepended to summary so agent sees it first"
    )


# ---------------------------------------------------------------------------
# Test 3: unknown species → note about registry, data returned
# ---------------------------------------------------------------------------

def test_unknown_species_proceeds_with_note():
    """species='unknown_organism' → registry note added, execution not blocked."""
    result = _mock_tool(gene="X001", species="unknown_organism", dataset_dir=str(_FIXTURE_DIR))

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3], "Data must still be returned for unknown species"
    # The decorator should note the species is not in the registry
    assert "species_warning" in result, "species_warning key expected for unregistered species"
    assert "registry" in result["species_warning"].lower() or "metadata" in result["species_warning"].lower()
    assert "returned anyway" in result["species_warning"].lower()


# ---------------------------------------------------------------------------
# Test 4: multi-species dataset, requested species IS in list → no warning
# ---------------------------------------------------------------------------

def test_multi_species_dataset_match():
    """species='rice' on a dataset covering Arabidopsis + Oryza sativa → no warning.

    'rice' must resolve to 'Oryza sativa' which IS in the covered list.
    """
    result = _mock_tool(gene="Os01g0100100", species="rice", dataset_dir=str(_FIXTURE_DIR))

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3]
    assert "species_warning" not in result, (
        "No warning expected: rice resolves to Oryza sativa which is covered"
    )


# ---------------------------------------------------------------------------
# Test 5: no manifest file → proceed silently (no warning, no error)
# ---------------------------------------------------------------------------

def test_no_manifest_proceeds_silently(tmp_path: Path):
    """dataset_dir points to empty directory (no manifest) → no species_warning."""
    # tmp_path is an empty directory — no manifest.yaml
    result = _mock_tool(gene="AT1G01010", species="arabidopsis", dataset_dir=str(tmp_path))

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3]
    assert "species_warning" not in result, "No warning expected when manifest is absent"


# ---------------------------------------------------------------------------
# Test 6: no species param → validation skipped entirely
# ---------------------------------------------------------------------------

def test_no_species_param_skips_validation():
    """No species kwarg → skip validation, return original data unchanged."""
    result = _mock_tool(gene="AT1G01010", dataset_dir=str(_FIXTURE_DIR))

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3]
    assert result["summary"] == "Found data for AT1G01010"
    assert "species_warning" not in result


# ---------------------------------------------------------------------------
# Test 7: no dataset_dir kwarg → validation skipped
# ---------------------------------------------------------------------------

def test_no_dataset_dir_skips_validation():
    """No dataset_dir kwarg → skip validation, return original data unchanged."""
    result = _mock_tool(gene="AT1G01010", species="arabidopsis")

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3]
    assert result["summary"] == "Found data for AT1G01010"
    assert "species_warning" not in result


# ---------------------------------------------------------------------------
# Test 8: empty species_covered in manifest → no warning
# ---------------------------------------------------------------------------

def test_empty_species_covered_no_warning(tmp_path: Path):
    """Manifest exists but species_covered is [] → cannot validate, no warning."""
    manifest_data = {
        "dataset": "Test",
        "description": "Empty coverage manifest",
        "species_covered": [],
    }
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(yaml.safe_dump(manifest_data), encoding="utf-8")

    result = _mock_tool(gene="AT1G01010", species="zea mays", dataset_dir=str(tmp_path))

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3]
    assert "species_warning" not in result, (
        "No warning expected when species_covered is empty (nothing to validate against)"
    )


# ---------------------------------------------------------------------------
# Test 9: dataset_kwarg resolves absolute path → manifest loaded, warning present
# ---------------------------------------------------------------------------

def test_dataset_kwarg_resolves_absolute_path(tmp_path: Path):
    """dataset=str(tmp_path) where tmp_path has manifest.yaml → warning present.

    Proves the decorator resolved the absolute path and loaded the manifest
    BEFORE the function body ran.
    """
    manifest_data = {
        "dataset": "Single-species dataset",
        "description": "Covers only Arabidopsis",
        "species_covered": ["Arabidopsis thaliana"],
    }
    (tmp_path / "manifest.yaml").write_text(yaml.safe_dump(manifest_data), encoding="utf-8")

    result = _mock_tool_with_dataset_kwarg(
        gene="ZM00001",
        species="zea mays",
        dataset=str(tmp_path),  # absolute path passed as dataset kwarg
    )

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3], "Data must still be returned"
    assert "species_warning" in result, (
        "Warning expected: decorator resolved absolute path, loaded manifest, "
        "detected mismatch (zea mays not in [Arabidopsis thaliana])"
    )


# ---------------------------------------------------------------------------
# Test 10: dataset_kwarg resolves name via Config.data.base → warning present
# ---------------------------------------------------------------------------

def test_dataset_kwarg_resolves_name_via_config(tmp_path: Path):
    """dataset='plantexp' resolved via Config.data.base → warning present.

    Proves the decorator resolved "plantexp" to data.base/plantexp/ and loaded
    the manifest before the function body ran.
    """
    # Create tmp_path/plantexp/manifest.yaml covering only Arabidopsis
    dataset_dir = tmp_path / "plantexp"
    dataset_dir.mkdir()
    manifest_data = {
        "dataset": "PlantExp (config resolution test)",
        "description": "Only Arabidopsis covered",
        "species_covered": ["Arabidopsis thaliana"],
    }
    (dataset_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest_data), encoding="utf-8")

    # Mock Config.load() to return data.base pointing at tmp_path
    mock_config = MagicMock()
    mock_config.get.return_value = str(tmp_path)  # data.base = tmp_path

    with patch("ct.agent.config.Config") as MockConfig:
        MockConfig.load.return_value = mock_config

        result = _mock_tool_with_dataset_kwarg(
            gene="ZM00001",
            species="zea mays",
            dataset="plantexp",  # relative name → resolved to tmp_path/plantexp
        )

    assert isinstance(result, dict)
    assert result["data"] == [1, 2, 3], "Data must still be returned"
    assert "species_warning" in result, (
        "Warning expected: decorator resolved 'plantexp' → data.base/plantexp/, "
        "loaded manifest, detected mismatch (zea mays not in [Arabidopsis thaliana])"
    )
