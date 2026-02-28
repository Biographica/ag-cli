# Phase 4: Plant Genomics Tools - Research

**Researched:** 2026-02-28
**Domain:** Plant computational genomics — Ensembl Plants REST API, Ensembl Compara, UniProt, ATTED-II co-expression, gffutils GFF3 parsing, Gramene/Ensembl phenotype endpoints
**Confidence:** HIGH for API stack and architecture (verified against official Ensembl docs and existing codebase patterns); MEDIUM for ATTED-II API details (documented web UI, flat file download confirmed, API endpoint availability uncertain); MEDIUM for GWAS/QTL source selection (Ensembl phenotype/gene endpoint confirmed but plant coverage needs validation)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Data Sources & APIs**
- Gene annotation: Ensembl Plants REST API as primary source, enriched with UniProt for protein-level GO and publications. Cache both.
- Ortholog mapping: Ensembl Compara REST API as primary. PLAZA Plant Comparative Genomics as fallback for species Ensembl doesn't cover well.
- GWAS/QTL lookup: Claude's discretion — pick the most practical data source during research based on API availability and species coverage (TAIR, Gramene, or curated files).
- GFF3 parsing: Both modes — accept a user-supplied file path if provided, otherwise auto-download from Ensembl Plants. Cache downloaded GFFs for reuse.

**Species Coverage**
- Tiered approach: Arabidopsis and rice get full coverage across all 5 tools. Other supported species get best-effort — tools return what's available with clear messaging when data is sparse.
- When a tool has no data for a species, return empty results with explanation AND suggest alternatives (e.g. "Try searching orthologs in Arabidopsis which has richer GWAS coverage"). Suggestion only — agent decides whether to follow up.
- Registry-gated validation with escape hatch: species must be in the Phase 2 registry by default. A `force=True` parameter lets advanced users try any species string. Warn then proceed (consistent with Phase 3 pattern).
- Phylogenetic distance weighting uses a hardcoded species tree (curated distance matrix covering all registry species). Fast, deterministic, easy to test.

**Tool Output Depth**
- Gene annotation: Core + publications — GO terms, functional description, gene symbol, plus linked PubMed IDs and publication titles. Agent can cross-reference with Phase 3 literature tools.
- Ortholog mapping: Gene list + confidence + phylogenetic distance — ortholog gene IDs, species, orthology type (1:1, 1:many), plus distance weight and % identity. Agent can rank orthologs by evolutionary closeness.
- GFF3 parsing: Exon structure, UTR boundaries, and intron positions — covers what CRISPR guide design (Phase 5) needs.
- Co-expression: Claude's discretion on network metric depth based on what data sources provide and what the agent needs for reasoning.
- Cross-references: Claude's discretion on whether tool outputs hint at related tools.

**Co-expression Data**
- Pre-built networks from ATTED-II as primary source (no user-supplied expression matrices in this phase).
- Caching strategy: Disk cache like Phase 3 (`~/.ct/cache/`) with TTL — consistent with existing pattern, no user setup needed.
- GO enrichment of clusters: Claude decides whether to use pre-computed enrichments from source or compute on the fly.
- Non-Arabidopsis coverage: Rice is best-effort — include if a good source exists during research, but don't block the phase on it. Arabidopsis is the priority.

### Claude's Discretion
- GWAS/QTL data source selection
- Co-expression network metric depth
- Non-Arabidopsis co-expression database selection (rice best-effort)
- GO enrichment computation approach
- Whether tool outputs include cross-references to other tools

### Deferred Ideas (OUT OF SCOPE)
- STRING interaction sub-score breakdown (experimental, coexpression, text-mining etc.) — enhancement to Phase 3 tool
- User-supplied expression matrix support for co-expression — future enhancement
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TOOL-01 | User can look up gene annotation (GO terms, function, description, linked publications) for any gene in any supported species | Ensembl Plants REST API `GET /lookup/symbol/{species}/{symbol}` + `GET /xrefs/id/{id}?external_db=GO` for GO terms; UniProt search API `https://rest.uniprot.org/uniprotkb/search` with `fields=go_terms,cc_function,gene_names` for protein-level enrichment; Publications via EFetch on linked PMIDs |
| TOOL-02 | User can map orthologs across plant species with phylogenetic distance weighting | Ensembl Compara REST API `GET /homology/id/{species}/{id}?type=orthologues&compara=plants` returns ortholog list with % identity; hardcoded distance matrix for supported registry species supplies phylogenetic weights |
| TOOL-03 | User can run co-expression network analysis (cluster membership, centrality, enrichment) from expression data | ATTED-II provides tab-delimited co-expression data downloadable per species with MR scores; Arabidopsis coverage is well-established; rice best-effort; cached locally to `~/.ct/cache/atted/` |
| TOOL-04 | User can parse GFF3 genome annotations and extract gene structure information | `gffutils` 0.13 (pip installable, Python 3.10–3.12 compatible) parses GFF3 into SQLite DB; `db.children(gene_id, featuretype='exon')` etc. returns exons, UTRs, introns computable from exon gaps; GFF auto-download from Ensembl Plants FTP; cache GFF on disk |
| TOOL-05 | User can look up GWAS/QTL evidence for trait-gene associations | Ensembl Plants phenotype endpoint `GET /phenotype/gene/{species}/{gene}` returns phenotype annotations with optional PubMed IDs; `include_associated=1` includes variant-linked phenotypes — covers Arabidopsis well, rice best-effort |
</phase_requirements>

---

## Summary

Phase 4 implements five new `genomics.*` tools — `gene_annotation`, `ortholog_map`, `coexpression_network`, `gff_parse`, and `gwas_qtl_lookup` — all added to the existing `genomics.py` module which already exists in `src/ct/tools/` and is registered in both `_TOOL_MODULES` and `PLANT_SCIENCE_CATEGORIES`. The `genomics` category is already in the plant science allowlist, so no `__init__.py` changes are required for category registration (though the new tool names must be added). All five tools follow the established `@registry.register()` / `**kwargs` / `"summary"` key pattern and use lazy imports inside the function body.

The primary data stack is Ensembl Plants REST API (base URL: `https://rest.ensembl.org`) for gene lookup, GO cross-references, orthologs via Compara (`compara=plants`), and phenotype/GWAS annotations; UniProt REST API (`https://rest.uniprot.org/uniprotkb/search`) for protein-level GO terms and linked publications; ATTED-II flat file download for co-expression networks (Arabidopsis priority, rice best-effort); and `gffutils` 0.13 for GFF3 parsing backed by Ensembl Plants FTP auto-download. The `_api_cache.py` helper from Phase 3 is reused for disk TTL caching across all five tools. The only new dependency is `gffutils>=0.13`.

