"""
Interim species resolution helper for ag-cli plant science tools.

Maps common species names, abbreviations, and binomial names to NCBI taxon IDs
and canonical binomial names. Used by all tools that make species-specific API
calls (STRING, UniProt, Ensembl, MyGene, etc.).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Taxon map: maps lowercase key to (taxon_id, canonical_binomial)
# Keys include: canonical binomial, common names, abbreviations
# ---------------------------------------------------------------------------

_PLANT_TAXON_MAP: dict[str, tuple[int, str]] = {
    # ---- Core model plants ----
    "arabidopsis thaliana":   (3702, "Arabidopsis thaliana"),
    "arabidopsis":            (3702, "Arabidopsis thaliana"),
    "thale cress":            (3702, "Arabidopsis thaliana"),
    "at":                     (3702, "Arabidopsis thaliana"),

    # ---- Rice ----
    "oryza sativa":           (4530, "Oryza sativa"),
    "oryza sativa japonica":  (39947, "Oryza sativa"),
    "oryza sativa indica":    (39946, "Oryza sativa"),
    "rice":                   (4530, "Oryza sativa"),
    "os":                     (4530, "Oryza sativa"),

    # ---- Maize / corn ----
    "zea mays":               (4577, "Zea mays"),
    "maize":                  (4577, "Zea mays"),
    "corn":                   (4577, "Zea mays"),
    "zm":                     (4577, "Zea mays"),

    # ---- Tomato ----
    "solanum lycopersicum":   (4081, "Solanum lycopersicum"),
    "lycopersicon esculentum": (4081, "Solanum lycopersicum"),
    "tomato":                 (4081, "Solanum lycopersicum"),
    "sl":                     (4081, "Solanum lycopersicum"),

    # ---- Potato ----
    "solanum tuberosum":      (4113, "Solanum tuberosum"),
    "potato":                 (4113, "Solanum tuberosum"),
    "st":                     (4113, "Solanum tuberosum"),

    # ---- Wheat ----
    "triticum aestivum":      (4565, "Triticum aestivum"),
    "wheat":                  (4565, "Triticum aestivum"),
    "bread wheat":            (4565, "Triticum aestivum"),
    "ta":                     (4565, "Triticum aestivum"),

    # ---- Soybean ----
    "glycine max":            (3847, "Glycine max"),
    "soybean":                (3847, "Glycine max"),
    "soy":                    (3847, "Glycine max"),
    "gm":                     (3847, "Glycine max"),

    # ---- Oilseed rape / canola ----
    "brassica napus":         (3708, "Brassica napus"),
    "oilseed rape":           (3708, "Brassica napus"),
    "canola":                 (3708, "Brassica napus"),
    "rapeseed":               (3708, "Brassica napus"),
    "bn":                     (3708, "Brassica napus"),

    # ---- Tobacco ----
    "nicotiana tabacum":      (4097, "Nicotiana tabacum"),
    "tobacco":                (4097, "Nicotiana tabacum"),
    "nt":                     (4097, "Nicotiana tabacum"),

    # ---- Poplar ----
    "populus trichocarpa":    (3694, "Populus trichocarpa"),
    "black cottonwood":       (3694, "Populus trichocarpa"),
    "poplar":                 (3694, "Populus trichocarpa"),
    "pt":                     (3694, "Populus trichocarpa"),

    # ---- Barley ----
    "hordeum vulgare":        (4513, "Hordeum vulgare"),
    "barley":                 (4513, "Hordeum vulgare"),
    "hv":                     (4513, "Hordeum vulgare"),

    # ---- Sorghum ----
    "sorghum bicolor":        (4558, "Sorghum bicolor"),
    "sorghum":                (4558, "Sorghum bicolor"),
    "sb":                     (4558, "Sorghum bicolor"),

    # ---- Medicago (model legume) ----
    "medicago truncatula":    (3880, "Medicago truncatula"),
    "barrel medic":           (3880, "Medicago truncatula"),
    "medicago":               (3880, "Medicago truncatula"),
    "mt":                     (3880, "Medicago truncatula"),

    # ---- Lotus (model legume) ----
    "lotus japonicus":        (34305, "Lotus japonicus"),
    "lotus":                  (34305, "Lotus japonicus"),
    "lj":                     (34305, "Lotus japonicus"),

    # ---- Banana ----
    "musa acuminata":         (214687, "Musa acuminata"),
    "banana":                 (214687, "Musa acuminata"),

    # ---- Cassava ----
    "manihot esculenta":      (3983, "Manihot esculenta"),
    "cassava":                (3983, "Manihot esculenta"),

    # ---- Strawberry ----
    "fragaria vesca":         (57918, "Fragaria vesca"),
    "strawberry":             (57918, "Fragaria vesca"),

    # ---- Cotton ----
    "gossypium hirsutum":     (3635, "Gossypium hirsutum"),
    "cotton":                 (3635, "Gossypium hirsutum"),

    # ---- Grape ----
    "vitis vinifera":         (29760, "Vitis vinifera"),
    "grapevine":              (29760, "Vitis vinifera"),
    "grape":                  (29760, "Vitis vinifera"),

    # ---- Cross-species reference organisms (retained for interoperability) ----
    "homo sapiens":           (9606, "Homo sapiens"),
    "human":                  (9606, "Homo sapiens"),
    "hs":                     (9606, "Homo sapiens"),
    "mus musculus":           (10090, "Mus musculus"),
    "mouse":                  (10090, "Mus musculus"),
    "mm":                     (10090, "Mus musculus"),
    "rattus norvegicus":      (10116, "Rattus norvegicus"),
    "rat":                    (10116, "Rattus norvegicus"),
    "yeast":                  (559292, "Saccharomyces cerevisiae"),
    "saccharomyces cerevisiae": (559292, "Saccharomyces cerevisiae"),
    "zebrafish":              (7955, "Danio rerio"),
    "danio rerio":            (7955, "Danio rerio"),
}

# Default plant species (the model plant)
_DEFAULT_TAXON: int = 3702
_DEFAULT_BINOMIAL: str = "Arabidopsis thaliana"


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

    entry = _PLANT_TAXON_MAP.get(key)
    if entry is not None:
        return entry[0]

    # Unknown species — return default
    return default_taxon


def resolve_species_binomial(species: str, default: str = _DEFAULT_BINOMIAL) -> str:
    """Resolve a species string to a canonical binomial name.

    Handles the same input forms as resolve_species_taxon.

    Args:
        species: Species name, abbreviation, or taxon ID string.
        default: Canonical binomial to return when species is unknown or empty.
            Defaults to 'Arabidopsis thaliana'.

    Returns:
        Canonical binomial name as stored in the map (e.g. 'Oryza sativa').
    """
    if not species:
        return default

    s = str(species).strip()

    # Numeric taxon ID — reverse lookup
    if s.isdigit():
        taxon_id = int(s)
        for _key, (tid, binomial) in _PLANT_TAXON_MAP.items():
            if tid == taxon_id:
                return binomial
        return default

    key = " ".join(s.lower().split())
    entry = _PLANT_TAXON_MAP.get(key)
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
