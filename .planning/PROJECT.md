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

### Active

<!-- Current scope. Building toward these. -->

**Milestone 1: Working Plant Science Agent**
- [ ] Runtime domain-based tool filtering (ag-cli exposes only plant-relevant tools, pharma tools hidden at runtime)
- [ ] Plant science system prompt replacing oncology domain knowledge
- [ ] Local-first data loader pattern (bulk-downloaded, curated datasets from local folders)
- [ ] PlantExp RNA-seq data loader (expression data across species/tissues/conditions)
- [ ] Ensembl Plants data loader (gene models, orthologs, variation, cross-species)
- [ ] STRING plant PPI network data loader
- [ ] TAIR / Gramene annotation data loaders
- [ ] Plant genomics tools (GFF parsing, plant GWAS/QTL lookup, ortholog mapping)
- [ ] Co-expression analysis tools (network construction, cluster analysis, centrality metrics)
- [ ] Gene editing assessment tools (CRISPR guide design, PAM analysis, editability scoring)
- [ ] Literature tools adapted for plant science (plant-specific PubMed queries, patent search)
- [ ] Organism validation middleware (species consistency checks on data access)
- [ ] Species-agnostic architecture (works with any plant species that has data)
- [ ] Open-ended plant science Q&A capability
- [ ] Evidence gathering across species for a given gene list

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
- Deletion of pharma tools from codebase — runtime filtering instead; keep for potential cross-domain use

## Context

**Forked from:** [celltype/cli](https://github.com/celltype/cli/tree/main) — a Claude Code-style agentic research tool for biomedical tasks. Provides a production-grade agentic architecture (Claude Agent SDK + MCP + tool registry + sandbox + session management + reporting). Currently optimised for human oncology drug discovery with ~191 tools, ~60 of which are pharma-specific and should be hidden at runtime for ag use.

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
| Fork celltype-cli rather than build from scratch | Proven agentic architecture (SDK, MCP, tools, sandbox) saves months of infrastructure work | — Pending |
| One repo with two internal packages | Avoids premature two-repo overhead while maintaining clean separation for eventual extraction | — Pending |
| Runtime tool filtering rather than tool deletion | Keeps optionality for cross-domain use; simpler than managing deleted code | — Pending |
| Local-first data access pattern | Avoids API throttling, enables curation, matches existing data workflow with Dagster backend | — Pending |
| Species-agnostic from day one | Avoids costly refactoring later; real customers work across crop species | — Pending |
| Pseudo-Bayesian evidence integration (from product spec) | Balances interpretability, configurability, and robustness; avoids intractable probabilistic models | — Pending |
| Scoring as deterministic code, not agent judgement | Prevents hallucination in quantitative outputs; agent plans the pipeline, code executes it | — Pending |

---
*Last updated: 2025-02-25 after initialization*