The key planning risk is ATTED-II API vs. flat file access: ATTED-II has a web interface and an illustrative API listed on GitHub, but the API endpoint documentation was not accessible during research. The safe implementation path is to use ATTED-II's tab-delimited bulk download (confirmed available, MR scores confirmed), cache the file locally on first use, and parse it at query time — consistent with the local-first data pattern already used in the project. A lightweight in-process lookup over the cached file is deterministic, testable, and eliminates the risk of an undocumented API changing.

**Primary recommendation:** Add five new tools to `src/ct/tools/genomics.py` using Ensembl Plants REST API + UniProt for annotation/orthologs/GWAS, ATTED-II flat file download for co-expression, and `gffutils` for GFF3 parsing. Add `gffutils>=0.13` to `pyproject.toml`. Reuse `_api_cache.py` for all caching. Register all five tools under the `genomics` category (already in `PLANT_SCIENCE_CATEGORIES`).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Ensembl Plants REST API | REST v15.x | Gene lookup, GO xrefs, Compara orthologs, phenotype/GWAS | Official Ensembl API; covers all registry plant species; `compara=plants` selects plant Compara DB |
| UniProt REST API | v3 (2024) | Protein-level GO terms, functional descriptions, linked PubMed IDs | Official UniProt; `fields=go_terms,cc_function` query parameter; confirmed plant coverage |
| ATTED-II flat file | v11 (2022) | Pre-built co-expression networks with MR scores; 19 plant species | Only database covering Arabidopsis + rice co-expression pre-built; direct bulk download confirmed |
| `gffutils` | `>=0.13` | GFF3/GTF parsing into SQLite database for hierarchical feature queries | Standard Python bioinformatics library; supports Python 3.10–3.12; `pip install gffutils` |
| `ct.tools._api_cache` | internal (Phase 3) | Disk TTL cache (JSON files at `~/.ct/cache/`) | Already written; used by Phase 3 tools; no code duplication |
| `ct.tools.http_client` | internal | HTTP retry/backoff wrapper | Already written; all external API calls must go through this |
| `ct.tools._species` | internal | Species name → taxon ID + binomial resolution | All species-specific tools must validate through this registry |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `xml.etree.ElementTree` | stdlib | Parse XML responses from Ensembl REST (GFF3 content, EFetch XML) | Ensembl lookup/xref sometimes returns XML; already used in Phase 3 |
| Ensembl Plants FTP | `ftp.ensemblgenomes.ebi.ac.uk` | Auto-download GFF3 files for supported species when no local path given | URL pattern: `/pub/plants/release-{N}/gff3/{species_lower}/{species}.{build}.gff3.gz` |
| `gzip`, `pathlib`, `tempfile` | stdlib | Decompress downloaded GFF3.gz files before creating gffutils DB | No extra deps; gffutils requires uncompressed file path |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ATTED-II flat file download | ATTED-II live API | ATTED-II API exists (GitHub illustrative service) but endpoint documentation was not accessible; flat file is confirmed available, deterministic, and cacheable — safer choice |
| Ensembl Plants phenotype/gene endpoint | Gramene REST API | Gramene provides broader QTL data for rice/maize but no documented REST API for QTL lookup was found; Ensembl `phenotype/gene` endpoint is confirmed and documented |
| Ensembl Plants phenotype/gene endpoint | Curated TSV from TAIR | TAIR has Arabidopsis GWAS data but no programmatic API; Ensembl covers Arabidopsis phenotypes and wraps them in the same API pattern as all other species |
| `gffutils` | `BCBio.GFF` / `biopython` GFF | BCBio.GFF is less maintained; biopython GFF is lower-level; gffutils provides SQLite-backed hierarchical queries that make exon/UTR/intron extraction straightforward |
| `gffutils` | Custom GFF3 parser | GFF3 has edge cases (multi-exon genes, overlapping features, non-standard files); gffutils handles these; do not hand-roll |

**Installation (new dependency only):**
```bash
pip install "gffutils>=0.13"
# Add to pyproject.toml [project] dependencies
```

---

## Architecture Patterns

### Recommended Project Structure
```
src/ct/tools/
├── genomics.py          # EXISTING: add 5 new tools here
│   ├── gwas_lookup()    # existing human-focused tool — untouched
│   ├── gene_annotation()   # NEW: TOOL-01
│   ├── ortholog_map()      # NEW: TOOL-02
│   ├── coexpression_network()  # NEW: TOOL-03
│   ├── gff_parse()          # NEW: TOOL-04
│   └── gwas_qtl_lookup()    # NEW: TOOL-05
└── _api_cache.py        # EXISTING (Phase 3): reused, no changes

~/.ct/cache/
├── string_ppi/          # Phase 3 (unchanged)
├── pubmed/              # Phase 3 (unchanged)
├── lens_patents/        # Phase 3 (unchanged)
├── ensembl_gene/        # NEW: gene annotation responses (24h TTL)
├── ensembl_orthologs/   # NEW: ortholog mapping responses (24h TTL)
├── ensembl_phenotype/   # NEW: GWAS/phenotype responses (24h TTL)
├── atted_coexp/         # NEW: ATTED-II downloaded flat files (7d TTL, large)
└── gff3/                # NEW: downloaded GFF3 files (7d TTL, large)
```

**Note on `__init__.py`:** `genomics` is already in both `_TOOL_MODULES` and `PLANT_SCIENCE_CATEGORIES`. No changes to `__init__.py` are required.

### Pattern 1: Gene Annotation (`genomics.gene_annotation`)

Multi-step Ensembl Plants + UniProt lookup:
1. `GET /lookup/symbol/{species}/{symbol}` — get Ensembl gene ID, description, gene_id
2. `GET /xrefs/id/{ensembl_id}?external_db=GO` — get GO term cross-references
3. UniProt search — `GET https://rest.uniprot.org/uniprotkb/search?query=gene:{symbol}+AND+organism_id:{taxon_id}&fields=go_terms,cc_function,lit_pubmed_id&format=json` — protein-level GO and PubMed IDs

