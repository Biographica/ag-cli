---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
last_updated: "2026-02-28T14:22:00.000Z"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 10
  completed_plans: 8
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** A working plant science agent that can explore local curated data, query external databases, and run computational biology analyses across plant species — the engine on which a structured shortlisting pipeline will later be built.
**Current focus:** Phase 04 — Plant Genomics Tools (Ensembl Plants gene annotation, GWAS/QTL, GFF3, orthologs)

## Current Position

Phase: 04 of 5 (Plant Genomics Tools — COMPLETE)
Plan: 3 of 3 in current phase (complete) — phase complete, advancing to Phase 05
Status: Plan 04-03 complete — gff_parse and coexpression_network tools added; 12 new tests pass; all 5 Phase 4 tools registered
Last activity: 2026-02-28 — Plan 04-03 complete: genomics.gff_parse (gffutils, GFF3 parsing) + genomics.coexpression_network (ATTED-II bulk flat-file co-expression)

Progress: [█████████░] 90%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 17 min
- Total execution time: 1.4 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2 | 71 min | 36 min |
| 02-data-infrastructure | 4 | 16 min | 4 min |
| 02.1-integration-fixes | 1 | 6 min | 6 min |
| 02.2-integration-fixes-ii | 1 | 8 min | 8 min |
| 03-external-connectors | 2 | 11 min | 5.5 min |
| 04-plant-genomics-tools | 3 | 31 min | 10.3 min |

**Recent Trend:**
- Last 5 plans: 03-01 (6 min), 03-02 (5 min), 04-01 (6 min), 04-02 (5 min), 04-03 (20 min)
- Trend: Stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Fork celltype-cli rather than build from scratch — proven agentic architecture saves months
- Runtime tool filtering rather than deletion — keeps optionality for cross-domain use
- Species-agnostic architecture from day one — explicit `species` parameter on all tools
- Local-first data access — avoids API throttling, enables curation
- AGENT_NAME = "Harvest" as single module-level constant in system_prompt.py — trivially swappable
- Allowlist approach (PLANT_SCIENCE_CATEGORIES frozenset) for tool filtering — safer than blocklist; unknown future categories default hidden
- Hard invisible tool filtering at MCP layer — agent never wastes turns on pharma tools
- Pharma workflow injection disabled in build_system_prompt() — avoids domain contamination; plant workflows deferred to later phase
- Arabidopsis thaliana (3702) as default species across all tools — it is the model plant organism, analogous to human being the original default
- ct Python namespace retained unchanged — only the installed CLI script changes to ag via pyproject.toml scripts
- resolve_species_binomial returns exact stored casing not .title() — avoids breaking Ensembl URL construction
- MyGene.info plant species use numeric taxon ID strings ('3702') not named strings — API only supports named strings for human/mouse
- genomics.py coloc function left with homo_sapiens reference — Open Targets Platform is human-only API, not parameterizable
- Rice subspecies (japonica/indica) handled as common_names aliases in species_registry.yaml — simpler than a separate subspecies_taxon_ids field
- load_manifest tries YAML first, JSON as fallback; never raises on missing files — registry is a convenience, not a gatekeeper
- Sentinel default string used in resolve_species_binomial to reliably detect unknown species — avoids false negative when arabidopsis (the standard default) appears in the dataset's covered list
- [Phase 02-data-infrastructure]: Sentinel 0 / '' for unknown species rather than default Arabidopsis — callers see 0 and surface clear errors
- [Phase 02-data-infrastructure]: Guards placed at API entry points (network.py, protein.py) not inside _species.py — context-aware error messages close to the failing call
- [Phase 02.1-integration-fixes]: Plant species removed from parity.py inline dict — all plant species resolved via YAML registry through resolve_species_taxon; eliminates drift between registry and parity.py
- [Phase 02.1-integration-fixes]: Default species in load_expression uses space-form 'Arabidopsis thaliana' not underscore 'arabidopsis_thaliana' — underscore form doesn't match YAML registry key
- [Phase 02.1-integration-fixes]: Slim inline maps retained for MyGene.info reference organisms and parasites — reference organisms only accept named strings from the API; parasites not in YAML
- [Phase 02.2-integration-fixes-ii]: pyyaml listed as runtime dependency (lowercase PyPI name, >=6.0 floor) — used by _species.py and manifest.py
- [Phase 02.2-integration-fixes-ii]: species added to entry() passthrough set alongside other registered Typer subcommands
- [Phase 02.2-integration-fixes-ii]: entry() passthrough set must include every Typer subcommand registered with app.add_typer() — omissions silently route to NL query mode
- [Phase 03-external-connectors]: Patch source modules not lazy-import tool namespaces — lazy imports inside function body mean names never exist at module level; tests must patch ct.tools._species, ct.tools.http_client, ct.tools._api_cache directly
- [Phase 03-external-connectors 03-02]: Module-level _pubmed_rate_limit_warned flag for once-per-process semantics — simpler than session attribute, correct for NCBI rate limit UX
- [Phase 03-external-connectors 03-02]: MCP credential gating via set union on exclude_tools before registry loop — minimal change, consistent with existing exclusion pattern; tool still guards internally for belt-and-suspenders safety
- [Phase 04-plant-genomics-tools 04-01]: Import genomics tool functions directly in tests (not via registry.get_tool().fn) — Tool dataclass uses .function attribute not .fn; direct module import is cleaner and consistent with Phase 3 approach
- [Phase 04-plant-genomics-tools 04-01]: gffutils>=0.13 added as core dependency not optional — required for GFF3 parsing in plan 04-03; core status avoids install friction
- [Phase 04-plant-genomics-tools 04-02]: frozenset keys in _PHYLO_DISTANCES_MYA — symmetric pairs stored once, O(1) lookup without ordering logic in caller
- [Phase 04-plant-genomics-tools 04-02]: 200 Mya default for unknown taxon pairs — conservative estimate avoids false high weights for distant/uncatalogued pairs
- [Phase 04-plant-genomics-tools 04-02]: compara=plants hardcoded in params dict not as parameter default — prevents accidental omission; critical correctness requirement
- [Phase 04-plant-genomics-tools 04-02]: Sort orthologs by phylo_weight desc then percent_identity desc — evolutionary closeness ranks first, sequence similarity breaks ties
- [Phase 04-plant-genomics-tools 04-03]: gff_parse uses gene: prefix retry before Name attribute scan — Ensembl GFF3 IDs have gene: prefix, raw locus code lookup fails without it
- [Phase 04-plant-genomics-tools 04-03]: _ATTED_DOWNLOAD_URLS module-level dict allows URL updates without touching function code — ATTED-II URLs are known to change between versions
- [Phase 04-plant-genomics-tools 04-03]: *.db added to .gitignore — gffutils SQLite databases are generated caches that should not be version-controlled

### Pending Todos

None yet.

### Blockers/Concerns

- PyPI version verification needed for ete3 (Python 3.12 compat), leidenalg, PyWGCNA before Phase 4/5 implementation
- PlantExp download format must be confirmed at plantexp.org before Phase 2 loader implementation
- Gramene bulk download vs. REST API decision needed before Phase 2 implementation
- FlashFry version and Java requirements must be confirmed before Phase 5 CRISPR tooling

## Session Continuity

Last session: 2026-02-28
Stopped at: Completed 04-03-PLAN.md — Phase 04 complete; gff_parse and coexpression_network tools added, 12 new tests pass
Resume file: None
