"""Unit tests for the YAML-backed species resolution module.

All tests mock the YAML loading so they are independent of the registry file
on disk and run without any filesystem I/O beyond module import.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Synthetic registry used across all tests
# ---------------------------------------------------------------------------

_FAKE_REGISTRY = [
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
        "common_names": ["rice", "oryza sativa japonica", "oryza sativa indica"],
        "abbreviations": ["os"],
        "genome_build": "IRGSP-1.0",
    },
    {
        "binomial": "Zea mays",
        "taxon_id": 4577,
        "common_names": ["maize", "corn"],
        "abbreviations": ["zm"],
        "genome_build": "Zm-B73-REFERENCE-NAM-5.0",
    },
    {
        "binomial": "Hordeum vulgare",
        "taxon_id": 4513,
        "common_names": ["barley"],
        "abbreviations": ["hv"],
        "genome_build": "MorexV3",
    },
    {
        "binomial": "Homo sapiens",
        "taxon_id": 9606,
        "common_names": ["human"],
        "abbreviations": ["hs"],
        "genome_build": "",
    },
]


def _patch_registry(func):
    """Decorator: replace _load_registry and _build_lookup caches with fake data."""

    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import ct.tools._species as mod

        # Clear lru_cache state before each test
        mod._load_registry.cache_clear()
        mod._build_lookup.cache_clear()

        with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
            # Also need to clear _build_lookup so it uses the patched _load_registry
            mod._build_lookup.cache_clear()
            return func(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_imports():
    """Import resolution functions fresh (avoids stale module-level state)."""
    from ct.tools._species import (
        resolve_species_taxon,
        resolve_species_binomial,
        resolve_species_ensembl_name,
        resolve_species_genome_build,
        list_all_species,
    )
    return (
        resolve_species_taxon,
        resolve_species_binomial,
        resolve_species_ensembl_name,
        resolve_species_genome_build,
        list_all_species,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolve_species_taxon_by_common_name():
    """Common name 'rice' resolves to taxon 4530."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        result = mod.resolve_species_taxon("rice")

    assert result == 4530


def test_resolve_species_taxon_by_abbreviation():
    """Abbreviation 'at' resolves to taxon 3702 (Arabidopsis)."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        result = mod.resolve_species_taxon("at")

    assert result == 3702


def test_resolve_species_taxon_by_binomial():
    """Full binomial 'Arabidopsis thaliana' resolves to taxon 3702."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        result = mod.resolve_species_taxon("Arabidopsis thaliana")

    assert result == 3702


def test_resolve_species_taxon_unknown_returns_default():
    """Unknown species name returns 0 (not found), not a default species."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        result = mod.resolve_species_taxon("unknown_plant")

    assert result == 0


def test_resolve_species_taxon_numeric_passthrough():
    """A numeric string is passed through as-is without registry lookup."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        result = mod.resolve_species_taxon("9606")

    assert result == 9606


def test_resolve_species_binomial_returns_stored_casing():
    """Abbreviation 'at' resolves to 'Arabidopsis thaliana' (not title-cased variant)."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        result = mod.resolve_species_binomial("at")

    assert result == "Arabidopsis thaliana"
    # Ensure no accidental .title() transformation
    assert result != "Arabidopsis Thaliana"


def test_resolve_species_genome_build():
    """'arabidopsis' resolves to genome build 'TAIR10'."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        result = mod.resolve_species_genome_build("arabidopsis")

    assert result == "TAIR10"


def test_resolve_species_genome_build_unknown():
    """Unknown species returns empty string for genome build."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        result = mod.resolve_species_genome_build("unknown")

    assert result == ""


def test_resolve_species_genome_build_empty_field():
    """Species present in registry but with empty genome_build returns default."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        # homo sapiens has genome_build: "" in fake registry
        result = mod.resolve_species_genome_build("human")

    assert result == ""


def test_list_all_species_returns_all_entries():
    """list_all_species returns a list of dicts with expected keys."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        result = mod.list_all_species()

    assert isinstance(result, list)
    assert len(result) == len(_FAKE_REGISTRY)
    for entry in result:
        assert "binomial" in entry
        assert "taxon_id" in entry
        assert "common_names" in entry
        assert "genome_build" in entry


def test_rice_subspecies_resolve():
    """'oryza sativa japonica' resolves to taxon 4530 (or subspecies ID — must not default)."""
    import ct.tools._species as mod

    mod._load_registry.cache_clear()
    mod._build_lookup.cache_clear()

    with patch.object(mod, "_load_registry", return_value=_FAKE_REGISTRY):
        mod._build_lookup.cache_clear()
        result = mod.resolve_species_taxon("oryza sativa japonica")

    # Must resolve to a real taxon (4530 or 39947), NOT the unknown sentinel 0
    assert result in (4530, 39947), (
        f"Expected 4530 or 39947, got {result} — subspecies lookup failed"
    )