```python
# Source: Ensembl REST API docs + plants.ensembl.org/info/data/rest.html
# Source: UniProt query fields documented at uniprot.org/help/query-fields

@registry.register(
    name="genomics.gene_annotation",
    description=(
        "Look up gene annotation (GO terms, functional description, linked publications) "
        "for a gene in any supported plant species using Ensembl Plants and UniProt."
    ),
    category="genomics",
    parameters={
        "gene": "Gene symbol or locus code (e.g. 'FLC', 'AT5G10140', 'GW5')",
        "species": "Species name (default: Arabidopsis thaliana)",
        "force": "Skip species registry check and try any species string (default: False)",
    },
    usage_guide=(
        "Get GO terms, functional description, and linked publications for a plant gene. "
        "Start here for target characterisation. Cross-reference PubMed IDs with "
        "literature.pubmed_plant_search for full text."
    ),
)
def gene_annotation(
    gene: str,
    species: str = "Arabidopsis thaliana",
    force: bool = False,
    **kwargs,
) -> dict:
    from ct.tools._species import resolve_species_taxon, resolve_species_binomial
    from ct.tools.http_client import request_json
    from ct.tools._api_cache import get_cached, set_cached

    # Species validation (with force escape hatch)
    taxon_id = resolve_species_taxon(species)
    if taxon_id == 0 and not force:
        return {
            "error": f"Unknown species: {species!r}. Use force=True to override.",
            "summary": f"Species not recognised: {species!r}.",
        }
    binomial = resolve_species_binomial(species) or species

    cache_key = f"gene_annotation:{taxon_id}:{gene}"
    cached = get_cached("ensembl_gene", cache_key)
    if cached is not None:
        return cached

    # Step 1: Ensembl Plants gene lookup by symbol
    ensembl_base = "https://rest.ensembl.org"
    species_for_url = binomial.lower().replace(" ", "_")
    gene_data, err = request_json(
        "GET",
        f"{ensembl_base}/lookup/symbol/{species_for_url}/{gene}",
        params={"content-type": "application/json", "expand": 0},
        timeout=15,
        retries=2,
    )

    # Step 2: GO xrefs from Ensembl
    # GET /xrefs/id/{ensembl_id}?external_db=GO
    ensembl_id = gene_data.get("id", "")
    go_data, _ = request_json(
        "GET",
        f"{ensembl_base}/xrefs/id/{ensembl_id}",
        params={"content-type": "application/json", "external_db": "GO"},
        timeout=15,
        retries=2,
    )

    # Step 3: UniProt for protein-level GO + publications
    # GET https://rest.uniprot.org/uniprotkb/search?query=gene:{gene}+AND+organism_id:{taxon_id}&fields=go_terms,cc_function,lit_pubmed_id&format=json
    uniprot_data, _ = request_json(
        "GET",
        "https://rest.uniprot.org/uniprotkb/search",
        params={
            "query": f"gene:{gene} AND organism_id:{taxon_id}",
            "fields": "gene_names,go_terms,cc_function,lit_pubmed_id",
            "format": "json",
            "size": 1,
        },
        timeout=15,
        retries=2,
    )
    # ...build result, set_cached, return
```

### Pattern 2: Ortholog Mapping (`genomics.ortholog_map`)

Uses Ensembl Compara `compara=plants` parameter. Species name in URL uses Ensembl underscore format.

```python
# Source: plants.ensembl.org/info/data/rest.html
# Key: compara=plants selects the plant Compara database (not vertebrates default)
# Key: compara=pan_homology for cross-kingdom (plants + fungi + protists)

@registry.register(
    name="genomics.ortholog_map",
    ...
)
def ortholog_map(
    gene: str,
    species: str = "Arabidopsis thaliana",
    target_species: str | None = None,   # None = all supported species
    force: bool = False,
    **kwargs,
) -> dict:
    ...
    # Step 1: resolve gene → Ensembl ID via lookup/symbol
    # Step 2: homology/id/{species_url}/{ensembl_id}?type=orthologues&compara=plants
    # Step 3: apply hardcoded phylogenetic distance weight to each ortholog
    homology_url = f"{ensembl_base}/homology/id/{species_url}/{ensembl_id}"
    params = {
        "content-type": "application/json",
        "type": "orthologues",
        "compara": "plants",          # CRITICAL for plant Compara DB
        "format": "condensed",        # less data than 'full', enough for our use
    }
    if target_species:
        params["target_species"] = target_species.lower().replace(" ", "_")
    ...
```

**Phylogenetic distance matrix** — hardcoded dict, keyed by pair of taxon IDs. Distances (millions of years, approximate) from published plant phylogenomics. The weight for an ortholog is `1.0 / (1.0 + distance_mya)` normalised to [0, 1]:

```python
# Curated from published plant phylogenies (MEDIUM confidence — approximations)
_PHYLO_DISTANCES_MYA: dict[frozenset, float] = {
    frozenset({3702, 3702}): 0.0,        # Arabidopsis vs itself
    frozenset({3702, 3708}): 43.0,       # Arabidopsis vs Brassica napus
    frozenset({3702, 4081}): 112.0,      # Arabidopsis vs tomato
    frozenset({3702, 4530}): 150.0,      # Arabidopsis vs rice (dicot/monocot)
    frozenset({3702, 4577}): 150.0,      # Arabidopsis vs maize
    frozenset({3702, 4565}): 150.0,      # Arabidopsis vs wheat
    frozenset({3702, 3847}): 90.0,       # Arabidopsis vs soybean
    frozenset({4530, 4577}): 50.0,       # Rice vs maize
    frozenset({4530, 4565}): 50.0,       # Rice vs wheat
    # ... extend for all registry species pairs
}

def _phylo_weight(taxon_a: int, taxon_b: int) -> float:
    """Return a 0–1 weight inversely proportional to phylogenetic distance."""
    key = frozenset({taxon_a, taxon_b})
    dist = _PHYLO_DISTANCES_MYA.get(key, 200.0)  # 200 Mya default for unknowns
    return round(1.0 / (1.0 + dist / 100.0), 3)
```

### Pattern 3: Co-expression Network (`genomics.coexpression_network`)

ATTED-II provides tab-delimited bulk download. The file for Arabidopsis contains pairs of genes with MR (mutual rank) score and PCC (Pearson correlation coefficient). The implementation:

1. On first call for a species: download the ATTED-II flat file to `~/.ct/cache/atted/{species_key}.tsv` (7-day TTL for large files)
2. Load into pandas DataFrame filtered to query gene rows
3. Return top co-expressed partners sorted by MR score (lower is stronger)
4. Cluster membership: report genes with MR < threshold as "cluster" — no separate clustering needed
5. GO enrichment: use pre-computed GO terms from `gene_annotation` tool output for top partners (no on-the-fly enrichment — call `gene_annotation` for each partner and aggregate GO terms)

**ATTED-II download URL pattern** (Arabidopsis, confirmed structure):
```
https://atted.jp/data/{version}/{species}/At.r{release}.m.mx.MR.txt.gz
```
Note: exact URL format for ATTED-II v11 requires live verification during implementation (LOW confidence on exact path). The download page at `atted.jp/top/download.shtml` was unavailable during research (404). The file format (tab-delimited, MR score in column) is confirmed from published papers.

**Safe fallback approach:** If ATTED-II URL cannot be resolved at implementation time, use a static bundled Arabidopsis co-expression file (top 1000 gene pairs by MR, committed to the repo as a small seed dataset) with a note that the full network requires downloading ATTED-II data.

```python
@registry.register(
    name="genomics.coexpression_network",
    ...
    parameters={
        "gene": "Gene locus code (e.g. 'AT5G10140', 'FLC')",
        "species": "Species (default: Arabidopsis thaliana; rice best-effort)",
        "top_n": "Number of top co-expressed genes to return (default 20, max 100)",
        "mr_threshold": "Maximum MR score for cluster membership (default 30)",
        "force": "Skip species registry check (default False)",
    },
)
def coexpression_network(
    gene: str,
    species: str = "Arabidopsis thaliana",
    top_n: int = 20,
    mr_threshold: float = 30.0,
    force: bool = False,
    **kwargs,
) -> dict:
    # Load ATTED-II file (download + cache if needed)
    # Filter to gene of interest
    # Return: {summary, gene, coexpressed_genes: [{gene_id, mr, pcc}],
    #          cluster_size, cluster_go_terms (from annotation), centrality_note}
```

