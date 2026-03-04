"""
SessionInfo: manifest for a session directory.

Each session gets a ``session_info.json`` inside its directory that stores
the session name, directory configuration, status, and timestamps.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SessionInfo:
    """Manifest for a session stored as ``session_info.json``."""

    session_id: str
    name: str | None = None
    created_at: str = ""  # ISO 8601
    working_dir: str = ""  # defaults to session dir
    output_dir: str = ""  # defaults to working_dir
    read_dirs: list[str] = field(default_factory=list)
    temp: bool = False
    status: str = "active"  # "active" | "completed"

    # -- derived paths ---------------------------------------------------------

    @property
    def session_dir(self) -> Path:
        """The session directory (parent of the manifest)."""
        return self._sessions_root() / self.session_id

    @property
    def manifest_path(self) -> Path:
        return self.session_dir / "session_info.json"

    @property
    def trajectory_path(self) -> Path:
        return self.session_dir / "trajectory.jsonl"

    @property
    def trace_path(self) -> Path:
        return self.session_dir / "trace.jsonl"

    # -- factory / persistence -------------------------------------------------

    @classmethod
    def create(
        cls,
        session_id: str,
        *,
        name: str | None = None,
        output_dir: str | None = None,
        working_dir: str | None = None,
        read_dirs: list[str] | None = None,
        temp: bool = False,
    ) -> "SessionInfo":
        """Create a new SessionInfo, write it to disk, and return it."""
        sessions_root = cls._sessions_root()
        session_dir = sessions_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        effective_working = (
            str(Path(working_dir).expanduser().resolve()) if working_dir
            else str(session_dir)
        )
        effective_output = (
            str(Path(output_dir).expanduser().resolve()) if output_dir
            else effective_working
        )
        resolved_read = [
            str(Path(d).expanduser().resolve()) for d in (read_dirs or [])
        ]

        info = cls(
            session_id=session_id,
            name=name,
            created_at=datetime.now(timezone.utc).isoformat(),
            working_dir=effective_working,
            output_dir=effective_output,
            read_dirs=resolved_read,
            temp=temp,
        )
        info._save()
        return info

    @classmethod
    def load(cls, session_dir: Path) -> "SessionInfo":
        """Load a SessionInfo from a session directory."""
        manifest = session_dir / "session_info.json"
        if not manifest.exists():
            raise FileNotFoundError(f"No session_info.json in {session_dir}")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return cls(
            session_id=data["session_id"],
            name=data.get("name"),
            created_at=data.get("created_at", ""),
            working_dir=data.get("working_dir", ""),
            output_dir=data.get("output_dir", ""),
            read_dirs=data.get("read_dirs", []),
            temp=data.get("temp", False),
            status=data.get("status", "active"),
        )

    # -- mutators --------------------------------------------------------------

    def set_name(self, name: str) -> None:
        self.name = name
        self._save()

    def set_status(self, status: str) -> None:
        self.status = status
        self._save()

    # -- internals -------------------------------------------------------------

    def _save(self) -> None:
        """Persist manifest to ``session_info.json``."""
        self.session_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "session_id": self.session_id,
            "name": self.name,
            "created_at": self.created_at,
            "working_dir": self.working_dir,
            "output_dir": self.output_dir,
            "read_dirs": self.read_dirs,
            "temp": self.temp,
            "status": self.status,
        }
        self.manifest_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )

    @staticmethod
    def _sessions_root() -> Path:
        d = Path.home() / ".ct" / "sessions"
        d.mkdir(parents=True, exist_ok=True)
        return d
