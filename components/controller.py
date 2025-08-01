"""
Controller component - handles action execution via GUI automation
"""

import time
import pyautogui
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from pynput import keyboard
import psutil
import subprocess

from config import CONFIG, ACTION_SAFETY_LEVELS, SENSITIVE_KEYWORDS
from utils.logger import logger
from utils.platform_utils import platform_manager


@dataclass
class ActionResult:
    """Result of an action execution"""

    success: bool
    action_type: str
    details: Dict[str, Any]
    timestamp: datetime
    error: Optional[str] = None
    confirmation_required: bool = False


class ActionValidator:
    """Validates actions for safety and feasibility"""

    def __init__(self):
        self.sensitive_keywords = SENSITIVE_KEYWORDS
        self.safety_levels = ACTION_SAFETY_LEVELS

    def validate_action(
        self, action: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], bool]:
        """
        Validate an action for safety and feasibility
        Returns: (is_valid, error_message, requires_confirmation)
        """
        action_type = action.get("type", "").lower()

        # Check if action type is supported
        if action_type not in self.safety_levels:
            return False, f"Unsupported action type: {action_type}", False

        # Check safety level
        safety_level = self.safety_levels[action_type]
        requires_confirmation = safety_level >= 3 or not CONFIG.controller.safe_mode

        # Check for sensitive content
        action_text = str(action).lower()
        for keyword in self.sensitive_keywords:
            if keyword in action_text:
                requires_confirmation = True
                logger.warning(f"Sensitive keyword detected: {keyword}")
                break

        # Validate action parameters
        if action_type == "click":
            if "x" not in action or "y" not in action:
                return False, "Click action missing coordinates", False
        elif action_type == "type":
            if "text" not in action:
                return False, "Type action missing text", False
        elif action_type == "key_press":
            if "key" not in action:
                return False, "Key press action missing key", False

        return True, None, requires_confirmation