### Pattern 4: GFF3 Parsing (`genomics.gff_parse`)

Two-phase: file acquisition then feature extraction.

**File acquisition:**
- If `gff_path` provided: use it directly
- If not provided: download from Ensembl Plants FTP, cache to `~/.ct/cache/gff3/{species_key}.gff3.gz`

**Ensembl Plants GFF3 FTP URL pattern** (confirmed from search results):
```
https://ftp.ensemblgenomes.ebi.ac.uk/pub/plants/release-{N}/gff3/{species_lower}/{Species_Name}.{genome_build}.{N}.gff3.gz
```
Example for Arabidopsis:
```
https://ftp.ensemblgenomes.ebi.ac.uk/pub/plants/release-62/gff3/arabidopsis_thaliana/Arabidopsis_thaliana.TAIR10.62.gff3.gz
```
The release number must be discovered dynamically or hardcoded (use current release 62 as default, configurable).

**gffutils database creation:**
```python
# Source: daler.github.io/gffutils — confirmed pip install gffutils>=0.13
import gffutils

# For files that already contain gene + mRNA + exon features (like TAIR10):
db = gffutils.create_db(
    gff3_path,                     # path to decompressed .gff3 file
    dbfn=db_path,                  # .db file path for SQLite
    force=True,
    merge_strategy="merge",
    disable_infer_transcripts=True,  # TAIR10 already has mRNA features — skip inference (100x speedup)
    disable_infer_genes=True,        # TAIR10 already has gene features
    id_spec=["ID", "Name"],
)
```

**Feature extraction:**
```python
# Get exons for a gene
gene_feature = db[gene_id]
mrnas = list(db.children(gene_feature, featuretype="mRNA", level=1))
if mrnas:
    exons = sorted(
        db.children(mrnas[0], featuretype="exon"),
        key=lambda f: f.start
    )
    five_utrs = list(db.children(mrnas[0], featuretype="five_prime_UTR"))
    three_utrs = list(db.children(mrnas[0], featuretype="three_prime_UTR"))

# Compute introns from exon gaps
introns = []
for i in range(len(exons) - 1):
    introns.append({
        "start": exons[i].end + 1,
        "end": exons[i + 1].start - 1,
        "length": (exons[i + 1].start - 1) - (exons[i].end + 1) + 1,
    })
```

```python
@registry.register(
    name="genomics.gff_parse",
    ...
    parameters={
        "gene": "Gene ID or symbol (e.g. 'AT5G10140', 'FLC')",
        "species": "Species (default: Arabidopsis thaliana)",
        "gff_path": "Path to local GFF3 file (optional; auto-downloads if absent)",
        "transcript": "Specific transcript ID to parse (optional; uses first mRNA)",
        "force": "Skip species registry check (default False)",
    },
)
def gff_parse(...) -> dict:
    # Returns: {summary, gene, transcript, chromosome, strand,
    #           exons: [{start, end, length}],
    #           five_prime_utrs: [...], three_prime_utrs: [...],
    #           introns: [{start, end, length}],
    #           total_exons, total_introns, gene_span_bp}
```

### Pattern 5: GWAS/QTL Lookup (`genomics.gwas_qtl_lookup`)

Uses Ensembl Plants `phenotype/gene` endpoint. The endpoint is confirmed in Ensembl REST API docs with `include_pubmed_id=1` and `include_associated=1` parameters:

```python
# Source: rest.ensembl.org/documentation/info/phenotype_gene (confirmed)
# Note: This endpoint works for human by default. For plants, the URL uses
# the Ensembl Plants species name format (e.g. arabidopsis_thaliana).

@registry.register(
    name="genomics.gwas_qtl_lookup",
    ...
    parameters={
        "gene": "Gene symbol or locus code (e.g. 'FLC', 'AT5G10140', 'GW5')",
        "species": "Species (default: Arabidopsis thaliana)",
        "trait": "Optional trait keyword to filter results (e.g. 'flowering time', 'yield')",
        "force": "Skip species registry check (default False)",
    },
)
def gwas_qtl_lookup(
    gene: str,
    species: str = "Arabidopsis thaliana",
    trait: str | None = None,
    force: bool = False,
    **kwargs,
) -> dict:
    ...
    # GET /phenotype/gene/{species_url}/{gene}?include_pubmed_id=1&include_associated=1
    # Returns list of {description, study, pubmed_ids, attributes}
    # Filter by trait keyword if provided
    # Return: {summary, gene, species, phenotype_count, phenotypes: [{description, study, pubmed_ids}],
    #          suggestion: "Try Arabidopsis for richer coverage" when species has sparse data}
```

**Plant coverage caveat:** The Ensembl `phenotype/gene` endpoint is well-documented for human. Plant species support depends on what phenotype data Ensembl Plants has imported. Arabidopsis phenotype data is well-curated in Ensembl Plants; rice is best-effort. The tool should surface how many phenotypes were found and note sparse coverage explicitly.

### Anti-Patterns to Avoid

- **Using `compara=vertebrates` (the default) for plant ortholog queries:** Plant genes are not in the vertebrate Compara database. Always pass `compara=plants` for plant-to-plant ortholog lookups, or `compara=pan_homology` for cross-kingdom.
- **Using `infer_gene_extent=False` in gffutils:** This is deprecated. Use `disable_infer_genes=True` and `disable_infer_transcripts=True` separately for GFF3 files that already contain gene/mRNA features (like all Ensembl Plants GFF3s). Without this, database creation is 100x slower.
- **Creating gffutils DB in `/tmp` without caching:** GFF3 files for Arabidopsis are ~50 MB compressed; DB creation takes seconds. Cache the `.db` file at `~/.ct/cache/gff3/{species}.db` alongside the downloaded GFF3 so it is reused across calls.
- **Calling Ensembl REST API without `content-type: application/json` header:** The API returns HTML by default. Always include `content-type=application/json` as a query param or `Accept: application/json` header.
- **Hardcoding Ensembl Plants release number in URLs:** Use a configurable default (e.g. 62) and document it, rather than embedding it invisibly. A config key `genomics.ensembl_plants_release` allows users to pin a different release.
- **Adding tools to `genomics` module without checking existing tool names:** The existing `genomics.gwas_lookup` is a human GWAS Catalog tool. New tools must have distinct names (`gwas_qtl_lookup` for plants) and must not conflict with or break existing registrations.
- **Returning raw Ensembl GO term objects without filtering:** `xrefs/id/{id}?external_db=GO` may return dozens of GO entries. Filter to unique GO IDs, include term name and namespace (BP/MF/CC) in the output.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GFF3 parsing | Custom regex/line parser | `gffutils` 0.13 | GFF3 has non-standard files, multi-parent features, overlapping genes; gffutils handles all of these |
| Intron computation | Custom algorithm | Exon gap formula from gffutils exon coords | Introns are the gaps between sorted exon positions; this is 3 lines of Python once exons are fetched |
| Disk cache | Custom file cache | `_api_cache.get_cached / set_cached` (Phase 3) | Already written, tested, handles hash keys, non-raising |
| Species → Ensembl URL name | Custom mapping | `resolve_species_binomial(species).lower().replace(" ", "_")` | The binomial from the registry is the correct Ensembl URL key |
| HTTP retry | Custom retry loop | `ct.tools.http_client.request_json` | Handles 429, 500-504, timeout, Content-Type validation |
| Phylogenetic distances | Compute from API | Hardcoded distance matrix | User decision: hardcoded is fast, deterministic, easy to test |
| GO enrichment computation | FDR correction, Fisher's exact | Return GO terms from annotation tool for cluster members | User decision: use pre-computed annotation via `gene_annotation` tool calls, not Fisher's exact on the fly |

