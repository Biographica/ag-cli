# ag-cli

## What This Is

An agentic research platform for agricultural biotechnology — like Claude Code for plant science. Built on a fork of celltype-cli, ag-cli provides a general-purpose plant science agent (natural language → tool-orchestrated research) with a structured shortlisting pipeline framework on top for target identification and prioritisation. The end-to-end product takes a gene longlist and project specification and produces a ranked, auditable, configurable shortlist of gene × editing strategy targets with quantitative scores and written dossiers.

For seed breeders, trait developers, and internal scientists.

## Core Value

Given a gene longlist and project spec, produce a ranked shortlist of gene × edit strategy targets that is auditable, reproducible, and configurable — with quantitative scores for novelty, efficacy, pleiotropic risk, and editability, plus written dossiers for top targets.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Claude Agent SDK agentic loop (up to 30 tool-use turns, self-correcting) — existing from celltype-cli
- ✓ MCP tool server with tool registry (`@registry.register()`) — existing
- ✓ Persistent Python sandbox (stateful pandas/numpy/scipy across turns) — existing
- ✓ Multi-agent orchestration (parallel research threads + merge) — existing
- ✓ Session persistence (save/resume/export trajectories) — existing
- ✓ Report generation (markdown + branded HTML export) — existing
- ✓ Config system (JSON config, CLI management) — existing
- ✓ Interactive terminal UI — existing
- ✓ Runtime domain-based tool filtering (pharma tools hidden at MCP layer) — v1.0
- ✓ Plant science system prompt with Harvest identity — v1.0
- ✓ Local-first data loader pattern with manifest system — v1.0
- ✓ PlantExp RNA-seq expression data loader — v1.0
- ✓ Species-agnostic architecture with YAML-backed registry — v1.0
- ✓ Organism validation middleware (@validate_species decorator) — v1.0
- ✓ STRING plant PPI network connector — v1.0
- ✓ PubMed plant search with species-specific query construction — v1.0
- ✓ Lens.org patent landscape search — v1.0
- ✓ Gene annotation lookup (GO terms, function, publications) — v1.0
- ✓ Ortholog mapping with phylogenetic distance weighting — v1.0
- ✓ Co-expression network analysis (cluster membership, centrality, enrichment) — v1.0
- ✓ GFF3 genome annotation parsing — v1.0
- ✓ GWAS/QTL evidence lookup — v1.0
- ✓ CRISPR guide design (PAM scanning, guide scoring, off-target prediction) — v1.0
- ✓ Editability scoring (gene structure, guide availability) — v1.0
- ✓ Paralogy and functional redundancy scoring — v1.0
- ✓ Multi-species evidence gathering orchestration — v1.0
- ✓ Open-ended plant science Q&A capability — v1.0

### Active

<!-- Current scope. Building toward these. -->

