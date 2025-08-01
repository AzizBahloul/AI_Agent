"""
Session management for AI Brain
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("desktop-genie")

class Session:
    def __init__(self, session_id: str, command: str):
        self.session_id = session_id
        self.command = command
        self.context = {}
        self.steps = []
        self.errors = []
        logger.info(f"Session {session_id} started with command: {command}")

    def add_context(self, key: str, value: Any):
        self.context[key] = value
        logger.debug(f"Context updated for session {self.session_id}: {key} = {value}")

    def add_step(self, step: Dict, result: Dict):
        self.steps.append({"step": step, "result": result})
        logger.debug(f"Step added to session {self.session_id}: {step}")

    def add_error(self, step: Dict, error: str):
        self.errors.append({"step": step, "error": error})
        logger.error(f"Error in session {self.session_id}: {error}")

    def complete(self):
        logger.info(f"Session {self.session_id} completed")

class SessionManager:
    def __init__(self):
        self.sessions = {}
        logger.info("Session manager initialized")

    def start_session(self, session_id: str, command: str) -> Session:
        session = Session(session_id, command)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session:
        return self.sessions.get(session_id)

    def end_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session {session_id} ended")
