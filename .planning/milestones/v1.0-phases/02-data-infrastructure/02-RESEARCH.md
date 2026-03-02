# Phase 2: Data Infrastructure - Research

**Researched:** 2026-02-25
**Domain:** Local-first plant data access — species registry, manifest conventions, organism validation middleware, dataset loaders
**Confidence:** HIGH (primary sources: existing codebase patterns, PyYAML/pyarrow confirmed available, pandas/functools confirmed in project)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Species Registry Design**
- YAML format, developer-maintained for now (format makes user-extensibility easy to add later)
- Registry is a convenience lookup table, not a gatekeeper: resolves aliases → canonical name → taxon ID → genome build
- Agent decides naturally when to ask about species — no forced species prompt or deterministic UX gate
- Unknown species proceed with a note; the registry helps when it can, stays out of the way when it can't
- Important: not all analyses have a single clear organism (e.g., nitrogen fixation involving soil metagenomics + root transcriptomics, or disease datasets with crop + pathogen strain). The registry must not block multi-organism or non-standard workflows
- Core species to include: Arabidopsis, rice, maize, wheat, soybean, tomato (expand as datasets arrive)

**Manifest Conventions**
- Manifests are a convention for curated/shipped data sources, never required for user-provided data
- When present, manifests describe: schema (column names/types), species covered, plain-English description of dataset contents
- Agent explores user-provided data dynamically (reads files, infers schema, works with it — like Claude Code handles code files)
- Persistent data connectors (Ensembl, Plant Metabolic Network, etc.) should ship with manifests so the agent knows what they contain and how to explore them

**Validation Behavior**
- Warn and proceed on species mismatch — informational, not blocking (e.g., "this dataset contains rice, not arabidopsis" returned to agent, data still returned)
- Shared middleware/decorator pattern for consistent behavior across tools
- Multi-species datasets: validation checks that requested species is IN the dataset, not that it's the only one
- Unknown/unregistered species: proceed with a note that metadata couldn't be resolved. Never block

**Dataset Scope and Format**
- Supported file formats: parquet, CSV, GFF3, FASTA, VCF, BED — all handled via Python sandbox (pandas, BioPython)
- Clean-on-pull architecture: `ag data pull <dataset>` downloads from S3/Dagster assets and saves clean, ready-to-use data to a configurable local data root
- Thin cached loaders for curated data: path resolution + `@lru_cache` only — no cleaning logic in loaders (cleaning happens at pull time or upstream in Dagster)
- No bespoke loader functions for user-provided data — agent reads files directly from whatever path the user provides
- In practical near terms, pulls will come from Dagster assets (backed by S3 paths) that have already undergone significant manual cleaning

### Claude's Discretion
- Manifest file format (YAML vs JSON) — whatever integrates cleanly with the codebase
- Species registry internal structure and resolution algorithm
- Exact middleware/decorator implementation pattern for organism validation
- Cache eviction strategy and memory management
- Data root directory structure and naming conventions

### Deferred Ideas (OUT OF SCOPE)
- User-extensible species registry (custom YAML in config directory) — add when a user actually needs it
- Dagster connector for `ag data pull --source dagster --asset my_custom_asset_name` — future enhancement beyond simple S3 paths
- Data integrity validation in manifests (content hashes, row counts) — not needed for Phase 2 discovery-focused manifests
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | Agent can explore and analyse data from a local project folder (parquets, CSVs, GFFs) using the Python sandbox | Existing `code.execute` sandbox + `files.*` tools already handle this; needs data.base config extension and `ag data pull` for plant datasets |
| DATA-02 | Data manifest pattern — each data folder has a manifest (JSON/YAML) describing available datasets, species, schema, and provenance | New: `manifest.yaml` convention per dataset folder, loader reads manifest before data files, agent uses manifest to plan queries |
| DATA-03 | Organism validation middleware — tools that access external data validate species consistency before returning results | New: `@validate_species` decorator wrapping tool functions; warn-and-proceed pattern; reads manifest species coverage |
| DATA-04 | Species registry — central registry of supported species with metadata (taxon ID, common name, genome build) | Partially exists as `_species.py` in-memory dict; needs YAML file, genome_build field, `ag species list` CLI command |
</phase_requirements>

---

## Summary

Phase 2 builds the data access layer that transforms ag-cli from a purely API-based agent into one that can reason about curated local plant datasets. The work has three distinct parts: (1) formalizing and extending the species registry from its current in-memory dict form to a YAML file that also captures genome build; (2) implementing a manifest convention that lets the agent discover what datasets are available and their schema before loading files; (3) adding organism validation middleware that warns (never blocks) when species mismatch is detected.

