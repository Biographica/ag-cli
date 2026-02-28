---
phase: 04-plant-genomics-tools
verified: 2026-02-28T14:30:00Z
status: passed
score: 18/18 must-haves verified
re_verification: false
---

# Phase 4: Plant Genomics Tools Verification Report

**Phase Goal:** The agent can look up gene annotations, map orthologs across species, analyse co-expression networks, parse genome annotations, and retrieve GWAS/QTL evidence — giving it the genomics reasoning capability needed for plant target research
**Verified:** 2026-02-28T14:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Agent can return GO terms, functional description, gene symbol, and linked PubMed IDs for any gene in any supported species using genomics.gene_annotation | VERIFIED | `gene_annotation` registered at line 1391, returns `go_terms`, `function_description`, `pubmed_ids`, `pubmed_count`; 6 tests all pass |
| 2 | Gene annotation enriches Ensembl lookup with UniProt protein-level GO terms and publications | VERIFIED | Steps 2 (Ensembl GO xrefs) and 3 (UniProt search for GO+publications) both implemented and tested; `test_arabidopsis_success` asserts UniProt PubMed IDs present |
| 3 | Agent can look up GWAS hits and phenotype annotations for a trait and species combination using genomics.gwas_qtl_lookup | VERIFIED | `gwas_qtl_lookup` registered at line 1560; `test_success` asserts `phenotype_count == 1`; trait filter verified in `test_trait_filter` |
| 4 | GWAS/QTL lookup returns empty results with explanation and alternative species suggestion when no phenotypes found | VERIFIED | `test_empty_with_suggestion` asserts `suggestion` contains "Arabidopsis"; `test_empty_arabidopsis` asserts sparsity message |
| 5 | Both tools validate species against the registry before making API calls, with force=True escape hatch | VERIFIED | Both tools call `resolve_species_taxon(species)` and return error dict if `taxon_id == 0 and not force`; verified by `test_unknown_species` and `test_force_override` |
| 6 | Both tools cache API responses to disk with 24h TTL via _api_cache | VERIFIED | Both call `get_cached(...)` and `set_cached(...)`; `test_cache_hit` confirms request_json NOT called on cache hit |
| 7 | gffutils>=0.13 is listed in pyproject.toml dependencies | VERIFIED | `pyproject.toml` line 31: `"gffutils>=0.13"` — confirmed |
| 8 | Agent can map a query gene to its orthologs with orthology type, percent identity, and phylogenetic distance weight using genomics.ortholog_map | VERIFIED | `ortholog_map` registered at line 1763; `test_success` asserts `ortholog_count`, `orthology_type`, `percent_identity`, `phylo_weight` all present |
| 9 | Ortholog mapping uses compara=plants parameter in all Ensembl Compara API calls | VERIFIED | Line 1841: `"compara": "plants"` hardcoded in params dict; `test_compara_plants_param` programmatically asserts this |
| 10 | Phylogenetic distance weights are computed from a hardcoded curated distance matrix | VERIFIED | `_PHYLO_DISTANCES_MYA` at line 1689 — 60-entry frozenset-keyed dict; `_phylo_weight()` at line 1746; `_phylo_weight(3702,4530)=0.4`, `_phylo_weight(4577,4558)=0.893`, `_phylo_weight(3702,3702)=1.0`, unknown pair=0.333 — all correct |
| 11 | Ortholog mapping returns empty list with species suggestion when no orthologs found | VERIFIED | `test_empty_response` asserts `ortholog_count == 0` and summary mentions "No orthologs" |
| 12 | Agent can parse a GFF3 file and extract exon structure, UTR boundaries, and intron positions using genomics.gff_parse | VERIFIED | `gff_parse` registered at line 1923; `test_local_file_success` asserts `total_exons==2`, `total_introns==1`, UTR lists present; `test_intron_computation` verifies intron start/end arithmetic |
| 13 | GFF3 tool accepts a local file path or auto-downloads from Ensembl Plants FTP when no path given | VERIFIED | Lines 1976-2007: `gff_path` branch (local file) and auto-download branch (Ensembl Plants FTP release-62); `test_auto_download` verifies URL contains "ensemblgenomes.ebi.ac.uk" |
| 14 | GFF3 tool falls back to Name attribute search when gene ID lookup fails in gffutils | VERIFIED | Lines 2062-2073: `db[gene]` → `db[f"gene:{gene}"]` → Name attribute scan; `test_name_fallback` verifies FLC found via Name=FLC |
| 15 | GFF3 database (.db) is cached alongside downloaded files for fast subsequent lookups | VERIFIED | Line 2046: `db_path = gff_local.with_suffix(".db")`; loads if exists, creates otherwise; `tests/fixtures/FLC_mini.db` present (73KB) confirming .db creation works |
| 16 | Agent can retrieve co-expression cluster membership and MR scores for an Arabidopsis gene using genomics.coexpression_network | VERIFIED | `coexpression_network` registered at line 2164; `test_arabidopsis_success` asserts `coexpressed_genes` has 4 entries, `cluster_size==3`, first entry `mr_score==2.5` |
| 17 | Co-expression tool returns meaningful fallback when ATTED-II download fails | VERIFIED | Lines 2244-2257: returns `fallback: True` with instructive message; `test_download_fallback` asserts `fallback==True` and `coexpressed_genes==[]` |
| 18 | Both gff_parse and coexpression_network validate species against registry with force=True escape hatch | VERIFIED | Both tools gate on `taxon_id == 0 and not force`; `test_unknown_species` in each class confirms error dict returned |

