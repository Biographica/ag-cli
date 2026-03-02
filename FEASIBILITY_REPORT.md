# Feasibility Report: Building an Agricultural Target-ID Platform on celltype-cli

## Executive Summary

**Verdict: celltype-cli is an excellent foundation for this product, with significant caveats.**

celltype-cli provides a production-grade agentic architecture (Claude Agent SDK + MCP tools + persistent sandbox) that is highly extensible. Its tool registry, multi-agent orchestration, session management, and reporting infrastructure can be repurposed for agricultural target identification with moderate effort. However, the product spec demands a level of **structured, auditable, deterministic workflow control** that celltype-cli's current "free-form agent loop" architecture does not provide. This is where a GSD-style meta-prompting layer becomes essential — not as a nice-to-have, but as the missing piece that transforms celltype-cli from "a smart agent that might do the right thing" into "a controlled pipeline that provably does the right thing."

---

## 1. What celltype-cli Gives You Today

### 1.1 Architecture (Strong Foundation)

| Component | What It Provides | Relevance to Product Spec |
|-----------|-----------------|--------------------------|
| **Claude Agent SDK loop** | Up to 30 tool-use turns per session, self-correcting | Core execution engine for evidence gathering |
| **MCP tool server** | 191 tools auto-exposed to Claude via JSON Schema | Framework for plant science tools |
| **Tool registry** (`@registry.register()`) | 3-line tool addition, auto-discovery, category grouping | Trivial to add ag-biotech tools |
| **Persistent Python sandbox** | Stateful pandas/numpy/scipy across turns, safe exec | Critical for batch scoring pipelines |
| **Multi-agent orchestration** | N parallel research threads + EvidenceBoard merge | Maps to parallel evidence stream computation |
| **Session persistence** | Save/resume/export trajectories | Audit trail for regulatory needs |
| **Report generation** | Auto-markdown + branded HTML export | Customer-facing dossier generation |
| **Config system** | JSON config, CLI management, API key handling | Project specification storage |

### 1.2 Reusable Tool Categories

Several existing tool categories are directly or partially relevant:

| Category | Tools | Applicability |
|----------|-------|---------------|
| **genomics** (6) | GWAS lookup, eQTL, variant annotation, Mendelian randomisation, colocalisation | **High** — directly maps to efficacy/causal confidence evidence streams |
| **expression** (6) | Pathway enrichment, TF activity, differential expression | **High** — co-expression, tissue specificity evidence |
| **literature** (4) | PubMed, OpenAlex, ChEMBL search | **High** — novelty scoring, prior art, patent landscape |
| **network** (2) | Network analysis | **Medium** — PPI centrality, pleiotropic risk |
| **protein** (3) | Function prediction, domain annotation, ESM-2 embeddings | **Medium** — functional annotation evidence |
| **dna** (10) | Sequence analysis, codon optimization, restriction analysis | **Medium** — editability assessment |
| **data_api** (14) | UniProt, Reactome, MyGene | **Medium** — cross-reference and annotation |
| **target** (6) | Druggability, disease association, co-essentiality | **Low-Medium** — human-focused but patterns transferable |
| **code.execute** (1) | Arbitrary Python in sandbox | **Critical** — custom scoring functions, normalisation |
| **statistics** (3) | Statistical analysis | **Medium** — evidence stream scoring |

### 1.3 What's Missing (Domain Gap)

celltype-cli is optimised for **human oncology drug discovery**. It has zero plant science infrastructure:

- **No plant databases**: No PlantExp, PlantTFDB, Phytozome, Ensembl Plants, TAIR, Gramene loaders
- **No plant genomics tools**: No GFF parsing for plant genomes, no plant-specific GWAS tools, no crop QTL databases
- **No gene editing assessment tools**: No CRISPR guide design, no PAM site analysis, no regulatory element mapping for plants
- **No orthology tools**: No plant-specific ortholog mapping (e.g., via OrthoFinder, Ensembl Compara)
- **No ag-specific workflows**: No shortlisting workflow, no evidence aggregation pipeline, no dossier template
- **Human-centric system prompt**: Domain knowledge, workflow templates, and accuracy anchors are all drug discovery