The existing codebase provides strong patterns to follow. `ct.data.loaders` demonstrates the `@lru_cache` + path-resolution loader pattern already. `ct.data.downloader` shows how `ag data pull` works and how datasets are registered. `ct.tools._species` provides a complete in-memory taxon map that serves as the foundation for the YAML registry. `ct.tools.files` and `ct.agent.config` show how data paths are surfaced to tools. PyYAML is already available in the environment (v6.0.1), pyarrow is available (v11.0.0), and pandas is a core dependency — all needed formats (parquet, CSV) are immediately loadable.

The key design insight from CONTEXT.md: manifests are informational metadata for the agent to read, not gatekeeping infrastructure. Validation is a warning, not a block. The registry resolves aliases but never rejects unknown species. All three components should feel lightweight and helpful rather than bureaucratic.

**Primary recommendation:** Model all three components (registry YAML, manifest YAML, validation decorator) on existing patterns in `ct.data.loaders` and `ct.tools._species`. The work is additive, not refactoring.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | 6.0.1 (env confirmed) | Parse species registry YAML and manifest files | Already in environment; `yaml.safe_load` is safe, fast, human-readable |
| pandas | >=2.0 (pyproject.toml) | Load parquet and CSV datasets via `read_parquet` / `read_csv` | Core project dependency; already used throughout loaders.py |
| pyarrow | 11.0.0 (env confirmed) | Backend for `pd.read_parquet` — required for parquet support | Confirmed available; pandas delegates to it for parquet |
| functools.lru_cache | stdlib | Cache loaded DataFrames to avoid repeated disk reads | Pattern already used in `ct.data.loaders` for all 5 existing loaders |
| pathlib.Path | stdlib | Path resolution and existence checks | Used throughout the codebase; canonical path handling pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| BioPython | >=1.81 (pyproject.toml) | Parse GFF3, FASTA, VCF, BED via `Bio.SeqIO`, `Bio.SeqUtils` | Already in dependencies; agent will use for genomic file formats in sandbox |
| typer | >=0.12 (pyproject.toml) | Add `ag species list` and `ag data list` CLI commands | Already used for all CLI subcommands; same pattern as `data_app` |
| rich | >=13.0 (pyproject.toml) | Render species list and manifest status as tables | Already used for `dataset_status()` and `config.to_table()` |
| hashlib | stdlib | Content hash in manifests (deferred per CONTEXT.md but field can be pre-populated as empty) | Not needed Phase 2 — deferred |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| YAML for manifests | JSON | YAML is developer-friendlier (comments, no quotes), JSON is more machine-native; YAML wins for developer-maintained files per locked decision |
| `@lru_cache` for loaders | `functools.cache` | `cache` is Python 3.9+, `lru_cache(maxsize=None)` is equivalent and more explicit; project uses `lru_cache` already |
| Decorator for validation | Mixin class | Decorator is simpler, composable, matches Python functional style used elsewhere in tools |
| YAML for species registry | Python dict in .py file | YAML allows non-developer edits, survives refactoring, and was explicitly chosen by user |

**Installation:** No new packages needed — PyYAML, pandas, pyarrow, BioPython, typer, rich are all available.

---

## Architecture Patterns

### Recommended Project Structure

```
src/ct/
├── data/
│   ├── loaders.py          # EXTEND: add plant dataset loaders (plantexp, etc.)
│   ├── downloader.py       # EXTEND: add plant dataset entries to DATASETS dict
│   ├── manifest.py         # NEW: manifest loading and schema validation
│   └── species_registry.yaml  # NEW: YAML species registry
│
├── tools/
│   ├── _species.py         # EXTEND: add genome_build, load from YAML
│   ├── _validation.py      # NEW: @validate_species decorator
│   └── plant_data.py       # NEW: data.* tools (data.list_datasets, data.load_expression)
│
└── agent/
    └── config.py           # EXTEND: add data.plant_data_root config key
```

The CLI changes are in `src/ct/cli.py`: add `species_app` subcommand with `species list`.

### Pattern 1: Species Registry YAML Structure

**What:** A YAML file shipped with the package that maps canonical binomial names to taxon ID, common names, genome build, and aliases. Loaded once at module import, cached as a dict.

**When to use:** Whenever a tool needs to resolve species names, validate species coverage, or list supported species.

