---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-02T15:13:08.656Z"
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 17
  completed_plans: 16
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** A working plant science agent that can explore local curated data, query external databases, and run computational biology analyses across plant species — the engine on which a structured shortlisting pipeline will later be built.
**Current focus:** Phase 05 — Gene Editing and Evidence Tools (CRISPR guide design, editability scoring, local tool executor)

## Current Position

Phase: 05 of 6 (Gene Editing and Evidence Tools — in progress)
Plan: 2 of 3 in current phase (complete)
Status: Plan 05-02 complete — genomics.paralogy_score with OrthoFinder-first/Ensembl-Compara fallback, GO/co-expression overlap detail; 12 new tests pass
Last activity: 2026-03-02 — Plan 05-02 complete: paralogy scoring tool (TOOL-08), OrthoFinder Orthogroups.tsv parser, Ensembl Compara paralogues endpoint

Progress: [██████████] 100%

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
| 04-plant-genomics-tools | 4 | 39 min | 9.8 min |
| 05-gene-editing-and-evidence-tools | 1 | 8 min | 8 min |

**Recent Trend:**
- Last 5 plans: 04-01 (6 min), 04-02 (5 min), 04-03 (20 min), 04-04 (8 min), 05-01 (8 min)
- Trend: Stable

*Updated after each plan completion*
| Phase 05 P02 | 7 | 2 tasks | 2 files |

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
- [Phase 04-plant-genomics-tools 04-04]: Usage guides describe what a tool returns, not directives on when/how to chain tools — neutral tone, atomic tool outputs
- [Phase 04-plant-genomics-tools 04-04]: Sparse-result messages use "data coverage is limited" generic phrasing — no species tiering or specific tool suggestions
- [Phase 04-plant-genomics-tools 04-04]: All species treated as equals in tool descriptions — existence of data stated factually without "best-effort" or "richest coverage" language
- [Phase 05-gene-editing-and-evidence-tools 05-01]: _local_tools.py uses stdlib only (subprocess, shutil) at module level — mirrors http_client.py (result, error) tuple contract
- [Phase 05-gene-editing-and-evidence-tools 05-01]: SpCas9 PAM scanning uses re lookahead (?=(...)) to capture overlapping NGG matches — standard regex misses adjacent PAMs sharing a nucleotide
- [Phase 05-gene-editing-and-evidence-tools 05-01]: Off-target regex mismatch scan used for M1 even when aligner present — full Bowtie2 pipeline requires genome indexing, deferred to future plan
- [Phase 05-gene-editing-and-evidence-tools 05-01]: editability_score regulatory_complexity_score returns None for M1 — explicitly documented stub; callers treat None as data-unavailable
- [Phase 05-gene-editing-and-evidence-tools 05-02]: OrthoFinder Orthogroups.tsv parsed via stdlib csv.DictReader — no pandas dependency; reads incrementally, stops at first match
- [Phase 05-gene-editing-and-evidence-tools 05-02]: Sub-calls to gene_annotation and coexpression_network use direct function calls (not registry) — same module, no lookup overhead, easier to mock in tests
- [Phase 05-gene-editing-and-evidence-tools 05-02]: compara=plants hardcoded in paralogy_score params dict (same pattern as ortholog_map) — prevents accidental omission on paralogues endpoint

### Pending Todos

None yet.

### Blockers/Concerns

- PyPI version verification needed for ete3 (Python 3.12 compat), leidenalg, PyWGCNA before Phase 4/5 implementation
- PlantExp download format must be confirmed at plantexp.org before Phase 2 loader implementation
- Gramene bulk download vs. REST API decision needed before Phase 2 implementation
- FlashFry version and Java requirements must be confirmed before Phase 5 CRISPR tooling

## Session Continuity

Last session: 2026-03-02
Stopped at: Completed 05-02-PLAN.md — genomics.paralogy_score with OrthoFinder-first/Ensembl-Compara fallback; 12 new tests pass
Resume file: None
