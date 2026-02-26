---
phase: 03-external-connectors
plan: 02
subsystem: tools/literature
tags: [pubmed, lens-org, patents, plant-science, disk-cache, mcp-hiding, registry]
dependency_graph:
  requires:
    - _api_cache.py (created in Plan 03-01)
    - interactions.string_plant_ppi (Pattern established in Plan 03-01)
  provides:
    - literature.pubmed_plant_search (PubMed plant literature search)
    - literature.lens_patent_search (Lens.org patent search, gene + landscape modes)
    - MCP-layer hiding of lens_patent_search when api.lens_key absent
  affects:
    - src/ct/tools/literature.py (two new tools + _pubmed_rate_limit_warned flag)
    - src/ct/agent/mcp_server.py (Lens key check before tool loop)
tech_stack:
  added: []
  patterns:
    - Once-per-session module flag for user warnings (_pubmed_rate_limit_warned)
    - XML parsing with xml.etree.ElementTree for EFetch abstract extraction
    - MCP-layer credential gating — exclude_tools set augmented before loop
    - Source-module patch targets for lazy-import unit tests (inherited from 03-01)
key_files:
  created:
    - tests/test_pubmed_plant.py
    - tests/test_lens_patent.py
  modified:
    - src/ct/tools/literature.py
    - src/ct/agent/mcp_server.py
decisions:
  - Module-level _pubmed_rate_limit_warned flag rather than session attribute — simpler, zero dependencies, correct once-per-process semantics
  - EFetch abstract parsing is non-fatal — XML failure logs nothing and returns empty abstract strings; citations still returned
  - MCP hiding via set union on exclude_tools before registry loop — minimal, clean, consistent with existing exclusion pattern
  - lens_patent_search still guards against missing key internally — belt-and-suspenders in case tool is somehow called outside MCP
metrics:
  duration_minutes: 5
  completed_date: "2026-02-26"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 03 Plan 02: PubMed Plant Search + Lens.org Patent Search Summary

**One-liner:** Plant-specific PubMed literature search (species+gene query, EFetch abstracts, once-per-session rate warning) and Lens.org patent search (gene/landscape modes, claims extraction) with MCP-layer credential gating.

## What Was Built

### `src/ct/tools/literature.py` (modified)

**Module-level flag:**
- `_pubmed_rate_limit_warned: bool = False` — controls once-per-session rate limit warning emission

**`literature.pubmed_plant_search` tool:**
- Constructs PubMed query as `(GENE[Title/Abstract]) AND ("BINOMIAL"[Organism])` for known species, or falls back to `(GENE[Title/Abstract]) AND (plant[MeSH Terms])` for unknown
- Supports `extra_terms` ANDed into query
- Emits a NCBI API key rate-limit warning once per session (via `_pubmed_rate_limit_warned` flag)
- ESearch → ESummary → EFetch (XML abstract parsing) pipeline
- EFetch failures are non-fatal — tool returns citations without abstracts
- Caps `max_results` at 50
- Caches results to `~/.ct/cache/pubmed/` with 24h TTL
- Returns `query_used` so agent can refine searches

**`literature.lens_patent_search` tool:**
- Gene mode: `("GENE") AND ("BINOMIAL")` — resolves species binomial via `_species.py`
- Landscape mode: `("CROP") AND ("TRAIT")` — requires `trait` parameter
- Parses title/abstract (list-of-dicts or plain string), claims (first 3), applicants
- Guards against missing API key internally (belt-and-suspenders)
- Caches to `~/.ct/cache/lens_patents/` with 24h TTL

### `src/ct/agent/mcp_server.py` (modified)

Added before the registry loop in `create_ct_mcp_server()`:
```python
if not session.config.get("api.lens_key"):
    exclude_tools = set(exclude_tools) | {"literature.lens_patent_search"}
```

The agent never sees `literature.lens_patent_search` in its tool list when no Lens.org key is configured — avoids wasted tool-use turns on unconfigured connectors.

## Test Results

| File | Tests | Result |
|------|-------|--------|
| tests/test_pubmed_plant.py | 7 | PASS |
| tests/test_lens_patent.py | 10 | PASS |
| **Total (Plan 03-02)** | **17** | **PASS** |
| **Total (Phase 03 all)** | **31** | **PASS** |

### test_pubmed_plant.py coverage
- `test_query_construction_known_species` — organism-scoped query with [Organism] tag
- `test_query_construction_unknown_species` — falls back to plant[MeSH Terms]
- `test_extra_terms_added` — extra_terms ANDed into query
- `test_empty_results_returns_structured_response` — zero PMIDs handled gracefully
- `test_abstract_fetched_and_included` — EFetch XML parsed, abstract in article entry
- `test_rate_limit_warning_emitted_once` — warning in summary on call 1, absent on call 2
- `test_cache_hit_skips_network` — get_cached hit → request_json not called

### test_lens_patent.py coverage
- `test_gene_mode_query_construction` — gene + binomial in query_used
- `test_gene_mode_returns_patents` — patents list with lens_id, title, abstract, claims
- `test_landscape_mode_query_construction` — crop + trait in query_used
- `test_landscape_missing_trait_returns_error` — error dict with "trait" mention
- `test_no_api_key_returns_error` — error dict with api.lens_key instruction
- `test_mcp_hiding_when_no_lens_key` — tool absent from MCP tool_names list
- `test_mcp_exposes_lens_when_key_present` — tool present when key configured
- `test_response_includes_claims` — claims list with string entries
- `test_no_results_returns_structured_response` — zero patents handled gracefully
- `test_cache_hit_skips_network` — get_cached hit → request not called

## Deviations from Plan

None — plan executed exactly as written.

The patch target decision from Plan 03-01 (patch source modules, not tool module namespace, due to lazy imports) applied directly here without deviation.

## Self-Check: PASSED

All created/modified files exist on disk. Both task commits verified in git history.
