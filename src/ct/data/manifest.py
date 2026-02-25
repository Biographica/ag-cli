"""
Dataset manifest loader for ag-cli / Harvest.

Provides a lightweight convention for dataset directories: a ``manifest.yaml``
(or ``manifest.json``) file at the root of a dataset directory describes the
dataset's contents, species coverage, and file inventory.  This lets the agent
discover what data is available before loading any files.

Functions:
    load_manifest(dataset_dir)  -- loads manifest.yaml/.json or returns None
    manifest_species(manifest)  -- extracts species_covered list
    manifest_summary(manifest)  -- returns human-readable summary string
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manifest(dataset_dir: Path) -> dict[str, Any] | None:
    """Load a dataset manifest from *dataset_dir*.

    Tries ``manifest.yaml`` first, then ``manifest.json`` as a fallback.
    Returns ``None`` if neither file exists — never raises on missing files.

    Args:
        dataset_dir: Path to the dataset directory.

    Returns:
        Parsed manifest as a dict, or ``None`` if no manifest is found.
    """
    dataset_dir = Path(dataset_dir)

    # Try YAML first
    yaml_path = dataset_dir / "manifest.yaml"
    if yaml_path.exists():
        try:
            import yaml  # lazy import

            with open(yaml_path, encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        except Exception:
            return None

    # JSON fallback
    json_path = dataset_dir / "manifest.json"
    if json_path.exists():
        try:
            with open(json_path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None

    return None


def manifest_species(manifest: dict[str, Any]) -> list[str]:
    """Extract the list of species covered by the dataset.

    Args:
        manifest: Parsed manifest dict (as returned by :func:`load_manifest`).

    Returns:
        List of species strings from the ``species_covered`` key.
        Returns an empty list if the key is absent or empty.
    """
    return list(manifest.get("species_covered", []) or [])


def manifest_summary(manifest: dict[str, Any]) -> str:
    """Return a human-readable summary of a dataset manifest.

    Format::

        {dataset}: {description}
        Species: {comma-separated species}
        Files: {comma-separated filenames}

    Args:
        manifest: Parsed manifest dict (as returned by :func:`load_manifest`).

    Returns:
        Multi-line summary string.
    """
    dataset = manifest.get("dataset", "(unknown dataset)")
    description = manifest.get("description", "")
    species = manifest_species(manifest)
    files_list = manifest.get("files", [])

    # Extract file names — support both plain strings and dicts with a "name" key
    file_names: list[str] = []
    for f in files_list:
        if isinstance(f, dict):
            file_names.append(f.get("name", str(f)))
        else:
            file_names.append(str(f))

    species_str = ", ".join(species) if species else "(none)"
    files_str = ", ".join(file_names) if file_names else "(none)"

    lines = [
        f"{dataset}: {description}",
        f"Species: {species_str}",
        f"Files: {files_str}",
    ]
    return "\n".join(lines)