**Example:**
```yaml
# src/ct/data/species_registry.yaml
species:
  - binomial: "Arabidopsis thaliana"
    taxon_id: 3702
    common_names: ["arabidopsis", "thale cress"]
    abbreviations: ["at", "ath"]
    genome_build: "TAIR10"
    notes: "Model plant organism; most tools default to this species"

  - binomial: "Oryza sativa"
    taxon_id: 4530
    common_names: ["rice"]
    abbreviations: ["os"]
    genome_build: "IRGSP-1.0"

  - binomial: "Zea mays"
    taxon_id: 4577
    common_names: ["maize", "corn"]
    abbreviations: ["zm"]
    genome_build: "B73 RefGen_v4"

  - binomial: "Triticum aestivum"
    taxon_id: 4565
    common_names: ["wheat", "bread wheat"]
    abbreviations: ["ta"]
    genome_build: "IWGSC RefSeq v1.0"

  - binomial: "Glycine max"
    taxon_id: 3847
    common_names: ["soybean", "soy"]
    abbreviations: ["gm"]
    genome_build: "Wm82.a2.v1"

  - binomial: "Solanum lycopersicum"
    taxon_id: 4081
    common_names: ["tomato"]
    abbreviations: ["sl"]
    genome_build: "SL3.0"
```

### Pattern 2: Species Registry Loader (extending _species.py)

**What:** Load the YAML at module import, build lookup dicts, expose `resolve_species_*` functions. Adds genome_build to returned data.

**When to use:** Replace the in-memory `_PLANT_TAXON_MAP` dict with YAML-backed version; resolution functions stay identical.

```python
# src/ct/tools/_species.py (extended)
import yaml
from functools import lru_cache
from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent.parent / "data" / "species_registry.yaml"


@lru_cache(maxsize=1)
def _load_registry() -> list[dict]:
    """Load species registry from YAML. Cached after first call."""
    with open(_REGISTRY_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("species", [])


def _build_taxon_map() -> dict[str, tuple[int, str, str]]:
    """Build lookup dict: key → (taxon_id, canonical_binomial, genome_build)."""
    result = {}
    for entry in _load_registry():
        binomial = entry["binomial"]
        taxon_id = entry["taxon_id"]
        genome_build = entry.get("genome_build", "")
        # Index by canonical binomial (lowercase)
        key = binomial.lower()
        result[key] = (taxon_id, binomial, genome_build)
        # Index by common names
        for name in entry.get("common_names", []):
            result[name.lower()] = (taxon_id, binomial, genome_build)
        # Index by abbreviations
        for abbr in entry.get("abbreviations", []):
            result[abbr.lower()] = (taxon_id, binomial, genome_build)
    return result


# New: expose full registry entry for species list command
def list_all_species() -> list[dict]:
    """Return all registry entries for display."""
    return _load_registry()


def resolve_species_genome_build(species: str, default: str = "") -> str:
    """Resolve a species string to its genome build identifier."""
    ...
```

### Pattern 3: Manifest Convention

**What:** A `manifest.yaml` file in each curated dataset directory. Describes schema, species coverage, and dataset description. Agent reads this before loading files.

**When to use:** Every curated dataset directory shipped with `ag data pull` includes one. Agent reads it to discover what data is available.

```yaml
# ~/.ct/data/plantexp/manifest.yaml
dataset: "PlantExp Expression Atlas"
version: "2024-01"
description: "Tissue-level gene expression profiles across plant species from public RNA-seq datasets"
species_covered:
  - "Arabidopsis thaliana"
  - "Oryza sativa"
  - "Zea mays"
files:
  - name: "expression_matrix.parquet"
    description: "Gene × sample expression matrix (TPM normalized)"
    format: "parquet"
    schema:
      gene_id: "string — TAIR/RAP-DB/MaizeGDB gene identifier"
      sample_id: "string — SRA accession or dataset-internal ID"
      tpm: "float — TPM expression value"
      tissue: "string — tissue/organ descriptor"
      species: "string — binomial species name"
      study: "string — GEO/SRA study accession"
  - name: "sample_metadata.csv"
    description: "Sample metadata: tissue, developmental stage, treatment, study"
    format: "csv"
source: "PlantExp (https://plantexp.org)"
pulled_at: "2024-01-15T10:30:00Z"
```