**Score:** 18/18 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/ct/tools/genomics.py` | gene_annotation and gwas_qtl_lookup tools (Plan 01) | VERIFIED | Tool registrations at lines 1391, 1560; both substantive implementations (100+ lines each); lazy imports wired to _api_cache, _species, http_client |
| `pyproject.toml` | gffutils>=0.13 dependency | VERIFIED | Line 31: `"gffutils>=0.13"` — installed and importable (`gffutils 0.13`) |
| `tests/test_genomics_plant.py` | Unit tests for all 5 Phase 4 tools | VERIFIED | 34 tests across 5 classes + 4 standalone; all 34 pass in 1.56s |
| `src/ct/tools/genomics.py` | ortholog_map tool (Plan 02) | VERIFIED | Registration at line 1763; `_PHYLO_DISTANCES_MYA` (60 entries) at line 1689; `_phylo_weight()` at line 1746; compara=plants at line 1841 |
| `src/ct/tools/genomics.py` | gff_parse and coexpression_network tools (Plan 03) | VERIFIED | Registrations at lines 1923, 2164; gff_parse has full ID/prefix/Name fallback chain; coexpression_network has ATTED-II download + fallback |
| `tests/fixtures/FLC_mini.gff3` | Minimal 2-exon GFF3 test fixture | VERIFIED | 9-line file with gene, mRNA, 2 exons, five_prime_UTR, three_prime_UTR; FLC_mini.db (73KB) confirms successful parsing |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/ct/tools/genomics.py` | `src/ct/tools/_api_cache.py` | `from ct.tools._api_cache import get_cached, set_cached` | WIRED | Lines 1412, 1582, 1792, 1957, 2194 — all 5 tools import from _api_cache inside function body; cache calls verified by test_cache_hit tests |
| `src/ct/tools/genomics.py` | `src/ct/tools/_species.py` | `resolve_species_taxon` for species validation | WIRED | Lines 1410, 1580, 1790, 1955, 2192 — all 5 tools import and call `resolve_species_taxon`; species guard verified by test_unknown_species tests |
| `src/ct/tools/genomics.py` | `src/ct/tools/http_client.py` | `request_json` and `request` for REST API calls | WIRED | Lines 1411, 1581, 1791, 1956, 2193 — gene_annotation/gwas_qtl/ortholog_map use `request_json`; gff_parse/coexpression_network use `request` |
| `src/ct/tools/genomics.py` (ortholog_map) | Ensembl Compara API | `compara=plants` param | WIRED | Line 1841 hardcodes `"compara": "plants"` in params dict; verified programmatically by test_compara_plants_param |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| TOOL-01 | 04-01-PLAN.md | User can look up gene annotation (GO terms, function, description, linked publications) for any gene in any supported species | SATISFIED | `genomics.gene_annotation` returns `go_terms`, `function_description`, `pubmed_ids`; 6 passing tests |
| TOOL-02 | 04-02-PLAN.md | User can map orthologs across plant species with phylogenetic distance weighting | SATISFIED | `genomics.ortholog_map` returns `orthologs` with `phylo_weight`, `orthology_type`, `percent_identity`; 9 passing tests |
| TOOL-03 | 04-03-PLAN.md | User can run co-expression network analysis from expression data | SATISFIED | `genomics.coexpression_network` returns `coexpressed_genes` with MR scores and `cluster_size`; 6 passing tests |
| TOOL-04 | 04-03-PLAN.md | User can parse GFF3 genome annotations and extract gene structure information | SATISFIED | `genomics.gff_parse` returns `exons`, `introns`, `five_prime_utrs`, `three_prime_utrs`; 6 passing tests |
| TOOL-05 | 04-01-PLAN.md | User can look up GWAS/QTL evidence for trait-gene associations | SATISFIED | `genomics.gwas_qtl_lookup` returns `phenotypes` with trait filtering; 6 passing tests |

