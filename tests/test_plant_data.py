"""
Tests for plant data tools: data.list_datasets and data.load_expression.

Uses pytest's tmp_path fixture to generate synthetic parquet/CSV data
dynamically — no real datasets required.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from ct.tools import PLANT_SCIENCE_CATEGORIES, _TOOL_MODULES
from ct.tools.plant_data import list_datasets, load_expression


# ---------------------------------------------------------------------------
# Test data factory
# ---------------------------------------------------------------------------


def _create_test_dataset(path: Path) -> None:
    """Create a minimal synthetic dataset in *path* for testing.

    Writes:
    - expression_matrix.parquet  (20 rows, 4 genes, 5 tissues each)
    - manifest.yaml              (Arabidopsis + Oryza sativa coverage)
    """
    path.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        {
            "gene_id": (
                ["AT1G65480"] * 5
                + ["Os01g0100100"] * 5
                + ["AT5G10140"] * 5
                + ["Zm00001d012345"] * 5
            ),
            "sample_id": [f"SRR{i:05d}" for i in range(20)],
            "tpm": [
                # AT1G65480
                100.0,
                50.0,
                200.0,
                75.0,
                150.0,
                # Os01g0100100
                80.0,
                120.0,
                60.0,
                90.0,
                30.0,
                # AT5G10140
                10.0,
                5.0,
                20.0,
                8.0,
                15.0,
                # Zm00001d012345
                300.0,
                250.0,
                400.0,
                180.0,
                220.0,
            ],
            "tissue": (
                ["leaf", "root", "flower", "seed", "stem"] * 4
            ),
            "species": (
                ["Arabidopsis thaliana"] * 5
                + ["Oryza sativa"] * 5
                + ["Arabidopsis thaliana"] * 5
                + ["Zea mays"] * 5
            ),
            "study": ["GSE12345"] * 20,
        }
    )
    df.to_parquet(path / "expression_matrix.parquet", index=False)

    manifest = {
        "dataset": "Test PlantExp",
        "description": "Synthetic tissue-level expression data for testing",
        "species_covered": ["Arabidopsis thaliana", "Oryza sativa"],
        "files": [
            {"name": "expression_matrix.parquet", "format": "parquet"},
            {"name": "sample_metadata.csv", "format": "csv"},
        ],
    }
    with open(path / "manifest.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(manifest, fh)


# ---------------------------------------------------------------------------
# data.list_datasets tests
# ---------------------------------------------------------------------------


def test_list_datasets_with_manifest(tmp_path: Path) -> None:
    """list_datasets returns summary and dataset list when manifest exists."""
    ds_dir = tmp_path / "plantexp"
    _create_test_dataset(ds_dir)

    result = list_datasets(data_root=str(tmp_path))

    assert "summary" in result
    assert "datasets" in result
    assert len(result["datasets"]) == 1
    # Summary should mention the dataset
    assert "plantexp" in result["summary"].lower() or "Test PlantExp" in result["summary"]


def test_list_datasets_empty_dir(tmp_path: Path) -> None:
    """list_datasets handles an empty data root without error."""
    result = list_datasets(data_root=str(tmp_path))

    assert "summary" in result
    assert isinstance(result["datasets"], list)
    assert len(result["datasets"]) == 0


def test_list_datasets_no_dir(tmp_path: Path) -> None:
    """list_datasets handles a non-existent path gracefully."""
    non_existent = tmp_path / "does_not_exist"
    result = list_datasets(data_root=str(non_existent))

    assert "summary" in result
    assert "No data directory found" in result["summary"]
    # No crash — result is a valid dict
    assert isinstance(result, dict)


def test_list_datasets_dir_without_manifest(tmp_path: Path) -> None:
    """list_datasets lists directories without manifests with a note."""
    no_manifest_dir = tmp_path / "raw_data"
    no_manifest_dir.mkdir()
    (no_manifest_dir / "some_file.txt").write_text("hello")

    result = list_datasets(data_root=str(tmp_path))

    assert "summary" in result
    assert len(result["datasets"]) == 1
    # The directory name (not a manifest dict) is returned as a string
    assert result["datasets"][0] == "raw_data"
    assert "No manifest" in result["summary"]


# ---------------------------------------------------------------------------
# data.load_expression tests
# ---------------------------------------------------------------------------


def test_load_expression_finds_gene(tmp_path: Path) -> None:
    """load_expression returns data for a gene that exists in the parquet."""
    ds_dir = tmp_path / "plantexp"
    _create_test_dataset(ds_dir)

    result = load_expression(
        gene="AT1G65480",
        species="Arabidopsis thaliana",
        dataset=str(ds_dir),
    )

    assert "summary" in result
    assert result["n_samples"] > 0
    assert isinstance(result["expression"], list)
    assert len(result["expression"]) > 0
    assert result["gene"] == "AT1G65480"


def test_load_expression_gene_not_found(tmp_path: Path) -> None:
    """load_expression returns n_samples=0 for an unknown gene."""
    ds_dir = tmp_path / "plantexp"
    _create_test_dataset(ds_dir)

    result = load_expression(
        gene="NONEXISTENT_GENE_XYZ",
        species="Arabidopsis thaliana",
        dataset=str(ds_dir),
    )

    assert "summary" in result
    assert result["n_samples"] == 0
    assert result["expression"] == []


def test_load_expression_tissue_filter(tmp_path: Path) -> None:
    """load_expression respects the tissue filter."""
    ds_dir = tmp_path / "plantexp"
    _create_test_dataset(ds_dir)

    result = load_expression(
        gene="AT1G65480",
        species="Arabidopsis thaliana",
        dataset=str(ds_dir),
        tissue="leaf",
    )

    assert result["n_samples"] > 0
    # Only leaf tissue should be returned
    for row in result["expression"]:
        assert row["tissue"] == "leaf"


def test_load_expression_default_species_no_warning(tmp_path: Path) -> None:
    """load_expression with no explicit species argument returns data without species_warning.

    The default value 'Arabidopsis thaliana' (space form) must match the YAML
    registry key so @validate_species resolves it correctly and emits NO warning.
    """
    ds_dir = tmp_path / "plantexp"
    _create_test_dataset(ds_dir)

    # Call WITHOUT explicit species — relies entirely on the default parameter value
    result = load_expression(gene="AT1G65480", dataset=str(ds_dir))

    assert result["n_samples"] > 0, "Expected data to be returned for AT1G65480"
    assert "species_warning" not in result, (
        "Expected NO species_warning when using the default species 'Arabidopsis thaliana'. "
        f"Got: {result.get('species_warning')}"
    )


def test_load_expression_species_mismatch_warns(tmp_path: Path) -> None:
    """Species mismatch on load_expression injects species_warning into result.

    The dataset manifest covers Arabidopsis + Oryza sativa.
    Requesting 'zea mays' (maize) triggers the @validate_species decorator
    warning — but data is still returned.
    """
    ds_dir = tmp_path / "plantexp"
    _create_test_dataset(ds_dir)

    result = load_expression(
        gene="Zm00001d012345",
        species="zea mays",
        dataset=str(ds_dir),
    )

    # Data is returned — never blocked
    assert "summary" in result
    # Warning is injected by the decorator
    assert "species_warning" in result, (
        "Expected 'species_warning' key from @validate_species decorator — "
        "mismatch between 'Zea mays' and manifest coverage "
        "[Arabidopsis thaliana, Oryza sativa] should trigger a warning."
    )
    # Warning text explains the mismatch
    warning = result["species_warning"]
    assert "mismatch" in warning.lower() or "not" in warning.lower()


def test_load_expression_data_not_found(tmp_path: Path) -> None:
    """load_expression returns an error message when parquet is absent."""
    empty_dir = tmp_path / "empty_dataset"
    empty_dir.mkdir()

    result = load_expression(
        gene="AT1G65480",
        species="Arabidopsis thaliana",
        dataset=str(empty_dir),
    )

    assert "summary" in result
    assert "ag data pull" in result["summary"] or "not found" in result["summary"].lower()
    assert result["n_samples"] == 0


def test_load_expression_case_insensitive_gene(tmp_path: Path) -> None:
    """load_expression matches gene IDs case-insensitively."""
    ds_dir = tmp_path / "plantexp"
    _create_test_dataset(ds_dir)

    result_upper = load_expression(
        gene="AT1G65480",
        species="Arabidopsis thaliana",
        dataset=str(ds_dir),
    )
    result_lower = load_expression(
        gene="at1g65480",
        species="Arabidopsis thaliana",
        dataset=str(ds_dir),
    )

    assert result_upper["n_samples"] == result_lower["n_samples"]
    assert result_upper["n_samples"] > 0


# ---------------------------------------------------------------------------
# Registry / category tests
# ---------------------------------------------------------------------------


def test_data_category_in_allowlist() -> None:
    """'data' category is visible to the plant science agent."""
    assert "data" in PLANT_SCIENCE_CATEGORIES, (
        "'data' must be in PLANT_SCIENCE_CATEGORIES so data.* tools are "
        "exposed at the MCP layer."
    )


def test_plant_data_module_in_tool_modules() -> None:
    """'plant_data' module is in _TOOL_MODULES for auto-registration."""
    assert "plant_data" in _TOOL_MODULES, (
        "'plant_data' must be in _TOOL_MODULES so the tools auto-register "
        "on import."
    )
