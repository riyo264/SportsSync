from collections import deque
from typing import Dict, Any, List

class StateManager:
    def __init__(self):
        # Maps session_id -> {"current_state": dict, "event_logs": deque}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def _ensure_session(self, session_id: str, sport: str):
        """Creates the memory block for a game if it doesn't exist."""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "current_state": {"sport": sport},
                "event_logs": deque(maxlen=50)
            }

    def update_state(self, session_id: str, sport: str, key: str, value: Any):
        self._ensure_session(session_id, sport)
        self.active_sessions[session_id]["current_state"][key] = value

    def add_log(self, session_id: str, sport: str, log_message: str):
        self._ensure_session(session_id, sport)
        self.active_sessions[session_id]["event_logs"].append(log_message)

    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Returns context for a specific game, or empty defaults if not found."""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"current_state": {}, "recent_logs": []}
        return {
            "current_state": session["current_state"],
            "recent_logs": list(session["event_logs"])
        }

state_manager = StateManager()