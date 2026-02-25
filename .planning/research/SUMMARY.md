# Project Research Summary

**Project:** ag-cli — Agricultural Biotech Target Identification Platform
**Domain:** Agentic plant science research + deterministic shortlisting pipeline (brownfield fork of celltype-cli)
**Researched:** 2026-02-25
**Confidence:** MEDIUM-HIGH

## Executive Summary

ag-cli is an agricultural biotech target identification tool built by forking celltype-cli (a drug discovery AI agent) and adapting its agentic loop, tool registry, and MCP server architecture for plant science. The core engine — Claude Agent SDK, in-process MCP server, lazy data loaders, and the `@registry.register()` tool pattern — is inherited and stable. The build is fundamentally an additive fork: replace the domain layer (system prompt, tool categories, data loaders) while preserving the agentic infrastructure. The platform will operate in two modes: M1 is a free-form plant science research agent, and M2 is a structured, auditable pipeline that scores a customer-provided gene longlist against configurable output metrics (novelty, efficacy, pleiotropic risk, editability) and produces ranked dossiers.

The recommended technical approach is a two-layer architecture. The engine layer (ag-cli / ct/ package) provides the agentic loop, tool registry, domain filtering, and local-first data loaders. The framework layer (shortlist/ package) provides the deterministic pipeline: EvidenceStream transform DSL, ScoringEngine, ScoreStore, StageOrchestrator, and PipelineRunner. The critical design rule is that the framework calls the engine through a clean public API; the engine never imports from the framework. Scoring is deterministic Python code — never agent prose — and all pipeline outputs derive from a single canonical ranking DataFrame. The agentic loop handles biological reasoning; all numerical scoring is handled by the ScoringEngine.

The top risks are all inherited from a real predecessor tool (Kosmos) whose failure modes are directly documented in the product spec. Five "gotchas" have already happened in production: post-hoc constraint fixing that creates inconsistent deliverables, wrong-organism datasets silently corrupting evidence, targets added outside the customer's longlist, inconsistent dossier format across runs, and PDF/ranking table divergence. Each has a clear programmatic solution. Additional critical risks include species-hardcoding early in the codebase (costly to retrofit), scoring logic leaking into agent prompts (non-deterministic results), and evidence double-counting from correlated streams. All of these must be designed out architecturally before implementation begins — they cannot be patched with prompt instructions.

## Key Findings

### Recommended Stack

The inherited celltype-cli stack (anthropic SDK, typer, rich, pandas, numpy, scipy, httpx, python-dotenv, markdown, nbformat) is confirmed stable and carries over unchanged. Five new core libraries are needed: `pydantic>=2.5` for schema validation of ProjectSpec, EvidenceStream, and ScoredTarget models; `jinja2>=3.1` for dossier template rendering; `biopython>=1.83` for sequence retrieval and GFF manipulation; `gffutils>=0.12` for fast SQLite-backed genome annotation queries; and `pyranges>=0.0.129` for genomic interval operations. `networkx>=3.0` and `ete3>=3.1.3` are needed for co-expression network centrality and phylogenetic distance computation. `openpyxl>=3.1` enables Excel export for customer-facing ranking tables.

For plant-specific data, the recommended stack uses bulk-downloaded local datasets — not live API calls — following the existing `ct data pull` pattern. Priority datasets are Ensembl Plants (GFF3, orthologs, variation), PlantExp (RNA-seq expression matrices), TAIR (Arabidopsis annotations), Gramene (QTL/GWAS), STRING (plant PPI networks), and pre-computed CRISPR guide libraries via FlashFry. Total storage footprint for 4-5 species is approximately 30-50 GB. `PyWGCNA>=1.1.9` (optional extra) handles co-expression network analysis using the WGCNA method that plant biologists expect to see.

**Core technologies:**
- `anthropic` + `claude-agent-sdk`: Inherited agentic loop — no changes needed
- `pydantic>=2.5`: Schema validation for ProjectSpec, EvidenceStream, ScoredTarget — enforces reproducibility
- `biopython` + `gffutils` + `pyranges`: Plant genomics stack — sequence retrieval, annotation queries, interval operations
- `PyWGCNA` + `networkx`: Co-expression analysis — WGCNA is the plant science standard
- `jinja2` + `openpyxl`: Dossier rendering and Excel export — customer-facing output formats
- FlashFry (Java, subprocess): Genome-scale CRISPR guide enumeration — local, no web API dependency
- Ensembl Plants + PlantExp + TAIR + Gramene + STRING: Local bulk datasets — species-aware, version-tracked

