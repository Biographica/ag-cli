"""
YAML-backed species resolution helper for ag-cli plant science tools.

Maps common species names, abbreviations, and binomial names to NCBI taxon IDs,
canonical binomial names, and reference genome build identifiers.

The single source of truth is src/ct/data/species_registry.yaml — all additions
and corrections should be made there.  Used by all tools that make
species-specific API calls (STRING, UniProt, Ensembl, MyGene, etc.).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Registry path — relative to this module's location
# ---------------------------------------------------------------------------

_REGISTRY_PATH = Path(__file__).parent.parent / "data" / "species_registry.yaml"

# Default plant species (the model plant)
_DEFAULT_TAXON: int = 3702
_DEFAULT_BINOMIAL: str = "Arabidopsis thaliana"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_registry() -> list[dict[str, Any]]:
    """Load and return the species list from the YAML registry.

    Cached after first call — the file is read once per process lifetime.
    """
    import yaml  # lazy import to avoid import-time overhead

    with open(_REGISTRY_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data.get("species", [])


@lru_cache(maxsize=1)
def _build_lookup() -> dict[str, tuple[int, str, str]]:
    """Build and return a normalised lookup dict from the registry.

    Maps every lowercase key (binomial, common names, abbreviations) to a
    ``(taxon_id, binomial, genome_build)`` tuple.  The result is cached.
    """
    lookup: dict[str, tuple[int, str, str]] = {}

    for entry in _load_registry():
        taxon_id: int = entry["taxon_id"]
        binomial: str = entry["binomial"]
        genome_build: str = entry.get("genome_build", "")
        value = (taxon_id, binomial, genome_build)

        # Canonical binomial (lowercase)
        lookup[binomial.lower()] = value

        # Common names (already lowercase in YAML, but normalise anyway)
        for name in entry.get("common_names", []):
            lookup[" ".join(name.lower().split())] = value

        # Abbreviations (lowercase)
        for abbrev in entry.get("abbreviations", []):
            lookup[abbrev.lower()] = value

    return lookup


# ---------------------------------------------------------------------------
# Public API — signatures are IDENTICAL to the previous in-memory version
# ---------------------------------------------------------------------------


def resolve_species_taxon(species: str, default_taxon: int = _DEFAULT_TAXON) -> int:
    """Resolve a species string to its NCBI taxon ID.

    Handles:
    - Numeric taxon ID strings (passed through as int)
    - Common names: 'rice', 'maize', 'arabidopsis', 'human', etc.
    - Abbreviations: 'at', 'os', 'zm', 'hs', 'mm', etc.
    - Canonical binomial names: 'Arabidopsis thaliana', 'Oryza sativa', etc.
    - None / empty string: returns default_taxon

    Args:
        species: Species name, abbreviation, or taxon ID string.
        default_taxon: Taxon ID to return when species is unknown or empty.
            Defaults to 3702 (Arabidopsis thaliana).

    Returns:
        NCBI taxon ID as an integer.
    """
    if not species:
        return default_taxon

    s = str(species).strip()

    # Numeric passthrough (e.g. "9606", "3702")
    if s.isdigit():
        return int(s)

    # Normalise for lookup: lowercase, collapse internal whitespace
    key = " ".join(s.lower().split())

    entry = _build_lookup().get(key)
    if entry is not None:
        return entry[0]

    return default_taxon


def resolve_species_binomial(species: str, default: str = _DEFAULT_BINOMIAL) -> str:
    """Resolve a species string to a canonical binomial name.

    Handles the same input forms as resolve_species_taxon.

    Args:
        species: Species name, abbreviation, or taxon ID string.
        default: Canonical binomial to return when species is unknown or empty.
            Defaults to 'Arabidopsis thaliana'.

    Returns:
        Canonical binomial name as stored in the registry
        (e.g. 'Oryza sativa').  Exact casing is preserved — Ensembl URL
        construction relies on lowercase conversion of this value.
    """
    if not species:
        return default

    s = str(species).strip()

    # Numeric taxon ID — reverse lookup
    if s.isdigit():
        taxon_id = int(s)
        for _value in _build_lookup().values():
            if _value[0] == taxon_id:
                return _value[1]
        return default

    key = " ".join(s.lower().split())
    entry = _build_lookup().get(key)
    if entry is not None:
        return entry[1]

    return default


def resolve_species_ensembl_name(species: str, default: str = "arabidopsis_thaliana") -> str:
    """Resolve a species string to the Ensembl REST API species path component.

    Ensembl uses lowercase binomial names with underscores, e.g.:
      'arabidopsis_thaliana', 'oryza_sativa', 'homo_sapiens'

    Args:
        species: Species name, abbreviation, or taxon ID string.
        default: Ensembl species name to use when species is unknown.

    Returns:
        Lowercase underscore-separated species name for Ensembl REST URLs.
    """
    binomial = resolve_species_binomial(species)
    return binomial.lower().replace(" ", "_")


def resolve_species_genome_build(species: str, default: str = "") -> str:
    """Resolve a species string to its reference genome build identifier.

    Args:
        species: Species name, abbreviation, or taxon ID string.
        default: Value to return when species is unknown or has no build set.
            Defaults to empty string.

    Returns:
        Genome build string (e.g. 'TAIR10', 'IRGSP-1.0') or *default* if
        the species is unknown or its genome_build field is empty.
    """
    if not species:
        return default

    s = str(species).strip()

    if s.isdigit():
        taxon_id = int(s)
        for _value in _build_lookup().values():
            if _value[0] == taxon_id:
                build = _value[2]
                return build if build else default
        return default

    key = " ".join(s.lower().split())
    entry = _build_lookup().get(key)
    if entry is not None:
        build = entry[2]
        return build if build else default

    return default


def list_all_species() -> list[dict[str, Any]]:
    """Return all species entries from the registry as a list of dicts.

    Each dict has the keys: binomial, taxon_id, common_names, abbreviations,
    genome_build, and optionally notes.

    Used by the ``ag species list`` CLI command.

    Returns:
        List of species dicts in registry order.
    """
    return list(_load_registry())
