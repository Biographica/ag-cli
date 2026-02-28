# Roadmap: ag-cli (Milestone 1 — Working Plant Science Agent)

## Overview

This roadmap covers Milestone 1 only: transforming a fork of celltype-cli into a working plant science agent. The journey runs from stripping out oncology domain knowledge (Phase 1), through building local-first data infrastructure with organism validation (Phase 2), wiring in external API connectors (Phase 3), implementing core plant genomics tools (Phase 4), and finishing with gene editing assessment tools plus the multi-species evidence gathering capability that ties the full agent together (Phase 5). At the end of Phase 5, the agent can receive open-ended plant science research questions and execute multi-step tool-orchestrated workflows across species.

Milestone 2 (Shortlisting Pipeline Framework) is v2 scope and not represented here.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Fork setup, plant system prompt, runtime pharma tool filtering, and rebranding (completed 2026-02-25)
- [x] **Phase 2: Data Infrastructure** - Local-first data loader pattern, species registry, manifest system, organism validation (gap closure in progress) (completed 2026-02-25)
- [x] **Phase 2.1: Integration Fixes** - INSERTED — Fix cross-phase wiring issues found by milestone audit (species default form, parity YAML backing, stale branding) (completed 2026-02-26)
- [ ] **Phase 2.2: Integration Fixes II** - INSERTED — Fix CLI routing bug for species subcommand and missing PyYAML dependency found by re-audit
- [x] **Phase 3: External Connectors** - STRING, PubMed, and Lens.org API connectors with plant-specific query construction (completed 2026-02-26)
- [ ] **Phase 4: Plant Genomics Tools** - Gene annotation, ortholog mapping, co-expression analysis, GFF parsing, GWAS/QTL lookup
- [ ] **Phase 5: Gene Editing and Evidence Tools** - CRISPR guide design, editability scoring, paralogy scoring, multi-species evidence gathering

## Phase Details

### Phase 1: Foundation
**Goal**: ag-cli operates as a plant science agent — answering open-ended plant biology questions using the inherited agentic loop, without surfacing pharma tools or oncology reasoning
**Depends on**: Nothing (first phase)
**Requirements**: FOUN-01, FOUN-02, FOUN-03, FOUN-04
**Success Criteria** (what must be TRUE):
  1. Running `ag "what is the function of FT in Arabidopsis?"` returns a plant-focused answer with no oncology, drug discovery, or clinical framing in the response
  2. Running `ct tool list` shows only plant-relevant and general-purpose tools; pharma-category tools (chemistry, clinical, safety, CRO, viability, combination, structure, biomarker, PK) are absent from the active list
  3. Every tool call accepts `species` as an explicit parameter and no tool has a hardcoded species reference
  4. The CLI command is `ag` (not `ct`) and `ag --version` returns the ag-cli version correctly
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Plant science system prompt and category allowlist filtering (FOUN-01, FOUN-02)
- [x] 01-02-PLAN.md — Species-agnostic architecture and CLI rebranding (FOUN-03, FOUN-04)

### Phase 2: Data Infrastructure
**Goal**: The agent can access and explore local curated plant datasets through a versioned manifest system with programmatic organism validation on every data access
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04
**Success Criteria** (what must be TRUE):
  1. The agent can load and query a local PlantExp expression dataset using the Python sandbox (parquet/CSV) and return tissue-level expression values for a given gene and species
  2. A manifest file exists for each data folder describing available datasets, species covered, schema, and content hash; the agent reads the manifest to discover what data is available before loading files
  3. A tool call specifying `species="arabidopsis_thaliana"` on a dataset containing only rice data returns an organism validation error, not silently mismatched results
  4. `ag species list` (or equivalent) returns a registry of supported species with taxon ID, common name, and genome build
**Plans**: 4 plans

Plans:
- [x] 02-01-PLAN.md — Species registry YAML, manifest loader, ag species list CLI command (DATA-02, DATA-04)
- [x] 02-02-PLAN.md — Organism validation middleware (@validate_species decorator) (DATA-03)
- [x] 02-03-PLAN.md — Plant data tools (data.list_datasets, data.load_expression) and downloader entry (DATA-01)
- [x] 02-04-PLAN.md — Gap closure: fix unknown-species default (0 not Arabidopsis) and genome_build docs (DATA-02)

### Phase 2.1: Integration Fixes (INSERTED)
**Goal**: All cross-phase wiring between Phase 1 and Phase 2 works correctly — no spurious warnings, no standalone species maps diverging from the YAML registry, no stale CLI branding in user-facing output
**Depends on**: Phase 2
**Requirements**: DATA-03, DATA-04, FOUN-03, FOUN-04 (gap closure — requirements already satisfied but integration checker found wiring issues)
**Gap Closure**: Closes integration gaps from v1.0 milestone audit
**Success Criteria** (what must be TRUE):
  1. `data.load_expression()` called with no species argument does NOT emit a "not in registry" warning for Arabidopsis (the default species)
  2. `parity.mygene_lookup` resolves species via `_species.py` backed by `species_registry.yaml`, not a standalone hardcoded dict
  3. `ag data pull plantexp` output says `ag config set` not `ct config set`
  4. No user-facing CLI output references `ct` instead of `ag`
**Plans**: 1 plan

