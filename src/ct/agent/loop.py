"""
AgentLoop: wraps AgentRunner with trajectory persistence and clarification.

Provides the ``AgentLoop`` class used by the interactive terminal for
multi-turn sessions with memory, and ``ClarificationNeeded`` for requesting
additional input from the user.
"""

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ct.agent.runner import AgentRunner
from ct.agent.session_info import SessionInfo
from ct.agent.trace_store import TraceStore
from ct.agent.trajectory import Trajectory

logger = logging.getLogger("ct.loop")


@dataclass
class Clarification:
    """A request for user clarification before executing a query."""
    question: str
    missing: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class ClarificationNeeded(Exception):
    """Raised when the planner needs additional information."""

    def __init__(self, clarification: Clarification):
        self.clarification = clarification
        super().__init__(clarification.question)


class AgentLoop:
    """Multi-turn agent loop with trajectory memory.

    Wraps ``AgentRunner`` (SDK-based) and maintains a ``Trajectory``
    for multi-turn session context.
    """

    def __init__(
        self,
        session,
        *,
        name: str | None = None,
        output_dir: str | None = None,
        working_dir: str | None = None,
        read_dirs: list[str] | None = None,
        temp: bool = False,
    ):
        self.session = session
        self.trajectory = Trajectory()
        self._session_id = str(uuid.uuid4())[:8]

        # Create SessionInfo manifest
        self.session_info = SessionInfo.create(
            self._session_id,
            name=name,
            output_dir=output_dir,
            working_dir=working_dir,
            read_dirs=read_dirs,
            temp=temp,
        )

        # Output directory from SessionInfo
        self._output_dir = Path(self.session_info.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        session.config.set("sandbox.output_dir", str(self._output_dir))

        # Set extra read dirs on sandbox config
        if read_dirs:
            session.config.set("sandbox.extra_read_dirs", read_dirs)

        self.trace_store = TraceStore(
            session_id=self._session_id,
            trace_dir=self.session_info.session_dir,
        )
        self._runner = AgentRunner(
            session, trajectory=self.trajectory, trace_store=self.trace_store,
        )

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def run(self, query: str, context: dict | None = None):
        """Execute a query and record it in the trajectory."""
        result = self._runner.run(query, context)

        # Check for clarification request in result
        if result and result.raw_results:
            clar_data = result.raw_results.get("clarification")
            if isinstance(clar_data, dict) and clar_data.get("clarification_needed"):
                raise ClarificationNeeded(Clarification(
                    question=clar_data.get("question", "Could you clarify?"),
                    missing=clar_data.get("missing", []),
                    suggestions=clar_data.get("suggestions", []),
                ))

        # Record turn in trajectory and persist
        if result:
            tools_used = []
            if result.plan:
                tools_used = [s.tool for s in result.plan.steps if s.tool]
            self.trajectory.add_turn(
                query=query,
                answer=result.summary or "",
                plan=result.plan,
            )
            self.trajectory.save(self.session_info.trajectory_path)

        # Auto-generate notebook from trace
        self._auto_generate_notebook()

        return result

    def _auto_generate_notebook(self) -> None:
        """Generate session.ipynb from the trace file, if nbformat is available."""
        try:
            from ct.reports.notebook import trace_to_notebook, save_notebook
        except ImportError:
            return  # nbformat not installed

        trace_path = self.trace_store.path
        if not trace_path.exists():
            return

        try:
            nb = trace_to_notebook(trace_path)
            notebook_path = self._output_dir / "session.ipynb"
            save_notebook(nb, notebook_path)
        except Exception as e:
            logger.debug("Auto-notebook generation failed: %s", e)

    @classmethod
    def resume(cls, session, session_id: str):
        """Resume a saved session by ID or name."""
        # Try name-based resolution first
        resolved_id = cls._resolve_session_id(session_id)

        sessions_dir = Trajectory.sessions_dir()
        session_dir = sessions_dir / resolved_id

        # Load SessionInfo (with legacy fallback)
        session_info = None
        if (session_dir / "session_info.json").exists():
            session_info = SessionInfo.load(session_dir)

        # Load trajectory — new layout first, then legacy, then empty
        traj_path = session_dir / "trajectory.jsonl"
        if not traj_path.exists():
            # Legacy flat file
            traj_path = sessions_dir / f"{resolved_id}.jsonl"

        if traj_path.exists():
            trajectory = Trajectory.load(traj_path)
        elif session_info is not None:
            # Session exists (has manifest) but no queries yet — start fresh
            trajectory = Trajectory(session_id=resolved_id)
        else:
            raise FileNotFoundError(f"Session '{session_id}' not found.")

        loop = cls.__new__(cls)
        loop.session = session
        loop.trajectory = trajectory
        loop._session_id = resolved_id

        # Restore or create SessionInfo
        if session_info:
            loop.session_info = session_info
        else:
            loop.session_info = SessionInfo.create(resolved_id)

        # Output directory
        loop._output_dir = Path(loop.session_info.output_dir)
        loop._output_dir.mkdir(parents=True, exist_ok=True)
        session.config.set("sandbox.output_dir", str(loop._output_dir))

        # Trace store with session dir
        loop.trace_store = TraceStore(
            session_id=resolved_id,
            trace_dir=loop.session_info.session_dir,
        )
        loop._runner = AgentRunner(
            session, trajectory=trajectory, trace_store=loop.trace_store,
        )
        return loop

    @classmethod
    def resume_latest(cls, session):
        """Resume the most recent saved session."""
        sessions = Trajectory.list_sessions()
        if not sessions:
            raise FileNotFoundError("No saved sessions found.")
        latest = sessions[0]
        return cls.resume(session, latest["session_id"])

    @staticmethod
    def _resolve_session_id(identifier: str) -> str:
        """Resolve a session name to its ID, or return as-is if already an ID."""
        sessions_dir = Trajectory.sessions_dir()
        for sub in sessions_dir.iterdir():
            if sub.is_dir():
                manifest = sub / "session_info.json"
                if manifest.exists():
                    try:
                        import json
                        data = json.loads(manifest.read_text(encoding="utf-8"))
                        if data.get("name") == identifier:
                            return data.get("session_id", sub.name)
                    except (Exception,):
                        continue
        return identifier