**Milestone 2: Shortlisting Pipeline Framework**
- [ ] Pipeline stage orchestration (target construction → evidence aggregation → scoring → ranking → dossier)
- [ ] Project specification JSON schema and parsing
- [ ] Target construction (longlist × allowed strategy enumeration, constraint enforcement)
- [ ] Evidence stream framework (EvidenceStream class, transform_spec DSL, batch scoring)
- [ ] Evidence planning agent (identify relevant studies and streams per project)
- [ ] Evidence computation (parallel batch scoring pipelines over target set)
- [ ] Metric-specific priors and evidence stream → output metric mapping
- [ ] Stream reliability and applicability scoring
- [ ] Batch normalisation (percentile, z-score, rank-based with clipping, missingness handling)
- [ ] Exclusion gating (hard pass/fail rules, global eligibility, audit reporting)
- [ ] Pseudo-Bayesian posterior update (prior + delta + squashing + weighted aggregation)
- [ ] Four output metrics: novelty, efficacy/causal confidence, pleiotropic risk, editability
- [ ] Guardrails (coverage tracking, conflict detection, comparability checks, organism validation)
- [ ] Dynamic re-weighting of output metrics via configurable weights
- [ ] Target ranking (gene × edit level) with gene-level aggregation and recommended strategy
- [ ] Target dossier generation (executive summary, quantitative profile, mechanistic hypothesis, editing strategy, risks, uncertainties, validation priorities, references)
- [ ] Pipeline state management (resume after interruption)
- [ ] Evidence provenance and audit tables (long-format attribution with full traceability)
- [ ] Transform spec versioning for reproducible scoring
- [ ] Single canonical ranking table (all outputs derive from one source — no "PDF drift")
- [ ] Hard constraint: only rank targets from provided longlist × allowed strategy set
- [ ] Hard constraint: all external data passes organism/species match check
- [ ] Hard constraint: every claim backed by citation or flagged as hypothesis

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Mobile app — CLI-first, web later if needed
- Real-time collaboration — single-user research tool
- Field trial design pipeline — potential future framework, not this project
- Regulatory submission pipeline — potential future framework, not this project
- Dagster backend integration — eventual goal, not M1 or M2 (local-first data pattern for now)
- Two-repo separation — one repo with clean internal separation; extract when a second framework is needed
- Deletion of pharma tools from codebase — runtime filtering works well (validated in v1.0); keep for potential cross-domain use
- Bespoke data download/cleaning scripts per database — Dagster backend handles data curation; ag-cli reads from local folders
- Full Bowtie2 off-target alignment for CRISPR — regex mismatch scan sufficient for M1; genome indexing pipeline deferred
- Ensembl Plants bulk data loader (separate from REST API tools) — REST API sufficient for v1.0 tool suite; bulk loader needed for pipeline scale

## Context

**Current state (post v1.0):** 43,524 LOC Python (src/), 19,299 LOC tests. 15+ plant science tools across 5 categories (genomics, editing, interactions, literature, data). 20+ supported plant species via YAML registry. Tech stack: Python, Claude Agent SDK, MCP protocol, PyYAML, gffutils. 139 tests passing (3 e2e gated behind `--run-e2e`).

