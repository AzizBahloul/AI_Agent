#!/usr/bin/env python3
"""
Advanced Features Module for MCP AI Agent
Includes multi-modal capabilities, task planning, and safety systems
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import queue
import hashlib

from config import CONFIG
from utils.logger import logger
from models.ollama_client import ollama_client


@dataclass
class Task:
    """Represents a high-level task to be completed"""

    id: str
    description: str
    priority: int  # 1-10, 10 being highest
    steps: List[Dict[str, Any]]
    status: str  # pending, in_progress, completed, failed
    created_at: datetime
    deadline: Optional[datetime] = None
    dependencies: List[str] = None
    progress: float = 0.0


class TaskPlanner:
    """Plans and manages complex multi-step tasks"""

    def __init__(self):
        self.tasks = {}
        self.task_queue = queue.PriorityQueue()
        self.current_task = None

    def create_task_from_prompt(self, user_prompt: str) -> Task:
        """Create a structured task from user prompt using AI"""
        planning_prompt = f"""
Break down this user request into a structured task with specific steps:
User Request: "{user_prompt}"

Respond in JSON format:
{{
    "description": "Clear task description",
    "priority": 5,
    "steps": [
        {{"action": "specific_action", "target": "what_to_interact_with", "description": "what this step does"}},
        ...
    ],
    "estimated_time": "in minutes"
}}

Make steps concrete and actionable for a desktop automation agent.
"""

        try:
            response = ollama_client.generate_text(
                model=CONFIG.models.reasoning_model,
                prompt=planning_prompt,
                temperature=0.3,
                max_tokens=500,
            )

            if response.success:
                task_data = json.loads(response.content)
                task_id = hashlib.md5(user_prompt.encode()).hexdigest()[:8]

                task = Task(
                    id=task_id,
                    description=task_data["description"],
                    priority=task_data.get("priority", 5),
                    steps=task_data["steps"],
                    status="pending",
                    created_at=datetime.now(),
                )

                self.tasks[task_id] = task
                self.task_queue.put(
                    (-task.priority, task_id)
                )  # Negative for max-heap behavior

                logger.info(
                    f"Created task: {task.description} with {len(task.steps)} steps"
                )
                return task

        except Exception as e:
            logger.error(f"Task planning failed: {e}")

        # Fallback simple task
        return self._create_simple_task(user_prompt)

    def _create_simple_task(self, user_prompt: str) -> Task:
        """Create a simple single-step task as fallback"""
        task_id = hashlib.md5(user_prompt.encode()).hexdigest()[:8]

        task = Task(
            id=task_id,
            description=user_prompt,
            priority=5,
            steps=[
                {
                    "action": "interpret",
                    "target": "user_request",
                    "description": user_prompt,
                }
            ],
            status="pending",
            created_at=datetime.now(),
        )

        self.tasks[task_id] = task
        self.task_queue.put((-task.priority, task_id))
        return task

    def get_next_task(self) -> Optional[Task]:
        """Get the next highest priority task"""
        if not self.task_queue.empty():
            _, task_id = self.task_queue.get()
            task = self.tasks.get(task_id)
            if task and task.status == "pending":
                task.status = "in_progress"
                self.current_task = task
                return task
        return None

    def update_task_progress(
        self, task_id: str, progress: float, step_completed: bool = False
    ):
        """Update task progress"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.progress = min(100.0, progress)

            if step_completed:
                logger.info(
                    f"Task {task_id}: Step completed ({task.progress:.1f}% done)"
                )

            if task.progress >= 100.0:
                task.status = "completed"
                logger.info(f"✅ Task completed: {task.description}")