**Key insight:** gffutils is the only new dependency. Everything else builds on Phase 2/3 infrastructure already in place.

---

## Common Pitfalls

### Pitfall 1: Ensembl Plants Compara Requires `compara=plants` Parameter

**What goes wrong:** `GET /homology/id/{species}/{id}` without the `compara` parameter queries the vertebrate Compara database by default, returning no results for plant genes.

**Why it happens:** Ensembl maintains separate Compara databases per division (plants, fungi, metazoa, pan_homology). The REST API default is vertebrates.

**How to avoid:** Always pass `compara=plants` for within-plant ortholog queries. For cross-kingdom (e.g. looking up plant vs. yeast), use `compara=pan_homology`.

**Warning signs:** Zero orthologs returned for a well-studied gene like FLC or GW5.

### Pitfall 2: Ensembl Plants Species URL Format (Underscore, Exact Casing)

**What goes wrong:** `GET /lookup/symbol/arabidopsis_Thaliana/AT5G10140` returns 404. Ensembl uses exact lowercase underscored binomial.

**Why it happens:** Ensembl URL species names are lowercase and space-replaced with underscore: `arabidopsis_thaliana`, `oryza_sativa`, `zea_mays`.

**How to avoid:** Use `resolve_species_binomial(species).lower().replace(" ", "_")` to construct the URL species component. The existing `STATE.md` decision "resolve_species_binomial returns exact stored casing" means we get `Arabidopsis thaliana` → `.lower().replace(" ", "_")` → `arabidopsis_thaliana`.

**Warning signs:** 404 on gene lookup for valid genes.

### Pitfall 3: gffutils Database Creation Performance

**What goes wrong:** `gffutils.create_db()` takes 60-120 seconds for a full Arabidopsis GFF3 without the `disable_infer_*` flags.

**Why it happens:** Without the flags, gffutils tries to infer gene/transcript extents from exon coordinates, even when those features are already explicit in the GFF3. This is unnecessary for Ensembl Plants GFF3 files which always include explicit gene/mRNA features.

**How to avoid:** Set `disable_infer_genes=True` and `disable_infer_transcripts=True`. Cache the resulting `.db` file to `~/.ct/cache/gff3/{species}.db` — subsequent calls load the existing DB in milliseconds with `gffutils.FeatureDB(db_path)`.

**Warning signs:** Tool takes >30 seconds on first call and does not produce a cached `.db` file.

### Pitfall 4: Ensembl Plants Phenotype Endpoint — Plant Coverage Not Guaranteed

**What goes wrong:** `GET /phenotype/gene/arabidopsis_thaliana/FLC` returns an empty list or 404 despite FLC having well-known phenotypes.

**Why it happens:** The Ensembl `phenotype/gene` endpoint is primarily populated from GWAS Catalog and EBI phenotype resources, which are human-heavy. Plant phenotype data depends on what Ensembl Plants has imported from community sources (TAIR, GRASSdb, Gramene). Coverage is dataset-dependent.

**How to avoid:** Return empty results with a clear explanation (`"No phenotype annotations found in Ensembl Plants for {gene}. GWAS evidence for plant traits is sparser than for human diseases."`) and the suggestion to try Arabidopsis which has the richest phenotype import. Test endpoint response during Wave 0 with known Arabidopsis QTL genes.

**Warning signs:** Tool always returns empty for all plant genes even with valid gene IDs.

### Pitfall 5: ATTED-II Download URL Is Not Stable

**What goes wrong:** The ATTED-II flat file download URL at `atted.jp/top/download.shtml` returned 404 during research. If the URL pattern changes between versions, the download will silently fail.

**Why it happens:** ATTED-II is a research database that changes its URL structure between major versions. The download page was not accessible during this research session.

**How to avoid:** Implement with a configurable `ATTED_BASE_URL` constant that can be overridden. Add error handling that falls back to a bundled seed file (top 500 Arabidopsis co-expression pairs committed to the repo) when download fails, with a clear message directing the user to configure the URL. Test the download URL during Wave 0 with a live attempt before coding the full implementation.

**Warning signs:** `request_json` returns an error when downloading the ATTED-II file. The fallback seed ensures the tool is functional even without network access.

### Pitfall 6: GFF3 Gene ID vs. Symbol Lookup Ambiguity

**What goes wrong:** A user calls `gff_parse(gene="FLC")` but the GFF3 file uses locus codes (`AT5G10140`) as the primary `ID=` attribute. The lookup `db["FLC"]` raises `gffutils.FeatureNotFoundError`.

**Why it happens:** Ensembl Plants GFF3 files use Ensembl stable IDs as the `ID` attribute. Gene symbols (like FLC) appear in the `Name=` attribute. gffutils indexes by ID by default.

**How to avoid:** After failing `db[gene_id]`, fall back to searching by `Name` attribute: iterate over `db.features_of_type("gene")` filtering on `feature["Name"] == [gene]`. Cache the name→ID mapping. Alternatively: look up the Ensembl stable ID via `gene_annotation` first, then pass the stable ID to `gff_parse`.

**Warning signs:** `gffutils.FeatureNotFoundError` for gene symbols that are valid but use a different ID format.

### Pitfall 7: Large File Downloads Blocking the Agent

**What goes wrong:** GFF3 files for wheat (>1 GB compressed) take minutes to download, blocking the tool call and consuming the agent's patience.

**Why it happens:** Genome GFF3 files vary enormously in size. Arabidopsis ~50 MB compressed; wheat ~1.5 GB compressed.