All versions tagged `[VERIFY]` in STACK.md must be confirmed against PyPI before pinning. Notable compatibility risks: `ete3` on Python 3.12+, `leidenalg` on Python 3.12+, and `PyWGCNA` maintenance status should be checked before committing to it.

### Expected Features

**Must have — M1 (table stakes for a plant science agent):**
- Plant-domain system prompt (replaces oncology framing completely)
- Runtime pharma tool filtering (60+ pharma tools hidden, not deleted)
- PlantExp RNA-seq expression loader with tissue metadata
- Ensembl Plants loader (gene models, orthologs, variation)
- TAIR + Gramene annotation loaders (GO terms, phenotypes, QTL)
- Cross-species ortholog mapping with phylogenetic distance weighting
- GFF3 genome annotation parsing (prerequisite for CRISPR guide design)
- Co-expression network analysis tools
- Species-agnostic architecture with explicit species parameter everywhere
- Organism validation middleware (programmatic, not prompt-level)
- Local-first data access with versioned dataset metadata
- Plant-adapted literature and patent search (PubMed, Lens.org)

**Must have — M2 (table stakes for a shortlisting pipeline):**
- Project specification schema (Pydantic-validated JSON with target_organism, allowed_strategies, metric weights)
- Target construction with programmatic longlist lock after Stage 1
- EvidenceStream class with transform DSL (percentile/z-score/rank normalisation + clipping)
- Exclusion gating (hard pass/fail rules enforced in code)
- Four output metrics: novelty, efficacy, pleiotropic risk, editability
- Pseudo-Bayesian posterior update (deterministic code, per PRODUCT_SPEC.md §3.5 formula)
- Single canonical ranking DataFrame as source of truth for all outputs
- Evidence provenance and audit tables (every score traceable to source)
- Pipeline state management (stage-level checkpointing)
- Transform spec versioning (content-hashed, replayable)
- Target dossier generation (schema-enforced sections, per-target independent agent calls)

**Should have — M1 differentiators:**
- STRING plant PPI network loader for pleiotropic risk
- PlantTFDB transcription factor loader
- CRISPR guide design tools with editability scoring
- Paralogy/redundancy scoring
- Patent landscape search via Lens.org

**Should have — M2 differentiators:**
- Evidence planning agent with scientist-in-the-loop review gate
- Dynamic metric re-weighting without re-running pipeline
- Stream independence validation (correlation check gate)
- Coverage tracking and conflict detection guardrails
- Alternative editing strategy presentation with quantitative tradeoffs

**Defer to v2+:**
- Dagster integration for pipeline orchestration
- Real-time collaboration features
- Field trial design features
- Web product interface
- Fully probabilistic Bayesian model (MCMC/variational)
- Black-box ML scoring (transformer-based gene ranking)

### Architecture Approach

The platform uses a strict two-layer architecture where the framework layer (shortlist/ package containing PipelineRunner, StageOrchestrator, ScoringEngine, EvidenceStream, ScoreStore) imports from the engine layer (ct/ package containing ToolRegistry, DomainFilter, MCPServer, AgentRunner, DataLoaderCache) but never vice versa. Each M2 pipeline stage is an isolated AgentRunner session with domain-filtered tools (15-30 tools per stage via DomainFilter, not 190+). The key hand-off contract between the agentic and deterministic layers is the `EvidenceUnit` type — a typed, normalized struct carrying signal_value (float 0-1), confidence, source, type, and raw provenance. EvidenceUnits are persisted to ScoreStore (SQLite), enabling re-scoring with different weights without re-invoking Claude.

**Major components:**
1. `DomainFilter` (engine) — filters tool registry by category for each pipeline stage; prevents context bloat and wrong-domain tool calls
2. `AgentBridge` (framework) — calls AgentRunner with domain-filtered tool set, extracts structured findings into EvidenceUnits
3. `EvidenceStream` (framework) — applies transform DSL to normalize raw agent findings into typed, scored EvidenceUnit objects
4. `ScoringEngine` (framework) — deterministic weighted-sum formula; reads weights from project spec config; produces CandidateScore with per-type breakdown
5. `ScoreStore` (framework) — SQLite persistence for EvidenceUnits and CandidateScores with run provenance; enables re-scoring
6. `StageOrchestrator` (framework) — sequences pipeline stages with gate conditions; isolates each stage as its own AgentRunner session
7. `PipelineRunner` (framework) — top-level entrypoint; reads pipeline config; drives stages; emits canonical ranking table

