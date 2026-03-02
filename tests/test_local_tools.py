"""Tests for _local_tools.py shell executor utility."""

from unittest.mock import patch, MagicMock
import subprocess
import pytest

from ct.tools._local_tools import run_local_tool, check_tool_available, _BIO_TOOL_REGISTRY


class TestRunLocalTool:
    """Tests for run_local_tool function."""

    @patch("ct.tools._local_tools.subprocess.run")
    def test_success(self, mock_run):
        """Successful subprocess call returns (stdout, None)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output data\n",
            stderr="",
        )
        stdout, err = run_local_tool(["echo", "hello"])
        assert stdout == "output data\n"
        assert err is None
        mock_run.assert_called_once()

    @patch("ct.tools._local_tools.subprocess.run")
    def test_nonzero_exit(self, mock_run):
        """Non-zero exit code returns (None, error)."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="some error",
        )
        stdout, err = run_local_tool(["failing_tool"])
        assert stdout is None
        assert "failed (exit 1)" in err
        assert "some error" in err

    @patch("ct.tools._local_tools.subprocess.run", side_effect=FileNotFoundError)
    def test_tool_not_installed_with_hint(self, mock_run):
        """FileNotFoundError for registered tool includes install hint."""
        stdout, err = run_local_tool(["bowtie2", "--version"], tool_name="bowtie2")
        assert stdout is None
        assert "Tool not installed" in err
        assert "conda install" in err

    @patch("ct.tools._local_tools.subprocess.run", side_effect=FileNotFoundError)
    def test_tool_not_installed_without_hint(self, mock_run):
        """FileNotFoundError for unregistered tool has no install hint."""
        stdout, err = run_local_tool(["unknown_tool"])
        assert stdout is None
        assert "Tool not installed" in err
        assert "conda install" not in err

    @patch("ct.tools._local_tools.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["slow"], timeout=5))
    def test_timeout(self, mock_run):
        """TimeoutExpired returns (None, timeout error)."""
        stdout, err = run_local_tool(["slow"], timeout=5)
        assert stdout is None
        assert "timed out" in err

    @patch("ct.tools._local_tools.subprocess.run", side_effect=OSError("permission denied"))
    def test_generic_exception(self, mock_run):
        """Other exceptions return (None, str(exc))."""
        stdout, err = run_local_tool(["broken"])
        assert stdout is None
        assert "permission denied" in err

    @patch("ct.tools._local_tools.subprocess.run")
    def test_stderr_truncated(self, mock_run):
        """Long stderr is truncated to 500 chars."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="x" * 1000,
        )
        stdout, err = run_local_tool(["verbose_fail"])
        assert stdout is None
        # Error message includes at most 500 chars of stderr
        assert len(err) < 600


class TestCheckToolAvailable:
    """Tests for check_tool_available function."""

    @patch("ct.tools._local_tools.run_local_tool", return_value=("Bowtie2 v2.5.0\n", None))
    def test_registered_tool_available(self, mock_run):
        """Registered tool that runs successfully returns True."""
        assert check_tool_available("bowtie2") is True
        mock_run.assert_called_once()

    @patch("ct.tools._local_tools.run_local_tool", return_value=(None, "Tool not installed"))
    def test_registered_tool_missing(self, mock_run):
        """Registered tool that fails returns False."""
        assert check_tool_available("bowtie2") is False

    @patch("ct.tools._local_tools.shutil.which", return_value="/usr/bin/custom_tool")
    def test_unregistered_tool_on_path(self, mock_which):
        """Unregistered tool found via shutil.which returns True."""
        assert check_tool_available("custom_tool") is True
        mock_which.assert_called_once_with("custom_tool")

    @patch("ct.tools._local_tools.shutil.which", return_value=None)
    def test_unregistered_tool_missing(self, mock_which):
        """Unregistered tool not on PATH returns False."""
        assert check_tool_available("custom_tool") is False


class TestBioToolRegistry:
    """Tests for the bio tool registry structure."""

    def test_registry_has_expected_tools(self):
        """Registry contains minimum M1 tool set."""
        for tool in ("bowtie2", "minimap2", "blastn", "orthofinder"):
            assert tool in _BIO_TOOL_REGISTRY
            assert "check_cmd" in _BIO_TOOL_REGISTRY[tool]
            assert "install_hint" in _BIO_TOOL_REGISTRY[tool]

    def test_check_cmds_are_lists(self):
        """All check_cmd entries are lists (not strings — avoid shell=True)."""
        for tool, info in _BIO_TOOL_REGISTRY.items():
            assert isinstance(info["check_cmd"], list), f"{tool} check_cmd must be a list"
