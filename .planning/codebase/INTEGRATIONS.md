# External Integrations

**Analysis Date:** 2026-02-25

## APIs & External Services

**Language Models:**
- Anthropic Claude - Primary LLM provider
  - SDK/Client: `anthropic>=0.40`
  - Auth: `ANTHROPIC_API_KEY` environment variable or `llm.api_key` config
  - Models: claude-sonnet-4-5-20250929 (default), claude-opus-4-6, claude-haiku-4-5-20251001
  - Pricing tracked: Usage cost estimation included in `ct.models.llm.UsageTracker`
  - Config location: `src/ct/models/llm.py`

- OpenAI GPT Models - Fallback/alternative LLM
  - SDK/Client: `openai>=1.0`
  - Auth: `OPENAI_API_KEY` environment variable or `llm.openai_api_key` config
  - Models: gpt-4o (default), gpt-4o-mini
  - Config location: `src/ct/models/llm.py`

**Chemistry & Molecular Design:**
- IBM RXN for Chemistry - Retrosynthesis prediction
  - API: https://rxn.res.ibm.com
  - Auth: `IBM_RXN_API_KEY` environment variable or `api.ibm_rxn_key` config
  - Tool: `chemistry.retrosynthesis` in `src/ct/tools/design.py`
  - Free tier: Yes
  - HTTP client: Uses `httpx` with retry logic from `src/ct/tools/http_client.py`

**Protein & Structure Data:**
- UniProt API - Protein function and annotation
  - API: https://www.uniprot.org/rest/
  - Auth: None required (public API)
  - Tool: `protein.function` (references UniProt data)
  - HTTP client: `httpx` from `src/ct/tools/http_client.py`

- InterPro API - Protein domain annotation
  - API: https://www.ebi.ac.uk/interpro/api/
  - Auth: None required
  - Tool: Domain annotation in `src/ct/tools/protein.py`
  - HTTP client: `httpx` from `src/ct/tools/http_client.py`

- AlphaFold Structure API - Predicted protein structures
  - API: https://alphafold.ebi.ac.uk/
  - Auth: None required (public)
  - Tool: `structure.alphafold_fetch` (on-demand per-protein)
  - Data source: `src/ct/data/downloader.py` (DATASETS["alphafold"])

**Patents & Literature:**
- Lens.org - Patent search and literature indexing
  - API: https://www.lens.org/lens/user/subscriptions
  - Auth: `LENS_API_KEY` environment variable or `api.lens_key` config
  - Tool: `literature.patent_search`
  - Free tier: Yes
  - HTTP client: `httpx`

**Single-Cell Genomics:**
- CellXGene Census API - Human cell census data
  - SDK: `cellxgene-census>=1.0`
  - API: https://cellxgene.cziscience.com/
  - Auth: None required (public, though rate-limited)
  - Tool: `singlecell.cellxgene_*` tools in `src/ct/tools/cellxgene.py`
  - Query: Via Python API (cellxgene_census library)

**Email & Notifications:**
- SendGrid - Email delivery service
  - API: https://api.sendgrid.com/v3/mail/send
  - Auth: `SENDGRID_API_KEY` environment variable or `notification.sendgrid_api_key` config
  - Tool: `notification.send_email` in `src/ct/tools/notification.py`
  - Free tier: No
  - Dry-run support: Yes (default is dry-run without sending)
  - HTTP client: `src/ct/tools/http_client.py` with retry logic

**Computational Resources:**
- Lambda Labs GPU Cloud - GPU compute jobs
  - API: https://cloud.lambdalabs.com
  - Auth: `LAMBDA_API_KEY` environment variable or `compute.lambda_api_key` config
  - Tool: `compute.submit_job` (default provider)
  - Free tier: No
  - Config: `src/ct/agent/config.py` (compute.default_provider)

- RunPod GPU Cloud - Alternative GPU compute provider
  - API: https://www.runpod.io
  - Auth: `RUNPOD_API_KEY` environment variable or `compute.runpod_api_key` config
  - Tool: `compute.submit_job` (fallback provider)
  - Free tier: No
  - Config: `src/ct/agent/config.py` (compute.runpod_api_key)

## Data Storage

**Databases:**
- DuckDB - In-memory SQL query engine
  - Client: `duckdb>=1.0`
  - Purpose: Queries Parquet and CSV files directly without loading entire dataset into memory
  - Location: `src/ct/api/engine.py`
  - Use: Data API endpoint for querying large datasets with filtering and aggregation
  - Connection: `:memory:` (ephemeral, in-process)

**File Storage:**
- Local filesystem only - No cloud storage integration detected
  - Data paths configured via `~/.ct/config.json`
  - Data directories: `data.depmap`, `data.prism`, `data.l1000`, `data.proteomics`, `data.string`, `data.alphafold`, `data.msigdb`
  - Default base: `~/.ct/data/`

**Data Downloads:**
- Figshare - DepMap dataset hosting
  - URLs configured in `src/ct/data/downloader.py`
  - Auto-download: Yes
  - Files: CRISPRGeneEffect.csv, Model.csv, OmicsSomaticMutationsMatrixDamaging.csv