### Critical Pitfalls

1. **Post-hoc constraint fixing creates inconsistent deliverables (G1)** — Lock the target set programmatically at Stage 1; all formatted outputs must derive from a single canonical ranking DataFrame generated first; implement cross-artifact hash validation.

2. **Wrong-organism dataset silently corrupts evidence (G2)** — Organism validation must be programmatic middleware at every data-fetching tool, not a prompt instruction; every data loader validates the organism field before returning results; project spec carries `target_organism` that all loaders check.

3. **Scoring logic in agent prompts produces non-reproducible results (C1)** — The ScoringEngine is a Python module with typed, tested code; the agent plans evidence streams and configures reliability/applicability values but never computes scores; all score values carry a `transform_spec_id`.

4. **Species-hardcoding accumulates irreversible technical debt (C2)** — Every tool and loader requires `species` as an explicit parameter from day one; maintain a species registry; test suite covers at least two species (Arabidopsis + rice or maize) from the start.

5. **Evidence double-counting from correlated streams inflates scores (C3)** — Post-evidence-plan correlation check is a mandatory pipeline gate; flag any stream pair with |r| > 0.7; streams sharing an upstream dataset are treated as correlated by default.

## Implications for Roadmap

Based on the combined research, the project maps cleanly to the two milestones defined in the product spec, with M1 sub-divided into foundation and plant tools phases to enforce architectural discipline before domain tools are built.

### Phase 1: Foundation — Fork Setup and Agent Adaptation
**Rationale:** Must come first because every subsequent tool depends on the correct domain context. Pharma tool leakage and oncology system prompt residue will corrupt all plant science work if not eliminated in Phase 1. The fork maintenance strategy must also be established before any divergence accumulates.
**Delivers:** A working ag-cli agent that answers plant science questions without surfacing pharma tools or oncology reasoning; confirmed species-agnostic architecture pattern; fork tracking documentation.
**Addresses:** Runtime pharma tool filtering, plant-domain system prompt, open-ended plant Q&A.
**Avoids:** Pharma tool leakage (L2), oncology system prompt residue (L5), fork maintenance trap (M1).
**Stack:** Inherited celltype-cli stack only; pydantic added; pyproject.toml restructured for ag-cli.
**Research flag:** Standard patterns — well-documented; skip research-phase.

### Phase 2: Plant Data Infrastructure
**Rationale:** All M1 domain tools depend on local-first data loaders. Loaders must be built before tools. Dataset version tracking must be implemented on the first loader, not retrofitted later. Species-agnostic architecture must be validated in the loader layer before tools are written.
**Delivers:** Data download scripts and loaders for PlantExp, Ensembl Plants, TAIR, Gramene, STRING; organism validation middleware; species registry; dataset metadata + content hash pattern.
**Addresses:** Local-first data access, species-agnostic architecture, organism validation middleware.
**Avoids:** Dataset version drift (C5), species-hardcoding (C2), wrong-organism data (G2), gene name ambiguity (L4).
**Stack:** biopython, gffutils, pyranges, pandas, pydantic (for loader metadata schemas).
**Research flag:** Data format verification needed during implementation — download URLs and file formats for PlantExp and Gramene should be confirmed against current database documentation before coding.

### Phase 3: Plant Science Domain Tools
**Rationale:** Builds on the data infrastructure from Phase 2. Tools must follow the established species-agnostic and organism-validated patterns. GFF parsing and gene structure tools are prerequisites for CRISPR guide design, so must be sequenced correctly within this phase.
**Delivers:** Full M1 tool suite: gene annotation lookup, cross-species ortholog mapping, co-expression network analysis, GWAS/QTL lookup, GFF parsing, CRISPR guide design, editability scoring, literature and patent search.
**Addresses:** All M1 table stakes and differentiator features.
**Avoids:** Hardcoded Arabidopsis bias, missing ortholog species distance weighting (M4).
**Stack:** PyWGCNA, networkx, ete3, metapub; FlashFry pre-installed for CRISPR guide enumeration.
**Internal sequencing:** gene annotation → ortholog mapping → co-expression → GFF parsing → gene structure tools → CRISPR guide design → editability scoring → literature/patent search.
**Research flag:** CRISPR guide scoring implementation details (Doench 2016 Rule Set 2, off-target scoring) should be validated against current plant CRISPR literature. PyWGCNA maintenance status must be confirmed before committing.