---

## 2. What the Product Spec Demands (Gap Analysis)

### 2.1 Structured, Deterministic Pipeline (Critical Gap)

The product spec describes a **mathematically specified pipeline** with:
- Defined stages (target construction → evidence aggregation → scoring → ranking → dossier)
- Explicit formulas (pseudo-Bayesian updates, weighted metric aggregation)
- Versioned transform specs (reproducible scoring)
- Exclusion gating (hard rules, not suggestions)
- Audit tables (long-format attribution with provenance)

celltype-cli's architecture is **free-form agentic**: Claude decides what to do, in what order, with what tools. This is the root cause of every "gotcha" in the spec:
- Agent ignoring constraints → needs **hard-coded guardrails**, not prompt-based instructions
- Wrong organism datasets → needs **programmatic validation**, not agent judgement
- Inconsistent outputs → needs **structured templates**, not free-form synthesis
- Post-hoc "fixing" → needs **pipeline stages that gate progression**

**This is exactly the gap a meta-prompting framework fills.**

### 2.2 Mapping Product Spec Stages to Required Capabilities

| Spec Stage | What's Needed | celltype-cli Today | Gap |
|------------|--------------|-------------------|-----|
| **1. Target construction** | Longlist × strategy enumeration, constraint enforcement | Nothing | Full build |
| **2a. Evidence planning** | Project-spec-aware study identification, evidence stream definition | Some via literature tools + code sandbox | Partial — needs plant DB integration |
| **2b. Evidence computation** | Batch scoring pipelines over target set | code.execute sandbox | Partial — framework exists, needs orchestration |
| **3.1 Metric priors** | Prior specification per metric per target | Nothing | Full build |
| **3.2 Stream scoring** | Reliability, applicability assignment | Nothing | Full build |
| **3.3 Batch normalisation** | Rank/percentile/z-score with clipping, missingness | code.execute can do this | Low gap — sandbox handles computation |
| **3.4 Exclusion gating** | Hard pass/fail rules, audit reporting | Nothing | Full build |
| **3.5 Pseudo-posterior update** | Formula implementation, squashing, ranking | code.execute can do this | Low gap — sandbox handles computation |
| **3.6 Guardrails** | Coverage tracking, conflict detection, comparability checks | Nothing | Full build |
| **3.7 Per-target investigations** | Hypothesis-led deep dives with evidence update | Multi-agent orchestration supports this | Medium gap — needs structured update mechanism |
| **4. Dossier generation** | Structured target reports with quantitative profiles | Report generation infrastructure exists | Medium gap — needs ag-specific templates |

### 2.3 Hard Constraints from Gotchas

| Constraint | Implementation Approach | Framework Need |
|-----------|------------------------|---------------|
| Only rank from longlist × allowed strategies | **Programmatic**: validate target set before any reasoning | Pre-pipeline validation step |
| Organism match check on all external data | **Tool-level**: every data-fetching tool validates organism | Tool wrapper / middleware |
| Single canonical ranking table | **Pipeline**: all outputs derive from one DataFrame | Pipeline architecture |
| Pre-filter novel-only before reasoning | **Programmatic**: filter at target construction, audit count | Stage 1 hard gate |
| Citation backing for all claims | **System prompt + output validation** | Dossier template enforcement |

---

## 3. The Case for a Meta-Prompting Framework

### 3.1 What GSD Demonstrates

GSD (Get Shit Done) provides a meta-prompting layer for Claude Code that transforms free-form agent sessions into **structured, auditable, resumable workflows**. Its key patterns:

