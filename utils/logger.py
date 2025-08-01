"""
Comprehensive logging system for the MCP AI Agent
"""

import sys
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from logging.handlers import RotatingFileHandler

# Avoid circular imports by importing config inside functions when needed


@dataclass
class ModelCall:
    """Record of a model API call"""

    timestamp: datetime
    model: str
    prompt_length: int
    response_length: int
    success: bool
    duration_ms: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ActionRecord:
    """Record of an executed action"""

    timestamp: datetime
    action_type: str
    target: Optional[str]
    coordinates: Optional[tuple]
    success: bool
    error: Optional[str] = None


@dataclass
class PerceptionRecord:
    """Record of a perception cycle"""

    timestamp: datetime
    screenshot_path: str
    ocr_words: int
    ui_elements: int
    vlm_description_length: int
    confidence: float
    processing_time_ms: float


class MCPLogger:
    """Enhanced logger for MCP agent with structured logging"""

    def __init__(self, config=None):
        self.config = config
        self.setup_logging()
        self.model_calls: List[ModelCall] = []
        self.actions: List[ActionRecord] = []
        self.perceptions: List[PerceptionRecord] = []
        self.session_start = datetime.now()

    def setup_logging(self):
        """Initialize logging configuration"""
        # Import CONFIG here to avoid circular imports
        from config import CONFIG

        # Create logs directory
        log_dir = Path(CONFIG.data_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Main logger
        self.logger = logging.getLogger("mcp_agent")
        self.logger.setLevel(getattr(logging, CONFIG.log_level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)8s | %(name)s | %(message)s", datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler (rotating)
        log_file = log_dir / CONFIG.log_file
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Structured log files
        self.model_log_file = log_dir / "model_calls.jsonl"
        self.action_log_file = log_dir / "actions.jsonl"
        self.perception_log_file = log_dir / "perceptions.jsonl"
        self.error_log_file = log_dir / "errors.jsonl"

        self.info("MCP Logger initialized")

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, exception: Exception = None, **kwargs):
        """Log error message with optional exception"""
        if exception:
            self.logger.error(f"{message}: {exception}", extra=kwargs)
            self._log_error(message, exception)
        else:
            self.logger.error(message, extra=kwargs)

    def critical(self, message: str, exception: Exception = None, **kwargs):
        """Log critical message"""
        if exception:
            self.logger.critical(f"{message}: {exception}", extra=kwargs)
            self._log_error(message, exception, level="CRITICAL")
        else:
            self.logger.critical(message, extra=kwargs)

    def log_model_call(
        self,
        model: str,
        prompt: str,
        response: str,
        success: bool = True,
        duration_ms: float = None,
        error: str = None,
    ):
        """Log a model API call"""
        call = ModelCall(
            timestamp=datetime.now(),
            model=model,
            prompt_length=len(prompt),
            response_length=len(response),
            success=success,
            duration_ms=duration_ms,
            error=error,
        )
        self.model_calls.append(call)
        self._write_jsonl(self.model_log_file, asdict(call))

        # Log to main logger too
        if success:
            self.debug(
                f"Model call: {model} | Prompt: {len(prompt)} chars | "
                f"Response: {len(response)} chars"
            )
        else:
            self.warning(f"Model call failed: {model} | Error: {error}")

    def log_action(
        self,
        action_type: str,
        target: str = None,
        coordinates: tuple = None,
        success: bool = True,
        error: str = None,
    ):
        """Log an executed action"""
        action = ActionRecord(
            timestamp=datetime.now(),
            action_type=action_type,
            target=target,
            coordinates=coordinates,
            success=success,
            error=error,
        )
        self.actions.append(action)
        self._write_jsonl(self.action_log_file, asdict(action))

        # Log to main logger
        action_desc = f"{action_type}"
        if target:
            action_desc += f" on '{target}'"
        if coordinates:
            action_desc += f" at {coordinates}"

        if success:
            self.info(f"Action executed: {action_desc}")
        else:
            self.warning(f"Action failed: {action_desc} | Error: {error}")

    def log_perception(self, data: Dict[str, Any]):
        """Log a perception cycle"""
        perception = PerceptionRecord(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            screenshot_path=data.get("screenshot_path", ""),
            ocr_words=data.get("ocr_words", 0),
            ui_elements=data.get("ui_elements", 0),
            vlm_description_length=data.get("vlm_length", 0),
            confidence=data.get("confidence", 0.0),
            processing_time_ms=data.get("processing_time_ms", 0.0),
        )
        self.perceptions.append(perception)
        self._write_jsonl(self.perception_log_file, asdict(perception))

        self.debug(
            f"Perception: {perception.ocr_words} words, "
            f"{perception.ui_elements} elements, "
            f"confidence: {perception.confidence:.2f}"
        )

    def _log_error(self, message: str, exception: Exception, level: str = "ERROR"):
        """Log detailed error information"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc(),
        }
        self._write_jsonl(self.error_log_file, error_data)

    def _write_jsonl(self, file_path: Path, data: Dict[str, Any]):
        """Write data to JSONL file"""
        try:
            # Convert datetime objects to ISO strings
            data_copy = self._serialize_datetime(data)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data_copy) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write to {file_path}: {e}")

    def _serialize_datetime(self, obj):
        """Recursively serialize datetime objects to ISO strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        return obj

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for the current session"""
        now = datetime.now()
        session_duration = (now - self.session_start).total_seconds()

        return {
            "session_start": self.session_start.isoformat(),
            "session_duration_seconds": session_duration,
            "total_model_calls": len(self.model_calls),
            "successful_model_calls": sum(
                1 for call in self.model_calls if call.success
            ),
            "total_actions": len(self.actions),
            "successful_actions": sum(1 for action in self.actions if action.success),
            "total_perceptions": len(self.perceptions),
            "average_perception_confidence": (
                sum(p.confidence for p in self.perceptions) / len(self.perceptions)
                if self.perceptions
                else 0.0
            ),
        }

    def export_session_log(self) -> str:
        """Export complete session log as JSON"""
        session_data = {
            "session_info": self.get_session_stats(),
            "model_calls": [asdict(call) for call in self.model_calls],
            "actions": [asdict(action) for action in self.actions],
            "perceptions": [asdict(perception) for perception in self.perceptions],
        }

        # Serialize datetime objects
        session_data = self._serialize_datetime(session_data)

        # Save to file
        from config import CONFIG

        export_file = (
            Path(CONFIG.data_dir)
            / "logs"
            / f"session_{self.session_start.strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)

        self.info(f"Session log exported to {export_file}")
        return str(export_file)


# Global logger instance
logger = MCPLogger()