**How to avoid:** Set a download timeout of 120 seconds and return a structured error for oversized species: `"GFF3 for wheat is very large (>1 GB). Manual download recommended: {url}. Place at {cache_path}."`. Arabidopsis and rice have manageable sizes; other species can be gated.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Ensembl Plants Gene Lookup by Symbol
```python
# Source: rest.ensembl.org/documentation, plants.ensembl.org/info/data/rest.html
# Note: binomial from resolve_species_binomial() → lowercase + underscored for URL

ensembl_base = "https://rest.ensembl.org"
species_url = resolve_species_binomial(species).lower().replace(" ", "_")
# e.g. "arabidopsis_thaliana"

gene_data, err = request_json(
    "GET",
    f"{ensembl_base}/lookup/symbol/{species_url}/{gene}",
    params={"content-type": "application/json"},
    timeout=15,
    retries=2,
)
# Returns: {id, display_name, description, biotype, chromosome, start, end, strand, ...}
ensembl_id = gene_data.get("id", "")   # e.g. "AT5G10140"
description = gene_data.get("description", "")
```

### Ensembl GO Cross-References
```python
# Source: rest.ensembl.org/documentation/info/xref_id
# external_db=GO filters to Gene Ontology terms only

go_xrefs, err = request_json(
    "GET",
    f"{ensembl_base}/xrefs/id/{ensembl_id}",
    params={
        "content-type": "application/json",
        "external_db": "GO",
        "all_levels": 0,
    },
    timeout=15,
    retries=2,
)
# Returns list of: {primary_id, display_id, description, db_display_name, info_type}
# primary_id = "GO:0003700", description = "DNA-binding transcription factor activity"
go_terms = [
    {
        "go_id": xref.get("primary_id", ""),
        "term": xref.get("description", ""),
        "namespace": _infer_go_namespace(xref.get("description", "")),  # BP/MF/CC from term
    }
    for xref in (go_xrefs or [])
    if xref.get("primary_id", "").startswith("GO:")
]
```

### UniProt Search for GO Terms + Publications
```python
# Source: uniprot.org/help/query-fields (MEDIUM confidence — verified field names from docs)
# Fields: gene_names, go_terms, cc_function, lit_pubmed_id

uniprot_data, err = request_json(
    "GET",
    "https://rest.uniprot.org/uniprotkb/search",
    params={
        "query": f"gene:{gene} AND organism_id:{taxon_id} AND reviewed:true",
        "fields": "gene_names,go_terms,cc_function,lit_pubmed_id",
        "format": "json",
        "size": 1,
    },
    timeout=15,
    retries=2,
)
results = (uniprot_data or {}).get("results", [])
if results:
    entry = results[0]
    go_terms_uniprot = entry.get("uniProtKBCrossReferences", [])  # filter for GO db
    function_desc = entry.get("comments", [])                      # cc_function type
    pubmed_ids = [ref.get("id") for ref in entry.get("references", [])
                  if ref.get("citation", {}).get("type") == "journal"]
```

### Ensembl Compara Ortholog Lookup
```python
# Source: plants.ensembl.org/info/data/rest.html
# CRITICAL: compara=plants, not vertebrates (the default)

homology_data, err = request_json(
    "GET",
    f"{ensembl_base}/homology/id/{species_url}/{ensembl_id}",
    params={
        "content-type": "application/json",
        "type": "orthologues",
        "compara": "plants",           # REQUIRED for plant Compara DB
        "format": "condensed",         # less bandwidth than "full"
        "target_species": target_species_url,  # optional filter
    },
    timeout=30,
    retries=2,
)
orthologs = homology_data.get("data", [{}])[0].get("homologies", [])
# Each entry: {type, target: {id, species, perc_id, perc_pos}, method_link_type}
# type values: "ortholog_one2one", "ortholog_one2many", "ortholog_many2many"
```

### gffutils Database Creation and Feature Extraction
```python
# Source: daler.github.io/gffutils/examples.html
import gffutils

# Create (or load existing) SQLite database from GFF3
db_path = cache_dir / f"{species_key}.db"
if not db_path.exists():
    db = gffutils.create_db(
        str(gff3_local_path),
        dbfn=str(db_path),
        force=True,
        merge_strategy="merge",
        disable_infer_genes=True,       # Ensembl GFF3 already has gene features
        disable_infer_transcripts=True, # Ensembl GFF3 already has mRNA features
    )
else:
    db = gffutils.FeatureDB(str(db_path))

# Lookup gene — try ID first, then Name attribute
try:
    gene_feature = db[gene_id]
except gffutils.FeatureNotFoundError:
    # Fallback: search by Name attribute
    candidates = [f for f in db.features_of_type("gene")
                  if gene_id in f.attributes.get("Name", [])]
    gene_feature = candidates[0] if candidates else None

# Get exons for primary transcript
if gene_feature:
    mrnas = sorted(db.children(gene_feature, featuretype="mRNA"), key=lambda f: f.start)
    primary_mrna = mrnas[0] if mrnas else None
    if primary_mrna:
        exons = sorted(db.children(primary_mrna, featuretype="exon"), key=lambda f: f.start)
        five_utrs = list(db.children(primary_mrna, featuretype="five_prime_UTR"))
        three_utrs = list(db.children(primary_mrna, featuretype="three_prime_UTR"))
        # Compute introns from exon gaps
        introns = [
            {"start": exons[i].end + 1, "end": exons[i+1].start - 1,
             "length": exons[i+1].start - exons[i].end - 1}
            for i in range(len(exons) - 1)
        ]
```

