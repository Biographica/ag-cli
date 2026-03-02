# Phase 5: Gene Editing and Evidence Tools - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

The agent can assess CRISPR guide design and editability for any gene, score paralogy and functional redundancy risk, and orchestrate multi-species evidence collection across the full M1 tool suite for a provided gene list. This is the capstone phase — it builds on all prior tools (gene_annotation, ortholog_map, coexpression_network, gff_parse, gwas_qtl_lookup, string_ppi, pubmed_plant_search) to deliver gene editing assessment and evidence gathering capabilities.

</domain>

<decisions>
## Implementation Decisions

### CRISPR Guide Design
- Sequence-aware PAM scanning: tool fetches CDS/exon sequence and scans for PAM sites, scores guides by GC content and position
- SpCas9 only (NGG PAM) for M1 — the workhorse covering the vast majority of plant CRISPR work
- Sequence source: Ensembl Plants API fetch by gene ID, with fallback to user-provided raw sequence
- Off-target prediction is NOT computed by the tool — the agent handles off-target reasoning narratively using knowledge.py domain context (CRISPOR references, polyploid homeolog considerations)
- Tool registers under a new `editing` category (must be added to PLANT_SCIENCE_CATEGORIES in `src/ct/tools/__init__.py`)

### Editability Scoring
- Three factors as specified in roadmap: guide availability, gene structure complexity, regulatory region breadth
- Polyploidy and paralogy are NOT part of the editability score — they live in their own dedicated tools
- Score format: multi-dimensional with composite — return per-factor scores (guide_score, structure_score, regulatory_score) AND a 0-1 composite for ranking
- Gene structure data: Ensembl Plants API primary, local GFF fallback via gff_parse if available
- Registers under `editing` category

### Paralogy & Redundancy Assessment
- Paralog discovery: Ensembl Compara paralog endpoint (homology/id with type=paralogues) — same API family as ortholog_map
- Full redundancy assessment matching roadmap success criterion: paralog count + shared GO terms + co-expression overlap
- Output: per-paralog detail table (identity %, shared GO count, co-expression correlation) plus overall redundancy risk score (high/medium/low or 0-1)
- Registers under `genomics` category (alongside ortholog_map)

### Evidence Gathering Orchestration
- Single orchestrator tool: `evidence.gather_evidence` takes a gene list + species and internally calls all relevant tools
- Seven evidence sources: expression (coexpression_network), ortholog (ortholog_map), GWAS (gwas_qtl_lookup), PPI (string_ppi), literature (pubmed_plant_search), gene annotation (gene_annotation), editability (editability_score)
- Output: structured dict per gene, with keys for each evidence type containing the tool results. Agent synthesizes narratively.
- Registers under a new `evidence` category (must be added to PLANT_SCIENCE_CATEGORIES)

### Claude's Discretion
- Guide design output format — as long as it includes guide sequence, position, strand, and quality indicator
- Whether editability_score calls crispr_guide_design internally or expects pre-computed input
- Whether paralogy_score calls gene_annotation/coexpression_network internally or has its own implementation
- Sequential vs. batch processing strategy for evidence gathering
- Internal composition patterns for all tools (call existing registered tools vs. independent implementation)

</decisions>

<specifics>
## Specific Ideas

- knowledge.py already contains detailed CRISPR domain knowledge (PAM requirements, delivery methods, off-target risk in polyploids, editing outcomes) at lines 172-204 — the agent can reason about editing context narratively without the tools needing to compute everything
- The evidence gathering tool should produce a complete picture for each gene — the kind of summary a researcher would compile manually across databases
- Editability composite score enables ranking genes by editing feasibility, which feeds directly into M2's shortlisting pipeline

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `genomics.gene_annotation` (line 1391): GO terms, function, publications — feeds paralogy GO overlap and evidence gathering
- `genomics.ortholog_map` (line 1762): Ensembl Compara API pattern — paralogy tool uses same API family (paralogues endpoint)
- `genomics.coexpression_network` (line 2160): ATTED-II co-expression — feeds paralogy co-expression overlap
- `genomics.gff_parse` (line 1919): GFF3 parsing — fallback for gene structure in editability scoring
- `genomics.gwas_qtl_lookup` (line 1560): GWAS evidence — feeds evidence gathering
- `network.string_ppi`: PPI evidence — feeds evidence gathering
- `literature.pubmed_plant_search`: Literature evidence — feeds evidence gathering
- `knowledge.py` (lines 172-270): CRISPR domain knowledge, cross-disciplinary thinking patterns — agent reasoning context

### Established Patterns
- Tool registration: `@registry.register()` with category, parameters, optional `requires_data`
- API caching: `_api_cache` module for Ensembl REST API responses
- Species validation: `_species.py` backed by `species_registry.yaml`
- Error handling: always return dict with `summary` key, never raise
- Lazy imports: data loaders imported inside function body
- Neutral messaging: no species-first language, generic sparse-result messages (established in Phase 4 plan 04-04)

### Integration Points
- `PLANT_SCIENCE_CATEGORIES` in `src/ct/tools/__init__.py` (line 21): must add `editing` and `evidence` categories
- `src/ct/tools/genomics.py`: paralogy_score goes here alongside existing genomics tools
- New file needed: `src/ct/tools/editing.py` for CRISPR guide design and editability scoring
- New file needed: `src/ct/tools/evidence.py` for the evidence gathering orchestrator
- `src/ct/agent/knowledge.py`: CRISPR/editing knowledge already present — no additions needed

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-gene-editing-and-evidence-tools*
*Context gathered: 2026-03-02*