| GSD Pattern | Relevance to Your Pipeline |
|-------------|---------------------------|
| **Plans as executable prompts** | Each pipeline stage (target construction, evidence aggregation, scoring, dossier) becomes a structured prompt with inputs, outputs, and verification criteria |
| **Goal-backward verification** | "Did we actually produce valid rankings?" not just "did we run all the tools?" |
| **Specialized subagents** | Evidence researcher, scorer, verifier, dossier writer — each with focused system prompts |
| **Wave-based parallel execution** | Parallel evidence stream computation (independent streams computed simultaneously) |
| **Checkpoint gates** | Human-in-the-loop at critical points (evidence plan approval, ranking review) |
| **STATE.md session memory** | Resume long-running shortlisting jobs across sessions |
| **Frontmatter-driven orchestration** | Pipeline stage metadata (dependencies, inputs, outputs) in versioned files |
| **Atomic commits per task** | Full git audit trail for each pipeline step |
| **Config-driven behaviour** | Project spec as config → deterministic pipeline behaviour |

### 3.2 What Your Pipeline-Specific Meta-Layer Needs

Your meta-prompting framework would be more specialised than GSD. Rather than general-purpose software development, it would orchestrate a **scientific evidence integration pipeline**:

```
┌─────────────────────────────────────────────────────┐
│               Meta-Prompting Framework               │
│                                                      │
│  Project Spec (JSON)                                 │
│       │                                              │
│       ▼                                              │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Stage 1   │  │ Stage 2       │  │ Stage 3        │ │
│  │ Target    │→│ Evidence      │→│ Scoring &      │ │
│  │ Construct │  │ Aggregation   │  │ Ranking        │ │
│  └──────────┘  └──────────────┘  └───────────────┘  │
│       │              │                   │           │
│       │         ┌────┴─────┐             │           │
│       │         │ Parallel │             │           │
│       │         │ Streams  │             │           │
│       │         └────┬─────┘             │           │
│       ▼              ▼                   ▼           │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Gate:     │  │ Gate:         │  │ Gate:          │ │
│  │ Valid     │  │ Coverage      │  │ Ranking        │ │
│  │ Targets?  │  │ Sufficient?   │  │ Sane?          │ │
│  └──────────┘  └──────────────┘  └───────────────┘  │
│                                          │           │
│                                          ▼           │
│                                   ┌───────────────┐  │
│                                   │ Stage 4        │ │
│                                   │ Dossier Gen    │ │
│                                   └───────────────┘  │
└─────────────────────────────────────────────────────┘
```

Key differences from GSD:
- **Domain-specific stages** instead of generic phases
- **Mathematical specifications** baked into stage prompts (the formulas from §3.5 of your spec)
- **Data validation gates** (organism checks, target set validation) instead of code quality gates
- **Evidence provenance tracking** instead of git commit tracking
- **Scoring reproducibility** (transform_spec versioning) instead of test suite verification

### 3.3 Proposed Subagent Architecture

Drawing from GSD's patterns but specialised for your pipeline:

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **target-constructor** | Enumerate gene × strategy combinations, enforce constraints | Project spec + longlist + allowed strategies | Validated target table |
| **evidence-planner** | Identify relevant studies & evidence streams per project | Project spec + available databases + target table | Evidence plan (streams + justifications) |
| **evidence-researcher** | Compute a single evidence stream across all targets | Stream definition + target table + data sources | Raw evidence vector + normalised scores |
| **stream-scorer** | Assign reliability & applicability, validate independence | Evidence streams + project spec | Scored stream table |
| **metric-integrator** | Execute §3.5 pseudo-posterior update formula | Scored streams + priors + exclusion rules | Ranking table + audit tables |
| **ranking-verifier** | Check guardrails (§3.6): coverage, conflicts, comparability | Ranking table + evidence attribution | Verification report |
| **dossier-writer** | Generate structured target dossiers | Top-K targets + all evidence + ranking | Formatted dossiers |
| **organism-validator** | Cross-check all external data references against project species | Data references + project spec | Validation report |

---

## 4. Concrete Build Strategy

### 4.1 Phase 1: Foundation (Replatform celltype-cli for Ag-Biotech)

**Effort: Medium | Risk: Low**

