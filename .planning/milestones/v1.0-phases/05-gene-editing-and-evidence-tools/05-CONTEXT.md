# Phase 5: Gene Editing and Evidence Tools - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver three atomic tools — CRISPR guide design, editability scoring, and paralogy scoring — plus a local bioinformatics CLI tool invocation pattern. The multi-species evidence gathering capability (TOOL-09) is validated as an end-to-end test proving the agent can compose tools from Phases 3-5, not built as a new tool.

The overarching philosophy: build atomic tools the agent can compose. Scoring rubrics, orchestration logic, and opinionated evidence-gathering workflows belong in meta-prompting / M2 pipeline framework — not baked into the tools themselves.

</domain>

<decisions>
## Implementation Decisions

### CRISPR guide design (editing.crispr_guide_design)
- Extensible Cas system registry — pluggable architecture for adding new nucleases
- Ship SpCas9 (NGG PAM) and Cas12a/Cpf1 (TTTV PAM) for M1
- Off-target prediction via local alignment against reference genome
- Data resolution chain for genome FASTA: user-provided file > locally cached reference > auto-download from NCBI
- Guide scoring returns both a ranked list with composite on-target scores AND tier classification (high confidence / acceptable / poor) per guide
- Return all viable guides, capped at 20 per default
- Each guide includes: on-target score, off-target count, GC%, position in gene, tier label

### Editability scoring (editing.editability_score)
- Thin wrapper / convenience aggregator — calls guide design + gene structure + regulatory info tools
- Returns structured per-factor sub-scores (guide quality, structure complexity, regulatory complexity)
- No opinionated composite score or weighting — the agent or downstream pipeline decides what "editable" means in context
- Atomic tools philosophy: this is a building block, not a scoring engine

### Paralogy scoring (genomics.paralogy_score)
- Data resolution: OrthoFinder results (local) > Ensembl Compara API (fallback)
- Returns paralog count, co-expression overlap with paralogs, shared GO annotations
- Follows same local-first philosophy as off-target prediction

### Evidence gathering (TOOL-09)
- NOT a new tool — validated as an end-to-end test
- Test: given a gene list and species, verify the agent naturally chains expression, ortholog, GWAS, PPI, literature, and editing tools into a structured per-gene evidence summary
- If the agent can't compose the workflow naturally, that's a signal for system prompt tuning or M2 meta-prompting — not a new tool

### Local bioinformatics tool invocation (new infrastructure)
- New shell executor utility — wraps subprocess calls with timeout, error handling, "tool not installed" detection
- Pluggable tool registry for adding new bioinformatics tools over time
- Minimum tool set for M1: BLAST+, OrthoFinder, Bowtie2/minimap2
- Graceful degradation: if a local tool isn't installed, fall back to API equivalent where available
- Establishes the reusable pattern for all future local tool integrations

### Claude's Discretion
- Shell executor design and API (dedicated utility vs. other patterns)
- Guide scoring algorithms (Rule Set 2, DeepCpf1, or simpler heuristics)
- Editability sub-score definitions and factor extraction approach
- Bowtie2 vs. minimap2 selection for off-target alignment
- NCBI genome download mechanism and caching strategy
- Bioinformatics tool registry design

</decisions>

<specifics>
## Specific Ideas

- "The goal isn't to create crazy comprehensive scoring rules but to create an agent with the necessary atomic tools so that scoring rubrics can be added on top" — tools are building blocks for the M2 pipeline framework
- Local data and tools should always dominate over API calls — APIs are fallbacks for when local resources aren't available
- The data resolution chain (user-provided > local cached > API fallback) should be consistent across all tools
- OrthoFinder preference over Ensembl Compara for both orthology and paralogy when local data exists (note: retrofitting ortholog_map is Phase 4 scope, capture for backlog)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `genomics.ortholog_map`: Ensembl Compara integration pattern — reusable for paralogy API fallback
- `genomics.gene_annotation`: GO term and function lookup — feeds into paralogy shared-annotation scoring
- `genomics.coexpression_network`: Co-expression data — feeds into paralogy co-expression overlap
- `genomics.gff_parse`: Gene structure extraction — feeds into editability gene structure factor
- `_species.py`: Species resolution (taxon ID, binomial, genome build) — used by all new tools
- `_api_cache.py`: API response caching — reusable for Ensembl/NCBI calls
- `http_client.py`: HTTP request utility with retries — pattern to mirror for local CLI executor

### Established Patterns
- `@registry.register()` decorator for all tools — new editing tools follow this exactly
- All tools return `{"summary": "...", ...}` dict pattern
- Lazy imports for data loaders inside function bodies
- Tools accept `**kwargs` for framework compatibility
- Species validation via `resolve_species_taxon()` at tool entry

### Integration Points
- New `src/ct/tools/editing.py` module for CRISPR and editability tools
- `genomics.paralogy_score` added to existing `src/ct/tools/genomics.py`
- New shell executor utility (likely `src/ct/tools/_local_tools.py` or similar)
- Category allowlist in Phase 1 filtering needs "editing" added to plant-allowed categories

</code_context>

<deferred>
## Deferred Ideas

- Retrofit `genomics.ortholog_map` to support local-first OrthoFinder data — Phase 4 scope, not Phase 5
- Expand bioinformatics toolbelt beyond BLAST+/OrthoFinder/Bowtie2 — future phases as needed
- Meta-prompting framework for evidence orchestration workflows — M2 pipeline scope
- Opinionated scoring rubrics and composite editability scores — M2 pipeline scope

</deferred>

---

*Phase: 05-gene-editing-and-evidence-tools*
*Context gathered: 2026-03-02*