**Manifest loader in `manifest.py`:**
```python
# src/ct/data/manifest.py
import yaml
from pathlib import Path
from functools import lru_cache


def load_manifest(dataset_dir: Path) -> dict | None:
    """Load manifest.yaml from a dataset directory. Returns None if not found."""
    manifest_path = dataset_dir / "manifest.yaml"
    if not manifest_path.exists():
        # Try JSON fallback
        manifest_path = dataset_dir / "manifest.json"
        if not manifest_path.exists():
            return None
    with open(manifest_path) as f:
        return yaml.safe_load(f)


def manifest_species(manifest: dict) -> list[str]:
    """Extract species list from manifest. Returns [] if not present."""
    return manifest.get("species_covered", [])


def manifest_summary(manifest: dict) -> str:
    """Return a human-readable summary of dataset contents."""
    name = manifest.get("dataset", "Unknown dataset")
    desc = manifest.get("description", "")
    species = ", ".join(manifest.get("species_covered", [])) or "unspecified"
    files = [f["name"] for f in manifest.get("files", [])]
    return (
        f"{name}: {desc}\n"
        f"Species: {species}\n"
        f"Files: {', '.join(files)}"
    )
```

### Pattern 4: Organism Validation Decorator

**What:** A decorator applied to tools that access species-specific datasets. Checks that the requested species is covered by the dataset manifest. Warns and proceeds — never blocks.

**When to use:** Apply to any tool that: (a) accepts a `species` parameter, and (b) loads data from a specific curated dataset.

```python
# src/ct/tools/_validation.py
import functools
import logging
from pathlib import Path
from ct.data.manifest import load_manifest, manifest_species
from ct.tools._species import resolve_species_binomial

_log = logging.getLogger("ct.tools.validation")


def validate_species(dataset_dir_kwarg: str = "dataset_dir"):
    """Decorator: warn if requested species is not covered by the dataset manifest.

    The decorator looks for `species` and `dataset_dir` in the function kwargs.
    If the manifest for `dataset_dir` lists species_covered and the requested species
    is not in that list, a warning is included in the returned dict.

    Never blocks execution. Always proceeds with data loading.

    Usage:
        @validate_species()
        def load_expression(gene: str, species: str = "arabidopsis", **kwargs) -> dict:
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            species_str = kwargs.get("species", "")
            dataset_dir = kwargs.get(dataset_dir_kwarg)

            species_warning = None
            if species_str and dataset_dir:
                manifest = load_manifest(Path(dataset_dir))
                if manifest:
                    covered = [s.lower() for s in manifest_species(manifest)]
                    canonical = resolve_species_binomial(species_str).lower()
                    if covered and canonical not in covered:
                        covered_display = ", ".join(manifest_species(manifest))
                        species_warning = (
                            f"Note: requested species '{species_str}' "
                            f"(resolved: '{canonical}') is not listed in dataset "
                            f"species coverage: [{covered_display}]. "
                            f"Data returned anyway — verify results manually."
                        )
                        _log.warning(species_warning)

            result = func(*args, **kwargs)

            if species_warning and isinstance(result, dict):
                existing = result.get("species_warning", "")
                result["species_warning"] = (existing + "\n" + species_warning).strip()
                # Prepend warning to summary so agent sees it
                result["summary"] = species_warning + "\n\n" + result.get("summary", "")

            return result
        return wrapper
    return decorator
```

### Pattern 5: Plant Dataset Loader

**What:** A new tool module `plant_data.py` with tools the agent can call: `data.list_datasets`, `data.load_expression`. Follows the exact `@registry.register` pattern in CLAUDE.md.

**When to use:** These are MCP-exposed tools the agent calls; they are thin wrappers over pandas + manifest reading.

```python
# src/ct/tools/plant_data.py
from ct.tools import registry
from ct.agent.config import Config
from ct.data.manifest import load_manifest, manifest_summary
from pathlib import Path


@registry.register(
    name="data.list_datasets",
    description="List available local plant datasets with their species coverage and file schemas",
    category="data",
    parameters={
        "data_root": "Optional path to data root (defaults to configured data.plant_data_root)"
    },
    usage_guide=(
        "Call before any data analysis to discover what curated datasets are available locally. "
        "Returns dataset names, species covered, and file schemas from manifest files."
    ),
)
def list_datasets(data_root: str = "", **kwargs) -> dict:
    """List available datasets with manifest metadata."""
    import yaml
    cfg = Config.load()
    root = Path(data_root) if data_root else Path(cfg.get("data.plant_data_root", cfg.get("data.base")))
    ...


@registry.register(
    name="data.load_expression",
    description="Load gene expression data from a local plant expression dataset",
    category="data",
    parameters={
        "gene": "Gene identifier (e.g., 'AT1G65480', 'Os01g0100100')",
        "species": "Species name or taxon ID (default: arabidopsis_thaliana)",
        "dataset": "Dataset name or path (default: plantexp)",
        "tissue": "Optional tissue filter (e.g., 'leaf', 'root', 'seed')",
    },
    usage_guide=(
        "Load tissue-level expression values for a gene from a local curated expression dataset. "
        "Reads manifest first to validate species coverage, then loads the expression parquet."
    ),
)
def load_expression(gene: str, species: str = "arabidopsis_thaliana",
                    dataset: str = "plantexp", tissue: str = "", **kwargs) -> dict:
    """Load expression data for a gene from a curated dataset."""
    import pandas as pd
    ...
```