### Phase 4: Shortlisting Pipeline Core (M2 Foundation)
**Rationale:** M2 depends entirely on M1 tools being available. The scoring architecture — EvidenceUnit contract, ScoringEngine as deterministic code, single canonical ranking table — must be established before any evidence streams are implemented. Getting this architecture wrong is the most expensive mistake available.
**Delivers:** ProjectSpec schema, target construction with programmatic longlist lock, EvidenceStream class with transform DSL, ScoringEngine (deterministic weighted sum), ScoreStore (SQLite persistence), exclusion gating.
**Addresses:** Project specification schema, target set locking, evidence stream framework, batch normalisation, exclusion gating, transform spec versioning.
**Avoids:** Scoring as agent judgement (C1), post-hoc constraint fixing (G1), targets outside longlist (G3), editing strategy constraint violations (M5), transform spec complexity spiral (M2-pitfall).
**Stack:** pydantic, scipy (normalisation), numpy (scoring formulas), SQLite.
**Research flag:** Needs research-phase for pseudo-Bayesian posterior update formula implementation — verify against PRODUCT_SPEC.md §3.5 and assess whether the formula as specified maps cleanly to a deterministic Python function.

### Phase 5: Evidence Integration and Ranking
**Rationale:** Builds on the Phase 4 foundation. Evidence streams are implemented using the EvidenceStream class established in Phase 4. The pipeline can now be run end-to-end. Guardrails (correlation check, coverage tracking, conflict detection) must be implemented here, not deferred.
**Delivers:** Three-plus evidence streams (literature novelty, expression breadth, ortholog evidence), pseudo-Bayesian metric integration for all four output metrics, evidence planning agent, batch normalisation with explicit NA handling, correlation check gate, target ranking table.
**Addresses:** Pseudo-Bayesian posterior update, configurable metric weights, four output metrics, evidence planning agent, stream independence validation, coverage tracking, conflict detection, dynamic re-weighting.
**Avoids:** Evidence double-counting (C3), missing data as negative evidence (L3), context window exhaustion (C4), dataset hallucination by evidence planner (M3), ortholog evidence without species distance weighting (M4).
**Stack:** All M1 tools consumed via AgentBridge; per-stream agent sessions (not one monolithic session).
**Research flag:** Evidence planning agent prompting strategy may need research-phase — the scientist-in-the-loop review gate and structured JSON output format need careful design.

### Phase 6: Dossier Generation and Output
**Rationale:** Final phase because it depends on a stable ranking table. Dossiers must be schema-enforced and generated per-target (not as a single large agent call) to prevent the observed failures in Kosmos. PDF and Excel derivation from the single canonical ranking table closes the PDF drift risk.
**Delivers:** Schema-enforced target dossiers (Pydantic model for all required sections), per-target independent agent calls, mechanistic hypothesis generation, validation priority recommendations, alternative strategy presentation, Excel ranking table export, PDF report generation.
**Addresses:** Target dossier generation, evidence provenance, single canonical ranking table, pipeline state management.
**Avoids:** Rich output masking thin evidence (L1), inconsistent dossier format (G4), PDF drift (G5).
**Stack:** jinja2 (templates), openpyxl (Excel export), markdown (report rendering).
**Research flag:** Standard patterns for Jinja2 dossier templating — skip research-phase.

### Phase Ordering Rationale

- **Infrastructure before domain tools:** Phases 1-2 establish the foundation before any plant biology is implemented. Retrofitting species-agnostic architecture, organism validation, or dataset version tracking onto existing tools is 3-4x more expensive.
- **Agent tools before pipeline framework:** Phase 3 completes M1 before Phase 4 begins M2. The pipeline framework consumes M1 tools as evidence sources — building the consumer before the producers creates a dead end.
- **Pipeline architecture before evidence streams:** Phase 4 establishes the EvidenceUnit contract and ScoringEngine before any evidence streams are wired up. This prevents the worst anti-pattern: scoring logic drifting into agent prompts because the scoring module doesn't exist yet.
- **Guardrails in the evidence phase:** Correlation checks, coverage tracking, and organism validation are implemented in Phase 5 alongside the streams they protect. Deferring guardrails to a future phase is how production failures happen.
- **Dossiers last:** Dossier generation is strictly downstream from scoring. It has no architectural dependencies that require earlier implementation; deferring it avoids building against an unstable ranking table.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Shortlisting Pipeline Core):** Pseudo-Bayesian posterior update formula — PRODUCT_SPEC.md §3.5 formula must be reviewed carefully and implemented as deterministic Python with explicit formula mapping. Transform spec DSL scope should be designed with the 200-line parser limit in mind.
- **Phase 5 (Evidence Integration):** Evidence planning agent design — the structured JSON output format, manifest-driven planning approach, and scientist-in-the-loop gate design benefit from careful prompt engineering research.
- **Phase 3 (Plant Science Tools):** CRISPR guide scoring — Doench 2016 Rule Set 2 implementation details and off-target scoring calibration for plant genomes.

