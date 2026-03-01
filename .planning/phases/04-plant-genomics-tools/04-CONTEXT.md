# Phase 4: Plant Genomics Tools - Context

**Gathered:** 2026-02-28 (updated)
**Status:** Complete — context updated post-implementation for alignment check

<domain>
## Phase Boundary

Five computational genomics tools — gene annotation, ortholog mapping, co-expression analysis, GFF3 parsing, and GWAS/QTL lookup — that give the agent core genomics reasoning capability for plant target research. These are `genomics.*` category tools following the existing tool pattern.

</domain>

<decisions>
## Implementation Decisions

### Data Sources & APIs
- **Gene annotation:** Ensembl Plants REST API + UniProt. This combination is good for now. System should be deeply extensible for future source additions.
- **Ortholog mapping:** Ensembl Compara REST API (plants). Acceptable as an API connector, but local analysis tools (OrthoFinder) should be prioritised in future — see Strategic Direction below.
- **GWAS/QTL lookup:** Ensembl Plants phenotype endpoint as primary. Claude's discretion on adding richer sources (Gramene, TAIR) for better crop coverage — user wants good coverage but doesn't prescribe the source.
- **GFF3 parsing:** Local file path or auto-download from Ensembl Plants FTP. Cache downloaded GFFs.
- **Co-expression:** ATTED-II bulk download with user permission; API fallback if bulk download isn't wanted. Arabidopsis + rice only is acceptable — no data for other species returns clear messaging, not errors.

### Species Coverage
- **Crops should be treated as equals to Arabidopsis** — not tiered. All tools should try to return useful results for all supported species.
- When data genuinely doesn't exist for a species, return empty results with generic messaging ("data coverage is limited for this species") — NOT specific tool suggestions.
- Registry-gated validation with `force=True` escape hatch (consistent with Phase 3 pattern).
- Phylogenetic distance matrix: Claude's discretion on expanding coverage as needed.

### Tool Output & Behaviour
- **Annotation depth:** GO terms, function description, genomic location, PubMed IDs is the right level. KEGG/Reactome pathway data deferred for later.
- **Ortholog output:** Keep lean (IDs, scores, phylo weight). Agent can chain gene_annotation for details. Claude's discretion on whether to include brief annotations.
- **Tools should be atomic** — no assumptions about chaining order. Tool outputs should NOT prescribe what tool to call next.
- **Usage guides:** Neutral tone describing what the tool does and what it returns. May mention related tools neutrally but should not be opinionated about chaining order.
- **Sparse-result messaging:** Generic ("data coverage is limited for this species"), not specific tool suggestions like "try ortholog_map".

### Strategic Direction (Critical — Shapes Future Phases)
- **Local analysis tools over external API connectors.** The value of the agent is NOT in connecting to more external databases. It IS in running strong local analysis tools like OrthoFinder, InterProScan, etc.
- **New `analysis.*` tool category** for locally-installed computational biology tools that wrap CLI binaries (analysis.orthofinder, analysis.interproscan, etc.). Agent should prefer these over external APIs.
- **Private data backend (Dagster):** Future phase should connect to a private Dagster data catalogue for controlled data quality and harmonisation, replacing external API dependencies.
- **Don't over-invest in external data connectors** at this stage. Ensure current connectors work, but future effort should go toward local computation capability.

### Claude's Discretion
- GWAS/QTL additional data sources for crop coverage
- Co-expression data: GO enrichment computation approach
- Phylogenetic distance matrix expansion
- Ortholog output: whether to include brief functional annotations
- Usage guide wording (neutral tone, no chaining directives)

</decisions>

<specifics>
## Specific Ideas

- All tools follow the existing `@registry.register()` pattern with `**kwargs` and dict return with `summary` key
- Disk cache pattern from Phase 3 (`~/.ct/cache/`) reused where appropriate
- Species validation matches the Phase 3 STRING PPI pattern (registry-gated before API calls)
- Usage guides should describe what the tool extracts/returns, not how to chain it
- Agent preference for local tools vs APIs should be handled via system prompt / tool registry metadata, not hardcoded in tool outputs

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ct.tools._api_cache` (get_cached, set_cached): Disk cache with TTL at `~/.ct/cache/`
- `ct.tools._species` (resolve_species_taxon, resolve_species_binomial): Registry-gated species validation
- `ct.tools.http_client` (request, request_json): HTTP client with retries and timeout
- `gffutils`: GFF3 database creation and querying (already a dependency)

### Established Patterns
- `@registry.register()` decorator with name, description, category, parameters, usage_guide
- Lazy imports inside function bodies for optional dependencies
- Species validation before API calls with `force=True` escape hatch
- Dict return with `summary` key, structured data in additional keys

### Integration Points
- Phase 3 literature tools (pubmed_plant_search) — agent can cross-reference PubMed IDs from gene_annotation
- Phase 2 species registry YAML — all tools validate against this
- Phase 5 CRISPR tools — gff_parse provides exon structure needed for guide design

</code_context>

<deferred>
## Deferred Ideas

- **Private Dagster data backend** — connect to a private data catalogue for controlled data quality and harmonisation instead of relying on external APIs
- **`analysis.*` tool category** — OrthoFinder, InterProScan, and other locally-installed computational biology tools as first-class agent capabilities
- **KEGG/Reactome pathway data** in gene annotation — potential UniProt enrichment
- User-supplied expression matrix support for co-expression — future enhancement
- STRING interaction sub-score breakdown — enhancement to Phase 3 tool

</deferred>

---

*Phase: 04-plant-genomics-tools*
*Context gathered: 2026-02-28 (updated post-implementation)*