### Pattern 6: ag species list CLI Command

**What:** A new `species_app` typer subcommand that renders the species registry as a rich table.

**When to use:** User runs `ag species list` to see all supported species with their metadata.

```python
# In src/ct/cli.py — add after data_app

species_app = typer.Typer(help="Species registry management")
app.add_typer(species_app, name="species")


@species_app.command("list")
def species_list():
    """List all species in the registry with taxon IDs and genome builds."""
    from ct.tools._species import list_all_species
    from rich.table import Table
    entries = list_all_species()
    table = Table(title="Supported Species Registry")
    table.add_column("Binomial Name", style="cyan")
    table.add_column("Taxon ID")
    table.add_column("Common Names")
    table.add_column("Genome Build")
    for entry in entries:
        table.add_row(
            entry["binomial"],
            str(entry["taxon_id"]),
            ", ".join(entry.get("common_names", [])),
            entry.get("genome_build", "—"),
        )
    console.print(table)
```

### Pattern 7: ag data pull for Plant Datasets

**What:** Extend `DATASETS` dict in `ct.data.downloader` with plant-specific datasets. Near-term: S3 URL downloads. Writes `manifest.yaml` to destination on successful pull.

**When to use:** `ag data pull plantexp` downloads and populates the local data root.

```python
# In ct.data.downloader — extend DATASETS dict
"plantexp": {
    "description": "PlantExp tissue expression atlas (Arabidopsis, rice, maize, wheat, soybean, tomato)",
    "files": {
        "expression_matrix.parquet": "https://s3.biographica.io/plantexp/expression_matrix.parquet",
        "sample_metadata.csv": "https://s3.biographica.io/plantexp/sample_metadata.csv",
        "manifest.yaml": "https://s3.biographica.io/plantexp/manifest.yaml",
    },
    "source": "https://plantexp.org",
    "auto_download": True,
    "size_hint": "TBD",
},
```

**NOTE:** The STATE.md blocker notes: "PlantExp download format must be confirmed at plantexp.org before Phase 2 loader implementation." This means the S3 URL and file format for PlantExp is unconfirmed. The plan should build the loader infrastructure with a **placeholder/mock dataset** and note that the real URL must be confirmed separately. The architecture does not depend on the specific dataset.

### Anti-Patterns to Avoid

- **Blocking on unknown species:** The registry must never raise an exception or return an error for unknown species. Always resolve to default with a note.
- **Required manifests:** Never require a manifest to load data. If manifest is absent, proceed silently. Manifests are advisory.
- **Cleaning in loaders:** Do not add any data cleaning logic to loader functions. Cleaning happens at pull time or in Dagster. Loaders are `path_resolution + pd.read_parquet + @lru_cache` only.
- **Shared lru_cache across dataset paths:** `@lru_cache(maxsize=1)` works when there is one canonical dataset path. If the data root is reconfigurable at runtime, the cache must be keyed by path or cleared on config change.
- **Polluting PLANT_SCIENCE_CATEGORIES:** The new `"data"` category must be added to the `PLANT_SCIENCE_CATEGORIES` frozenset in `ct/tools/__init__.py`, or the agent will not see the new tools.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom text parser | `yaml.safe_load()` from PyYAML | PyYAML handles edge cases (multiline, special chars, Unicode); `safe_load` prevents code execution |
| Parquet loading | Custom binary reader | `pd.read_parquet(path)` | pandas+pyarrow handle schema evolution, compression, column projection; battle-tested |
| Path caching | Custom dict cache | `@functools.lru_cache` | Already used in `loaders.py`; zero-overhead memoization; thread-safe for reads |
| Species alias resolution | Fuzzy string match | Exact dict lookup (already in `_species.py`) | Fuzzy matching introduces ambiguity for abbreviations ('at' = Arabidopsis, not Avena); exact is correct |
| CLI table rendering | Custom string formatting | `rich.Table` | Already used for `dataset_status()`, `config.to_table()`; consistent with rest of CLI |
| Config-backed path resolution | Hardcoded paths | `Config.load().get("data.plant_data_root")` with `~/.ct/data` fallback | Same pattern used by all existing loaders; user can override without code changes |

