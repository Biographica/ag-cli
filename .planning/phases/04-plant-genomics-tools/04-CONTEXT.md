# Phase 4: Plant Genomics Tools - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Five computational genomics tools — gene annotation, ortholog mapping, co-expression analysis, GFF3 parsing, and GWAS/QTL lookup — that give the agent core genomics reasoning capability for plant target research. These are new `genomics.*` category tools following the existing tool pattern.

</domain>

<decisions>
## Implementation Decisions

### Data Sources & APIs
- **Gene annotation:** Ensembl Plants REST API as primary source, enriched with UniProt for protein-level GO and publications. Cache both.
- **Ortholog mapping:** Ensembl Compara REST API as primary. PLAZA Plant Comparative Genomics as fallback for species Ensembl doesn't cover well.
- **GWAS/QTL lookup:** Claude's discretion — pick the most practical data source during research based on API availability and species coverage (TAIR, Gramene, or curated files).
- **GFF3 parsing:** Both modes — accept a user-supplied file path if provided, otherwise auto-download from Ensembl Plants. Cache downloaded GFFs for reuse.

### Species Coverage
- Tiered approach: Arabidopsis and rice get full coverage across all 5 tools. Other supported species get best-effort — tools return what's available with clear messaging when data is sparse.
- When a tool has no data for a species, return empty results with explanation AND suggest alternatives (e.g. "Try searching orthologs in Arabidopsis which has richer GWAS coverage").
- Registry-gated validation with escape hatch: species must be in the Phase 2 registry by default. A `force=True` parameter lets advanced users try any species string. Consistent with Phase 3 pattern.
- Phylogenetic distance weighting uses a hardcoded species tree (curated distance matrix for supported species). Fast, deterministic, easy to test.

### Tool Output Depth
- **Gene annotation:** Core + publications — GO terms, functional description, gene symbol, plus linked PubMed IDs and publication titles. Agent can cross-reference with Phase 3 literature tools.
- **Ortholog mapping:** Gene list + confidence + phylogenetic distance — ortholog gene IDs, species, orthology type (1:1, 1:many), plus distance weight and % identity. Agent can rank orthologs by evolutionary closeness.
- **Co-expression:** Claude's discretion on network metric depth based on what data sources provide and what the agent needs for reasoning.
- **Cross-references:** Claude's discretion on whether tool outputs hint at related tools.

### Co-expression Data
- Pre-built networks from ATTED-II as primary source (no user-supplied expression matrices in this phase).
- Non-Arabidopsis coverage: Claude decides during research which species have usable pre-built co-expression databases. Likely Arabidopsis + rice minimum.
- Caching strategy: Claude decides based on data size — could be disk cache (Phase 3 pattern) or dedicated `ag data pull` command for large networks.
- GO enrichment of clusters: Claude decides whether to use pre-computed enrichments from source or compute on the fly.

### Claude's Discretion
- GWAS/QTL data source selection
- Co-expression network metric depth
- Non-Arabidopsis co-expression database selection
- Caching strategy for co-expression data (disk cache vs data pull)
- GO enrichment computation approach
- Whether tool outputs include cross-references to other tools

</decisions>

<specifics>
## Specific Ideas

- All tools should follow the existing `@registry.register()` pattern with `**kwargs` and dict return with `summary` key
- Disk cache pattern from Phase 3 (`~/.ct/cache/`) should be reused where appropriate
- Species validation should match the Phase 3 STRING PPI pattern (registry-gated before API calls)
- Publication cross-referencing with Phase 3 PubMed tool is a key integration point

</specifics>

<deferred>
## Deferred Ideas

- STRING interaction sub-score breakdown (experimental, coexpression, text-mining etc.) — enhancement to Phase 3 tool
- User-supplied expression matrix support for co-expression — future enhancement

</deferred>

---

*Phase: 04-plant-genomics-tools*
*Context gathered: 2026-02-28*
