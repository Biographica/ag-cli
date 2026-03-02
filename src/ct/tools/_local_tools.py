"""
Shell executor utility for local bioinformatics tools.

Provides a consistent interface for running external CLI tools (Bowtie2,
OrthoFinder, BLAST+, etc.) with timeout handling, error normalization,
and "tool not installed" detection with install hints.

Mirrors http_client.py pattern: returns (result, error) tuples, never raises.
"""

import shutil
import subprocess


# ---------------------------------------------------------------------------
# Bioinformatics tool registry
# ---------------------------------------------------------------------------

_BIO_TOOL_REGISTRY: dict[str, dict] = {
    "bowtie2": {
        "check_cmd": ["bowtie2", "--version"],
        "install_hint": "conda install -c bioconda bowtie2",
    },
    "minimap2": {
        "check_cmd": ["minimap2", "--version"],
        "install_hint": "conda install -c bioconda minimap2",
    },
    "blastn": {
        "check_cmd": ["blastn", "-version"],
        "install_hint": "conda install -c bioconda blast",
    },
    "orthofinder": {
        "check_cmd": ["orthofinder", "--help"],
        "install_hint": "conda install -c bioconda orthofinder",
    },
}


def run_local_tool(
    cmd: list[str],
    *,
    timeout: int = 120,
    tool_name: str | None = None,
) -> tuple[str | None, str | None]:
    """Run a local bioinformatics tool as a subprocess.

    Returns ``(stdout, None)`` on success or ``(None, error_message)`` on
    failure.  Exactly one element of the tuple is non-None.

    Detects "tool not installed" via ``FileNotFoundError`` and provides
    install hints from the registry when available.

    Args:
        cmd: Command and arguments as a list (never use shell=True).
        timeout: Maximum seconds to wait (default 120).
        tool_name: Optional registry key for richer error messages.

    Returns:
        Tuple of (stdout_string, error_string).  Exactly one is non-None.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            stderr_snippet = (result.stderr or "")[:500]
            return None, f"{cmd[0]} failed (exit {result.returncode}): {stderr_snippet}"
        return result.stdout, None
    except FileNotFoundError:
        hint = ""
        name = tool_name or cmd[0]
        if name in _BIO_TOOL_REGISTRY:
            hint = f" Install with: {_BIO_TOOL_REGISTRY[name]['install_hint']}"
        return None, f"Tool not installed: {cmd[0]}.{hint}"
    except subprocess.TimeoutExpired:
        return None, f"{cmd[0]} timed out after {timeout}s"
    except Exception as exc:
        return None, str(exc)


def check_tool_available(tool_name: str) -> bool:
    """Return True if a named tool is installed and executable.

    Checks the registry first for a specific check command.  Falls back
    to ``shutil.which`` for tools not in the registry.

    Args:
        tool_name: Tool name (e.g. "bowtie2", "minimap2").

    Returns:
        True if the tool is available on PATH.
    """
    if tool_name not in _BIO_TOOL_REGISTRY:
        return bool(shutil.which(tool_name))
    check_cmd = _BIO_TOOL_REGISTRY[tool_name]["check_cmd"]
    _, err = run_local_tool(check_cmd, timeout=10, tool_name=tool_name)
    return err is None