**Key insight:** The existing codebase has already solved path resolution, config management, caching, table rendering, and CLI subcommands. All Phase 2 work is additive plumbing on top of these working patterns.

---

## Common Pitfalls

### Pitfall 1: `@lru_cache` on Methods or Config-Dependent Functions
**What goes wrong:** If a loader is defined as a module-level function with `@lru_cache(maxsize=1)` and the data path comes from `Config.load()` inside the function, changing the config at runtime does not invalidate the cache. Second call returns stale data from old path.
**Why it happens:** `lru_cache` caches on arguments; `Config.load()` is called inside the function body where it is not an argument.
**How to avoid:** For Phase 2, loaders will typically be called with the data root path as an argument rather than reading config inside. OR accept that the cache is per-process and document that `ag data pull` should be followed by a new agent session.
**Warning signs:** Test shows data from wrong path; changing `data.plant_data_root` config has no effect within a running session.

### Pitfall 2: YAML Loading with `yaml.load()` Instead of `yaml.safe_load()`
**What goes wrong:** `yaml.load()` without a Loader argument can execute arbitrary Python code embedded in YAML. Security vulnerability if manifest files come from untrusted sources.
**Why it happens:** Old PyYAML tutorials use `yaml.load()` without Loader argument.
**How to avoid:** Always use `yaml.safe_load()`. Add a note to code review checklist.
**Warning signs:** `yaml.load()` in codebase without explicit `Loader=yaml.SafeLoader`.

### Pitfall 3: Category Not in PLANT_SCIENCE_CATEGORIES
**What goes wrong:** New `plant_data.py` tools registered under category `"data"` are not visible to the agent because `"data"` is not in the `PLANT_SCIENCE_CATEGORIES` frozenset.
**Why it happens:** The frozenset in `ct/tools/__init__.py` is an allowlist; anything not listed is hidden at the MCP layer.
**How to avoid:** Add `"data"` to `PLANT_SCIENCE_CATEGORIES` as part of the same plan that creates `plant_data.py`.
**Warning signs:** `ag tool list` does not show `data.*` tools; agent cannot call `data.list_datasets`.

### Pitfall 4: Species Registry Not Covering All Entries in _species.py
**What goes wrong:** The existing `_PLANT_TAXON_MAP` in `_species.py` has ~20 species. If the YAML only covers the 6 core species from CONTEXT.md decisions, calls that previously resolved e.g. "barley" now silently fall back to default (Arabidopsis) without a warning that the species IS known but not in registry.
**Why it happens:** YAML registry and in-memory dict diverge.
**How to avoid:** YAML registry should contain ALL species from the current `_PLANT_TAXON_MAP` plus the genome_build field. The YAML is the single source of truth; `_PLANT_TAXON_MAP` is replaced entirely by YAML-derived lookups.
**Warning signs:** `resolve_species_binomial("barley")` returns "Arabidopsis thaliana" instead of "Hordeum vulgare".

### Pitfall 5: Manifest species_covered vs. Actual Data Coverage
**What goes wrong:** Manifest says `species_covered: ["Arabidopsis thaliana"]` but the data file actually has rice rows. Validator passes because manifest matches, but data is wrong.
**Why it happens:** Manifests are manually maintained; they can be out of sync with data.
**How to avoid:** At pull time, optionally validate manifest against data (but CONTEXT.md defers data integrity validation). Document that manifests reflect intended coverage, not guaranteed coverage. The validator should surface this to the agent as a note, not an error.
**Warning signs:** Agent gets rice data when requesting Arabidopsis.

### Pitfall 6: PlantExp Format Is Unconfirmed
**What goes wrong:** Implementation hardcodes assumptions about PlantExp file format (column names, structure) that turn out to be wrong when the actual data is downloaded.
**Why it happens:** STATE.md explicitly notes this as an open blocker: "PlantExp download format must be confirmed at plantexp.org before Phase 2 loader implementation."
**How to avoid:** Build loader infrastructure against a synthetic test dataset with a documented schema. Use manifest-driven schema (column names documented in manifest, loader reads from there). This decouples the loader architecture from the specific dataset format.
**Warning signs:** Hardcoded column names in loader; no tests against mock data.

---

## Code Examples

Verified patterns from existing codebase:

