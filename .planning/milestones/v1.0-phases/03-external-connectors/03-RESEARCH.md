# Phase 3: External Connectors - Research

**Researched:** 2026-02-26
**Domain:** REST API connectors for biological databases (STRING, PubMed/NCBI E-utilities, Lens.org patents)
**Confidence:** HIGH for STRING and PubMed (existing code to build on); MEDIUM for Lens.org (existing code but new plant-specific tool design); HIGH for architecture patterns (directly verified from codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Query construction**
- STRING gene-to-protein ID resolution: Claude's discretion on approach (best-match vs disambiguation), keeping in mind that ID harmonization is acknowledged as hard — robust solutions are deferred to Dagster backend and advanced tooling in future iterations
- PubMed: basic query construction in the tool (species + gene), agent-driven refinement for synonyms and broader terms. Tool returns the query it used so agent can iterate
- Lens.org: two query templates — gene-focused (narrow, for specific target assessment) and landscape (broad, crop + trait combo for freedom-to-operate). Agent selects which mode fits the question
- STRING species resolution: wire through species registry for taxon IDs (Claude's discretion on exact mechanism)

**Response shaping**
- STRING PPI results: configurable `limit` and `min_score` parameters with a hard ceiling to protect the agent's context window
- PubMed citations: standard fields — title, abstract, authors, journal, year, PMID. Rich enough for agent to assess relevance without follow-up calls
- Lens.org patents: include abstract and claims information (Claude's discretion on exact balance — informed by user's experience that claims and abstract are crucial for relevance assessment)
- Summary field in tool responses: Claude's discretion, follow existing codebase conventions

**Rate limiting & authentication**
- API keys managed via ag config + environment variable fallback (config checked first, env var as fallback). Consistent with existing config pattern
- Persistent disk cache with TTL for API responses. Data in these databases changes slowly enough that 24h-ish TTL is reasonable. Survives across sessions for iterative research
- PubMed works without API key at lower rate limits; warn user once per session that rate limits may apply without a configured key
- Lens.org: tool is disabled/hidden from the agent when API token is not configured — agent shouldn't consider it as available if user hasn't set up credentials
- STRING: free API, no key needed
- Rate limit handling (retry/backoff strategy): Claude's discretion

**Error & edge cases**
- Empty results: return structured empty response with context (query used, species queried, database queried). Let the agent reason about pivots — don't hardcode alternative suggestions that may be wrong in context
- STRING species pre-validation: Claude's discretion on whether to maintain a supported-species list or let the API respond
- PubMed zero results: echo back the constructed query so agent can debug and refine

### Claude's Discretion
- STRING ID resolution approach (best-match vs multi-match handling)
- STRING species pre-validation strategy
- Lens.org response detail level (abstract always, claims on-demand or always)
- Summary field conventions
- Rate limit retry/backoff strategy
- Persistent cache implementation details (TTL values, cache location, eviction)

### Deferred Ideas (OUT OF SCOPE)
- Robust ID harmonization via pan-genome-based disambiguation (exists in other internal tools, future iteration)
- Dagster-backed connectors for production-grade data pipelines (v2+ scope)
- PatSnap-style deep patent analysis (richer than Lens.org API alone)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONN-01 | User can query STRING plant PPI networks via API for protein interaction evidence | STRING API verified: `/api/json/interaction_partners` endpoint, taxon ID via `resolve_species_taxon()`, existing `ppi_analysis` in `network.py` to build on or create new `interactions.string_plant_ppi` tool alongside |
| CONN-02 | User can search PubMed with plant-specific query construction for literature evidence | NCBI E-utilities verified: existing `pubmed_search` in `literature.py` provides base; new `literature.pubmed_plant_search` tool adds species-aware query construction and PMID abstract fetching |
| CONN-03 | User can search Lens.org for patent landscape and novelty assessment | Lens.org API verified: `/patent/search` POST endpoint with Bearer auth; new `literature.lens_patent_search` tool with gene-focused and landscape modes; MCP-layer hiding when `api.lens_key` absent |
</phase_requirements>

---

## Summary

Phase 3 implements three API connector tools for evidence gathering during plant science research workflows. The phase builds on significant existing infrastructure: `network.py` already has a fully working STRING connector (`network.ppi_analysis`), `literature.py` already has PubMed search and Lens.org patent search code, and the config system already has `api.lens_key` registered. The work is therefore largely about creating **new plant-science-specific variants** of these tools with better tool names, plant-specific query construction, species validation hooks, and a persistent disk cache layer, rather than writing API clients from scratch.

The primary technical challenges are: (1) deciding how to name and position the new tools relative to existing ones (create new `interactions.*` category tools vs. extend `network.*`), (2) implementing the persistent disk cache with TTL correctly, (3) getting the STRING gene-name-to-protein-ID resolution right for plant gene names (Arabidopsis locus codes, rice locus codes), (4) implementing the PubMed plant query builder (species + gene synonyms), and (5) implementing the Lens.org MCP-layer hiding when no API key is configured.

**Primary recommendation:** Create three new tools in appropriate categories (`interactions.string_plant_ppi`, `literature.pubmed_plant_search`, `literature.lens_patent_search`), each with a shared `_api_cache.py` helper for disk-based TTL caching, and wire into the plant science category allowlist. Reuse all existing HTTP client infrastructure from `http_client.py`.

---

## Standard Stack

### Core (all already in pyproject.toml dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | `>=0.27` | HTTP requests to all three APIs | Already declared; used by all tools via `ct.tools.http_client` wrappers |
| Standard library `json`, `hashlib`, `pathlib`, `time` | stdlib | Disk cache (JSON files keyed by hash), TTL computation | No new dependency; avoids third-party cache complexity |

### Supporting (no new dependencies required)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ct.tools.http_client.request_json` | internal | Retry/backoff HTTP wrapper with status-code handling | All external API calls |
| `ct.tools._species.resolve_species_taxon` | internal | Taxon ID from any species name/abbreviation | STRING species param |
| `ct.tools._species.resolve_species_binomial` | internal | Canonical name for error messages and cache keys | Error messages, cache keys |
| Standard library `functools.lru_cache` | stdlib | In-process cache for species registry lookup | Already in `_species.py`; not needed for API responses (use disk cache) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib JSON file cache | `diskcache`, `joblib.Memory`, `requests_cache` | stdlib is zero-dependency; diskcache requires install; joblib is ML-focused. JSON files are transparent and inspectable. Acceptable for 24h TTL on biology databases that change slowly. |
| stdlib JSON file cache | `hishel` (httpx caching middleware) | hishel is elegant but not in the project's dependency profile and adds complexity |
| Gene-name-only STRING call | `get_string_ids` pre-resolution step | Pre-resolution avoids ambiguity but adds a round-trip. Best-match (first result from STRING) is sufficient for the generalist agent given the deferred ID harmonization decision. |

**Installation:**
```bash
# No new dependencies required for the standard approach
# All required libraries already in pyproject.toml
```

---

## Architecture Patterns

### Recommended Project Structure
```
src/ct/tools/
├── interactions.py          # NEW: STRING plant PPI tool (interactions.string_plant_ppi)
├── literature.py            # EXISTING: add pubmed_plant_search, lens_patent_search
├── _api_cache.py            # NEW: shared disk TTL cache helper
└── __init__.py              # ADD "interactions" to _TOOL_MODULES and PLANT_SCIENCE_CATEGORIES
```

Cache location (consistent with AlphaFold cache pattern at `~/.ct/cache/alphafold`):
```
~/.ct/cache/
├── string_ppi/              # STRING API responses
├── pubmed/                  # PubMed E-utilities responses
└── lens_patents/            # Lens.org patent responses
```

### Pattern 1: New Tool Category (interactions)

The existing `network.ppi_analysis` tool serves the oncology domain with all seven STRING interaction score types (nscore, fscore, pscore, etc.). The plant science variant should be a new tool under a new `interactions` category to:
- Appear cleanly to the plant science agent under the `interactions` allowlist category
- Have plant-specific defaults (`species="Arabidopsis thaliana"`) and `min_score`, `limit` params
- Use `interaction_partners` endpoint (returns all partners for a gene, not just inter-query-gene edges)

Register `interactions` in `PLANT_SCIENCE_CATEGORIES` frozenset and in `_TOOL_MODULES`.

**Tool skeleton (verified against existing patterns):**
```python
# Source: src/ct/tools/network.py (existing ppi_analysis pattern)
# Source: STRING API docs https://string-db.org/help/api/

@registry.register(
    name="interactions.string_plant_ppi",
    description="Query STRING for protein-protein interactions for a plant gene",
    category="interactions",
    parameters={
        "gene": "Gene symbol or locus code (e.g. 'FLC', 'AT5G10140', 'OsMADS51')",
        "species": "Species name or taxon ID (default: Arabidopsis thaliana)",
        "min_score": "Minimum interaction confidence 0-1 (default 0.4)",
        "limit": "Max interaction partners to return (default 20, max 50)",
    },
    usage_guide="Retrieve protein interaction partners and confidence scores for a plant gene from STRING. Use for target validation, pathway context, and identifying functional partners.",
)
def string_plant_ppi(
    gene: str,
    species: str = "Arabidopsis thaliana",
    min_score: float = 0.4,
    limit: int = 20,
    **kwargs,
) -> dict:
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial
    from ct.tools.http_client import request_json
    from ct.tools._api_cache import get_cached, set_cached

    # Validate species via registry
    taxon_id = resolve_species_taxon(species)
    if taxon_id == 0:
        return {
            "error": f"Unknown species: {species!r}. Use 'ag species list'.",
            "summary": f"Species not recognised: {species!r}.",
        }

    # Cap limit to protect agent context window
    limit = min(int(limit), 50)

    # Check disk cache
    cache_key = f"string_ppi:{taxon_id}:{gene}:{min_score}:{limit}"
    cached = get_cached("string_ppi", cache_key, ttl_seconds=86400)
    if cached is not None:
        return cached

    # STRING: get_string_ids first (best-match resolution)
    # ... then interaction_partners
    # ... build result dict with summary
    # set_cached("string_ppi", cache_key, result)
    return result
```

### Pattern 2: PubMed Plant Search Tool

The existing `literature.pubmed_search` does not include the returned abstract (only title, first_author, journal, pub_date, doi). The new `literature.pubmed_plant_search` tool adds:
- Plant-specific query construction: `"{gene}" AND "{species binomial}"` with fallback `"{gene}" AND "plant"`
- Abstract retrieval via EFetch (one additional API call for up to N articles)
- Returns the constructed query in output so agent can debug and refine

NCBI E-utilities requires `tool` and `email` params to identify the caller (prevents IP blocking). The existing code passes only basic params. The new tool should include these.

**NCBI API key pattern:**
- Without key: 3 requests/second
- With key (`api.ncbi_key`): 10 requests/second
- Session-level warning when key absent: use a module-level `_warned_no_key` flag (once per process, not per call)

**New config key needed:** `api.ncbi_key` (config + env var `NCBI_API_KEY`)

```python
# Source: NCBI E-utilities docs https://www.ncbi.nlm.nih.gov/books/NBK25497/
# Pattern: existing pubmed_search in literature.py

@registry.register(
    name="literature.pubmed_plant_search",
    description="Search PubMed with plant-specific query construction (species + gene)",
    category="literature",
    parameters={
        "gene": "Gene name or symbol to search for",
        "species": "Plant species (e.g. 'Arabidopsis thaliana', 'rice'). Used to construct query.",
        "extra_terms": "Additional search terms to AND into the query",
        "max_results": "Maximum number of results (default 10)",
        "fetch_abstracts": "Whether to fetch full abstracts (default True)",
    },
    usage_guide="Search PubMed for plant gene literature. Constructs species+gene query automatically. Returns query used so agent can refine if needed.",
)
def pubmed_plant_search(
    gene: str,
    species: str = "Arabidopsis thaliana",
    extra_terms: str = "",
    max_results: int = 10,
    fetch_abstracts: bool = True,
    **kwargs,
) -> dict:
    ...
    # Construct: (gene[Title/Abstract]) AND ("Arabidopsis thaliana"[Organism])
    # Extra terms ANDed in if provided
    # Returns: {summary, query_used, total_count, articles: [{pmid, title, abstract, authors, journal, year, doi}]}
```

### Pattern 3: Lens.org Patent Search (Plant-Specific)

The existing `_patent_search_lens` private function in `literature.py` uses a simple `{"match": query}` payload. The new `literature.lens_patent_search` tool adds:
- Two query template modes: `gene` (narrow: `gene AND organism`) and `landscape` (broad: `crop AND trait`)
- Always include abstract; always include claims (the user's experience is that both are essential)
- Hide tool from MCP when `api.lens_key` is absent

**MCP hiding approach:** The clean mechanism is to check for the key at MCP tool registration time in `create_ct_mcp_server()`, or at tool-load time using a tool attribute. The simplest approach: check inside the tool function and return a clear error — but the requirement is the agent should not "consider it as available." The correct implementation is to check `api.lens_key` at MCP server build time and exclude `literature.lens_patent_search` from the `sdk_tools` list if key is absent.

```python
# In mcp_server.py create_ct_mcp_server():
# After `ensure_loaded()`, before the tool loop:
lens_key = session.config.get("api.lens_key")
if not lens_key:
    exclude_tools = exclude_tools | {"literature.lens_patent_search"}
```

**Lens API request body for plant patents:**
```python
# Source: https://docs.api.lens.org/request-patent.html

# Gene-focused mode
payload_gene = {
    "query": {
        "query_string": {
            "query": f'("{gene}") AND ("{species}")',
            "fields": ["title", "abstract", "claim"],
        }
    },
    "include": ["lens_id", "title", "abstract", "claim", "applicant",
                "publication_date", "doc_number", "jurisdiction"],
    "size": max_results,
    "sort": [{"relevance": "desc"}],
}

# Landscape mode
payload_landscape = {
    "query": {
        "query_string": {
            "query": f'("{crop}") AND ("{trait}")',
            "fields": ["title", "abstract", "claim"],
        }
    },
    "include": [...],
    "size": max_results,
}
```

### Pattern 4: Disk TTL Cache Helper (_api_cache.py)

Consistent with the AlphaFold cache pattern (`~/.ct/cache/alphafold/`). All three tools share one helper module.

```python
# src/ct/tools/_api_cache.py

import json
import hashlib
import time
from pathlib import Path

_CACHE_BASE = Path.home() / ".ct" / "cache"

def _cache_path(namespace: str, key: str) -> Path:
    """Derive a stable cache file path from namespace + key."""
    key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
    return _CACHE_BASE / namespace / f"{key_hash}.json"

def get_cached(namespace: str, key: str, ttl_seconds: int = 86400):
    """Return cached value or None if absent/expired."""
    path = _cache_path(namespace, key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data["_cached_at"] > ttl_seconds:
            return None
        return data["value"]
    except Exception:
        return None

def set_cached(namespace: str, key: str, value: dict) -> None:
    """Write value to disk cache with current timestamp."""
    path = _cache_path(namespace, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps({"_cached_at": time.time(), "value": value}))
    except Exception:
        pass  # Cache write failures are non-fatal
```

**Cache key construction:** `f"{namespace}:{taxon_id}:{gene}:{min_score}:{limit}"` — fully qualified to avoid collisions across species. Hash with SHA-256 for filesystem safety.

### Anti-Patterns to Avoid

- **Using in-process `lru_cache` for API responses:** Does not survive across sessions. The requirement is persistent disk cache. Use `_api_cache.py` pattern.
- **Blocking on missing Lens.org key inside the tool function:** The agent must never see the tool at all when the key is absent. Implement the hide at `create_ct_mcp_server()` time, not inside the function.
- **Hardcoding species-specific query terms:** All species handling goes through `resolve_species_taxon()` / `resolve_species_binomial()` — never construct URLs with hardcoded taxon IDs.
- **Returning empty list on zero results without context:** The decision is to return a structured empty response that includes the query used, species queried, and database queried. Let the agent reason about pivots.
- **Adding `interactions` to `_TOOL_MODULES` without `PLANT_SCIENCE_CATEGORIES`:** The allowlist controls what the agent sees. A module in `_TOOL_MODULES` but not in `PLANT_SCIENCE_CATEGORIES` will load but be invisible to the agent.
- **Calling STRING without `caller_identity`:** STRING docs ask for caller identity. The existing code uses `"ag-cli"`. Match this convention.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry/backoff | Custom retry loop | `ct.tools.http_client.request_json()` | Already handles retryable status codes (429, 500-504), timeout, Content-Type validation, backoff |
| Species → taxon ID | Custom mapping dict | `resolve_species_taxon(species)` from `_species.py` | YAML registry already covers all supported plant species; sentinel 0 for unknown |
| Disk cache | Custom pickle/shelve | `_api_cache.py` (JSON files) as per research recommendation | Transparent, inspectable, no extra dep |
| PubMed query normalization | Custom boolean parser | Reuse `_normalize_pubmed_query()` from `literature.py` | Already handles AND/OR/NOT uppercasing and quoted phrases |

**Key insight:** The project has invested heavily in shared infrastructure (HTTP client, species registry, tool registry, config). New tools must use these abstractions, not work around them.

---

## Common Pitfalls

### Pitfall 1: STRING Gene Name Ambiguity for Plant Genes

**What goes wrong:** STRING resolves gene names by best match. For plants, the same gene symbol (e.g. "FLC") may match poorly because STRING's identifier database is human-biased at the top of search results. Arabidopsis locus codes (AT5G10140) are more reliable but not always what the agent will use.

**Why it happens:** STRING's `network` endpoint does best-effort resolution; plant gene symbols are often non-unique.

**How to avoid:** Use the `get_string_ids` endpoint with `species` param and `limit=1` first to get the STRING ID for the gene, then pass the STRING ID to `interaction_partners`. Take the first result (best match). Document this in the tool description so the agent understands it may need to try locus codes when symbols fail.

**Warning signs:** STRING returns an empty list for `interaction_partners` when the gene name resolves to nothing. Return the query in the response so the agent can retry with a locus code.

### Pitfall 2: PubMed Query Construction Over-Specificity

**What goes wrong:** Combining gene + full species binomial + extra terms with AND returns zero results because not all papers use the canonical species name.

**Why it happens:** PubMed indexes organism names in MeSH terms; exact binomial matching differs from free-text matching.

**How to avoid:** Use the `[Organism]` field tag for species: `"Arabidopsis thaliana"[Organism]` rather than a plain text match. Include a fallback: if zero results with full species+gene, retry with just the gene and "plant" or "plants". Echo back which query succeeded.

**Warning signs:** Zero results when the gene is well-studied. The simplify_query fallback from the existing `_simplify_query()` helper applies here too.

### Pitfall 3: Lens.org Tool Appearing in Agent Context Without Key

**What goes wrong:** If the MCP tool is registered but returns an error at call time, the agent may waste turns trying the tool and failing. This is worse than not showing the tool.

**Why it happens:** Tool visibility and tool availability are separate concerns. The requirement is they must be unified.

**How to avoid:** Check `session.config.get("api.lens_key")` in `create_ct_mcp_server()` before the tool registration loop, and add `"literature.lens_patent_search"` to `exclude_tools` when absent.

**Warning signs:** Agent logs showing `literature.lens_patent_search` being called followed by an auth error.

### Pitfall 4: Cache Key Collisions Across Species

**What goes wrong:** Two queries for different species but same gene name hit the same cache entry.

**Why it happens:** Cache key doesn't include taxon ID.

**How to avoid:** Always include taxon ID in the cache key. Use resolved taxon ID (integer), not the raw species string, to normalise variations ("arabidopsis", "at", "Arabidopsis thaliana" all map to 3702).

### Pitfall 5: Missing `interactions` in PLANT_SCIENCE_CATEGORIES or _TOOL_MODULES

**What goes wrong:** Tool registers correctly but is invisible to the agent (silently filtered at MCP layer) OR module is in `PLANT_SCIENCE_CATEGORIES` but not in `_TOOL_MODULES` so it never loads.

**Why it happens:** Both lists must be kept in sync. The comment in `__init__.py` warns about this: "entry() passthrough set must include every Typer subcommand... omissions silently route to NL query mode."

**How to avoid:** Add `"interactions"` to BOTH `PLANT_SCIENCE_CATEGORIES` frozenset AND `_TOOL_MODULES` tuple in `src/ct/tools/__init__.py`. Verify with `ct tool list` after implementation.

### Pitfall 6: PubMed Rate Limit Warning — Wrong Implementation

**What goes wrong:** Warning is emitted on every call instead of once per session, creating noise in tool output that the agent sees repeatedly.

**Why it happens:** Naive implementation checks key on every call.

**How to avoid:** Use a module-level `_pubmed_rate_warned: bool = False` flag. Set it to True after first warning. The agent sees the warning once and knows to set the key if desired.

---

## Code Examples

Verified patterns from the existing codebase:

### STRING API Call (interaction_partners endpoint)

```python
# Source: Verified against https://string-db.org/help/api/ + existing network.py pattern
# Step 1: Resolve gene to STRING ID
ids_data, error = request_json(
    "GET",
    "https://string-db.org/api/json/get_string_ids",
    params={
        "identifiers": gene,
        "species": taxon_id,          # e.g. 3702 for Arabidopsis
        "limit": 1,                    # best match only
        "caller_identity": "ag-cli",
    },
    timeout=15,
    retries=2,
)
# ids_data is a list; take ids_data[0]["stringId"] as the resolved identifier

# Step 2: Fetch interaction partners
partners_data, error = request_json(
    "GET",
    "https://string-db.org/api/json/interaction_partners",
    params={
        "identifiers": string_id,      # resolved STRING ID
        "species": taxon_id,
        "required_score": int(min_score * 1000),  # STRING uses 0-1000
        "limit": limit,
        "caller_identity": "ag-cli",
    },
    timeout=15,
    retries=2,
)
```

### PubMed Plant Query Construction

```python
# Source: NCBI E-utilities docs + existing literature.py pattern
from ct.tools._species import resolve_species_binomial

binomial = resolve_species_binomial(species)  # e.g. "Arabidopsis thaliana"
if binomial:
    query = f'({gene}[Title/Abstract]) AND ("{binomial}"[Organism])'
else:
    query = f'({gene}[Title/Abstract]) AND (plant[MeSH Terms])'

if extra_terms:
    query = f"({query}) AND ({extra_terms})"

# Include NCBI tool/email params and optional API key
params = {
    "db": "pubmed",
    "term": _normalize_pubmed_query(query),  # reuse existing helper
    "retmax": max_results,
    "retmode": "json",
    "sort": "relevance",
    "tool": "ag-cli",
    "email": "research@biographica.com",
}
session = kwargs.get("_session")
if session:
    ncbi_key = session.config.get("api.ncbi_key")
    if ncbi_key:
        params["api_key"] = ncbi_key
```

### EFetch for Abstracts

```python
# Source: NCBI E-utilities docs https://www.ncbi.nlm.nih.gov/books/NBK25499/
# Fetch abstracts for retrieved PMIDs
fetch_data, error = request_json(
    "GET",
    f"{base}/efetch.fcgi",
    params={
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",  # XML for abstract parsing
        "rettype": "abstract",
    },
    timeout=30,
    retries=2,
)
# Parse XML with xml.etree.ElementTree — already used in _patent_search_epo()
```

### Lens.org Patent Search with Claims

```python
# Source: https://docs.api.lens.org/request-patent.html (verified)
payload = {
    "query": {
        "query_string": {
            "query": query_string,   # gene-focused or landscape template
            "fields": ["title", "abstract", "claim"],
        }
    },
    "include": [
        "lens_id", "title", "abstract", "claim",
        "applicant", "publication_date", "doc_number",
        "jurisdiction", "kind",
    ],
    "size": max_results,
    "sort": [{"relevance": "desc"}],
}
resp, error = request(
    "POST",
    "https://api.lens.org/patent/search",
    json=payload,
    headers={
        "Authorization": f"Bearer {lens_key}",
        "Content-Type": "application/json",
    },
    timeout=30,
    retries=2,
    raise_for_status=False,
)
```

### MCP-Layer Tool Hiding (Lens.org)

```python
# In src/ct/agent/mcp_server.py create_ct_mcp_server()
# Source: existing exclude_tools pattern in create_ct_mcp_server()

# After: ensure_loaded()
exclude_tools = set(exclude_tools or set())

# Hide lens patent tool if key not configured
lens_key = session.config.get("api.lens_key")
if not lens_key:
    exclude_tools.add("literature.lens_patent_search")
```

### Config Registration for New Keys

```python
# In src/ct/agent/config.py DEFAULTS dict:
"api.ncbi_key": None,      # NCBI E-utilities API key (optional, increases rate limit)

# In env_mappings dict:
"NCBI_API_KEY": "api.ncbi_key",

# In API_KEYS dict (for ct config keys display):
"api.ncbi_key": {
    "name": "NCBI E-utilities",
    "env_var": "NCBI_API_KEY",
    "description": "Higher rate limits for PubMed/EFetch (literature.pubmed_plant_search)",
    "url": "https://www.ncbi.nlm.nih.gov/account/",
    "free": True,
},
```

### Once-Per-Session PubMed Rate Limit Warning

```python
# In literature.py (module level)
_pubmed_rate_limit_warned: bool = False

# In pubmed_plant_search():
global _pubmed_rate_limit_warned
session = kwargs.get("_session")
ncbi_key = session.config.get("api.ncbi_key") if session else None
if not ncbi_key and not _pubmed_rate_limit_warned:
    _pubmed_rate_limit_warned = True
    # Include warning in summary but don't block execution
    rate_limit_note = (
        "Note: NCBI API key not configured — rate limited to 3 req/s. "
        "Set NCBI_API_KEY or run: ag config set api.ncbi_key <key>"
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Lens.org tiered fallback (Lens → EPO → PubMed) | Dedicated plant patent tool (Lens only, no fallback, hidden when no key) | Phase 3 decision | Simpler, agent-appropriate; EPO fallback not needed for plant patent assessment use case |
| Generic `network.ppi_analysis` (all species, all score types) | `interactions.string_plant_ppi` (plant-focused, `interaction_partners` endpoint, simpler output) | Phase 3 | Plant-appropriate defaults, better agent guidance |
| `pubmed_search` (general query, no abstract, no species) | `pubmed_plant_search` (species+gene query, abstract fetching, NCBI tool/email params) | Phase 3 | Agent gets richer context without follow-up calls |
| In-process only (lru_cache/module vars) | Persistent disk cache at `~/.ct/cache/` | Phase 3 | Research workflows span sessions; API results valid 24h |

**Deprecated/outdated in this phase:**
- The old `literature.patent_search` (with EPO fallback) remains for oncology domain use but should NOT be the tool the plant agent uses — the new `literature.lens_patent_search` is purpose-built for plant patents and is hidden when key absent.

---

## Open Questions

1. **STRING `get_string_ids` on Arabidopsis locus codes (AT*G*) vs gene symbols**
   - What we know: STRING supports locus codes for Arabidopsis (visible at `string-db.org/network/3702.AT1G60920.1`). The `get_string_ids` endpoint with `species=3702` should resolve both.
   - What's unclear: How reliably does STRING resolve short Arabidopsis gene symbols (e.g. "FLC", "FT") vs locus codes (e.g. "AT5G10140")? Resolution quality for rice/maize genes (OsMADS51, ZmMADS4) is unknown without live testing.
   - Recommendation: Implement `get_string_ids` pre-resolution step with `limit=1`; surface the resolved STRING ID in the tool response so agent can see what was matched. If pre-resolution fails (empty result), pass the gene name directly to `interaction_partners` as a fallback and note the uncertainty in the summary.

2. **PubMed EFetch for abstracts — response format and parsing**
   - What we know: EFetch returns XML by default for PubMed. The existing codebase already parses XML in `_patent_search_epo()` using `xml.etree.ElementTree`.
   - What's unclear: The exact XPath for abstract text in PubMed XML (it uses `//AbstractText` under `//Abstract`). Multiple `AbstractText` elements can exist (structured abstracts).
   - Recommendation: Join all `AbstractText` elements with newlines. Test with a known PMID during Wave 0.

3. **Persistent cache TTL edge case — stale cache during active research session**
   - What we know: 24h TTL is the user-approved default.
   - What's unclear: Should there be a `force_refresh` parameter to bypass the cache for a specific call? The current design does not include this.
   - Recommendation: Omit `force_refresh` for now — the agent doesn't need it. Cache is per cache key (gene + species + params), so changing any parameter naturally bypasses the old entry.

4. **Lens.org `claim` field structure in API response**
   - What we know: Lens API docs confirm `claim` is a supported include field. The structure is a list of claim objects.
   - What's unclear: Exact structure of claim objects (is it `[{"text": "..."}]` like `abstract`, or `[{"num": 1, "text": "..."}]`?).
   - Recommendation: Implement with defensive access (`claim[0].get("text", "")` pattern matching the `abstract` field pattern); concatenate first 3 claim texts for context without overwhelming the agent.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, no new config needed) |
| Config file | `pytest.ini` / `pyproject.toml` (existing setup) |
| Quick run command | `pytest tests/test_interactions.py tests/test_pubmed_plant.py tests/test_lens_patent.py -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONN-01 | `string_plant_ppi` returns interaction partners with scores for Arabidopsis gene | unit (mocked httpx) | `pytest tests/test_interactions.py::TestStringPlantPpi::test_success -x` | ❌ Wave 0 |
| CONN-01 | `string_plant_ppi` validates species via registry; returns error for unknown species | unit | `pytest tests/test_interactions.py::TestStringPlantPpi::test_unknown_species -x` | ❌ Wave 0 |
| CONN-01 | `string_plant_ppi` returns structured empty response when no interactions found | unit | `pytest tests/test_interactions.py::TestStringPlantPpi::test_empty_response -x` | ❌ Wave 0 |
| CONN-01 | `string_plant_ppi` is visible in plant agent tool list (`interactions` category in PLANT_SCIENCE_CATEGORIES) | unit | `pytest tests/test_interactions.py::TestStringPlantPpi::test_registered -x` | ❌ Wave 0 |
| CONN-02 | `pubmed_plant_search` constructs correct `[Organism]` field query for known species | unit | `pytest tests/test_pubmed_plant.py::TestPubmedPlantSearch::test_query_construction -x` | ❌ Wave 0 |
| CONN-02 | `pubmed_plant_search` returns structured empty response with query_used when no results | unit (mocked httpx) | `pytest tests/test_pubmed_plant.py::TestPubmedPlantSearch::test_empty_results -x` | ❌ Wave 0 |
| CONN-02 | `pubmed_plant_search` emits rate limit warning once when no NCBI key | unit | `pytest tests/test_pubmed_plant.py::TestPubmedPlantSearch::test_rate_limit_warning_once -x` | ❌ Wave 0 |
| CONN-02 | `pubmed_plant_search` includes abstract in returned articles when `fetch_abstracts=True` | unit (mocked httpx) | `pytest tests/test_pubmed_plant.py::TestPubmedPlantSearch::test_abstract_fetched -x` | ❌ Wave 0 |
| CONN-03 | `lens_patent_search` gene-mode query includes gene AND species in query_string | unit (mocked httpx) | `pytest tests/test_lens_patent.py::TestLensPatentSearch::test_gene_mode -x` | ❌ Wave 0 |
| CONN-03 | `lens_patent_search` landscape-mode query uses crop + trait combo | unit (mocked httpx) | `pytest tests/test_lens_patent.py::TestLensPatentSearch::test_landscape_mode -x` | ❌ Wave 0 |
| CONN-03 | `lens_patent_search` is excluded from MCP tool list when `api.lens_key` is absent | unit | `pytest tests/test_lens_patent.py::TestLensPatentSearch::test_mcp_hiding -x` | ❌ Wave 0 |
| CONN-03 | `lens_patent_search` includes abstract and claims in response | unit (mocked httpx) | `pytest tests/test_lens_patent.py::TestLensPatentSearch::test_response_includes_claims -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_interactions.py tests/test_pubmed_plant.py tests/test_lens_patent.py -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_interactions.py` — covers CONN-01 (STRING plant PPI)
- [ ] `tests/test_pubmed_plant.py` — covers CONN-02 (PubMed plant search)
- [ ] `tests/test_lens_patent.py` — covers CONN-03 (Lens.org patent search + MCP hiding)
- [ ] `src/ct/tools/_api_cache.py` — shared cache helper (needed by all three tools)
- [ ] `src/ct/tools/interactions.py` — new tool module (CONN-01)
- [ ] Config additions: `api.ncbi_key` in `DEFAULTS`, `env_mappings`, `API_KEYS` in `config.py`

Existing test infrastructure (pytest, conftest.py, `@patch("httpx.get")` / `@patch("httpx.post")` patterns) covers all needs. No framework installation required.

---

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/ct/tools/network.py` — STRING API call patterns, species resolution
- Existing codebase: `src/ct/tools/literature.py` — PubMed and Lens.org implementations
- Existing codebase: `src/ct/tools/http_client.py` — retry/backoff pattern
- Existing codebase: `src/ct/tools/_species.py` — species registry API
- Existing codebase: `src/ct/agent/config.py` — config/env pattern, `api.lens_key` already registered
- Existing codebase: `src/ct/agent/mcp_server.py` — `exclude_tools` mechanism verified
- STRING API documentation (fetched directly): https://string-db.org/help/api/ — `get_string_ids`, `interaction_partners` endpoints verified
- Lens.org API documentation (fetched directly): https://docs.api.lens.org/request-patent.html — `claim` field, `include` parameter, query_string format verified
- NCBI E-utilities documentation (WebSearch verified): https://www.ncbi.nlm.nih.gov/books/NBK25497/ — rate limits (3/s without key, 10/s with key), `tool` and `email` params

### Secondary (MEDIUM confidence)
- WebSearch: NCBI E-utilities 3 req/s without key, 10 req/s with key — corroborated by multiple sources (NCBI Insights 2017, LibGuides UC Merced, BioStars)
- WebSearch: STRING `get_string_ids` best-match approach for plant gene names — documented in STRING help but exact plant resolution quality not verified without live testing

### Tertiary (LOW confidence)
- STRING plant gene resolution quality (Arabidopsis locus codes vs symbols) — not tested live; flagged as Open Question #1
- Lens.org `claim` field exact object structure — API docs confirm field exists but exact JSON shape of array elements is inferred from `abstract` field pattern; flagged as Open Question #4

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all on existing httpx + stdlib + internal modules
- Architecture patterns: HIGH — directly modeled on existing verified codebase patterns (ppi_analysis, patent_search, config, mcp_server)
- API details (STRING, PubMed): HIGH — verified against live API docs fetched directly
- API details (Lens.org claims structure): MEDIUM — field existence confirmed but exact JSON shape inferred
- Pitfalls: HIGH — derived from existing code, known decisions in CONTEXT.md, and general API integration experience

**Research date:** 2026-02-26
**Valid until:** 2026-04-26 (stable: STRING, PubMed, Lens.org APIs change infrequently; 60 days reasonable)
