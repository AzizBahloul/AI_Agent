#!/usr/bin/env python3
"""
Task Tracking System - Tracks progress of multi-step commands and saves state
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from utils.logger import logger


class TaskTracker:
    """Tracks and persists progress of multi-step command execution"""

    def __init__(self, data_dir: str = None):
        """Initialize the task tracker"""
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self.task_log_dir = os.path.join(self.data_dir, "task_logs")
        self.current_session_id = None
        self.current_command = None
        self.current_steps = []
        self.completed_steps = []
        self.failed_steps = []
        self.step_times = {}
        self.start_time = None
        self.end_time = None

        # Ensure directories exist
        os.makedirs(self.task_log_dir, exist_ok=True)
    
    def start_new_task(self, command: str, steps: List[str]) -> str:
        """Start tracking a new task with the given steps"""
        # Generate session ID based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_id = f"task_{timestamp}"
        self.current_command = command
        self.current_steps = steps
        self.completed_steps = []
        self.failed_steps = []
        self.step_times = {}
        self.start_time = time.time()
        
        # Save initial state
        self._save_state()
        
        logger.info(f"📋 Started tracking task: {self.current_session_id} with {len(steps)} steps")
        return self.current_session_id
    
    def mark_step_complete(self, step_idx: int, step_text: str, success: bool = True) -> None:
        """Mark a step as completed or failed"""
        if not self.current_session_id:
            logger.warning("⚠️ Cannot mark step - no active task session")
            return
        
        # Record step completion time
        self.step_times[step_idx] = time.time()
        
        if success:
            self.completed_steps.append((step_idx, step_text))
            logger.info(f"✅ Marked step {step_idx+1} as complete: {step_text}")
        else:
            self.failed_steps.append((step_idx, step_text))
            logger.info(f"❌ Marked step {step_idx+1} as failed: {step_text}")
        
        # Save updated state
        self._save_state()
    
    def complete_task(self, success: bool = True) -> Dict[str, Any]:
        """Mark the entire task as complete and return summary"""
        if not self.current_session_id:
            logger.warning("⚠️ Cannot complete task - no active task session")
            return {}
        
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # Calculate statistics
        total_steps = len(self.current_steps)
        completed_steps = len(self.completed_steps)
        failed_steps = len(self.failed_steps)
        completion_rate = completed_steps / total_steps if total_steps > 0 else 0
        
        summary = {
            "session_id": self.current_session_id,
            "command": self.current_command,
            "success": success,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "completion_rate": completion_rate,
            "duration_seconds": duration,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
        }
        
        # Save final state with summary
        self._save_state(summary)
        
        # Log completion
        if success:
            logger.info(f"✅ Task completed successfully: {completion_rate:.1%} of steps done in {duration:.1f}s")
        else:
            logger.info(f"⚠️ Task ended with partial completion: {completion_rate:.1%} in {duration:.1f}s")
        
        # Reset current state
        self._reset()
        
        return summary
    
    def get_progress_report(self) -> Dict[str, Any]:
        """Get current progress report"""
        if not self.current_session_id:
            return {"status": "no_active_task"}
        
        total_steps = len(self.current_steps)
        completed_steps = len(self.completed_steps)
        failed_steps = len(self.failed_steps)
        remaining_steps = total_steps - completed_steps - failed_steps
        
        return {
            "session_id": self.current_session_id,
            "command": self.current_command,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "remaining_steps": remaining_steps,
            "completion_rate": completed_steps / total_steps if total_steps > 0 else 0,
            "elapsed_time": time.time() - self.start_time,
        }
    
    def get_formatted_progress(self) -> str:
        """Get a formatted string showing progress"""
        report = self.get_progress_report()
        
        if report.get("status") == "no_active_task":
            return "No active task"
        
        progress_bar_length = 30
        percent = report["completion_rate"]
        filled_length = int(progress_bar_length * percent)
        progress_bar = "■" * filled_length + "□" * (progress_bar_length - filled_length)
        
        return (
            f"Progress: [{progress_bar}] {report['completed_steps']}/{report['total_steps']} "
            f"({percent:.1%}) • {report['elapsed_time']:.1f}s elapsed"
        )
    
    def _save_state(self, summary: Optional[Dict[str, Any]] = None) -> None:
        """Save current state to disk"""
        if not self.current_session_id:
            return
            
        try:
            # Prepare data to save
            data = {
                "session_id": self.current_session_id,
                "command": self.current_command,
                "timestamp": datetime.now().isoformat(),
                "total_steps": len(self.current_steps),
                "steps": self.current_steps,
                "completed_steps": self.completed_steps,
                "failed_steps": self.failed_steps,
                "elapsed_time": time.time() - self.start_time,
            }
            
            # Add summary info if provided
            if summary:
                data["summary"] = summary
            
            # Save to JSON file
            file_path = os.path.join(self.task_log_dir, f"{self.current_session_id}.json")
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            logger.error(f"❌ Failed to save task state: {e}")
    
    def _reset(self) -> None:
        """Reset tracking state"""
        self.current_session_id = None
        self.current_command = None
        self.current_steps = []
        self.completed_steps = []
        self.failed_steps = []
        self.step_times = {}
        self.start_time = None
        self.end_time = None


# Global instance
task_tracker = TaskTracker()