1. **Fork and rebrand** — rename from `ct` to your product name
2. **Replace system prompt** — swap oncology domain knowledge for plant science domain knowledge
3. **Add plant data loaders** — PlantExp RNA-seq, PlantTFDB, Ensembl Plants, Phytozome, TAIR, Gramene, STRING (plant)
4. **Add plant science tools** — new tool categories:
   - `plant_genomics.*` — GFF parsing, plant GWAS, QTL lookup, ortholog mapping
   - `gene_editing.*` — CRISPR guide design, PAM analysis, regulatory element mapping, editability scoring
   - `coexpression.*` — co-expression network construction, cluster analysis, centrality metrics
   - `orthology.*` — OrthoFinder integration, cross-species evidence with distance weighting
   - `literature_ag.*` — plant-specific PubMed queries, patent search (Lens.org)
5. **Add organism validation middleware** — tool wrapper that checks species consistency

### 4.2 Phase 2: Pipeline Framework (Meta-Prompting Layer)

**Effort: High | Risk: Medium**

1. **Define pipeline stages as executable specifications** (analogous to GSD's PLAN.md):
   - Each stage has: inputs schema, outputs schema, validation criteria, mathematical specification
   - Stages are versioned and reproducible
2. **Build stage orchestrator** — replaces free-form agent loop for pipeline runs:
   - Reads project_spec.json → enumerates stages → executes in order → gates between stages
   - Supports parallel evidence stream computation within Stage 2
3. **Build pipeline state management** (analogous to GSD's STATE.md):
   - Tracks: current stage, completed evidence streams, computed metrics, exclusion audit
   - Enables resume after interruption
4. **Implement hard guardrails as code** (not prompts):
   - Target set validation (programmatic, not agent-judged)
   - Organism match checking (programmatic)
   - Output schema validation (programmatic)
5. **Build evidence stream framework**:
   - `EvidenceStream` class with raw_extraction, normalisation_spec, exclusion_rule_spec
   - `transform_spec` DSL for reproducible transforms
   - Batch scoring pipeline with coverage tracking

### 4.3 Phase 3: Scoring Engine (Mathematical Core)

**Effort: Medium | Risk: Low**

This is mostly computational — the sandbox already supports pandas/numpy/scipy:

1. **Implement §3.3 batch normalisation** — percentile, z-score, rank-based with clipping
2. **Implement §3.4 exclusion gating** — χ functions, global eligibility, audit output
3. **Implement §3.5 pseudo-posterior** — prior + delta update + squashing + weighted aggregation
4. **Implement §3.6 guardrails** — coverage tracking, conflict detection
5. **Output tables** — evidence stream table (§3 output 1), target attribution table (§3 output 2)

This could be implemented as a Python module (not an agent tool) that the pipeline orchestrator calls directly.

### 4.4 Phase 4: Dossier Generation

**Effort: Medium | Risk: Low**

1. **Define dossier template** matching §4 spec (executive summary, quantitative profile, mechanistic hypothesis, editing strategy, uncertainties, validation priorities, references)
2. **Build dossier agent** — specialised system prompt + output schema enforcement
3. **Leverage existing report infrastructure** — markdown + HTML export already works

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Agent hallucination in evidence scoring** | High | Implement scoring as deterministic code, not agent judgement. Agent plans the pipeline; code executes it. |
| **Wrong organism data (Gotcha #2)** | High | Programmatic organism validation in every data-fetching tool. Reject mismatches before agent sees data. |
| **Inconsistent outputs (Gotcha #3)** | Medium | Schema-validated outputs. Dossier template with required fields. Post-generation validation. |
| **Post-hoc fixing (Gotcha #1)** | High | Pipeline stages with hard gates. Target set locked after Stage 1. No adding genes outside longlist. |
| **Claude context window limits** | Medium | Per-gene evidence fits in context. Multi-agent parallel streams keep per-agent context manageable. |
| **Reproducibility** | Medium | Transform_spec versioning + deterministic scoring code + project_spec content hash |

### 5.2 Strategic Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Plant data availability** | Medium | PlantExp exists; Ensembl Plants is comprehensive; STRING has plant networks. Gap: some species have thin data. |
| **Over-engineering the framework** | Medium | Start with hardcoded pipeline, abstract to framework only when you have 3+ project runs to learn from. |
| **Dependency on celltype-cli upstream** | Low | You've forked. Cherry-pick useful upstream changes; don't track main. |
| **Claude model changes** | Low | Agent SDK abstracts model. System prompts and tools are model-agnostic. |

---

## 6. What You Should NOT Reuse from celltype-cli

| Component | Why |
|-----------|-----|
| **DepMap/PRISM/L1000 loaders** | Human cancer datasets, zero plant relevance |
| **Chemistry tools** (9) | Drug chemistry, not gene editing |
| **Safety tools** (7) | Drug safety profiling (ADMET, DDI) |
| **Clinical tools** (7) | Clinical trials, not field trials |
| **Viability tools** (3) | Cell viability, not plant phenotyping |
| **CRO tools** (5) | Contract research organisations for pharma |
| **Combination tools** (3) | Drug combinations |
| **Structure tools** (8) | Protein structure docking for drug design |
| **Biomarker tools** (3) | Cancer biomarkers |
| **PK tools** (1) | Pharmacokinetics |

**~60 tools (31%) can be removed.** The remaining ~130 tools include general-purpose infrastructure (files, ops, code, statistics, literature, data APIs, omics, expression, genomics, network, protein) that are either directly useful or easily adapted.

---

## 7. Recommendation

### Build on celltype-cli: Yes, with a clear separation of concerns.

**Layer 1 — celltype-cli core (keep):**
- Agent SDK loop + MCP server + tool registry + sandbox + session management + UI + reporting
- This is your execution engine. It's well-built, tested, and extensible.

**Layer 2 — Plant science domain (build):**
- New tool categories, data loaders, system prompt, and domain knowledge
- This is your scientific capability layer.

**Layer 3 — Pipeline meta-framework (build):**
- Stage-based orchestration, evidence stream framework, scoring engine, guardrails, audit tables
- This is your quality and reproducibility layer — the thing that prevents the gotchas.
- Draw heavily from GSD's patterns (plans as prompts, goal-backward verification, checkpoint gates, state management) but implement domain-specific stages rather than generic software development phases.

**The key insight:** celltype-cli gives you a strong "Layer 1" that would take months to build from scratch. GSD's patterns give you a proven blueprint for "Layer 3". The novel work is Layer 2 (plant science tools and data) and adapting Layer 3's patterns to a scientific pipeline context rather than a software development context.

### Estimated Effort Distribution

| Layer | Effort | Timeline Estimate |
|-------|--------|-------------------|
| Layer 1: Replatform celltype-cli | 15% | Fork, strip pharma tools, rebrand |
| Layer 2: Plant science domain | 40% | Data loaders, tools, system prompt, domain knowledge |
| Layer 3: Pipeline meta-framework | 45% | Orchestration, scoring engine, guardrails, audit infrastructure |

### First Milestone Suggestion

Build a minimal end-to-end pipeline for a single species (e.g., Arabidopsis) with:
- 3 evidence streams (literature novelty, expression breadth, ortholog evidence)
- 2 output metrics (novelty, efficacy)
- Hardcoded pipeline (no meta-framework yet)
- Validates the tool→evidence→scoring→ranking→dossier flow works

Then abstract the pipeline into a framework once you understand the real-world iteration patterns from 2-3 customer projects.

---

## Addendum: Repo Architecture — One Repo or Two?

*Added for review by future implementing agents.*

### The Question

Claude Code and GSD are two separate repos/products. Claude Code is the open-ended flexible tool; GSD is the opinionated framework built on top. Nothing stops you building a gsd-finance or gsd-biotech for different domains. Should we follow the same pattern here — `cli-ag` as the engine and `cli-gsd` (or similar) as the opinionated shortlisting workflow?

### Why the Analogy Is Imperfect

GSD never touches Claude Code's source code. It works through a **stable, well-defined extension interface**: `CLAUDE.md` instructions, `~/.claude/agents/` prompt files, skill definitions. GSD is pure prompt engineering layered on top. The interface boundary is clean and narrow.

Our situation is different. The coupling between engine and framework is much tighter. Here's where each component of the product spec actually lives:

| Component | Engine or Framework? | Rationale |
|-----------|---------------------|-----------|
| Plant data loaders (PlantExp, Ensembl Plants, TAIR) | **Engine** | These are tools, not workflow logic |
| Plant science tools (co-expression, orthology, GFF parsing) | **Engine** | Registered tools in the tool registry |
| Plant-domain system prompt | **Engine** | Core agent identity |
| `code.execute` sandbox | **Engine** | Already exists |
| Literature/genomics/expression tools | **Engine** | Already exist or are tool-level additions |
| Scoring engine (normalisation, exclusion gating, pseudo-Bayesian update) | **Straddles** | Python code, but only exists to serve the shortlisting workflow |
| Pipeline stage orchestration | **Framework** | The meta-prompting layer |
| Project spec schema + parsing | **Framework** | Workflow-specific |
| Evidence stream definitions + transform DSL | **Framework** | Workflow-specific |
| Guardrails (organism validation, target set locking) | **Straddles** | Some engine-level (organism check on every API call), some workflow-level (target set locking) |
| Dossier templates | **Framework** | Workflow-specific output format |
| Pipeline state management | **Framework** | Workflow-specific |

~50% of what needs to be built is engine-level work (plant tools, data loaders, domain prompt). Separating into two repos from day one means maintaining two repos where most early development is in the engine anyway, and the framework repo is thin and tightly coupled to engine internals that don't yet have a stable interface.

### Recommendation from claude code: One Repo Now, Designed for Eventual Separation

Start with one repo but **organise it internally** so that the engine and framework layers are distinct packages:

```
src/
├── ct/                          # Engine (the "cli-ag" layer)
│   ├── agent/                   # Agent loop, MCP server, system prompt
│   ├── tools/                   # All registered tools (plant + general)
│   ├── data/                    # Data loaders
│   ├── models/                  # LLM client
│   └── ui/                      # Interactive terminal
│
├── shortlist/                   # Framework (the "cli-gsd" layer)
│   ├── pipeline/                # Stage orchestration, state management
│   ├── scoring/                 # Normalisation, exclusion, pseudo-Bayesian engine
│   ├── evidence/                # Evidence stream framework, transform DSL
│   ├── specs/                   # Project spec schema, validation
│   ├── dossier/                 # Dossier templates, generation
│   └── guardrails/              # Pipeline-level validation
```

**Critical discipline:** `shortlist.*` imports from `ct.*`, never the reverse. The `shortlist/` package should use the same public interfaces (tool registry, agent runner, config system) that any other framework would use. This one-way dependency is what makes future extraction possible.

This gives you:
- **Clean import boundary** enforced by convention (and lintable)
- **Single repo convenience**: one test suite, one CI pipeline, shared fixtures
- **Extractable later**: `shortlist/` can become its own package with `ct` as a dependency when needed

### When to Actually Separate

Separate into two repos when any of these become true:
1. A second workflow framework is needed (e.g., "field trial design" or "regulatory submission" pipeline)
2. The engine should be shipped to users who don't need shortlisting
3. The framework's release cadence diverges significantly from the engine's
4. A second team is working on one layer but not the other

None of these seem imminent. Premature separation would cost: two CI pipelines, cross-repo version pinning, integration testing across repos, and a stable engine API that needs to be designed before it's been used enough to know what the right API is.

### The Real Lesson from GSD

The thing GSD gets right isn't the repo separation — it's the **conceptual separation**. GSD's authors thought clearly about "what is orchestration logic?" vs "what is the execution engine?" and kept those concerns distinct. We should do the same in code organisation, even within one repo. That discipline is what makes future extraction possible, not the repo boundary itself.
