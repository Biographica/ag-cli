"""
Organism validation middleware for ag-cli / Harvest tools.

Provides the ``@validate_species`` decorator, which wraps tool functions to
detect species mismatches between a caller's requested species and the
species coverage declared in the dataset manifest.

The decorator is purely informational — it NEVER blocks execution.  The
wrapped function always runs and its result is always returned.  When a
mismatch (or unresolvable species) is detected, a ``species_warning`` key is
added to the result dict and the warning text is prepended to the ``summary``
key so the agent sees it immediately.

Usage::

    from ct.tools._validation import validate_species

    @validate_species()
    def my_tool(gene: str = "", species: str = "", dataset_dir: str = "", **kwargs) -> dict:
        ...

    # Or, when the tool accepts a dataset name instead of a path:
    @validate_species(dataset_kwarg="dataset")
    def my_tool(gene: str = "", species: str = "", dataset: str = "", **kwargs) -> dict:
        ...

Design rules (from CONTEXT.md locked decisions):
- NEVER raise an exception
- NEVER return an error dict instead of real data
- NEVER block execution for any reason
- Warning is purely additive metadata on the result dict
"""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("ct.tools.validation")


def validate_species(
    dataset_dir_kwarg: str = "dataset_dir",
    dataset_kwarg: str = "",
) -> Callable:
    """Decorator factory: warn (never block) if requested species is not covered.

    Resolves the dataset directory BEFORE the wrapped function executes.
    Two resolution modes (tried in order):

    1. *dataset_dir_kwarg* — if the named kwarg holds an explicit directory
       path, use it directly (e.g. ``dataset_dir="/path/to/plantexp"``).
    2. *dataset_kwarg* — if the named kwarg holds a dataset name or path
       (e.g. ``dataset="plantexp"`` or ``dataset="/abs/path"``), the decorator
       resolves it: absolute paths are used directly; relative names are
       resolved via ``Config.data.base`` (e.g. "plantexp" becomes
       ``~/.ct/data/plantexp/``).

    This ensures the decorator can always find the manifest at wrapper time,
    even when the wrapped function would normally resolve the path internally.

    Never blocks execution.  Always calls the wrapped function and returns its
    result.  Warnings are purely additive: ``species_warning`` is added to the
    result dict and prepended to the ``summary`` key.

    Args:
        dataset_dir_kwarg: Name of the kwarg that provides an explicit dataset
            directory path.  Defaults to ``"dataset_dir"``.
        dataset_kwarg: Name of the kwarg that provides a dataset name or path
            for automatic resolution.  Empty string disables this mode.

    Returns:
        A decorator that wraps the tool function with species validation.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # ------------------------------------------------------------------
            # Step 1: Extract species from kwargs — skip if absent or empty
            # ------------------------------------------------------------------
            species: str = kwargs.get("species", "") or ""
            if not species.strip():
                return func(*args, **kwargs)

            # ------------------------------------------------------------------
            # Step 2: Resolve the dataset directory
            # ------------------------------------------------------------------
            dataset_dir: str | None = _resolve_dataset_dir(
                kwargs, dataset_dir_kwarg, dataset_kwarg
            )

            if not dataset_dir:
                # No dataset dir → cannot validate; proceed silently
                return func(*args, **kwargs)

            # ------------------------------------------------------------------
            # Step 3: Load manifest and validate species
            # ------------------------------------------------------------------
            warning: str | None = _check_species(species, dataset_dir)

            # ------------------------------------------------------------------
            # Step 4: Call the wrapped function unconditionally
            # ------------------------------------------------------------------
            result = func(*args, **kwargs)

            # ------------------------------------------------------------------
            # Step 5: Attach warning to result dict (purely additive)
            # ------------------------------------------------------------------
            if warning and isinstance(result, dict):
                result["species_warning"] = warning
                original_summary = result.get("summary", "")
                result["summary"] = f"{warning}\n{original_summary}" if original_summary else warning

            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_dataset_dir(
    kwargs: dict,
    dataset_dir_kwarg: str,
    dataset_kwarg: str,
) -> str | None:
    """Resolve the dataset directory path from kwargs.

    Returns:
        Resolved directory path string, or None if no path could be determined.
    """
    # Mode 1: explicit directory path kwarg
    if dataset_dir_kwarg:
        val = kwargs.get(dataset_dir_kwarg, "") or ""
        if val.strip():
            return str(val).strip()

    # Mode 2: dataset name or path kwarg
    if dataset_kwarg:
        val = kwargs.get(dataset_kwarg, "") or ""
        val = str(val).strip() if val else ""
        if val:
            p = Path(val)
            if p.is_absolute():
                return str(p)
            # Relative name: resolve via Config.data.base
            try:
                from ct.agent.config import Config  # lazy import

                base = Config.load().get(
                    "data.base",
                    str(Path.home() / ".ct" / "data"),
                )
                return str(Path(base) / val)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "validate_species: could not load Config to resolve dataset name %r: %s",
                    val,
                    exc,
                )
                return None

    return None


def _check_species(species: str, dataset_dir: str) -> str | None:
    """Check species against the dataset manifest.

    Returns:
        A warning string if the species is not covered, or None if OK / unknown
        manifest state.  Never raises.
    """
    # Sentinel value that cannot exist in the registry — used to detect
    # "species not in registry" without relying on the default fallback value.
    _SENTINEL = "__SENTINEL_NOT_IN_REGISTRY__"

    try:
        from ct.data.manifest import load_manifest, manifest_species  # lazy import
        from ct.tools._species import resolve_species_binomial  # lazy import

        manifest = load_manifest(Path(dataset_dir))

        # No manifest — validation skipped silently
        if manifest is None:
            return None

        covered: list[str] = manifest_species(manifest)

        # Empty species_covered list — nothing to validate against
        if not covered:
            return None

        # Determine whether the species is in the registry at all.
        # We use a sentinel default: if resolve returns the sentinel, the species
        # is NOT in the registry.  This is reliable regardless of what the
        # standard default is.
        canonical = resolve_species_binomial(species, default=_SENTINEL)

        if canonical == _SENTINEL:
            # Species is NOT in the registry — emit a note, never block
            return (
                f"Species '{species}' is not in the registry; "
                "metadata could not be verified. Data returned anyway."
            )

        # Species IS in the registry.  Check if it appears in the covered list.
        covered_lower = {s.strip().lower() for s in covered}

        if canonical.lower() in covered_lower:
            # Species is covered — no warning
            return None

        # Species is known but NOT covered by this dataset
        covered_str = ", ".join(covered)
        return (
            f"Species mismatch: requested '{species}' (resolved to '{canonical}') "
            f"but dataset covers: {covered_str}. Data returned anyway."
        )

    except Exception as exc:  # noqa: BLE001
        logger.debug("validate_species: error during species check: %s", exc)
        return None