class ScreenInteraction:
    """Handles low-level screen interactions"""

    def __init__(self):
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = CONFIG.controller.action_delay

        # Get screen info
        self.screen_info = platform_manager.get_screen_info()
        self.scaling_factor = self.screen_info.get("scaling", 1.0)

        logger.info(f"Screen interaction initialized. Scaling: {self.scaling_factor}")

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> bool:
        """Click at specified coordinates"""
        try:
            # Adjust for scaling
            adj_x = int(x * self.scaling_factor)
            adj_y = int(y * self.scaling_factor)

            # Validate coordinates are on screen
            if not self._validate_coordinates(adj_x, adj_y):
                logger.error(f"Coordinates out of bounds: ({adj_x}, {adj_y})")
                return False

            # Perform click
            logger.debug(f"Clicking at ({adj_x}, {adj_y}) with {button} button")
            pyautogui.click(adj_x, adj_y, clicks=clicks, button=button)

            time.sleep(CONFIG.controller.action_delay)
            return True

        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False

    def type_text(self, text: str, interval: float = 0.1) -> bool:
        """Type text with specified interval; on Linux use xdotool for reliability"""
        try:
            logger.debug(f"Typing text: {text[:50]}{'...' if len(text) > 50 else ''}")
            # Ensure focus
            time.sleep(0.2)
            # If Linux and xdotool is available, use it for reliable input
            if platform_manager.is_linux():
                try:
                    subprocess.run(["xdotool", "type", "--delay", str(int(interval*1000)), text], check=True)
                    time.sleep(CONFIG.controller.action_delay)
                    return True
                except Exception as e:
                    logger.warning(f"xdotool type failed: {e}, falling back to pyautogui.write")
            # Fallback: pyautogui write
            pyautogui.write(text, interval=interval)
            time.sleep(CONFIG.controller.action_delay)
            return True
        except Exception as e:
            logger.error(f"Type text failed: {e}")
            return False

    def press_key(self, key: str, presses: int = 1) -> bool:
        """Press a key or key combination"""
        try:
            logger.debug(f"Pressing key: {key} ({presses} times)")

            # Handle key combinations (e.g., "ctrl+c")
            if "+" in key:
                keys = key.split("+")
                pyautogui.hotkey(*keys)
            else:
                for _ in range(presses):
                    pyautogui.press(key)

            time.sleep(CONFIG.controller.action_delay)
            return True
        except Exception as e:
            logger.error(f"Key press failed: {e}")
            return False

    def scroll(self, direction: str, amount: int = 3) -> bool:
        """Scroll in specified direction"""
        try:
            scroll_amount = amount if direction.lower() == "up" else -amount
            logger.debug(f"Scrolling {direction} by {amount}")
            pyautogui.scroll(scroll_amount)
            time.sleep(CONFIG.controller.action_delay)
            return True
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False

    def drag(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 1.0
    ) -> bool:
        """Drag from start coordinates to end coordinates"""
        try:
            # Adjust for scaling
            start_x = int(start_x * self.scaling_factor)
            start_y = int(start_y * self.scaling_factor)
            end_x = int(end_x * self.scaling_factor)
            end_y = int(end_y * self.scaling_factor)

            logger.debug(f"Dragging from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
            time.sleep(CONFIG.controller.action_delay)
            return True
        except Exception as e:
            logger.error(f"Drag failed: {e}")
            return False

    def _validate_coordinates(self, x: int, y: int) -> bool:
        """Validate that coordinates are within screen bounds"""
        screen_width, screen_height = pyautogui.size()
        return 0 <= x <= screen_width and 0 <= y <= screen_height

    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return pyautogui.position()

    def move_mouse(self, x: int, y: int, duration: float = 0.5) -> bool:
        """Move mouse to specified position"""
        try:
            adj_x = int(x * self.scaling_factor)
            adj_y = int(y * self.scaling_factor)

            if self._validate_coordinates(adj_x, adj_y):
                pyautogui.moveTo(adj_x, adj_y, duration=duration)
                return True
            return False
        except Exception as e:
            logger.error(f"Mouse move failed: {e}")
            return False


class UserConfirmation:
    """Handles user confirmation for sensitive actions"""

    def __init__(self):
        self.confirmation_timeout = 30  # seconds
        self.pending_confirmations = {}

    def request_confirmation(
        self, action: Dict[str, Any], reason: str = "Sensitive action"
    ) -> bool:
        """Request user confirmation for an action"""
        if not CONFIG.controller.confirm_sensitive_actions:
            return True

        try:
            import importlib.util

            if importlib.util.find_spec("tkinter") is None:
                logger.warning("tkinter not available, defaulting to allow action")
                return True

            from tkinter import messagebox

            # Create confirmation dialog
            message = f"{reason}\n\nAction: {action}\n\nDo you want to proceed?"

            # Use messagebox for confirmation
            result = messagebox.askyesno("Action Confirmation", message)

            logger.info(f"User confirmation for action: {result}")
            return result

        except ImportError:
            # Fallback to console confirmation
            logger.warning("GUI not available, using console confirmation")
            print(f"\n{reason}")
            print(f"Action: {action}")
            response = input("Proceed? (y/N): ").strip().lower()
            return response in ["y", "yes"]
        except Exception as e:
            logger.error(f"Confirmation failed: {e}")
            return False


class ApplicationManager:
    """Manages application launching and window handling"""

    def __init__(self):
        self.running_apps = {}

    def launch_application(self, app_name: str, app_path: str = None) -> bool:
        """Launch an application"""
        try:
            import subprocess

            if app_path:
                # Launch specific executable
                process = subprocess.Popen([app_path])
            else:
                # Try to launch by name (platform-specific)
                if platform_manager.is_windows():
                    process = subprocess.Popen(["start", app_name], shell=True)
                elif platform_manager.is_linux():
                    process = subprocess.Popen([app_name])
                else:
                    return False

            self.running_apps[app_name] = process.pid
            logger.info(f"Launched application: {app_name} (PID: {process.pid})")
            time.sleep(2)  # Wait for app to start
            return True

        except Exception as e:
            logger.error(f"Failed to launch {app_name}: {e}")
            return False

    def close_application(self, app_name: str) -> bool:
        """Close an application"""
        try:
            if app_name in self.running_apps:
                pid = self.running_apps[app_name]
                process = psutil.Process(pid)
                process.terminate()
                del self.running_apps[app_name]
                logger.info(f"Closed application: {app_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to close {app_name}: {e}")
        return False

    def get_active_window(self) -> Optional[str]:
        """Get the title of the active window"""
        try:
            if platform_manager.is_windows():
                pass
            elif platform_manager.is_linux():
                # Linux implementation would require additional libraries
                pass
        except Exception as e:
            logger.error(f"Failed to get active window: {e}")
        return None


class Controller:
    """Main Controller component that orchestrates action execution"""

    def __init__(self):
        self.validator = ActionValidator()
        self.interaction = ScreenInteraction()
        self.confirmation = UserConfirmation()
        self.app_manager = ApplicationManager()
        self.action_history = []
        self.emergency_stop = False
        self.running = False

        # Setup emergency stop
        self._setup_emergency_stop()

        logger.info("Controller component initialized")

    def start(self):
        """Start the controller component"""
        self.running = True
        logger.info("Controller started")

    def stop(self):
        """Stop the controller component"""
        self.running = False
        logger.info("Controller stopped")

    def _setup_emergency_stop(self):
        """Setup emergency stop mechanism"""

        def on_emergency_key():
            self.emergency_stop = True
            logger.warning("Emergency stop activated!")

        # Set up Ctrl+Shift+Q as emergency stop
        try:

            def on_key_combination(key):
                if hasattr(key, "char") and key.char == "q":
                    # Check if Ctrl+Shift are held
                    if (
                        keyboard.Key.ctrl in self._pressed_keys
                        and keyboard.Key.shift in self._pressed_keys
                    ):
                        on_emergency_key()

            self._pressed_keys = set()

            def on_press(key):
                self._pressed_keys.add(key)
                on_key_combination(key)

            def on_release(key):
                self._pressed_keys.discard(key)

            # Start keyboard listener in background
            listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            listener.daemon = True
            listener.start()

        except Exception as e:
            logger.warning(f"Could not setup emergency stop: {e}")

    def execute_action(self, action: Dict[str, Any]) -> ActionResult:
        """Execute a single action with validation and confirmation"""
        timestamp = datetime.now()

        # Check for emergency stop
        if self.emergency_stop:
            return ActionResult(
                success=False,
                action_type=action.get("type", "unknown"),
                details=action,
                timestamp=timestamp,
                error="Emergency stop activated",
            )

        # Validate action
        is_valid, error_msg, needs_confirmation = self.validator.validate_action(action)
        if not is_valid:
            return ActionResult(
                success=False,
                action_type=action.get("type", "unknown"),
                details=action,
                timestamp=timestamp,
                error=error_msg,
            )

        # Request confirmation if needed
        if needs_confirmation:
            if not self.confirmation.request_confirmation(
                action, "Sensitive action detected"
            ):
                return ActionResult(
                    success=False,
                    action_type=action.get("type", "unknown"),
                    details=action,
                    timestamp=timestamp,
                    error="User denied confirmation",
                    confirmation_required=True,
                )

        # Execute action
        result = self._execute_action_internal(action, timestamp)

        # Log action
        self.action_history.append(result)
        logger.log_action(result.action_type, result.details)

        return result

    def _execute_action_internal(
        self, action: Dict[str, Any], timestamp: datetime
    ) -> ActionResult:
        """Internal action execution logic"""
        action_type = action.get("type", "").lower()

        try:
            success = False

            if action_type == "click":
                success = self.interaction.click(
                    action["x"],
                    action["y"],
                    action.get("button", "left"),
                    action.get("clicks", 1),
                )

            elif action_type == "type":
                success = self.interaction.type_text(
                    action["text"], action.get("interval", 0.01)
                )

            elif action_type == "key_press":
                success = self.interaction.press_key(
                    action["key"], action.get("presses", 1)
                )

            elif action_type == "scroll":
                success = self.interaction.scroll(
                    action.get("direction", "down"), action.get("amount", 3)
                )

            elif action_type == "drag":
                success = self.interaction.drag(
                    action["start_x"],
                    action["start_y"],
                    action["end_x"],
                    action["end_y"],
                    action.get("duration", 1.0),
                )

            elif action_type == "move_mouse":
                success = self.interaction.move_mouse(
                    action["x"], action["y"], action.get("duration", 0.5)
                )

            elif action_type == "launch_app":
                success = self.app_manager.launch_application(
                    action["app_name"], action.get("app_path")
                )

            elif action_type == "close_app":
                success = self.app_manager.close_application(action["app_name"])

            elif action_type == "wait":
                time.sleep(action.get("duration", 1.0))
                success = True

            else:
                return ActionResult(
                    success=False,
                    action_type=action_type,
                    details=action,
                    timestamp=timestamp,
                    error=f"Unknown action type: {action_type}",
                )

            return ActionResult(
                success=success,
                action_type=action_type,
                details=action,
                timestamp=timestamp,
                error=None if success else "Action execution failed",
            )

        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return ActionResult(
                success=False,
                action_type=action_type,
                details=action,
                timestamp=timestamp,
                error=str(e),
            )

    def execute_action_sequence(
        self, actions: List[Dict[str, Any]]
    ) -> List[ActionResult]:
        """Execute a sequence of actions"""
        results = []

        for i, action in enumerate(actions):
            if self.emergency_stop:
                logger.warning("Emergency stop during action sequence")
                break

            logger.info(
                f"Executing action {i + 1}/{len(actions)}: {action.get('type')}"
            )
            result = self.execute_action(action)
            results.append(result)

            # Stop on failure if specified
            if not result.success and action.get("stop_on_failure", False):
                logger.error(f"Action sequence stopped at step {i + 1} due to failure")
                break

        return results

    def get_screen_element_coordinates(
        self, element: Dict[str, Any]
    ) -> Tuple[int, int]:
        """Get click coordinates for a UI element"""
        bbox = element.get("bbox", {})
        x = bbox.get("x", 0) + bbox.get("width", 0) // 2
        y = bbox.get("y", 0) + bbox.get("height", 0) // 2
        return x, y

    def click_element(self, element: Dict[str, Any]) -> ActionResult:
        """Click on a UI element"""
        x, y = self.get_screen_element_coordinates(element)
        action = {
            "type": "click",
            "x": x,
            "y": y,
            "target_element": element.get("text", "unknown"),
        }
        return self.execute_action(action)

    def reset_emergency_stop(self):
        """Reset the emergency stop flag"""
        self.emergency_stop = False
        logger.info("Emergency stop reset")

    def get_action_history(self) -> List[ActionResult]:
        """Get the history of executed actions"""
        return self.action_history.copy()

    def clear_action_history(self):
        """Clear the action history"""
        self.action_history.clear()
        logger.info("Action history cleared")