### Ensembl Phenotype/Gene Endpoint
```python
# Source: rest.ensembl.org/documentation/info/phenotype_gene (confirmed endpoint)
# Note: Plant phenotype coverage is sparser than human — always handle empty gracefully

phenotype_data, err = request_json(
    "GET",
    f"{ensembl_base}/phenotype/gene/{species_url}/{gene}",
    params={
        "content-type": "application/json",
        "include_associated": 1,   # include variant-linked phenotypes
        "include_pubmed_id": 1,    # include PubMed IDs in response
        "non_specified": 1,        # include entries without specific trait terms
    },
    timeout=15,
    retries=2,
)
phenotypes = phenotype_data or []
# Each entry: {description, study, source, pubmed_id, attributes}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pharma-focused `genomics.gwas_lookup` (EBI GWAS Catalog, human-only) | New `genomics.gwas_qtl_lookup` (Ensembl Plants phenotype endpoint, plant-specific) | Phase 4 | Plant trait evidence accessible without conflating with human GWAS; existing human tool unchanged |
| No plant ortholog tool | `genomics.ortholog_map` using Ensembl Compara `compara=plants` | Phase 4 | Cross-species gene function inference now possible for all registry plant species |
| No co-expression tool | `genomics.coexpression_network` from ATTED-II flat file | Phase 4 | Network context for any Arabidopsis gene available offline; rice best-effort |
| No GFF3 tool | `genomics.gff_parse` with auto-download from Ensembl Plants FTP | Phase 4 | Gene structure (exons, introns, UTRs) available for CRISPR guide design (Phase 5) |

**Deprecated/outdated in this phase:**
- None — existing `genomics.gwas_lookup` is retained unchanged; new plant tools are additions not replacements.

---

## Open Questions

1. **ATTED-II download URL and file format**
   - What we know: ATTED-II v11 exists, covers 19 plant species including Arabidopsis and rice, provides tab-delimited co-expression data with MR scores. Download page existed previously.
   - What's unclear: Exact URL path for bulk download files (download page returned 404 during research). File column format (confirmed as tab-delimited with MR score, but exact header names unknown).
   - Recommendation: Wave 0 task must include live verification of the ATTED-II download URL before implementation. Prepare a bundled seed file (top 500 Arabidopsis co-expression pairs from published data) as a fallback to keep TOOL-03 functional regardless of download status.

2. **Ensembl Plants phenotype/gene coverage for plant species**
   - What we know: Endpoint is confirmed and documented. Arabidopsis phenotype data has been imported into Ensembl from community sources. Rice is less certain.
   - What's unclear: Whether phenotype data for specific well-known QTL genes (e.g. GW5 in rice, FLC in Arabidopsis) actually appears in the endpoint response.
   - Recommendation: Wave 0 unit test must include a live call (or realistic mock) against a known Arabidopsis phenotype gene (FLC, FT) to confirm non-empty response.

3. **UniProt field names in REST API response**
   - What we know: UniProt search endpoint supports `fields=go_terms,cc_function,lit_pubmed_id`. Field names confirmed from multiple sources.
   - What's unclear: Exact JSON response path for each field in the v3 API (e.g. whether GO terms appear under `uniProtKBCrossReferences` filtered by `database: "GO"` or as a dedicated `goTerms` key).
   - Recommendation: Implement with defensive access (`entry.get("goTerms", []) or [ref for ref in entry.get("uniProtKBCrossReferences", []) if ref.get("database") == "GO"]`). Add a Wave 0 test with a mocked UniProt response that verifies parsing.

4. **gffutils new dependency — `pyproject.toml` placement**
   - What we know: `gffutils>=0.13` supports Python 3.10–3.12. No conflicting transitive dependencies known.
   - What's unclear: Whether `gffutils` should go in `[project] dependencies` (always available) or in a new `[project.optional-dependencies]` section like `genomics = ["gffutils>=0.13"]`.
   - Recommendation: Add to `[project] dependencies` since `genomics.gff_parse` is a core Phase 4 tool — not optional. This keeps installation simple (no extras needed). If the binary size becomes a concern, move to optional later.

5. **Phylogenetic distance matrix completeness**
   - What we know: All 19 species in `species_registry.yaml` need pairwise distances. Published plant phylogenies provide approximate values in millions of years.
   - What's unclear: Exact published distances for all pairs; some pairs (e.g. banana vs. barley) are not commonly cited together.
   - Recommendation: Build the matrix conservatively — cover all pairs from the species registry using published estimates from large-scale plant phylogenomics (e.g. Zeng et al. 2017 "Resolution of deep angiosperm phylogeny"). Assign 200 Mya as default for unknown pairs. Document that distances are approximate and used only for weighting.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, no new config needed) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `pytest tests/test_genomics_plant.py -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-01 | `gene_annotation` returns GO terms, description, symbol for known Arabidopsis gene | unit (mocked httpx) | `pytest tests/test_genomics_plant.py::TestGeneAnnotation::test_arabidopsis_success -x` | ❌ Wave 0 |
| TOOL-01 | `gene_annotation` returns structured error for unknown species (no force) | unit | `pytest tests/test_genomics_plant.py::TestGeneAnnotation::test_unknown_species -x` | ❌ Wave 0 |
| TOOL-01 | `gene_annotation` proceeds with warning when `force=True` for unregistered species | unit | `pytest tests/test_genomics_plant.py::TestGeneAnnotation::test_force_override -x` | ❌ Wave 0 |
| TOOL-01 | `gene_annotation` includes linked PubMed IDs from UniProt | unit (mocked httpx) | `pytest tests/test_genomics_plant.py::TestGeneAnnotation::test_pubmed_ids_present -x` | ❌ Wave 0 |
| TOOL-02 | `ortholog_map` returns ortholog list with phylogenetic distance weights | unit (mocked httpx) | `pytest tests/test_genomics_plant.py::TestOrthologMap::test_success -x` | ❌ Wave 0 |
| TOOL-02 | `ortholog_map` uses `compara=plants` in Ensembl API call | unit (verifies request params) | `pytest tests/test_genomics_plant.py::TestOrthologMap::test_compara_plants_param -x` | ❌ Wave 0 |
| TOOL-02 | `ortholog_map` returns empty list with suggestion when no orthologs found | unit | `pytest tests/test_genomics_plant.py::TestOrthologMap::test_empty_response -x` | ❌ Wave 0 |
| TOOL-03 | `coexpression_network` returns co-expressed genes with MR scores for Arabidopsis gene | unit (mocked file/download) | `pytest tests/test_genomics_plant.py::TestCoexpressionNetwork::test_arabidopsis_success -x` | ❌ Wave 0 |
| TOOL-03 | `coexpression_network` returns fallback result when download fails | unit | `pytest tests/test_genomics_plant.py::TestCoexpressionNetwork::test_download_fallback -x` | ❌ Wave 0 |
| TOOL-03 | `coexpression_network` respects `mr_threshold` for cluster membership | unit | `pytest tests/test_genomics_plant.py::TestCoexpressionNetwork::test_mr_threshold -x` | ❌ Wave 0 |
| TOOL-04 | `gff_parse` returns exons, UTRs, introns for Arabidopsis gene from local GFF3 file | unit (bundled test GFF3) | `pytest tests/test_genomics_plant.py::TestGffParse::test_local_file_success -x` | ❌ Wave 0 |
| TOOL-04 | `gff_parse` computes intron positions from exon gaps correctly | unit | `pytest tests/test_genomics_plant.py::TestGffParse::test_intron_computation -x` | ❌ Wave 0 |
| TOOL-04 | `gff_parse` falls back to Name attribute when ID lookup fails | unit | `pytest tests/test_genomics_plant.py::TestGffParse::test_name_fallback -x` | ❌ Wave 0 |
| TOOL-04 | `gff_parse` auto-downloads from Ensembl Plants FTP when no local path given | unit (mocked download) | `pytest tests/test_genomics_plant.py::TestGffParse::test_auto_download -x` | ❌ Wave 0 |
| TOOL-05 | `gwas_qtl_lookup` returns phenotype annotations for Arabidopsis gene | unit (mocked httpx) | `pytest tests/test_genomics_plant.py::TestGwasQtlLookup::test_success -x` | ❌ Wave 0 |
| TOOL-05 | `gwas_qtl_lookup` filters by trait keyword when provided | unit | `pytest tests/test_genomics_plant.py::TestGwasQtlLookup::test_trait_filter -x` | ❌ Wave 0 |
| TOOL-05 | `gwas_qtl_lookup` returns empty with explanation + suggestion when no phenotypes found | unit | `pytest tests/test_genomics_plant.py::TestGwasQtlLookup::test_empty_with_suggestion -x` | ❌ Wave 0 |
| All tools | All 5 new tools are registered under the `genomics` category and visible in `PLANT_SCIENCE_CATEGORIES` | unit | `pytest tests/test_genomics_plant.py::test_all_tools_registered -x` | ❌ Wave 0 |