class SafetyMonitor:
    """Monitors agent actions for safety and prevents harmful operations"""

    def __init__(self):
        self.blocked_actions = set()
        self.warning_keywords = [
            "delete",
            "remove",
            "format",
            "rm",
            "del",
            "sudo",
            "admin",
            "password",
            "credit card",
        ]
        self.safe_zones = ["desktop", "documents", "downloads", "pictures"]

    def validate_action(
        self, action: Dict[str, Any], context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate if an action is safe to execute"""
        action_type = action.get("type", "")
        target = action.get("target", "").lower()

        # Check for dangerous keywords
        for keyword in self.warning_keywords:
            if keyword in target:
                return False, f"Blocked: Contains dangerous keyword '{keyword}'"

        # Check action type safety
        if action_type == "system_command":
            command = action.get("command", "").lower()
            if any(
                dangerous in command for dangerous in ["rm -rf", "format", "del /f"]
            ):
                return False, "Blocked: Dangerous system command"

        # File operations safety
        if action_type == "file_operation":
            operation = action.get("operation", "").lower()
            if operation in ["delete", "format"] and not self._is_safe_location(
                action.get("path", "")
            ):
                return False, "Blocked: Unsafe file operation in system area"

        # Rate limiting for rapid actions
        if self._is_rapid_action(action):
            return False, "Blocked: Too many rapid actions detected"

        return True, "Action approved"

    def _is_safe_location(self, path: str) -> bool:
        """Check if file path is in a safe location"""
        path_lower = path.lower()
        return any(safe_zone in path_lower for safe_zone in self.safe_zones)

    def _is_rapid_action(self, action: Dict[str, Any]) -> bool:
        """Check for suspiciously rapid actions"""
        # Simple implementation - could be enhanced
        return False


class MultiModalProcessor:
    """Processes multiple types of input (vision, text, audio) for richer context"""

    def __init__(self):
        self.vision_model = CONFIG.models.vision_model
        self.text_model = CONFIG.models.reasoning_model

    def analyze_screen_comprehensively(
        self, screenshot_path: str, ocr_text: str
    ) -> Dict[str, Any]:
        """Perform comprehensive multi-modal analysis of screen"""

        # Vision analysis
        vision_analysis = self._analyze_with_vision_model(screenshot_path)

        # Text understanding
        text_analysis = self._analyze_text_content(ocr_text)

        # Combine insights
        combined_analysis = self._combine_multimodal_insights(
            vision_analysis, text_analysis, ocr_text
        )

        return combined_analysis

    def _analyze_with_vision_model(self, screenshot_path: str) -> Dict[str, Any]:
        """Use vision-language model for detailed image analysis"""
        prompt = """
Analyze this desktop screenshot in detail. Describe:
1. What type of application/interface is shown
2. Main UI elements and their purpose
3. Current state/context of the interface
4. Potential next actions a user might want to take
5. Any error messages or notifications visible

Be specific and actionable in your analysis.
"""

        try:
            response = ollama_client.analyze_image(
                model=self.vision_model, image_path=screenshot_path, prompt=prompt
            )

            if response.success:
                return {
                    "vision_description": response.content,
                    "confidence": 0.8,
                    "model_used": self.vision_model,
                }
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")

        return {"vision_description": "Vision analysis unavailable", "confidence": 0.1}

    def _analyze_text_content(self, ocr_text: str) -> Dict[str, Any]:
        """Analyze OCR text for semantic understanding"""
        if not ocr_text.strip():
            return {
                "text_insights": "No text content",
                "entities": [],
                "intent": "unknown",
            }

        analysis_prompt = f"""
Analyze this text extracted from a desktop screen:
"{ocr_text}"

Identify:
1. Type of interface (browser, file manager, application, etc.)
2. Key entities (filenames, URLs, buttons, etc.)
3. Possible user intent or workflow
4. Important information or context

Respond in JSON format:
{{
    "interface_type": "type",
    "entities": ["entity1", "entity2"],
    "intent": "likely user intent",
    "key_info": "important context"
}}
"""

        try:
            response = ollama_client.generate_text(
                model=self.text_model,
                prompt=analysis_prompt,
                temperature=0.3,
                max_tokens=300,
            )

            if response.success:
                return json.loads(response.content)
        except Exception as e:
            logger.error(f"Text analysis failed: {e}")

        return {
            "text_insights": "Text analysis failed",
            "entities": [],
            "intent": "unknown",
        }

    def _combine_multimodal_insights(
        self, vision: Dict, text: Dict, raw_ocr: str
    ) -> Dict[str, Any]:
        """Combine vision and text analysis for comprehensive understanding"""

        return {
            "comprehensive_description": f"{vision.get('vision_description', '')}",
            "interface_type": text.get("interface_type", "unknown"),
            "detected_entities": text.get("entities", []),
            "user_intent": text.get("intent", "unknown"),
            "confidence_score": (vision.get("confidence", 0) + 0.7)
            / 2,  # Average confidence
            "raw_ocr_length": len(raw_ocr),
            "analysis_timestamp": datetime.now().isoformat(),
            "multimodal": True,
        }


class ContextAwareAgent:
    """Agent that maintains context awareness across sessions"""

    def __init__(self):
        self.session_context = {}
        self.long_term_context = self._load_long_term_context()
        self.context_window = []  # Recent interactions
        self.max_context_size = 20

    def update_context(self, interaction: Dict[str, Any]):
        """Update context with new interaction"""
        self.context_window.append(
            {"timestamp": datetime.now().isoformat(), "interaction": interaction}
        )

        # Maintain context window size
        if len(self.context_window) > self.max_context_size:
            self.context_window.pop(0)

        # Update session patterns
        self._update_session_patterns(interaction)

    def get_relevant_context(self, current_situation: Dict[str, Any]) -> Dict[str, Any]:
        """Get context relevant to current situation"""

        # Find similar past situations
        similar_contexts = self._find_similar_contexts(current_situation)

        # Get recent interaction patterns
        recent_patterns = self._extract_recent_patterns()

        return {
            "similar_past_situations": similar_contexts,
            "recent_patterns": recent_patterns,
            "session_summary": self._get_session_summary(),
            "long_term_insights": self._get_relevant_long_term_insights(
                current_situation
            ),
        }

    def _load_long_term_context(self) -> Dict[str, Any]:
        """Load long-term context from storage"""
        context_file = Path(CONFIG.data_dir) / "long_term_context.json"

        if context_file.exists():
            try:
                with open(context_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load long-term context: {e}")

        return {"user_patterns": {}, "successful_workflows": [], "preferences": {}}

    def save_long_term_context(self):
        """Save long-term context to storage"""
        context_file = Path(CONFIG.data_dir) / "long_term_context.json"

        try:
            with open(context_file, "w") as f:
                json.dump(self.long_term_context, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save long-term context: {e}")

    def _find_similar_contexts(self, current: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar past contexts"""
        # Simple similarity based on UI elements and text
        current_elements = set(
            elem.get("text", "") for elem in current.get("ui_elements", [])
        )

        similar = []
        for context_entry in self.context_window[-5:]:  # Last 5 interactions
            past_elements = set(
                elem.get("text", "")
                for elem in context_entry.get("interaction", {})
                .get("context", {})
                .get("ui_elements", [])
            )

            overlap = len(current_elements & past_elements)
            if overlap > 0:
                similar.append(
                    {
                        "context": context_entry,
                        "similarity": overlap
                        / max(len(current_elements), len(past_elements)),
                    }
                )

        return sorted(similar, key=lambda x: x["similarity"], reverse=True)[:3]

    def _extract_recent_patterns(self) -> Dict[str, Any]:
        """Extract patterns from recent interactions"""
        if len(self.context_window) < 3:
            return {"patterns": "Insufficient data"}

        # Analyze action sequences
        recent_actions = [
            entry["interaction"].get("action", {}).get("type")
            for entry in self.context_window[-5:]
        ]

        return {
            "recent_action_sequence": recent_actions,
            "most_common_action": max(set(recent_actions), key=recent_actions.count)
            if recent_actions
            else None,
            "interaction_count": len(self.context_window),
        }

    def _get_session_summary(self) -> str:
        """Get a summary of the current session"""
        if not self.context_window:
            return "No interactions yet"

        action_types = [
            entry["interaction"].get("action", {}).get("type")
            for entry in self.context_window
        ]
        unique_actions = set(action_types)

        return f"Session: {len(self.context_window)} interactions, {len(unique_actions)} action types"

    def _get_relevant_long_term_insights(
        self, current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get relevant long-term insights for current situation"""
        # Simple implementation - could be much more sophisticated
        return {
            "total_sessions": self.long_term_context.get("session_count", 0),
            "user_preferences": self.long_term_context.get("preferences", {}),
            "successful_patterns": len(
                self.long_term_context.get("successful_workflows", [])
            ),
        }

    def _update_session_patterns(self, interaction: Dict[str, Any]):
        """Update session-level patterns"""
        action = interaction.get("action", {})
        result = interaction.get("result", {})

        if result.get("success"):
            # Track successful action patterns
            pattern_key = f"{action.get('type')}_{action.get('target', 'unknown')}"
            if pattern_key not in self.session_context:
                self.session_context[pattern_key] = 0
            self.session_context[pattern_key] += 1


def create_enhanced_system():
    """Factory function to create enhanced system components"""
    return {
        "task_planner": TaskPlanner(),
        "safety_monitor": SafetyMonitor(),
        "multimodal_processor": MultiModalProcessor(),
        "context_agent": ContextAwareAgent(),
    }


# Example usage and integration helper
class AdvancedAgentWrapper:
    """Wrapper that integrates all advanced features"""

    def __init__(self, base_agent):
        self.base_agent = base_agent
        self.enhanced_components = create_enhanced_system()
        self.task_planner = self.enhanced_components["task_planner"]
        self.safety_monitor = self.enhanced_components["safety_monitor"]
        self.multimodal = self.enhanced_components["multimodal_processor"]
        self.context_agent = self.enhanced_components["context_agent"]

    def process_user_request(self, user_prompt: str) -> Dict[str, Any]:
        """Process user request with advanced planning and safety"""

        # Create structured task
        task = self.task_planner.create_task_from_prompt(user_prompt)

        # Safety validation
        is_safe, safety_message = self.safety_monitor.validate_action(
            {"type": "user_request", "content": user_prompt}, {}
        )

        if not is_safe:
            return {"status": "blocked", "reason": safety_message, "task": None}

        return {
            "status": "approved",
            "task": task,
            "safety_check": "passed",
            "plan_steps": len(task.steps),
        }

    def enhanced_perception(
        self, screenshot_path: str, ocr_text: str
    ) -> Dict[str, Any]:
        """Enhanced perception with multimodal analysis"""

        # Multi-modal analysis
        comprehensive_analysis = self.multimodal.analyze_screen_comprehensively(
            screenshot_path, ocr_text
        )

        # Context awareness
        relevant_context = self.context_agent.get_relevant_context(
            comprehensive_analysis
        )

        # Combine insights
        enhanced_context = {
            **comprehensive_analysis,
            "context_insights": relevant_context,
            "enhanced": True,
            "processing_timestamp": datetime.now().isoformat(),
        }

        # Update context for future reference
        self.context_agent.update_context(
            {"type": "perception", "context": enhanced_context}
        )

        return enhanced_context


if __name__ == "__main__":
    # Quick test of advanced features
    logger.info("🧪 Testing Advanced Features")

    # Test task planning
    planner = TaskPlanner()
    task = planner.create_task_from_prompt(
        "Open a text editor and write a shopping list"
    )
    print(f"Created task: {task.description} with {len(task.steps)} steps")

    # Test safety monitoring
    safety = SafetyMonitor()
    safe, msg = safety.validate_action({"type": "click", "target": "save button"}, {})
    print(f"Safety check: {safe} - {msg}")

    logger.info("✅ Advanced features test completed")
