"""
Plant data tools for ag-cli / Harvest.

Provides agent-callable tools for discovering and loading local curated
plant datasets. Uses the manifest system from 02-01 and the @validate_species
decorator from 02-02.

Tools:
    data.list_datasets   -- discover available local plant datasets
    data.load_expression -- load gene expression data from a local parquet
"""

from __future__ import annotations

from ct.tools import registry
from ct.tools._validation import validate_species


@registry.register(
    name="data.list_datasets",
    description="List available local plant datasets with their species coverage and file schemas",
    category="data",
    parameters={
        "data_root": "Optional path to data root (defaults to configured data.base)"
    },
    usage_guide=(
        "Call before any data analysis to discover what curated datasets are available locally. "
        "Returns dataset names, species covered, and file schemas from manifest files."
    ),
)
def list_datasets(data_root: str = "", **kwargs) -> dict:
    """List all local plant datasets found in the data root directory.

    Iterates subdirectories under *data_root*, loads each manifest, and
    returns a summary of available datasets.  Directories without a manifest
    are still listed with a note to explore files directly.

    Returns:
        dict with keys:
            summary  -- human-readable summary string
            datasets -- list of manifest dicts (or plain dir-name strings for
                        directories without a manifest)
    """
    from pathlib import Path  # lazy import

    from ct.agent.config import Config  # lazy import
    from ct.data.manifest import load_manifest, manifest_summary  # lazy import

    # Resolve data root
    if data_root:
        root = Path(data_root)
    else:
        try:
            cfg = Config.load()
            base = cfg.get("data.base")
            root = Path(base) if base else Path.home() / ".ct" / "data"
        except Exception:
            root = Path.home() / ".ct" / "data"

    if not root.exists():
        return {
            "summary": (
                f"No data directory found at {root}. "
                "Run 'ag data pull <dataset>' to download datasets."
            ),
            "datasets": [],
        }

    # Iterate subdirectories
    results = []
    summaries: list[str] = []

    try:
        subdirs = sorted(p for p in root.iterdir() if p.is_dir())
    except PermissionError:
        return {
            "summary": f"Permission denied reading {root}",
            "datasets": [],
        }

    for subdir in subdirs:
        manifest = load_manifest(subdir)
        if manifest is not None:
            results.append(manifest)
            summaries.append(manifest_summary(manifest))
        else:
            results.append(subdir.name)
            summaries.append(f"{subdir.name}: No manifest — explore files directly")

    if not results:
        summary_text = f"No datasets found in {root}"
    else:
        summary_text = f"Found {len(results)} dataset(s) in {root}\n\n" + "\n\n".join(summaries)

    return {
        "summary": summary_text,
        "datasets": results,
    }


@registry.register(
    name="data.load_expression",
    description="Load gene expression data from a local plant expression dataset",
    category="data",
    parameters={
        "gene": "Gene identifier (e.g., 'AT1G65480', 'Os01g0100100')",
        "species": "Species name or taxon ID (default: Arabidopsis thaliana)",
        "dataset": "Dataset name or path (default: plantexp)",
        "tissue": "Optional tissue filter (e.g., 'leaf', 'root', 'seed')",
    },
    usage_guide=(
        "Load tissue-level expression values for a gene from a local curated expression dataset. "
        "Reads manifest first to validate species coverage, then loads the expression parquet."
    ),
)
@validate_species(dataset_kwarg="dataset")
def load_expression(
    gene: str,
    species: str = "Arabidopsis thaliana",
    dataset: str = "plantexp",
    tissue: str = "",
    **kwargs,
) -> dict:
    """Load gene expression data from a local parquet expression matrix.

    Resolves the dataset path, loads the expression_matrix.parquet (or .csv),
    filters by gene and optionally by tissue, and returns per-tissue mean TPM
    values.

    The ``@validate_species(dataset_kwarg="dataset")`` decorator resolves the
    dataset path BEFORE this function body runs and injects ``species_warning``
    into the result dict when a mismatch is detected.

    Args:
        gene:    Gene identifier to look up (case-insensitive).
        species: Requested species — used only for validation warning.
        dataset: Dataset name (resolved via Config data.base) or absolute path.
        tissue:  Optional tissue filter.

    Returns:
        dict with keys:
            summary    -- human-readable result summary
            gene       -- requested gene identifier
            species    -- requested species string
            n_samples  -- number of matching samples
            expression -- list of {tissue, mean_tpm, n_samples} dicts
    """
    import pandas as pd  # lazy import
    from pathlib import Path  # lazy import

    from ct.agent.config import Config  # lazy import

    # Resolve dataset path
    p = Path(dataset)
    if p.is_absolute():
        dataset_path = p
    else:
        try:
            cfg = Config.load()
            base = cfg.get("data.base") or str(Path.home() / ".ct" / "data")
        except Exception:
            base = str(Path.home() / ".ct" / "data")
        dataset_path = Path(base) / dataset

    # Locate expression file
    parquet_path = dataset_path / "expression_matrix.parquet"
    csv_path = dataset_path / "expression_matrix.csv"

    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        return {
            "summary": (
                f"Expression data not found at {dataset_path}. "
                f"Run: ag data pull {dataset}"
            ),
            "error": f"Expression data not found at {dataset_path}",
            "gene": gene,
            "species": species,
            "n_samples": 0,
            "expression": [],
        }

    # Filter by gene (case-insensitive)
    gene_col = "gene_id" if "gene_id" in df.columns else df.columns[0]
    mask = df[gene_col].str.upper() == gene.upper()
    filtered = df[mask]

    # Optional tissue filter
    if tissue and "tissue" in filtered.columns:
        filtered = filtered[filtered["tissue"].str.lower() == tissue.lower()]

    if filtered.empty:
        no_match_msg = f"No expression data found for gene '{gene}'"
        if tissue:
            no_match_msg += f" in tissue '{tissue}'"
        return {
            "summary": no_match_msg,
            "gene": gene,
            "species": species,
            "n_samples": 0,
            "expression": [],
        }

    # Build tissue breakdown
    n_samples = len(filtered)
    tissue_means: list[dict] = []
    tissue_table_lines: list[str] = []

    if "tissue" in filtered.columns and "tpm" in filtered.columns:
        grouped = filtered.groupby("tissue")["tpm"].agg(["mean", "count"])
        for tissue_name, row in grouped.iterrows():
            tissue_means.append(
                {
                    "tissue": tissue_name,
                    "mean_tpm": round(float(row["mean"]), 3),
                    "n_samples": int(row["count"]),
                }
            )
            tissue_table_lines.append(
                f"  {tissue_name}: {row['mean']:.1f} TPM (n={int(row['count'])})"
            )
    else:
        # No tissue/tpm columns — return raw data summary
        tissue_means = []

    n_tissues = len(tissue_means)
    tissue_table = "\n".join(tissue_table_lines) if tissue_table_lines else ""
    summary = (
        f"Expression data for {gene}: {n_samples} samples across {n_tissues} tissue(s)\n"
        f"{tissue_table}"
    ).strip()

    return {
        "summary": summary,
        "gene": gene,
        "species": species,
        "n_samples": n_samples,
        "expression": tissue_means,
    }
