---
phase: 03-external-connectors
verified: 2026-02-26T00:00:00Z
status: passed
score: 3/3 must-haves verified
re_verification: false
---

# Phase 03: External Connectors — Verification Report

**Phase Goal:** The agent can query STRING plant PPI networks, search PubMed with plant-specific queries, and retrieve patent data from Lens.org as evidence sources in a research workflow
**Verified:** 2026-02-26
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Agent can retrieve PPI partners and confidence scores for a plant gene from STRING via `interactions.string_plant_ppi`, with organism validation applied before the API call | VERIFIED | `src/ct/tools/interactions.py` — `resolve_species_taxon` called first; returns structured error and exits before any HTTP call when `taxon_id == 0`. Two-step STRING API flow (get_string_ids, interaction_partners) confirmed. `test_unknown_species_returns_error` verifies no-network-call guarantee. |
| 2 | Agent can run a PubMed search with plant-specific query construction (species name, organism scope) via `literature.pubmed_plant_search` and return structured citation results with abstracts and `query_used` | VERIFIED | `src/ct/tools/literature.py` lines 800–971 — builds `(GENE[Title/Abstract]) AND ("BINOMIAL"[Organism])` for known species, falls back to `plant[MeSH Terms]` for unknown. Returns `query_used`, `articles` with abstract field, `total_count`. Tests `test_query_construction_known_species`, `test_query_construction_unknown_species`, `test_abstract_fetched_and_included`, `test_rate_limit_warning_emitted_once` all pass. |
| 3 | Agent can retrieve patent records for a gene or trait from Lens.org via `literature.lens_patent_search` and summarise the patent landscape; tool is hidden from agent when API key absent | VERIFIED | `src/ct/tools/literature.py` lines 974–1161 — gene mode and landscape mode both implemented, claims extracted (first 3), abstract parsed, summary text generated. MCP hiding confirmed in `mcp_server.py` lines 373–374. `test_mcp_hiding_when_no_lens_key` and `test_mcp_exposes_lens_when_key_present` both pass. |

**Score:** 3/3 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/ct/tools/_api_cache.py` | Shared disk TTL cache helper (`get_cached`, `set_cached`) | VERIFIED | 84 lines. `_cache_path`, `get_cached`, `set_cached` all present. JSON envelope with `_cached_at` timestamp. 24h TTL default. `_CACHE_BASE` patchable constant. No external deps. |
| `src/ct/tools/interactions.py` | STRING plant PPI tool with `@registry.register` | VERIFIED | 229 lines. `@registry.register(name="interactions.string_plant_ppi", category="interactions")` present. Two-step STRING API flow. Species validation, limit cap, disk cache, structured results. |
| `src/ct/tools/literature.py` | Two new tools: `pubmed_plant_search` and `lens_patent_search` | VERIFIED | `pubmed_plant_search` registered at line 755; `lens_patent_search` at line 974. Both have full implementations with lazy imports, caching, error handling, and substantive result structures. |
| `src/ct/agent/mcp_server.py` | MCP-layer hiding of `lens_patent_search` when key absent | VERIFIED | Lines 373–374: `if not session.config.get("api.lens_key"): exclude_tools = set(exclude_tools) | {"literature.lens_patent_search"}` — placed before registry loop. |
| `tests/test_api_cache.py` | Unit tests for disk cache helper | VERIFIED | 6 tests: `test_cache_path_deterministic`, `test_set_and_get_cached`, `test_get_cached_missing`, `test_get_cached_expired`, `test_get_cached_not_expired`, `test_set_cached_creates_directories` — all pass. |
| `tests/test_interactions.py` | Unit tests for STRING plant PPI tool | VERIFIED | 8 tests across `TestRegistration`, `TestUnknownSpecies`, `TestSuccessPath`, `TestCacheBehaviour` — all pass. |
| `tests/test_pubmed_plant.py` | Unit tests for PubMed plant search | VERIFIED | 7 tests covering query construction (known/unknown species), extra terms, empty results, abstract fetching, once-per-session rate warning, cache hit — all pass. |
| `tests/test_lens_patent.py` | Unit tests for Lens.org patent search and MCP hiding | VERIFIED | 10 tests covering gene mode, landscape mode, missing trait, no API key, MCP hiding (both absent and present key cases), claims parsing, no results, cache hit — all pass. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/ct/tools/interactions.py` | `src/ct/tools/_api_cache.py` | `from ct.tools._api_cache import get_cached, set_cached` (lazy) | WIRED | Confirmed at lines 80–81 of `interactions.py`. `get_cached` called at line 103, `set_cached` at line 227. |
| `src/ct/tools/interactions.py` | `src/ct/tools/_species.py` | `resolve_species_taxon` for organism validation | WIRED | Confirmed at line 78 of `interactions.py`. `resolve_species_taxon` result drives early-exit at line 84. |
| `src/ct/tools/__init__.py` | `src/ct/tools/interactions.py` | `"interactions"` in `PLANT_SCIENCE_CATEGORIES` and `_TOOL_MODULES` | WIRED | `PLANT_SCIENCE_CATEGORIES` at line 43; `_TOOL_MODULES` at line 85 of `__init__.py`. Python import confirmed: `registry.get_tool('interactions.string_plant_ppi')` returns the tool. |
| `src/ct/tools/literature.py` | `src/ct/tools/_api_cache.py` | `from ct.tools._api_cache import get_cached, set_cached` (lazy) | WIRED | Confirmed at line 780–781 (`pubmed_plant_search`) and line 996 (`lens_patent_search`). Cache hit returns early at lines 810–811 and 1028–1030. |
| `src/ct/tools/literature.py` | `src/ct/tools/_species.py` | `resolve_species_binomial` for query construction | WIRED | Confirmed at lines 779 and 998. Return value directly used in query construction at lines 799–802 and 1020–1024. |
| `src/ct/agent/mcp_server.py` | `src/ct/agent/config.py` | `session.config.get("api.lens_key")` check for tool hiding | WIRED | Confirmed at line 373 of `mcp_server.py`. Falsy result adds tool name to `exclude_tools` set before the registry loop at line 384. |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CONN-01 | 03-01 | User can query STRING plant PPI networks via API for protein interaction evidence | SATISFIED | `interactions.string_plant_ppi` registered, wired, tested. `REQUIREMENTS.md` marked `[x]`. |
| CONN-02 | 03-02 | User can search PubMed with plant-specific query construction for literature evidence | SATISFIED | `literature.pubmed_plant_search` registered, wired, tested. `REQUIREMENTS.md` marked `[x]`. |
| CONN-03 | 03-02 | User can search Lens.org for patent landscape and novelty assessment | SATISFIED | `literature.lens_patent_search` registered, wired, MCP-gated, tested. `REQUIREMENTS.md` marked `[x]`. |