- Broad Institute GSEA - MSigDB gene sets
  - URLs: `data.broadinstitute.org/gsea-msigdb/`
  - Auto-download: Yes
  - Files: Hallmark, KEGG, Reactome, GO gene sets (2024.1.Hs)

- STRING Database - Protein-protein interactions
  - URLs: `stringdb-downloads.org/`
  - Auto-download: Yes
  - Files: Human PPI network (v12.0)

- GEO/LINCS - L1000 gene expression
  - URL: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE92742
  - Auto-download: No (manual processing via scripts/prepare_l1000.py)

## Caching

**Strategy:**
- Python `functools.lru_cache` for data loaders
  - Location: `src/ct/data/loaders.py`
  - Caches: load_crispr, load_model_metadata, load_proteomics, load_l1000, load_prism
  - Purpose: Avoid re-reading large CSV/Parquet files within a single session

**No explicit caching layer detected:**
- No Redis/Memcached integration
- No database-level caching
- Relies on OS filesystem caching for data access

## Authentication & Identity

**Auth Providers:**
- Custom configuration-based (no OAuth/SAML)
- All auth via API keys stored in `~/.ct/config.json` or environment variables
- No user authentication system (single-user CLI tool)

**API Key Management:**
- Centralized in `src/ct/agent/config.py` via `API_KEYS` dict
- Environment variable mapping documented
- Safety: Encrypted keys never printed to console
- Source: `python-dotenv` loads from `.env` and project root `.env`

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, Rollbar, etc.)

**Logs:**
- Console output via `rich` library
- Dry-run logs for email notifications: `~/.ct/sent_emails.log`
- No centralized logging infrastructure
- Audit logs optional: `enterprise.audit_enabled` config (writes to `~/.ct/audit/`)

**Cost Tracking:**
- Token usage and cost estimation in `ct.models.llm.UsageTracker`
- Pricing data in `ct.models.llm.MODEL_PRICING`
- Cost-per-call calculated for Anthropic and OpenAI models

## CI/CD & Deployment

**Hosting:**
- Not detected (this is a CLI tool, not a deployed service)

**CI Pipeline:**
- Not detected (no GitHub Actions, GitLab CI, etc. in this snapshot)

**Testing:**
- Pytest with optional markers:
  - `@pytest.mark.e2e` - End-to-end tests hitting real APIs
  - `@pytest.mark.docker` - Tests requiring Docker
  - `@pytest.mark.e2e_matrix` - Optional live multi-prompt tests
  - `@pytest.mark.api_smoke` - Optional live API smoke tests
- Test environment: `tests/` directory
- Mocked data loaders for tests (never require real datasets)

## Environment Configuration

**Required env vars:**
- `ANTHROPIC_API_KEY` - For Anthropic Claude API access
- `OPENAI_API_KEY` - Optional, for OpenAI GPT access
- `IBM_RXN_API_KEY` - Optional, for retrosynthesis
- `LENS_API_KEY` - Optional, for patent search
- `SENDGRID_API_KEY` - Optional, for email notifications
- `LAMBDA_API_KEY` - Optional, for GPU compute
- `RUNPOD_API_KEY` - Optional, for GPU compute

**Optional env vars:**
- Loaded via `python-dotenv` from `.env` (project root and current directory)
- Validated in `src/ct/agent/config.py`

**Secrets location:**
- `.env` file (git-ignored, local development)
- Environment variables (production)
- Config file at `~/.ct/config.json` (persisted settings, includes keys)

## Webhooks & Callbacks

**Incoming:**
- Not detected (CLI tool, no server component)

**Outgoing:**
- SendGrid email delivery (fire-and-forget, no callbacks)
- No webhook integrations identified

## Data Sources (Research Tools)

**DepMap:**
- Source: Figshare (auto-downloadable)
- Data: CRISPR gene dependencies, cell line metadata, somatic mutations
- Latest: 24Q4 release
- Loader: `load_crispr()`, `load_model_metadata()`, `load_mutations()` in `src/ct/data/loaders.py`

**PRISM:**
- Source: https://depmap.org/repurposing/ (manual download required)
- Data: Cell viability screening across 4,686 compounds
- Loader: `load_prism()` in `src/ct/data/loaders.py`

**L1000 (LINCS):**
- Source: GEO GSE92742 (Broad LINCS Level 5 GCTX)
- Data: Gene expression signatures (978 landmark genes, 19,811 compounds)
- Processing: Custom scripts/prepare_l1000.py
- Loader: `load_l1000()` in `src/ct/data/loaders.py`

**MSigDB:**
- Source: Broad Institute GSEA
- Data: Gene set collections (Hallmark, KEGG, Reactome, GO)
- Version: 2024.1.Hs
- Loader: `load_msigdb(collection="h")` in `src/ct/data/loaders.py`

**STRING Database:**
- Source: https://string-db.org/
- Data: Human protein-protein interaction network
- Version: 12.0
- Loader: Auto-downloads to `~/.ct/data/string/`

---

*Integration audit: 2026-02-25*