**Forked from:** [celltype/cli](https://github.com/celltype/cli/tree/main) — a Claude Code-style agentic research tool for biomedical tasks. Provides a production-grade agentic architecture (Claude Agent SDK + MCP + tool registry + sandbox + session management + reporting). Pharma-specific tools (~60) are hidden at runtime via MCP-layer allowlist filtering.

**Architectural analogy:** celltype-cli : ag-cli :: Claude Code : Claude Code (domain swap). GSD : Claude Code :: shortlisting framework : ag-cli (opinionated workflow layer).

**Internal package structure:**
```
src/
├── ct/                          # Engine (the ag-cli layer)
│   ├── agent/                   # Agent loop, MCP server, system prompt
│   ├── tools/                   # All registered tools (plant + general)
│   ├── data/                    # Data loaders (local-first)
│   ├── models/                  # LLM client
│   └── ui/                      # Interactive terminal
│
├── shortlist/                   # Framework (shortlisting pipeline layer)
│   ├── pipeline/                # Stage orchestration, state management
│   ├── scoring/                 # Normalisation, exclusion, pseudo-Bayesian engine
│   ├── evidence/                # Evidence stream framework, transform DSL
│   ├── specs/                   # Project spec schema, validation
│   ├── dossier/                 # Dossier templates, generation
│   └── guardrails/              # Pipeline-level validation
```

**Critical dependency rule:** `shortlist.*` imports from `ct.*`, never the reverse. The shortlist package uses the same public interfaces (tool registry, agent runner, config system) that any other framework would use.

**Data access pattern:** Local-first. Databases are bulk downloaded and curated (potentially via Dagster data backend), stored in local folders. The ag-cli data loaders read from these local datasets. This avoids API throttling, enables manual harmonisation/curation, and keeps datasets version-controlled. PlantExp as example: all metadata and read count matrices fit in a local folder.

**Previous learnings (from gotchas in PRODUCT_SPEC.md):**
- Agents will ignore constraints and "fix" post-hoc → need hard-coded guardrails, not prompt-based
- Agents will use wrong-organism datasets → need programmatic organism validation
- Output inconsistency across runs → need structured templates and schema validation
- Post-hoc gene additions outside longlist → need target set locking at pipeline stage gates

**Other repo context:** A parallel attempt exists building agentic features from scratch using 12-factor agent principles. That repo is becoming monolithic. This project takes the opposite approach: use a proven engine and add domain + orchestration layers. The key bet is that celltype-cli's agent loop is sufficient for individual research steps, and the shortlisting framework provides the structured pipeline control the product spec demands.

## Constraints

- **Tech stack**: Python, Claude Agent SDK, MCP protocol — inherited from celltype-cli
- **Data**: Local-first; no dependency on external API availability for core functionality
- **Species**: Must be species-agnostic from the start — no hardcoding to Arabidopsis or any single species
- **Reproducibility**: Scoring pipeline must be deterministic and replayable from versioned transform specs and project spec
- **Quality**: Build for external customer quality from day one, even though internal scientists are first users
- **Import boundary**: `shortlist/` → `ct/` only, never reverse — enables eventual repo separation

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fork celltype-cli rather than build from scratch | Proven agentic architecture (SDK, MCP, tools, sandbox) saves months of infrastructure work | ✓ Good — v1.0 shipped in 7 days; agentic loop, MCP server, sandbox, session mgmt all inherited |
| One repo with two internal packages | Avoids premature two-repo overhead while maintaining clean separation for eventual extraction | — Pending (shortlist/ not yet built) |
| Runtime tool filtering rather than tool deletion | Keeps optionality for cross-domain use; simpler than managing deleted code | ✓ Good — PLANT_SCIENCE_CATEGORIES allowlist works cleanly; pharma tools invisible to agent |
| Local-first data access pattern | Avoids API throttling, enables curation, matches existing data workflow with Dagster backend | ✓ Good — manifest system + local loaders work well; REST API tools complement for external data |
| Species-agnostic from day one | Avoids costly refactoring later; real customers work across crop species | ✓ Good — YAML registry + @validate_species handle 20+ species; required 2 integration-fix phases |
| Pseudo-Bayesian evidence integration (from product spec) | Balances interpretability, configurability, and robustness; avoids intractable probabilistic models | — Pending (v2.0 scope) |
| Scoring as deterministic code, not agent judgement | Prevents hallucination in quantitative outputs; agent plans the pipeline, code executes it | — Pending (v2.0 scope) |
| Data loaders read from local curated folders, not download/clean | Dagster backend handles data curation; ag-cli loaders just read from local folders with manifests | ✓ Good — works for expression data; PlantExp URLs pending S3 confirmation |
| Multi-species tool signatures supported | Comparative genomics tools take source_species + target_species (or lists); single-species tools take species; species-agnostic tools make species optional | ✓ Good — ortholog_map uses source+target; paralogy_score single species; evidence gathering multi-species |
| Engine API must support meta-prompting layers | ag-cli's tool registry, agent runner, and MCP server are public interfaces | — Pending (shortlist framework will test this) |
| YAML-backed species registry (v1.0) | Single source of truth for species metadata; eliminates drift between inline dicts | ✓ Good — resolved 2 integration issues caused by duplicated species maps |
| MCP-layer allowlist filtering (v1.0) | Agent never sees pharma tools (not soft filter) — prevents wasted turns | ✓ Good — no pharma tool leakage observed in any UAT |
| Disk TTL cache for API responses (v1.0) | Avoids re-fetching from STRING/PubMed/Ensembl during iterative research | ✓ Good — shared across all Phase 3-5 tools |

---
*Last updated: 2026-03-02 after v1.0 milestone*