No orphaned requirements — all three CONN-* requirements are mapped, claimed by a plan, and verified implemented.

---

## Anti-Patterns Found

None detected in Phase 03 files.

Scanned: `src/ct/tools/_api_cache.py`, `src/ct/tools/interactions.py`, `src/ct/tools/literature.py` (Phase 03 section), `src/ct/agent/mcp_server.py` (Phase 03 change), `tests/test_api_cache.py`, `tests/test_interactions.py`, `tests/test_pubmed_plant.py`, `tests/test_lens_patent.py`.

No `TODO`, `FIXME`, `XXX`, `HACK`, placeholder comments, `return null`, stub handlers, or empty implementations found.

---

## Test Results

| File | Tests | Result |
|------|-------|--------|
| `tests/test_api_cache.py` | 6 | PASS |
| `tests/test_interactions.py` | 8 | PASS |
| `tests/test_pubmed_plant.py` | 7 | PASS |
| `tests/test_lens_patent.py` | 10 | PASS |
| **Phase 03 total** | **31** | **PASS** |

Full suite: 932 passed, 87 skipped, 57 failed. The 57 failures are all pre-existing failures in unrelated modules (`test_chemistry_new`, `test_cli`, `test_clue`, `test_code`, `test_files`, `test_imaging`, `test_kb_benchmarks`, `test_mention_completer`, `test_omics`, `test_sandbox`, `test_shell`, `test_terminal`). Zero regressions introduced by Phase 03.

---

## Human Verification Required

None. All success criteria are verifiable programmatically:
- Tool registration: verified via registry lookup
- Species validation: verified via mock patch confirming no-network-call on unknown species
- Query construction: verified via assertion on `query_used` field in test results
- MCP hiding: verified via `create_ct_mcp_server` integration test with mock session

---

## Gaps Summary

No gaps. All three phase goals are achieved:

1. `interactions.string_plant_ppi` — substantive implementation with two-step STRING API flow, organism validation, disk caching, and 8 passing tests.
2. `literature.pubmed_plant_search` — substantive implementation with species-scoped query construction, EFetch abstract pipeline, once-per-session rate warning, and 7 passing tests.
3. `literature.lens_patent_search` — substantive implementation with gene/landscape modes, claims extraction, MCP-layer credential gating, and 10 passing tests.

All three CONN-* requirements are satisfied and marked complete in `REQUIREMENTS.md`.

---

_Verified: 2026-02-26_
_Verifier: Claude (gsd-verifier)_