### Existing Loader Pattern (from `ct/data/loaders.py`)
```python
# Source: /src/ct/data/loaders.py

@lru_cache(maxsize=1)
def load_crispr() -> pd.DataFrame:
    """Load DepMap CRISPR gene effect data."""
    path = _find_file("CRISPRGeneEffect.csv", subdirs=["", "depmap"])
    if path is None:
        raise FileNotFoundError(
            "DepMap CRISPR data not found. "
            "Run: ct data pull depmap\n"
            "Or set: ct config set data.base /path/to/data"
        )
    df = _read_tabular(path, index_col=0)
    df.columns = [c.split(' (')[0] for c in df.columns]
    return df
```

This is the exact template to follow for plant dataset loaders. Key elements: `@lru_cache(maxsize=1)`, `_find_file` for path resolution, `FileNotFoundError` with actionable message, no cleaning logic.

### Existing Config Pattern (from `ct/agent/config.py`)
```python
# Source: /src/ct/agent/config.py

DEFAULTS = {
    ...
    "data.base": str(CONFIG_DIR / "data"),  # Falls back to ~/.ct/data
    ...
}
```

New config key to add: `"data.plant_data_root": str(CONFIG_DIR / "data")` — same default, but semantically clearer for plant-specific datasets. Or reuse `data.base` to avoid breaking existing path resolution.

### Existing Downloader Pattern (from `ct/data/downloader.py`)
```python
# Source: /src/ct/data/downloader.py

DATASETS = {
    "depmap": {
        "description": "DepMap CRISPR gene dependencies...",
        "files": {
            "CRISPRGeneEffect.csv": "https://ndownloader.figshare.com/files/...",
        },
        "source": "https://plus.figshare.com/...",
        "auto_download": True,
        "size_hint": "~580MB",
    },
    ...
}
```

Add plant datasets to this dict with the same structure. The downloader already handles progress bars, retries, and config auto-update.

### Existing CLI Subcommand Pattern (from `ct/cli.py`)
```python
# Source: /src/ct/cli.py

data_app = typer.Typer(help="Manage local datasets")
app.add_typer(data_app, name="data")

@data_app.command("pull")
def data_pull(
    dataset: str = typer.Argument(help="Dataset to download"),
    output: Optional[Path] = typer.Option(None, help="Output directory"),
):
    """Download a dataset for local use."""
    from ct.data.downloader import download_dataset
    download_dataset(dataset, output)
```

Same pattern for `species_app.command("list")`.

### Existing Tool Registration Pattern (from CLAUDE.md + `ct/tools/files.py`)
```python
# Source: /src/ct/tools/files.py

@registry.register(
    name="files.read_file",
    description="Read a text file and return its contents",
    category="files",
    parameters={"path": "Path to the file to read"},
    usage_guide=(
        "Use to read data files, prior reports, configuration files, or any file in the "
        "current working directory."
    ),
)
def read_file(path: str, _session=None, **kwargs) -> dict:
    ...
    return {
        "summary": "Human-readable result summary",
        ...
    }
```

New tools in `plant_data.py` must follow this exact pattern. Name prefix MUST match category (`data.list_datasets`, `data.load_expression`).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| In-memory dict in `_species.py` | YAML file at `data/species_registry.yaml` + dict built from YAML | Phase 2 | Adds genome_build; allows non-developer editing; single source of truth |
| No manifest convention | `manifest.yaml` per curated dataset directory | Phase 2 | Agent can discover dataset schema before loading; enables `data.list_datasets` tool |
| No organism validation | `@validate_species` decorator (warn+proceed) | Phase 2 | Consistent warning behavior across all data tools; agent aware of species mismatches |
| Only pharma datasets in downloader | Add plant datasets to `DATASETS` dict | Phase 2 | `ag data pull plantexp` works |

**Deprecated/outdated:**
- Direct dict access to `_PLANT_TAXON_MAP` from outside `_species.py`: after Phase 2, all resolution goes through the YAML-backed registry functions; the dict becomes an implementation detail.

---

## Open Questions

1. **PlantExp actual download URL and schema**
   - What we know: PlantExp exists at plantexp.org; STATE.md flags this as unconfirmed
   - What's unclear: Is it available as parquet/CSV for bulk download? What is the column schema? Is there an S3 path?
   - Recommendation: Build the loader with a synthetic mock dataset. Document the expected schema in the manifest. Real URL can be wired in when confirmed. Do not block Phase 2 progress on this.

