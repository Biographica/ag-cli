---
status: complete
phase: 04-plant-genomics-tools
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md, 04-04-SUMMARY.md]
started: 2026-03-02T14:00:00Z
updated: 2026-03-02T14:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Gene annotation returns GO terms and function
expected: Calling `gene_annotation(gene="FLC", species="Arabidopsis thaliana")` returns a dict with: ensembl_id, go_terms (list), function_description (string from UniProt), pubmed_ids (list of PubMed ID strings), location, biotype, and a summary mentioning the gene. The result includes at least one GO term.
result: pass

### 2. Gene annotation rejects unknown species
expected: Calling `gene_annotation(gene="FLC", species="martian_grass")` returns a dict with summary containing "not recognised" or similar error text — not a crash or traceback. No API call is made for unknown species.
result: pass

### 3. GWAS/QTL lookup returns phenotype associations
expected: Calling `gwas_qtl_lookup(gene="FLC", species="Arabidopsis thaliana")` returns a dict with phenotype_count (integer >= 0), phenotypes (list), and summary. If phenotypes exist, each entry has description and source fields.
result: pass

### 4. GWAS/QTL shows generic sparse-result messaging
expected: Calling `gwas_qtl_lookup(gene="FLC", species="Oryza sativa")` with no results returns a suggestion containing "data coverage is limited" — NOT "Arabidopsis has the richest coverage" or any species-tiering language.
result: pass

### 5. Ortholog mapping returns orthologs with phylogenetic weights
expected: Calling `ortholog_map(gene="FLC", species="Arabidopsis thaliana")` returns a dict with orthologs (list), each having gene_symbol, species, percent_identity, and phylo_weight (0-1 float). Orthologs are sorted by phylo_weight descending. Summary mentions "ortholog".
result: pass

### 6. GFF3 parsing extracts gene structure from local file
expected: Calling `gff_parse(gene="FLC", species="Arabidopsis thaliana", gff_path="tests/fixtures/FLC_mini.gff3")` returns a dict with exons (list with start/end positions), introns (list), gene_span_bp, and summary. The fixture has 2 exons so the result should show 2 exons and 1 intron.
result: pass

### 7. Co-expression network returns co-expressed partners
expected: Calling `coexpression_network(gene="FLC", species="Arabidopsis thaliana")` returns a dict with coexpressed_genes (list), each having gene, mr_score, and cluster fields. Summary mentions "co-expression" or "coexpressed". If ATTED-II data is unavailable, the tool returns a clear fallback message (not a crash).
result: issue
reported: "why can't this have an input path like the gff_parse? e.g. if someone had a genes by conditions matrix"
severity: minor

### 8. All 5 tools registered under genomics category
expected: Running `python -c "from ct.tools import registry, PLANT_SCIENCE_CATEGORIES; tools = [t.name for t in registry.list_tools() if t.category == 'genomics']; print([t for t in tools if t.startswith('genomics.')])"` shows all 5: gene_annotation, gwas_qtl_lookup, ortholog_map, gff_parse, coexpression_network. "genomics" is in PLANT_SCIENCE_CATEGORIES.
result: pass

### 9. Tool messaging uses neutral tone
expected: Running `grep -c 'Start here\|Cross-reference\|best coverage\|Needed for CRISPR\|richest coverage' src/ct/tools/genomics.py` returns 0 matches in user-facing strings. Usage guides describe what tools return, not directives on when/how to chain them.
result: pass

## Summary

total: 9
passed: 8
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Co-expression tool accepts local data path like gff_parse does for GFF3 files"
  status: failed
  reason: "User reported: why can't this have an input path like the gff_parse? e.g. if someone had a genes by conditions matrix"
  severity: minor
  test: 7
  artifacts: []
  missing: []