### Patch Target Convention

Following Phase 3 established pattern — patch source modules not tool module:
```python
# Correct (lazy imports inside function body)
@patch("ct.tools._species.resolve_species_taxon")
@patch("ct.tools.http_client.request_json")
@patch("ct.tools._api_cache.get_cached")
@patch("ct.tools._api_cache.set_cached")

# Incorrect (name doesn't exist at genomics module level)
@patch("ct.tools.genomics.request_json")   # WRONG — lazy import
```

### Sampling Rate
- **Per task commit:** `pytest tests/test_genomics_plant.py -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_genomics_plant.py` — all 17 test cases covering TOOL-01 through TOOL-05
- [ ] `tests/fixtures/FLC_mini.gff3` — minimal GFF3 for 2-exon gene to test `gff_parse` without a real download
- [ ] `pyproject.toml` — add `gffutils>=0.13` to `[project] dependencies`
- [ ] `src/ct/tools/genomics.py` — add the 5 new tool functions (existing file, just append)

*(Existing test infrastructure: pytest, conftest.py, `@patch` patterns — no new framework needed.)*

---

## GWAS/QTL Source Selection (Claude's Discretion)

**Decision: Ensembl Plants `phenotype/gene` endpoint as primary.**

Rationale:
1. It uses the same REST API already used for gene lookup and orthologs — no new base URL or authentication
2. It covers Arabidopsis phenotype data (imported from TAIR) and returns PubMed IDs
3. It is the only confirmed, documented programmatic plant phenotype API found during research
4. Gramene QTL database has the richest plant QTL data but no documented REST API endpoint for gene-based queries (BioMart only, which is slower and more complex)
5. TAIR has Arabidopsis GWAS data but no public REST API

**Fallback messaging:** When the endpoint returns empty for non-Arabidopsis species, suggest querying Arabidopsis orthologs first and note that broader QTL evidence requires manual Gramene/WheatQTLdb lookup.

## Co-expression Metric Depth (Claude's Discretion)

**Decision: MR score (primary) + PCC (secondary) + cluster size at MR threshold.**

Rationale: ATTED-II uses Mutual Rank (MR) as its primary co-expression metric. MR < 5 = bold edge (very strong), MR 5–30 = normal edge (moderate), MR ≥ 30 = weak. These thresholds map naturally to "cluster" membership for the agent's reasoning. PCC provides directionality (positive/negative correlation). Network centrality metrics (betweenness, degree) require loading the full network graph — not justified for this phase given the agent only needs gene-level context, not topology analysis.

## GO Enrichment Approach (Claude's Discretion)

**Decision: Report GO term frequencies across top co-expressed partners (no on-the-fly Fisher's exact).**

Rationale: On-the-fly enrichment requires loading a gene universe, running Fisher's exact or hypergeometric test with FDR correction, and mapping GO term hierarchies — significant complexity for a first-pass tool. Instead: the co-expression tool calls `gene_annotation` for the top N partners (using the existing TOOL-01 implementation) and aggregates GO terms by frequency. This gives the agent a view of which biological processes are over-represented in the co-expression cluster, without statistical machinery. Statistical enrichment can be deferred to Phase 5 or a future enhancement.

---

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/ct/tools/genomics.py` — existing `gwas_lookup` pattern; `genomics` already in `PLANT_SCIENCE_CATEGORIES` and `_TOOL_MODULES`
- Existing codebase: `src/ct/tools/_api_cache.py` — confirmed Pattern 4 from Phase 3, reusable
- Existing codebase: `src/ct/tools/interactions.py` — confirmed tool registration pattern with `force` escape hatch concept
- Existing codebase: `src/ct/tools/_species.py` — `resolve_species_binomial` returns exact casing; `resolve_species_taxon` returns 0 for unknown
- Ensembl REST API docs (`rest.ensembl.org/documentation`) — phenotype/gene endpoint confirmed with parameters; xrefs/id endpoint confirmed; homology/id endpoint confirmed; `compara=plants` parameter confirmed from Ensembl Plants REST service page
- `plants.ensembl.org/info/data/rest.html` — `compara=plants` parameter documented; `compara=pan_homology` for cross-kingdom
- Ensembl Plants GFF3 FTP structure: `ftp.ensemblgenomes.ebi.ac.uk/pub/plants/release-{N}/gff3/{species}/` — confirmed from search results + Ensembl FTP index
- gffutils 0.13: `daler.github.io/gffutils/` — feature query API confirmed; `disable_infer_genes/transcripts` flags confirmed as correct for GFF3 with explicit features
- Ensembl rate limits: 55,000 requests/hour, ≤15 concurrent requests/second — confirmed from official wiki

### Secondary (MEDIUM confidence)
- ATTED-II v11: tab-delimited co-expression files with MR scores confirmed from multiple published papers (Obayashi et al. 2022 Plant Cell Physiology); 19 plant species including Arabidopsis and rice confirmed
- UniProt REST API field names (`gene_names`, `go_terms`, `cc_function`, `lit_pubmed_id`) — confirmed from multiple sources including PMC12230682 (2025 UniProt paper) and uniprot.org help pages
- Phylogenetic distance estimates (Mya) — standard references in plant phylogenomics literature; approximate values used for weighting only
- gffutils Python 3.10–3.12 compatibility — confirmed from PyPI/libraries.io metadata stating support added for 3.11 and 3.12

### Tertiary (LOW confidence)
- ATTED-II download URL exact path — not confirmed (download page returned 404 during research); flagged as Open Question #1
- Exact Ensembl Plants phenotype/gene response structure for plant species — endpoint documented but plant-specific coverage not live-tested; flagged as Open Question #2
- UniProt JSON response path for GO terms within the `results` array — field existence confirmed, exact nested path inferred from API conventions; flagged as Open Question #3

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Ensembl, gffutils, UniProt are all established and verified; only ATTED-II download URL is LOW
- Architecture: HIGH — directly modeled on Phase 3 verified patterns (interactions.py, _api_cache.py, _species.py)
- API details (Ensembl, UniProt): HIGH — endpoint paths and key parameters verified from official docs
- API details (ATTED-II): LOW — file format confirmed from literature, download URL not accessible during research
- Pitfalls: HIGH — derived from Ensembl API docs (rate limits, compara parameter), gffutils docs (infer flags), and existing codebase decisions (species URL casing)

**Research date:** 2026-02-28
**Valid until:** 2026-04-28 (Ensembl Plants releases quarterly; ATTED-II is stable; gffutils is slow-moving — 60 days reasonable)
