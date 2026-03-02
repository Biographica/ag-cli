# Phase 2: Data Infrastructure - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Local-first data access layer: species registry, data manifests, organism validation, and dataset access so the agent can discover and query curated plant datasets. The agent should be a well-equipped plant science analysis engine — helpful infrastructure, not prescriptive rail-tracks. Opinionated workflows belong in metaprompting/GSD layers, not the core engine.

</domain>

<decisions>
## Implementation Decisions

### Species Registry Design
- YAML format, developer-maintained for now (format makes user-extensibility easy to add later)
- Registry is a convenience lookup table, not a gatekeeper: resolves aliases → canonical name → taxon ID → genome build
- Agent decides naturally when to ask about species — no forced species prompt or deterministic UX gate
- Unknown species proceed with a note; the registry helps when it can, stays out of the way when it can't
- Important: not all analyses have a single clear organism (e.g., nitrogen fixation involving soil metagenomics + root transcriptomics, or disease datasets with crop + pathogen strain). The registry must not block multi-organism or non-standard workflows
- Core species to include: Arabidopsis, rice, maize, wheat, soybean, tomato (expand as datasets arrive)

### Manifest Conventions
- Manifests are a convention for curated/shipped data sources, never required for user-provided data
- When present, manifests describe: schema (column names/types), species covered, plain-English description of dataset contents
- Agent explores user-provided data dynamically (reads files, infers schema, works with it — like Claude Code handles code files)
- Persistent data connectors (Ensembl, Plant Metabolic Network, etc.) should ship with manifests so the agent knows what they contain and how to explore them

### Validation Behavior
- Warn and proceed on species mismatch — informational, not blocking (e.g., "this dataset contains rice, not arabidopsis" returned to agent, data still returned)
- Shared middleware/decorator pattern for consistent behavior across tools
- Multi-species datasets: validation checks that requested species is IN the dataset, not that it's the only one
- Unknown/unregistered species: proceed with a note that metadata couldn't be resolved. Never block

### Dataset Scope and Format
- Supported file formats: parquet, CSV, GFF3, FASTA, VCF, BED — all handled via Python sandbox (pandas, BioPython)
- Clean-on-pull architecture: `ag data pull <dataset>` downloads from S3/Dagster assets and saves clean, ready-to-use data to a configurable local data root
- Thin cached loaders for curated data: path resolution + `@lru_cache` only — no cleaning logic in loaders (cleaning happens at pull time or upstream in Dagster)
- No bespoke loader functions for user-provided data — agent reads files directly from whatever path the user provides
- In practical near terms, pulls will come from Dagster assets (backed by S3 paths) that have already undergone significant manual cleaning

### Claude's Discretion
- Manifest file format (YAML vs JSON) — whatever integrates cleanly with the codebase
- Species registry internal structure and resolution algorithm
- Exact middleware/decorator implementation pattern for organism validation
- Cache eviction strategy and memory management
- Data root directory structure and naming conventions

</decisions>

<specifics>
## Specific Ideas

- "I want the agent to do the obvious thing when given a file or folder — like Claude Code does with code files"
- The registry should feel like a helpful reference table the agent consults, not a gate it must pass through
- Near-term data sources are Dagster assets from S3 — the pull command is essentially download + save to local data root
- The engine should be general-purpose enough that opinionated workflows (e.g., requiring specific species) are layered on top via metaprompting or GSD-style orchestration, not baked into the infrastructure

</specifics>

<deferred>
## Deferred Ideas

- User-extensible species registry (custom YAML in config directory) — add when a user actually needs it
- Dagster connector for `ag data pull --source dagster --asset my_custom_asset_name` — future enhancement beyond simple S3 paths
- Data integrity validation in manifests (content hashes, row counts) — not needed for Phase 2 discovery-focused manifests

</deferred>

---

*Phase: 02-data-infrastructure*
*Context gathered: 2026-02-25*