2. **Whether `data.base` should be reused or a new `data.plant_data_root` key introduced**
   - What we know: `data.base` defaults to `~/.ct/data` and is used by existing loaders; files.py security checks also use it
   - What's unclear: Will users expect plant data to be co-located with pharma datasets (same `data.base`) or separate?
   - Recommendation: Reuse `data.base` with subdirectory convention (e.g., `~/.ct/data/plantexp/`). This avoids a new config key and matches the existing `depmap`, `prism`, etc. pattern. Only introduce `data.plant_data_root` if the user signals they want separation.

3. **`ag data pull` for datasets that require S3 credentials**
   - What we know: Near-term pulls come from Dagster assets backed by S3; the existing downloader uses public URLs (figshare, Broad)
   - What's unclear: Will Biographica S3 bucket be public or require auth? boto3/aws-cli needed?
   - Recommendation: Start with public URL assumption. If auth is needed, add an optional `aws_profile` config key and boto3 dependency later. Do not block Phase 2 on S3 auth.

---

## Validation Architecture

> `workflow.nyquist_validation` is not in `.planning/config.json` — the field is absent, so this section is included based on the verifier/plan_check workflow being enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_species.py tests/test_manifest.py tests/test_plant_data.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Agent can load parquet/CSV from data root via Python sandbox | integration | `pytest tests/test_plant_data.py::test_load_expression_returns_data -x` | ❌ Wave 0 |
| DATA-02 | Manifest present in dataset dir; manifest_summary() returns species/schema | unit | `pytest tests/test_manifest.py::test_manifest_load_and_summary -x` | ❌ Wave 0 |
| DATA-03 | Species mismatch returns warning in result dict, not error | unit | `pytest tests/test_validation.py::test_species_mismatch_warns_not_blocks -x` | ❌ Wave 0 |
| DATA-04 | `ag species list` CLI returns table with taxon_id and genome_build | unit | `pytest tests/test_cli.py::test_species_list_command -x` | ❌ Wave 0 (extend existing test_cli.py) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_species.py tests/test_manifest.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_species.py` — covers DATA-04 (registry load, alias resolution, genome_build, list_all_species)
- [ ] `tests/test_manifest.py` — covers DATA-02 (manifest load, absent manifest, species extraction, summary)
- [ ] `tests/test_validation.py` — covers DATA-03 (mismatch warning, unknown species, multi-species, absent manifest)
- [ ] `tests/test_plant_data.py` — covers DATA-01 (list_datasets tool, load_expression tool with mock parquet)
- [ ] Extend `tests/test_cli.py` — cover `ag species list` CLI command (DATA-04)
- [ ] Fixtures: synthetic `manifest.yaml` + small `expression_matrix.parquet` in `tests/fixtures/plantexp/`

*(All test files are new; existing `tests/test_downloader.py` can be extended with plant dataset entries)*

---

## Sources

### Primary (HIGH confidence)
- `/src/ct/data/loaders.py` — loader pattern, `@lru_cache`, `_find_file`, `_read_tabular` — read directly
- `/src/ct/data/downloader.py` — `DATASETS` dict, download pattern, `auto_download`, manifest-free pull — read directly
- `/src/ct/tools/_species.py` — complete taxon map, all resolver functions — read directly
- `/src/ct/agent/config.py` — `DEFAULTS` dict, `data.base`, env var mapping — read directly
- `/src/ct/tools/__init__.py` — `PLANT_SCIENCE_CATEGORIES`, `@registry.register` pattern — read directly
- `/src/ct/tools/files.py` — tool registration pattern, `_allowed_paths` for data security — read directly
- `/src/ct/cli.py` — `data_app`, `species_app` pattern needed, existing CLI structure — read directly
- `pyproject.toml` — confirmed pandas, biopython, pyarrow presence in deps
- Environment check: PyYAML 6.0.1, pyarrow 11.0.0 confirmed available

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — blockers: PlantExp URL unconfirmed, Gramene API decision pending
- `.planning/REQUIREMENTS.md` — DATA-01 through DATA-04 definitions
- `.planning/phases/02-data-infrastructure/02-CONTEXT.md` — locked decisions, manifest convention, validation behavior

### Tertiary (LOW confidence)
- PyYAML `safe_load` security recommendation: standard community guidance; `yaml.safe_load` is documented behavior but not verified against current PyYAML 6.x changelog specifically

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed available in environment; existing codebase uses them
- Architecture: HIGH — patterns directly derived from working codebase code; no speculation
- Pitfalls: MEDIUM — derived from codebase analysis and general Python patterns; some (e.g., PlantExp format) are project-specific unknowns flagged in STATE.md

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable domain; PyYAML/pandas APIs are not moving fast)
