"""
External protein interaction connector tools for ag-cli / Harvest.

Provides agent-callable tools for querying protein-protein interaction
databases. Responses are cached to disk with a 24-hour TTL to minimise
redundant API calls across sessions.

Tools:
    interactions.string_plant_ppi  -- STRING protein interaction partners for
                                      a plant gene with confidence scores
"""

from __future__ import annotations

from ct.tools import registry


@registry.register(
    name="interactions.string_plant_ppi",
    description=(
        "Query STRING for protein-protein interactions for a plant gene. "
        "Returns interaction partners with confidence scores."
    ),
    category="interactions",
    parameters={
        "gene": "Gene symbol or locus code (e.g. 'FLC', 'AT5G10140', 'OsMADS51')",
        "species": "Species name or taxon ID (default: Arabidopsis thaliana)",
        "min_score": "Minimum interaction confidence 0-1 (default 0.4)",
        "limit": "Max interaction partners to return (default 20, max 50)",
    },
    usage_guide=(
        "Retrieve protein interaction partners and confidence scores for a plant gene "
        "from STRING. Use for target validation, pathway context, and identifying "
        "functional partners. If a gene symbol returns no results, try the locus code "
        "instead (e.g. AT5G10140 for FLC)."
    ),
)
def string_plant_ppi(
    gene: str,
    species: str = "Arabidopsis thaliana",
    min_score: float = 0.4,
    limit: int = 20,
    **kwargs,
) -> dict:
    """Query the STRING database for protein interaction partners of a plant gene.

    Performs two sequential STRING API calls:
      1. ``get_string_ids``     — resolves the gene symbol/locus to a STRING ID.
      2. ``interaction_partners`` — fetches scored interaction partners.

    Results are cached to disk at ``~/.ct/cache/string_ppi/`` with a 24-hour
    TTL so that repeated queries for the same gene/species do not incur
    additional network latency.

    Args:
        gene: Gene symbol or locus code (e.g. 'FLC', 'AT5G10140').
        species: Species name, abbreviation, or NCBI taxon ID string.
            Unknown species return a structured error without querying STRING.
        min_score: Minimum combined interaction score on a 0–1 scale
            (STRING stores scores as integers 0–1000; this value is converted
            internally). Default 0.4.
        limit: Maximum number of interaction partners to return. Capped at 50.

    Returns:
        dict with keys:
            summary          -- human-readable result string
            gene             -- requested gene identifier
            resolved_name    -- preferred name returned by STRING
            string_id        -- STRING identifier used for the query
            species          -- canonical binomial name
            taxon_id         -- NCBI taxon ID used
            min_score        -- effective minimum score filter applied
            interaction_count -- number of partners returned
            interactions     -- list of {partner, string_id, score} dicts
                                sorted by score descending
    """
    # Lazy imports — keep module import fast and avoid circular deps
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial
    from ct.tools.http_client import request_json
    from ct.tools._api_cache import get_cached, set_cached

    # --- Species validation -----------------------------------------------
    taxon_id = resolve_species_taxon(species)
    if taxon_id == 0:
        return {
            "summary": (
                f"Species not recognised: {species!r}. "
                "Run 'ag species list' for supported species."
            ),
            "error": f"Unknown species: {species!r}",
            "gene": gene,
            "species": species,
            "interactions": [],
        }

    binomial = resolve_species_binomial(species)

    # --- Cap limit --------------------------------------------------------
    limit = min(int(limit), 50)

    # --- Cache lookup -----------------------------------------------------
    cache_key = f"string_ppi:{taxon_id}:{gene}:{min_score}:{limit}"
    cached = get_cached("string_ppi", cache_key)
    if cached is not None:
        return cached

    # --- Step 1: Resolve gene to STRING ID --------------------------------
    ids_data, err = request_json(
        "GET",
        "https://string-db.org/api/json/get_string_ids",
        params={
            "identifiers": gene,
            "species": taxon_id,
            "limit": 1,
            "caller_identity": "ag-cli",
        },
        timeout=15,
        retries=2,
    )
    if err or not ids_data:
        return {
            "summary": (
                f"No STRING identifier found for '{gene}' in species "
                f"{binomial} (taxon {taxon_id}). "
                "Try using the locus code."
            ),
            "gene": gene,
            "species": binomial,
            "taxon_id": taxon_id,
            "interactions": [],
            "query_used": gene,
        }

    string_id = ids_data[0]["stringId"]
    preferred_name = ids_data[0].get("preferredName", gene)

    # --- Step 2: Fetch interaction partners --------------------------------
    partners_data, err = request_json(
        "GET",
        "https://string-db.org/api/json/interaction_partners",
        params={
            "identifiers": string_id,
            "species": taxon_id,
            "required_score": int(min_score * 1000),
            "limit": limit,
            "caller_identity": "ag-cli",
        },
        timeout=15,
        retries=2,
    )
    if err:
        return {
            "summary": (
                f"STRING interaction_partners request failed for '{gene}': {err}"
            ),
            "error": err,
            "gene": gene,
            "resolved_name": preferred_name,
            "string_id": string_id,
            "species": binomial,
            "taxon_id": taxon_id,
            "min_score": min_score,
            "interaction_count": 0,
            "interactions": [],
        }

    # --- Build partner list -----------------------------------------------
    partners: list[dict] = []
    for entry in (partners_data or []):
        # Determine which end is the query gene (stringId_A is typically the
        # query protein; skip self-interactions just in case).
        str_a = entry.get("stringId_A", "")
        str_b = entry.get("stringId_B", "")
        name_a = entry.get("preferredName_A", "")
        name_b = entry.get("preferredName_B", "")
        raw_score = entry.get("score", 0)
        score_float = round(raw_score / 1000, 4)

        if str_a == string_id:
            other_name = name_b
            other_id = str_b
        else:
            other_name = name_a
            other_id = str_a

        # Skip self-interactions
        if other_id == string_id:
            continue

        partners.append(
            {
                "partner": other_name,
                "string_id": other_id,
                "score": score_float,
            }
        )

    # Sort by score descending
    partners.sort(key=lambda p: p["score"], reverse=True)

    # --- Construct result -------------------------------------------------
    if partners:
        summary_text = (
            f"Found {len(partners)} interaction partner(s) for "
            f"{preferred_name} ({gene}) in {binomial} "
            f"(STRING, min_score={min_score})."
        )
    else:
        summary_text = (
            f"No interaction partners found for {preferred_name} ({gene}) "
            f"in {binomial} with score >= {min_score}."
        )

    result = {
        "summary": summary_text,
        "gene": gene,
        "resolved_name": preferred_name,
        "string_id": string_id,
        "species": binomial,
        "taxon_id": taxon_id,
        "min_score": min_score,
        "interaction_count": len(partners),
        "interactions": partners,
    }

    # --- Cache and return -------------------------------------------------
    set_cached("string_ppi", cache_key, result)
    return result
