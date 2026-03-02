# Technology Stack

**Analysis Date:** 2026-02-25

## Languages

**Primary:**
- Python 3.10+ - Core application, CLI, agent orchestration
- JavaScript/TypeScript - None detected (pure Python project)

## Runtime

**Environment:**
- Python 3.10+ (specified in `pyproject.toml`)

**Package Manager:**
- pip/hatch
- Lockfile: Not detected (uses standard pyproject.toml with version pinning)

## Frameworks

**Core:**
- Typer 0.12+ - CLI framework for command-line interface (`ct` command)
- Rich 13.0+ - Terminal UI, formatted output, progress bars, tables
- Prompt-toolkit 3.0+ - Interactive terminal mode, suggestions

**Agent Orchestration:**
- Claude Agent SDK 0.1+ - Agentic loop runner using MCP (Model Context Protocol)
- Anthropic SDK 0.40+ - Primary LLM provider (Claude models)
- OpenAI SDK 1.0+ - Secondary LLM provider (GPT-4o models)

**Data Processing:**
- Pandas 2.0+ - Tabular data manipulation, CSV/Parquet I/O
- NumPy 1.24+ - Numerical arrays, scientific computing
- SciPy 1.10+ - Scientific functions

**Optional Domain Libraries:**
- RDKit 2023.03+ - Chemistry: molecular descriptors, fingerprints, SMILES parsing
- BioPython 1.81+ - Biology: sequence analysis, bioinformatics
- ScanPy 1.9+ - Single-cell analysis (optional, installed with `[singlecell]` extra)
- AnnData 0.10+ - Annotated data matrices for single-cell
- CellTypist 1.6+ - Cell type annotation (optional)
- CellXGene Census 1.0+ - CellXGene data API client (optional)
- TileDBSoma 1.0+ - Genomic data format (optional)
- Torch 2.0+ - Deep learning (optional, installed with `[ml]` extra)
- Transformers 4.40+ - Hugging Face models, ESM-2 protein embeddings
- Fair-ESM 2.0+ - Meta's ESM protein language model (optional)
- Scikit-Learn 1.3+ - Machine learning algorithms (optional)
- Seaborn 0.13+ - Statistical data visualization (optional)

**API & HTTP:**
- httpx 0.27+ - Async-capable HTTP client with retry/backoff helpers

**Data & Config:**
- python-dotenv 1.0+ - Environment variable loading (.env support)
- DuckDB 1.0+ - In-memory query engine for Parquet/CSV files (Data API)
- Markdown 3.5+ - Markdown parsing (reports)
- nbformat 5.7+ - Jupyter notebook format support

**Development & Testing:**
- Pytest 8.0+ - Test runner
- Pytest-Cov 5.0+ - Coverage reporting
- Ruff 0.5+ - Fast Python linter/formatter

**Optional Deployment:**
- FastAPI 0.100+ - Web API framework (optional, `[api]` extra)
- Uvicorn[standard] 0.20+ - ASGI server (optional, `[api]` extra)

## Key Dependencies

**Critical:**
- `anthropic>=0.40` - Primary LLM client; all agent reasoning uses Claude
- `claude-agent-sdk>=0.1` - Agentic loop runner with MCP server
- `typer>=0.12` - CLI parsing and command routing
- `rich>=13.0` - Terminal rendering and progress tracking

**Domain/Biology:**
- `rdkit>=2023.03` - Chemistry descriptor computation, SMILES validation
- `scanpy>=1.9` - Single-cell analysis workflows
- `transformers>=4.40` - ESM-2 protein embeddings
- `duckdb>=1.0` - Query engine for data APIs

**Infrastructure:**
- `httpx>=0.27` - HTTP requests with retries (unified across all API tools)
- `pandas>=2.0` - Data loading and manipulation

## Configuration

**Environment:**
- Loads from `.env` in current directory and project root (via `python-dotenv`)
- Config stored at `~/.ct/config.json` (JSON, persisted)

**Key Configured Items:**
- LLM provider and API keys (Anthropic, OpenAI, local)
- Data paths (DepMap, PRISM, L1000, MSigDB, AlphaFold)
- External API keys (IBM RXN, Lens.org, SendGrid)
- Compute provider settings (Lambda Labs, RunPod)
- Agent behavior presets (research, enterprise, pharma)

**Build:**
- Hatchling: Standard Python build backend
- Config: `pyproject.toml` (no separate setup.py)
- Entry point: `ct = "ct.cli:entry"` (CLI command)

## Platform Requirements

**Development:**
- Python 3.10 or newer
- pip or compatible package manager
- Optional: GPU support for torch-based models (ESM-2, etc.)

**Production:**
- Python 3.10 or newer
- Internet connection for LLM APIs (Anthropic/OpenAI)
- Optional: Local GPU for protein embedding/ML models
- Optional: External API credentials (IBM RXN, Lens.org, SendGrid)
- Optional: Compute provider accounts (Lambda Labs, RunPod)

---

*Stack analysis: 2026-02-25*
