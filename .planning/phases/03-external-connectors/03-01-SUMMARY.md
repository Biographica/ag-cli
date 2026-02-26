---
phase: 03-external-connectors
plan: 01
subsystem: tools/interactions
tags: [string-api, protein-interactions, disk-cache, plant-science, registry]
dependency_graph:
  requires: []
  provides:
    - _api_cache.py (shared disk TTL cache helper used by all Phase 3 connectors)
    - interactions.string_plant_ppi (STRING plant PPI tool)
  affects:
    - src/ct/tools/__init__.py (PLANT_SCIENCE_CATEGORIES + _TOOL_MODULES)
    - src/ct/agent/config.py (api.ncbi_key registered)
tech_stack:
  added: []
  patterns:
    - Lazy imports inside function body (tool pattern)
    - JSON disk envelope with _cached_at timestamp for TTL
    - Source-module patch targets for lazy-import unit tests
key_files:
  created:
    - src/ct/tools/_api_cache.py
    - src/ct/tools/interactions.py
    - tests/test_api_cache.py
    - tests/test_interactions.py
  modified:
    - src/ct/tools/__init__.py
    - src/ct/agent/config.py
decisions:
  - Patch source modules (ct.tools._species, ct.tools.http_client, ct.tools._api_cache) rather than ct.tools.interactions — lazy imports inside function body mean names never exist at module level
  - _CACHE_BASE as module-level constant in _api_cache.py allows easy patching in tests
metrics:
  duration_minutes: 6
  completed_date: "2026-02-26"
  tasks_completed: 2
  files_created: 4
  files_modified: 2
---

# Phase 03 Plan 01: Disk Cache + STRING Plant PPI Connector Summary

**One-liner:** Shared JSON disk cache with 24h TTL and STRING protein-protein interaction connector for plant genes with two-step ID resolution, species validation, and per-session persistence.

## What Was Built

### `src/ct/tools/_api_cache.py`
Shared disk TTL cache helper with three functions:
- `_cache_path(namespace, key)`: derives a stable path under `~/.ct/cache/<namespace>/<sha256[:16]>.json`
- `get_cached(namespace, key, ttl_seconds=86400)`: returns cached dict or None on miss/expiry/error — never raises
- `set_cached(namespace, key, value)`: persists JSON envelope with `_cached_at` timestamp — silently swallows write failures

### `src/ct/tools/interactions.py`
`interactions.string_plant_ppi` tool registered with the tool registry:
- Validates species via `resolve_species_taxon` — returns structured error for unknown species (taxon_id == 0) without making any API call
- Caps `limit` at 50 regardless of user input
- Checks disk cache before any network request
- Step 1: `GET string-db.org/api/json/get_string_ids` — resolves gene symbol to STRING ID
- Step 2: `GET string-db.org/api/json/interaction_partners` — fetches scored partners using `required_score = int(min_score * 1000)`
- Parses partner list (handles A/B symmetry, skips self-interactions), sorts by score descending
- Caches result to disk before returning

### Registry wiring
- `"interactions"` added to `PLANT_SCIENCE_CATEGORIES` frozenset — tool visible to plant agent at MCP layer
- `"interactions"` added to `_TOOL_MODULES` tuple — auto-registered on `ensure_loaded()`

### Config registration
- `api.ncbi_key: None` added to `DEFAULTS`
- `NCBI E-utilities` entry added to `API_KEYS`
- `NCBI_API_KEY` → `api.ncbi_key` added to `env_mappings` in `Config.load()`

## Test Results

| File | Tests | Result |
|------|-------|--------|
| tests/test_api_cache.py | 6 | PASS |
| tests/test_interactions.py | 8 | PASS |
| **Total** | **14** | **PASS** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mock patch targets for lazy-import pattern**
- **Found during:** Task 2 test execution
- **Issue:** Plan specified patching `ct.tools.interactions.resolve_species_taxon` etc., but lazy imports inside the function body mean these names never exist at the `ct.tools.interactions` module level — `unittest.mock.patch` raises `AttributeError`.
- **Fix:** Tests patch source modules (`ct.tools._species.resolve_species_taxon`, `ct.tools.http_client.request_json`, `ct.tools._api_cache.get_cached`, `ct.tools._api_cache.set_cached`) instead — this is the correct approach when using lazy imports.
- **Files modified:** tests/test_interactions.py
- **Commit:** 79432fb

## Self-Check: PASSED

All created files exist on disk. Both task commits verified in git history.