Phases with well-established patterns (can skip research-phase):
- **Phase 1 (Foundation):** Fork setup, system prompt replacement, runtime tool filtering — all straightforward adaptations of existing celltype-cli patterns.
- **Phase 2 (Data Infrastructure):** Local-first loader pattern already established in celltype-cli; extending it for plant databases follows the same conventions.
- **Phase 6 (Dossier Generation):** Jinja2 templating, openpyxl export, per-target agent calls — all standard patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Inherited stack is HIGH (read from pyproject.toml directly). New additions (biopython, gffutils, pyranges, PyWGCNA) are MEDIUM — correct libraries, versions need PyPI verification. Items tagged [VERIFY] are LOW until checked. |
| Features | HIGH | Sourced directly from PROJECT.md, PRODUCT_SPEC.md, and FEASIBILITY_REPORT.md — all authoritative project documents. Competitive landscape (what existing tools provide) is HIGH confidence for well-established databases. |
| Architecture | MEDIUM-HIGH | Two-layer engine/framework separation is derived from project specifications and is HIGH confidence. Specific component interfaces (EvidenceUnit type, transform DSL shape) are MEDIUM — established patterns applied to project-specific needs. |
| Pitfalls | HIGH | Gotchas G1-G5 are directly observed production failures from Kosmos — not hypothetical. Critical pitfalls C1-C5 are well-grounded in agentic pipeline failure modes and project documentation. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **PyPI version verification:** All `[VERIFY]`-tagged library versions in STACK.md must be confirmed before pinning in pyproject.toml. Priority: ete3 Python 3.12 compatibility, leidenalg Python 3.12 compatibility, PyWGCNA active maintenance status.
- **PlantExp download format:** The specific file format and download structure for PlantExp must be confirmed at plantexp.org before implementing the loader. STACK.md notes this as a medium-confidence finding.
- **Gramene data access strategy:** Decision needed on bulk download vs. cached REST API calls for Gramene QTL/GWAS data. The Ensembl Plants FTP covers much of the same data — the redundancy should be resolved before implementing both loaders.
- **Phytozome access:** JGI institutional login is required; access process must be confirmed before planning any Phytozome-dependent features.
- **FlashFry version and Java requirements:** Current FlashFry release and Java version compatibility should be confirmed before committing to it for CRISPR guide enumeration.
- **PRODUCT_SPEC.md §3.5 formula:** The pseudo-Bayesian posterior update formula should be reviewed against the full product spec during Phase 4 planning to ensure the Python implementation maps exactly.

## Sources

### Primary (HIGH confidence)
- `PROJECT.md` — milestone definitions, scope boundaries, key decisions, previous learnings
- `PRODUCT_SPEC.md` — evidence integration framework, input/output schemas, Kosmos failure modes (gotchas), dossier section requirements
- `FEASIBILITY_REPORT.md` — existing celltype-cli capability assessment, tool category mapping, gap analysis
- `CLAUDE.md` (codebase instructions) — tool registry pattern, MCP server structure, `load_X()` convention, existing dependency versions

### Secondary (MEDIUM confidence)
- Training knowledge of plant science bioinformatics ecosystem (cutoff August 2025) — Ensembl Plants, TAIR, Gramene, Phytozome, STRING capabilities; plant CRISPR guide scoring; PyWGCNA WGCNA methodology
- Established software architecture patterns — ETL transform pipelines, weighted-sum scoring in target prioritization, multi-agent stage isolation, local-first data patterns

### Tertiary (LOW until verified)
- All library versions tagged `[VERIFY]` in STACK.md — requires PyPI verification before implementation
- PlantExp download structure — requires confirmation at plantexp.org
- Gramene FTP vs. REST strategy — requires assessment of current Gramene data access options
- Phytozome access process — requires JGI account verification

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