Plans:
- [x] 02.1-01-PLAN.md — Fix species default form, wire parity to YAML registry, fix stale branding (DATA-03, DATA-04, FOUN-03, FOUN-04)

### Phase 2.2: Integration Fixes II (INSERTED)
**Goal**: CLI routing correctly dispatches `ag species list` to the species subcommand, and clean installs succeed without missing PyYAML dependency
**Depends on**: Phase 2.1
**Requirements**: DATA-01, DATA-02, DATA-04 (gap closure — requirements satisfied but integration bugs found in re-audit)
**Gap Closure**: Closes integration gaps from v1.0 re-audit
**Success Criteria** (what must be TRUE):
  1. Running `ag species list` via the installed CLI entry point dispatches to the species subcommand and returns the species registry (not a natural-language query)
  2. A clean `pip install` in a fresh virtualenv succeeds and `import yaml` works in `_species.py` and `manifest.py`
**Plans**: 1 plan

Plans:
- [ ] 02.2-01-PLAN.md — Fix species CLI routing and add PyYAML dependency (DATA-01, DATA-02, DATA-04)

### Phase 3: External Connectors
**Goal**: The agent can query STRING plant PPI networks, search PubMed with plant-specific queries, and retrieve patent data from Lens.org as evidence sources in a research workflow
**Depends on**: Phase 2
**Requirements**: CONN-01, CONN-02, CONN-03
**Success Criteria** (what must be TRUE):
  1. The agent can retrieve protein–protein interaction partners and confidence scores for a plant gene from STRING via the `interactions.string_plant_ppi` tool, with organism validation applied before the API call
  2. The agent can run a PubMed search with plant-specific query construction (species name, gene synonym expansion) via the `literature.pubmed_plant_search` tool and return structured citation results
  3. The agent can retrieve patent records for a gene or trait from Lens.org via the `literature.lens_patent_search` tool and summarise the patent landscape
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — Disk cache helper, STRING plant PPI connector, config registration (CONN-01)
- [ ] 03-02-PLAN.md — PubMed plant search, Lens.org patent search, MCP hiding (CONN-02, CONN-03)

### Phase 4: Plant Genomics Tools
**Goal**: The agent can look up gene annotations, map orthologs across species, analyse co-expression networks, parse genome annotations, and retrieve GWAS/QTL evidence — giving it the genomics reasoning capability needed for plant target research
**Depends on**: Phase 2
**Requirements**: TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05
**Success Criteria** (what must be TRUE):
  1. The agent can return GO terms, functional description, and linked publications for any gene in any supported species using `genomics.gene_annotation`
  2. The agent can map a query gene to its orthologs in one or more target species, with phylogenetic distance weights applied, using `genomics.ortholog_map`
  3. The agent can retrieve co-expression cluster membership, network centrality metrics, and GO enrichment for a gene from a local expression dataset using `genomics.coexpression_network`
  4. The agent can parse a GFF3 file and extract exon structure, UTR boundaries, and intron positions for a gene using `genomics.gff_parse`
  5. The agent can look up GWAS hits and QTL intervals for a trait and species combination using `genomics.gwas_qtl_lookup`
**Plans**: TBD

Plans:
- [ ] 04-01: Gene annotation and GWAS/QTL lookup tools
- [ ] 04-02: Ortholog mapping with phylogenetic distance weighting
- [ ] 04-03: GFF3 parsing and co-expression network tools

### Phase 5: Gene Editing and Evidence Tools
**Goal**: The agent can assess CRISPR guide design and editability for any gene, score paralogy and functional redundancy risk, and orchestrate multi-species evidence collection across the full M1 tool suite for a provided gene list
**Depends on**: Phase 3, Phase 4
**Requirements**: TOOL-06, TOOL-07, TOOL-08, TOOL-09
**Success Criteria** (what must be TRUE):
  1. The agent can enumerate PAM sites, score guide RNAs, and flag predicted off-targets for a gene in a supported species using `editing.crispr_guide_design`
  2. The agent can return a composite editability score for a gene based on guide availability, gene structure complexity, and regulatory region breadth using `editing.editability_score`
  3. The agent can return a paralogy and functional redundancy assessment (paralog count, co-expression overlap with paralogs, shared GO annotations) for a gene using `genomics.paralogy_score`
  4. Given a list of 5+ genes and a target species, the agent executes a multi-step evidence collection workflow — spanning expression, ortholog, GWAS, PPI, and literature sources — and synthesises findings into a structured per-gene evidence summary
**Plans**: TBD

Plans:
- [ ] 05-01: CRISPR guide design and editability scoring tools
- [ ] 05-02: Paralogy scoring tool
- [ ] 05-03: Multi-species evidence gathering orchestration (TOOL-09)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 2.1 -> 2.2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete    | 2026-02-25 |
| 2. Data Infrastructure | 4/4 | Complete   | 2026-02-25 |
| 2.1 Integration Fixes | 1/1 | Complete | 2026-02-26 |
| 2.2 Integration Fixes II | 0/1 | Not started | - |
| 3. External Connectors | 2/2 | Complete   | 2026-02-26 |
| 4. Plant Genomics Tools | 2/3 | In Progress|  |
| 5. Gene Editing and Evidence Tools | 0/3 | Not started | - |