**All 5 requirement IDs satisfied. No orphaned requirements.**

REQUIREMENTS.md status column shows all 5 as `[x] Complete` with Phase 4 mapping confirmed.

---

## Anti-Patterns Found

No anti-patterns detected in the Phase 4 tool implementations (lines 1390-2350 of genomics.py):
- No TODO/FIXME/HACK/PLACEHOLDER comments
- No empty return statements or stub implementations
- All tools have substantive implementations with API calls, caching, error handling, and species validation
- All tools return dicts with `"summary"` key as required by the tool pattern

---

## Human Verification Required

The following items cannot be verified programmatically but have low risk given passing unit tests:

### 1. Live Ensembl Plants API Response Format

**Test:** Call `genomics.gene_annotation(gene="FLC", species="Arabidopsis thaliana")` on a machine with internet access
**Expected:** Returns `ensembl_id="AT5G10140"`, non-empty `go_terms` list, and at least 1 PubMed ID from UniProt
**Why human:** Real API response structure may differ from mocked test data; Ensembl Plants API versioning

### 2. ATTED-II Data File Format and Download

**Test:** On a clean machine, call `genomics.coexpression_network(gene="AT5G10140", species="Arabidopsis thaliana")`
**Expected:** Downloads from ATTED-II, parses successfully, returns co-expression partners with MR scores
**Why human:** ATTED-II URLs documented as unstable between versions; format assumptions in pandas read_csv may not match current file

### 3. GFF3 Auto-Download Integration

**Test:** Call `genomics.gff_parse(gene="FLC", species="Arabidopsis thaliana")` without `gff_path` on a clean machine
**Expected:** Downloads Arabidopsis GFF3 from Ensembl Plants FTP release-62, creates .db file, returns exon structure
**Why human:** Large file download (Arabidopsis ~25MB); genome_build lookup via `_build_lookup()` requires species registry entry with build info

---

## Commit Verification

All 6 Phase 4 commits exist in git history:

| Commit | Message |
|--------|---------|
| `9a29031` | feat(04-01): add gene_annotation and gwas_qtl_lookup tools; add gffutils dependency |
| `2bcb0cf` | test(04-01): add unit tests for gene_annotation and gwas_qtl_lookup |
| `7d2ec27` | feat(04-02): add ortholog_map tool with phylogenetic distance weighting |
| `4811a1a` | test(04-02): add TestOrthologMap and _phylo_weight unit tests |
| `4f4dced` | feat(04-03): add gff_parse and coexpression_network tools to genomics.py |
| `680f870` | test(04-03): add TestGffParse and TestCoexpressionNetwork unit tests |

---

## Summary

Phase 4 goal is fully achieved. All 5 genomics tools are implemented, registered, wired, and tested:

- `genomics.gene_annotation` (TOOL-01): Ensembl Plants + UniProt gene characterisation with GO terms, function description, and PubMed IDs
- `genomics.gwas_qtl_lookup` (TOOL-05): Ensembl Plants phenotype endpoint with trait filtering and species-aware empty-result suggestions
- `genomics.ortholog_map` (TOOL-02): Ensembl Compara cross-species ortholog mapping with curated 60-pair phylogenetic distance matrix and 0-1 weight scoring; compara=plants enforced
- `genomics.gff_parse` (TOOL-04): GFF3 parsing via gffutils with ID/prefix/Name fallback chain, local file and FTP auto-download modes, .db caching
- `genomics.coexpression_network` (TOOL-03): ATTED-II bulk flat-file co-expression with MR scores, cluster membership, and graceful download fallback

All 34 unit tests pass (1.56s). No regressions. No anti-patterns. All 5 requirements (TOOL-01 through TOOL-05) satisfied.

---

_Verified: 2026-02-28T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
