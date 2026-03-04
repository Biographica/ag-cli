"""Tests for CLI argument parsing and subcommand dispatch."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ct.agent.config import Config
from ct.cli import app


runner = CliRunner()


def test_keys_subcommand_not_treated_as_query():
    with patch("ct.cli.run_query") as mock_run_query, patch(
        "ct.agent.config.Config.load", return_value=Config(data={})
    ):
        result = runner.invoke(app, ["keys"])

    assert result.exit_code == 0
    assert "API Keys" in result.stdout
    mock_run_query.assert_not_called()


def test_doctor_subcommand_not_treated_as_query():
    with patch("ct.cli.run_query") as mock_run_query, patch(
        "ct.agent.config.Config.load", return_value=Config(data={"llm.api_key": "x"})
    ):
        result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "ag Doctor" in result.stdout
    mock_run_query.assert_not_called()


def test_query_mode_uses_remaining_args_as_query():
    with patch("ct.cli.run_query") as mock_run_query, patch(
        "ct.cli.run_interactive"
    ) as mock_run_interactive:
        result = runner.invoke(app, ["run", "profile", "TP53", "in", "AML"])

    assert result.exit_code == 0
    mock_run_interactive.assert_not_called()
    mock_run_query.assert_called_once()
    called_query = mock_run_query.call_args[0][0]
    assert called_query == "profile TP53 in AML"


def test_no_args_enters_interactive_mode():
    with patch("ct.cli.run_query") as mock_run_query, patch(
        "ct.cli.run_interactive"
    ) as mock_run_interactive:
        result = runner.invoke(app, ["run"])

    assert result.exit_code == 0
    mock_run_query.assert_not_called()
    mock_run_interactive.assert_called_once()


def test_entry_routes_plain_invocation_to_hidden_run(monkeypatch):
    called = {}

    def fake_app(*, args, prog_name):
        called["args"] = args
        called["prog_name"] = prog_name

    monkeypatch.setattr("ct.cli.app", fake_app)
    monkeypatch.setattr("sys.argv", ["ag", "profile", "FLC"])

    from ct.cli import entry

    entry()

    assert called["prog_name"] == "ag"
    assert called["args"] == ["run", "profile", "FLC"]


def test_entry_preserves_explicit_subcommand(monkeypatch):
    called = {}

    def fake_app(*, args, prog_name):
        called["args"] = args
        called["prog_name"] = prog_name

    monkeypatch.setattr("ct.cli.app", fake_app)
    monkeypatch.setattr("sys.argv", ["ag", "config", "show"])

    from ct.cli import entry

    entry()

    assert called["prog_name"] == "ag"
    assert called["args"] == ["config", "show"]


def test_entry_preserves_trace_subcommand(monkeypatch):
    called = {}

    def fake_app(*, args, prog_name):
        called["args"] = args
        called["prog_name"] = prog_name

    monkeypatch.setattr("ct.cli.app", fake_app)
    monkeypatch.setattr("sys.argv", ["ag", "trace", "diagnose"])

    from ct.cli import entry

    entry()

    assert called["prog_name"] == "ag"
    assert called["args"] == ["trace", "diagnose"]


def test_entry_preserves_species_subcommand(monkeypatch):
    called = {}

    def fake_app(*, args, prog_name):
        called["args"] = args
        called["prog_name"] = prog_name

    monkeypatch.setattr("ct.cli.app", fake_app)
    monkeypatch.setattr("sys.argv", ["ag", "species", "list"])

    from ct.cli import entry

    entry()

    assert called["prog_name"] == "ag"
    assert called["args"] == ["species", "list"]


def test_config_set_agent_profile_applies_preset():
    cfg = Config(data={})
    with patch("ct.agent.config.Config.load", return_value=cfg), patch.object(
        cfg, "save"
    ) as mock_save:
        result = runner.invoke(app, ["config", "set", "agent.profile", "enterprise"])

    assert result.exit_code == 0
    assert "applied preset settings" in result.stdout
    assert cfg.get("agent.profile") == "enterprise"
    assert cfg.get("agent.quality_gate_strict") is True
    mock_save.assert_called_once()


def test_config_set_agent_profile_rejects_invalid_value():
    cfg = Config(data={})
    with patch("ct.agent.config.Config.load", return_value=cfg), patch.object(
        cfg, "save"
    ) as mock_save:
        result = runner.invoke(app, ["config", "set", "agent.profile", "invalid"])

    assert result.exit_code == 2
    assert "Invalid agent.profile" in result.stdout
    mock_save.assert_not_called()


def test_knowledge_status_command():
    fake_summary = {
        "path": "/tmp/substrate.json",
        "schema_version": 1,
        "n_entities": 3,
        "n_relations": 2,
        "n_evidence": 5,
        "entity_types": {"gene": 2, "disease": 1},
    }
    with patch("ct.kb.substrate.KnowledgeSubstrate") as mock_cls:
        mock_cls.return_value.summary.return_value = fake_summary
        result = runner.invoke(app, ["knowledge", "status"])
    assert result.exit_code == 0
    assert "Knowledge Substrate" in result.stdout
    assert "Entities" in result.stdout


def test_knowledge_ingest_error_exits_nonzero():
    with patch("ct.kb.ingest.KnowledgeIngestionPipeline") as mock_pipeline:
        mock_pipeline.return_value.ingest.return_value = {"error": "boom"}
        result = runner.invoke(app, ["knowledge", "ingest", "evidence_store"])
    assert result.exit_code == 2
    assert "boom" in result.stdout


def test_knowledge_benchmark_strict_failure_exits_nonzero():
    class FakeSuite:
        def run(self):
            return {
                "total_cases": 2,
                "expected_behavior_matches": 1,
                "pass_rate": 0.5,
            }

        def gate(self, summary, min_pass_rate=0.9):
            return {
                "ok": False,
                "message": "failed",
            }

    with patch("ct.kb.benchmarks.BenchmarkSuite.load", return_value=FakeSuite()):
        result = runner.invoke(app, ["knowledge", "benchmark", "--strict"])
    assert result.exit_code == 2


def test_release_check_passes_with_no_tests_no_trace():
    cfg = Config(data={"llm.api_key": "x"})

    class FakeSuite:
        def run(self):
            return {
                "total_cases": 2,
                "expected_behavior_matches": 2,
                "pass_rate": 1.0,
            }

        def gate(self, summary, min_pass_rate=0.9):
            del summary, min_pass_rate
            return {
                "ok": True,
                "message": "passed",
            }

    with patch("ct.agent.config.Config.load", return_value=cfg), patch(
        "ct.agent.doctor.run_checks", return_value=[]
    ), patch("ct.agent.doctor.has_errors", return_value=False), patch(
        "ct.agent.doctor.to_table", return_value="doctor ok"
    ), patch("ct.kb.benchmarks.BenchmarkSuite.load", return_value=FakeSuite()):
        result = runner.invoke(app, ["release-check", "--no-tests", "--no-trace"])

    assert result.exit_code == 0
    assert "Release check passed" in result.stdout


def test_release_check_fails_when_pytest_step_fails():
    cfg = Config(data={"llm.api_key": "x"})

    class FakeSuite:
        def run(self):
            return {
                "total_cases": 2,
                "expected_behavior_matches": 2,
                "pass_rate": 1.0,
            }

        def gate(self, summary, min_pass_rate=0.9):
            del summary, min_pass_rate
            return {
                "ok": True,
                "message": "passed",
            }

    fail_proc = subprocess.CompletedProcess(args=["pytest"], returncode=1, stdout="boom", stderr="")
    with patch("ct.agent.config.Config.load", return_value=cfg), patch(
        "ct.agent.doctor.run_checks", return_value=[]
    ), patch("ct.agent.doctor.has_errors", return_value=False), patch(
        "ct.agent.doctor.to_table", return_value="doctor ok"
    ), patch("ct.kb.benchmarks.BenchmarkSuite.load", return_value=FakeSuite()), patch(
        "ct.cli.subprocess.run", return_value=fail_proc
    ):
        result = runner.invoke(app, ["release-check", "--no-trace"])

    assert result.exit_code == 2
    assert "Release check failed" in result.stdout


def test_release_check_pharma_policy_fails_without_profile():
    cfg = Config(data={"llm.api_key": "x", "agent.profile": "research"})
    with patch("ct.agent.config.Config.load", return_value=cfg), patch(
        "ct.agent.doctor.run_checks", return_value=[]
    ), patch("ct.agent.doctor.has_errors", return_value=False), patch(
        "ct.agent.doctor.to_table", return_value="doctor ok"
    ):
        result = runner.invoke(
            app,
            ["release-check", "--no-tests", "--no-benchmark", "--no-trace", "--pharma"],
        )

    assert result.exit_code == 2
    assert "Profile mismatch" in result.stdout


def test_release_check_pharma_policy_passes():
    cfg = Config(
        data={
            "llm.api_key": "x",
            "agent.profile": "pharma",
            "agent.synthesis_style": "pharma",
            "agent.quality_gate_strict": True,
            "agent.enable_experimental_tools": False,
            "agent.enable_claude_code_tool": False,
        }
    )
    with patch("ct.agent.config.Config.load", return_value=cfg), patch(
        "ct.agent.doctor.run_checks", return_value=[]
    ), patch("ct.agent.doctor.has_errors", return_value=False), patch(
        "ct.agent.doctor.to_table", return_value="doctor ok"
    ):
        result = runner.invoke(
            app,
            ["release-check", "--no-tests", "--no-benchmark", "--no-trace", "--pharma"],
        )

    assert result.exit_code == 0
    assert "Release check passed" in result.stdout


# ─── Session subcommand tests ────────────────────────────────


def test_session_list_no_sessions(tmp_path):
    with patch("ct.agent.trajectory.Trajectory.sessions_dir", return_value=tmp_path):
        result = runner.invoke(app, ["session", "list"])
    assert result.exit_code == 0
    assert "No sessions found" in result.stdout


def test_session_list_shows_sessions(tmp_path):
    sid = "abc-123"
    sess_dir = tmp_path / sid
    sess_dir.mkdir()
    (sess_dir / "session_info.json").write_text(json.dumps({
        "session_id": sid,
        "name": "my session",
        "created_at": "2025-01-01T00:00:00",
        "status": "completed",
    }))
    with patch("ct.agent.trajectory.Trajectory.sessions_dir", return_value=tmp_path):
        result = runner.invoke(app, ["session", "list"])
    assert result.exit_code == 0
    assert "abc-123" in result.stdout
    assert "my session" in result.stdout


def test_session_clear_requires_arg_or_all():
    result = runner.invoke(app, ["session", "clear"])
    assert result.exit_code == 2
    assert "Provide a session ID/name or use --all" in result.stdout


def test_session_clear_rejects_both_arg_and_all():
    result = runner.invoke(app, ["session", "clear", "foo", "--all"])
    assert result.exit_code == 2
    assert "Cannot combine" in result.stdout


def test_session_clear_all(tmp_path):
    for name in ["sess-1", "sess-2"]:
        d = tmp_path / name
        d.mkdir()
        (d / "session_info.json").write_text(json.dumps({"session_id": name}))
    (tmp_path / "legacy.jsonl").write_text('{"type":"meta","session_id":"leg"}\n')
    with patch("ct.agent.trajectory.Trajectory.sessions_dir", return_value=tmp_path):
        result = runner.invoke(app, ["session", "clear", "--all"])
    assert result.exit_code == 0
    assert "Cleared 3 session(s)" in result.stdout
    assert not any(tmp_path.iterdir())


def test_session_clear_by_exact_id(tmp_path):
    sid = "abc-123"
    sess_dir = tmp_path / sid
    sess_dir.mkdir()
    (sess_dir / "session_info.json").write_text(json.dumps({
        "session_id": sid,
        "name": "test",
        "created_at": "2025-01-01T00:00:00",
        "status": "active",
        "path": str(sess_dir),
    }))
    with patch("ct.agent.trajectory.Trajectory.sessions_dir", return_value=tmp_path):
        result = runner.invoke(app, ["session", "clear", sid])
    assert result.exit_code == 0
    assert "Cleared session abc-123" in result.stdout
    assert not sess_dir.exists()


def test_session_clear_by_prefix(tmp_path):
    sid = "abc-123-456"
    sess_dir = tmp_path / sid
    sess_dir.mkdir()
    (sess_dir / "session_info.json").write_text(json.dumps({
        "session_id": sid,
        "name": "test",
        "created_at": "2025-01-01T00:00:00",
        "status": "active",
    }))
    with patch("ct.agent.trajectory.Trajectory.sessions_dir", return_value=tmp_path):
        result = runner.invoke(app, ["session", "clear", "abc"])
    assert result.exit_code == 0
    assert "Cleared session abc-123-456" in result.stdout
    assert not sess_dir.exists()


def test_session_clear_ambiguous_prefix(tmp_path):
    for sid in ["abc-1", "abc-2"]:
        d = tmp_path / sid
        d.mkdir()
        (d / "session_info.json").write_text(json.dumps({
            "session_id": sid,
            "name": None,
            "created_at": "2025-01-01T00:00:00",
            "status": "active",
        }))
    with patch("ct.agent.trajectory.Trajectory.sessions_dir", return_value=tmp_path):
        result = runner.invoke(app, ["session", "clear", "abc"])
    assert result.exit_code == 2
    assert "Ambiguous prefix" in result.stdout


def test_session_clear_by_name(tmp_path):
    sid = "abc-123"
    sess_dir = tmp_path / sid
    sess_dir.mkdir()
    (sess_dir / "session_info.json").write_text(json.dumps({
        "session_id": sid,
        "name": "my-session",
        "created_at": "2025-01-01T00:00:00",
        "status": "active",
    }))
    with patch("ct.agent.trajectory.Trajectory.sessions_dir", return_value=tmp_path):
        result = runner.invoke(app, ["session", "clear", "my-session"])
    assert result.exit_code == 0
    assert "Cleared session abc-123" in result.stdout


def test_session_clear_not_found(tmp_path):
    with patch("ct.agent.trajectory.Trajectory.sessions_dir", return_value=tmp_path):
        result = runner.invoke(app, ["session", "clear", "nonexistent"])
    assert result.exit_code == 2
    assert "No session found" in result.stdout


def test_entry_preserves_session_subcommand(monkeypatch):
    called = {}

    def fake_app(*, args, prog_name):
        called["args"] = args
        called["prog_name"] = prog_name

    monkeypatch.setattr("ct.cli.app", fake_app)
    monkeypatch.setattr("sys.argv", ["ag", "session", "list"])

    from ct.cli import entry

    entry()

    assert called["prog_name"] == "ag"
    assert called["args"] == ["session", "list"]
