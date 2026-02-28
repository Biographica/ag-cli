---
status: complete
phase: 03-external-connectors
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md]
started: 2026-02-26T12:00:00Z
updated: 2026-02-28T12:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. STRING PPI tool appears in tool list
expected: Running `ag tool list` shows `interactions.string_plant_ppi` in the interactions category. The tool is visible to the plant agent.
result: pass

### 2. STRING PPI rejects unknown species
expected: Running `python -c "from ct.tools.interactions import string_plant_ppi; print(string_plant_ppi(gene='FLC', species='martian_grass'))"` returns a dict with summary containing "not recognised" (not a crash or traceback). The tool validates species before making any API call.
result: pass

### 3. STRING PPI returns interaction partners
expected: Running `ag "What are the protein interaction partners of FLC in Arabidopsis?"` (or calling the tool directly with gene='FLC', species='Arabidopsis thaliana') returns a result with interaction partners, each having a partner name, STRING ID, and confidence score (0-1). The summary mentions "interaction partners".
result: pass

### 4. Disk cache persists responses
expected: After a successful STRING PPI query, the cache directory `~/.ct/cache/string_ppi/` contains at least one `.json` file. Running `ls ~/.ct/cache/string_ppi/` shows a hex-named JSON file. Running the same query a second time returns instantly (cache hit, no network delay).
result: pass

### 5. PubMed plant search constructs species-scoped queries
expected: Running `ag "Find recent PubMed papers about FLC in Arabidopsis"` (or calling `pubmed_plant_search(gene="FLC", species="Arabidopsis thaliana")` directly) returns results with a `query_used` field containing both `FLC[Title/Abstract]` and `"Arabidopsis thaliana"[Organism]`. Articles include title, authors, journal, year, and abstract text.
result: pass

### 6. PubMed rate limit warning appears once
expected: With no NCBI API key configured (`ag config get api.ncbi_key` returns None), the first PubMed plant search includes a rate limit note in the summary mentioning "NCBI API key not configured". A second search in the same session does NOT repeat the warning.
result: pass

### 7. Lens.org patent search returns patents with claims
expected: With `api.lens_key` configured, running a Lens patent search in gene mode (e.g. `lens_patent_search(query_text="FLC", mode="gene", species="Arabidopsis thaliana")`) returns a result with patents list. Each patent entry includes lens_id, title, abstract text, and claims (first 3 claim texts). The query_used contains both the gene and species.
result: pass

### 8. Lens.org tool hidden when no API key
expected: With no `api.lens_key` configured, running `ag tool list` (or checking MCP server tool list) does NOT show `literature.lens_patent_search`. The agent cannot see or call the Lens tool without credentials.
result: pass

### 9. NCBI API key configurable
expected: Running `ag config set api.ncbi_key test-key-123` succeeds. Running `ag config get api.ncbi_key` returns `test-key-123`. The key is also loadable from the `NCBI_API_KEY` environment variable.
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
