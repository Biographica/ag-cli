# Requirements: ag-cli

**Defined:** 2026-02-25
**Core Value:** A working plant science agent that can explore local curated data, query external databases, and run computational biology analyses across plant species — the engine on which a structured shortlisting pipeline will later be built.

## v1 Requirements

Requirements for Milestone 1: Working Plant Science Agent.

### Foundation

- [x] **FOUN-01**: Agent uses plant science system prompt replacing all oncology domain knowledge
- [x] **FOUN-02**: Runtime domain-based tool filtering hides pharma-specific tools (chemistry, clinical, safety, CRO, viability, combination, structure, biomarker, PK) from the agent
- [x] **FOUN-03**: Species-agnostic architecture — no hardcoded species; species passed as parameter to all tools
- [x] **FOUN-04**: CLI and pyproject.toml rebranded from celltype-cli to ag-cli

### Data Access

- [x] **DATA-01**: Agent can explore and analyse data from a local project folder (parquets, CSVs, GFFs) using the Python sandbox
- [x] **DATA-02**: Data manifest pattern — each data folder has a manifest (JSON/YAML) describing available datasets, species, schema, and provenance
- [x] **DATA-03**: Organism validation middleware — tools that access external data validate species consistency before returning results
- [x] **DATA-04**: Species registry — central registry of supported species with metadata (taxon ID, common name, genome build)

### External Connectors

- [x] **CONN-01**: User can query STRING plant PPI networks via API for protein interaction evidence
- [x] **CONN-02**: User can search PubMed with plant-specific query construction for literature evidence
- [x] **CONN-03**: User can search Lens.org for patent landscape and novelty assessment

### Plant Science Tools

- [x] **TOOL-01**: User can look up gene annotation (GO terms, function, description, linked publications) for any gene in any supported species
- [x] **TOOL-02**: User can map orthologs across plant species with phylogenetic distance weighting
- [ ] **TOOL-03**: User can run co-expression network analysis (cluster membership, centrality, enrichment) from expression data
- [ ] **TOOL-04**: User can parse GFF3 genome annotations and extract gene structure information
- [x] **TOOL-05**: User can look up GWAS/QTL evidence for trait-gene associations
- [ ] **TOOL-06**: User can assess CRISPR guide design (PAM sites, guide scoring, off-target prediction) for a gene
- [ ] **TOOL-07**: User can estimate editability of a gene based on gene structure, guide availability, and regulatory complexity
- [ ] **TOOL-08**: User can score paralogy/functional redundancy for a gene (paralog count, co-expression overlap, shared annotations)
- [ ] **TOOL-09**: User can gather evidence across species for a given gene list (multi-species evidence collection orchestrated by agent)

## v2 Requirements

Deferred to Milestone 2: Shortlisting Pipeline Framework.

### Pipeline Core

- **PIPE-01**: Project specification JSON schema (Pydantic-validated) with target_organism, allowed_strategies, metric weights
- **PIPE-02**: Target construction (longlist × allowed strategy enumeration) with constraint enforcement
- **PIPE-03**: Programmatic target set lock after construction — no agent additions
- **PIPE-04**: EvidenceStream class with transform DSL (raw extraction + normalisation_spec + exclusion_rule_spec)
- **PIPE-05**: Batch normalisation (percentile, z-score, rank-based with clipping, missingness handling)
- **PIPE-06**: Exclusion gating (hard pass/fail rules, global eligibility, audit reporting)
- **PIPE-07**: ScoringEngine — deterministic code for all scoring, never agent judgement
- **PIPE-08**: Transform spec versioning (content-hashed, replayable)

### Evidence Integration & Ranking

- **RANK-01**: Four output metrics: novelty, efficacy/causal confidence, pleiotropic risk, editability
- **RANK-02**: Pseudo-Bayesian posterior update (prior + delta + squashing + weighted aggregation per PRODUCT_SPEC.md §3.5)
- **RANK-03**: Configurable metric weights from project spec
- **RANK-04**: Evidence provenance and audit tables (long-format attribution, every score traceable)
- **RANK-05**: Single canonical ranking table — all outputs derive from one source
- **RANK-06**: Pipeline state management (stage-level checkpointing, resume after interruption)
- **RANK-07**: Evidence planning agent with scientist-in-the-loop review gate
- **RANK-08**: Dynamic metric re-weighting without re-running evidence computation
- **RANK-09**: Stream independence validation (correlation check gate)
- **RANK-10**: Coverage tracking and conflict detection guardrails

### Dossier Generation

- **DOSS-01**: Target dossier generation (executive summary, quantitative profile, mechanistic hypothesis, editing strategy, risks, uncertainties, validation priorities, references)
- **DOSS-02**: Per-target independent dossier generation (not one monolithic agent call)
- **DOSS-03**: Schema-enforced output (Pydantic model for all required sections)
- **DOSS-04**: Alternative editing strategy presentation with quantitative tradeoffs
- **DOSS-05**: Excel ranking table export and PDF report generation from canonical table

## Out of Scope

| Feature | Reason |
|---------|--------|
| Fully probabilistic Bayesian model (MCMC/variational) | Intractable likelihood estimation; opaque to customers; pseudo-Bayesian approach is sufficient |
| Agent-judged numerical scores | Hallucination risk in quantitative outputs; scoring must be deterministic code |
| Black-box ML scoring (transformer-based gene ranking) | Non-interpretable; breaks auditability requirement |
| Real-time collaboration | Single-user research tool; no near-term multi-user need |
| Field trial design pipeline | Different workflow; potential future framework |
| Dagster backend integration | Eventual goal; local-first data pattern for now |
| Mobile / web interface | CLI-first; web later if needed |
| Two-repo separation | One repo with clean internal separation; extract when needed |
| Deletion of pharma tools from codebase | Runtime filtering instead; keeps optionality |
| Bespoke data download/cleaning scripts per database | Dagster backend handles data curation; ag-cli reads from local folders |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUN-01 | Phase 1 | Complete (01-01) |
| FOUN-02 | Phase 1 | Complete (01-01) |
| FOUN-03 | Phase 1 | Complete |
| FOUN-04 | Phase 1 | Complete |
| DATA-01 | Phase 2, 2.2 | Complete (integration fix pending) |
| DATA-02 | Phase 2, 2.2 | Complete (integration fix pending) |
| DATA-03 | Phase 2 | Complete |
| DATA-04 | Phase 2, 2.2 | Complete (integration fix pending) |
| CONN-01 | Phase 3 | Complete |
| CONN-02 | Phase 3 | Complete |
| CONN-03 | Phase 3 | Complete |
| TOOL-01 | Phase 4 | Complete |
| TOOL-02 | Phase 4 | Complete |
| TOOL-03 | Phase 4 | Pending |
| TOOL-04 | Phase 4 | Pending |
| TOOL-05 | Phase 4 | Complete |
| TOOL-06 | Phase 5 | Pending |
| TOOL-07 | Phase 5 | Pending |
| TOOL-08 | Phase 5 | Pending |
| TOOL-09 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-25 after roadmap creation*
