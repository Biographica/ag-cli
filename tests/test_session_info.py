"""Tests for SessionInfo: session manifest persistence."""

import json
import pytest
from pathlib import Path
from ct.agent.session_info import SessionInfo


class TestSessionInfo:
    def test_create_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(SessionInfo, "_sessions_root", staticmethod(lambda: tmp_path))

        info = SessionInfo.create("abc12345", name="my-analysis")
        assert info.session_id == "abc12345"
        assert info.name == "my-analysis"
        assert info.status == "active"
        assert info.created_at  # non-empty ISO string

        # Manifest file was written
        manifest = tmp_path / "abc12345" / "session_info.json"
        assert manifest.exists()

        # Round-trip via load
        loaded = SessionInfo.load(tmp_path / "abc12345")
        assert loaded.session_id == "abc12345"
        assert loaded.name == "my-analysis"
        assert loaded.created_at == info.created_at
        assert loaded.status == "active"

    def test_set_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr(SessionInfo, "_sessions_root", staticmethod(lambda: tmp_path))

        info = SessionInfo.create("sid001")
        assert info.name is None

        info.set_name("flowering-time")
        assert info.name == "flowering-time"

        # Persisted to disk
        loaded = SessionInfo.load(tmp_path / "sid001")
        assert loaded.name == "flowering-time"

    def test_custom_output_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(SessionInfo, "_sessions_root", staticmethod(lambda: tmp_path))

        info = SessionInfo.create(
            "sid002",
            output_dir="/tmp/my-results",
            working_dir="/tmp/my-work",
            read_dirs=["/data/genomes"],
        )
        # Paths are resolved to absolute (macOS: /tmp → /private/tmp)
        assert info.output_dir == str(Path("/tmp/my-results").resolve())
        assert info.working_dir == str(Path("/tmp/my-work").resolve())
        assert info.read_dirs == [str(Path("/data/genomes").resolve())]

        loaded = SessionInfo.load(tmp_path / "sid002")
        assert loaded.output_dir == info.output_dir
        assert loaded.working_dir == info.working_dir
        assert loaded.read_dirs == info.read_dirs

    def test_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(SessionInfo, "_sessions_root", staticmethod(lambda: tmp_path))

        info = SessionInfo.create("sid003")
        session_dir = str(tmp_path / "sid003")

        # working_dir defaults to session dir
        assert info.working_dir == session_dir
        # output_dir defaults to working_dir
        assert info.output_dir == session_dir

    def test_set_status(self, tmp_path, monkeypatch):
        monkeypatch.setattr(SessionInfo, "_sessions_root", staticmethod(lambda: tmp_path))

        info = SessionInfo.create("sid004")
        assert info.status == "active"

        info.set_status("completed")

        loaded = SessionInfo.load(tmp_path / "sid004")
        assert loaded.status == "completed"

    def test_temp_flag(self, tmp_path, monkeypatch):
        monkeypatch.setattr(SessionInfo, "_sessions_root", staticmethod(lambda: tmp_path))

        info = SessionInfo.create("sid005", temp=True)
        assert info.temp is True

        loaded = SessionInfo.load(tmp_path / "sid005")
        assert loaded.temp is True

    def test_path_properties(self, tmp_path, monkeypatch):
        monkeypatch.setattr(SessionInfo, "_sessions_root", staticmethod(lambda: tmp_path))

        info = SessionInfo.create("sid006")
        assert info.session_dir == tmp_path / "sid006"
        assert info.manifest_path == tmp_path / "sid006" / "session_info.json"
        assert info.trajectory_path == tmp_path / "sid006" / "trajectory.jsonl"
        assert info.trace_path == tmp_path / "sid006" / "trace.jsonl"

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            SessionInfo.load(tmp_path / "nonexistent")
