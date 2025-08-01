"""
Configuration settings for the MCP AI Agent
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class ModelConfig:
    """Configuration for AI models"""

    vision_model: str = "llava:13b"
    reasoning_model: str = "phi3:medium"
    fallback_model: str = "mistral:7b"  # Using available model instead of codellama:7b
    ollama_host: str = "http://localhost:11434"
    max_retries: int = 3
    timeout: int = 60  # Increased timeout for complex prompt refactoring
    health_check_interval: float = 30.0  # Seconds between model health checks
    model_warmup_time: float = 5.0  # Seconds to wait for model initialization
    gpu_memory_limit: float = 5.5  # GPU memory limit in GB for all models
    fallback_to_cpu: bool = True  # Fall back to CPU if GPU unavailable


@dataclass
class PerceiverConfig:
    """Configuration for the Perceiver component"""

    screenshot_interval: float = 1.0
    ocr_language: str = "eng"
    ocr_config: str = "--psm 6"
    max_screenshot_size: tuple = (1920, 1080)
    enable_ui_parsing: bool = True
    enable_vlm_description: bool = True
    retry_on_failure: bool = True
    max_ocr_retries: int = 3
    min_ocr_confidence: float = 0.6
    image_cache_size: int = 10


@dataclass
class ControllerConfig:
    """Configuration for the Controller component"""

    action_delay: float = 0.3
    failsafe_delay: float = 2.0
    max_click_attempts: int = 3
    safe_mode: bool = True
    confirm_sensitive_actions: bool = True
    error_retry_delay: float = 1.0
    recovery_actions: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "click_failed": ["wait", "retry", "move_slightly"],
            "type_failed": ["clear_input", "retry"],
            "ui_not_found": ["scroll", "wait", "retry"],
        }
    )


@dataclass
class MonitoringConfig:
    """Configuration for system monitoring"""

    enabled: bool = True
    check_interval: float = 5.0
    metrics_file: str = "./data/metrics.jsonl"
    error_file: str = "./data/errors.log"
    performance_tracking: bool = True
    alert_on_errors: bool = True
    max_consecutive_failures: int = 3
    memory_threshold: float = 0.9  # Alert if memory usage > 90%
    gpu_temp_threshold: float = 80  # Celsius


@dataclass
class SystemConfig:
    """Main system configuration"""

    models: ModelConfig
    perceiver: PerceiverConfig
    controller: ControllerConfig
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    log_level: str = "INFO"
    log_file: str = "mcp_agent.log"
    data_dir: str = "./data"
    screenshots_dir: str = "./data/screenshots"
    history_file: str = "./data/action_history.json"

    def __post_init__(self):
        """Create necessary directories"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def validate(self):
        """Validate configuration settings"""
        if not os.path.isdir(self.data_dir):
            raise ValueError(f"Data directory {self.data_dir} does not exist")
        if self.models.gpu_memory_limit > 6.0:  # GTX 1660 Ti has 6GB
            raise ValueError("GPU memory limit exceeds hardware capacity")


def create_default_config():
    """Create default configuration instance"""
    return SystemConfig(
        models=ModelConfig(),
        perceiver=PerceiverConfig(),
        controller=ControllerConfig(),
        monitoring=MonitoringConfig(),
    )


# Default configuration instance
CONFIG = create_default_config()

# Platform-specific configurations
PLATFORM_CONFIGS = {
    "windows": {
        "tesseract_cmd": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        "screenshot_backend": "mss",
        "automation_backend": "pyautogui",
    },
    "linux": {
        "tesseract_cmd": "tesseract",
        "screenshot_backend": "mss",
        "automation_backend": "pyautogui",
    },
}

# Action types and their safety levels
ACTION_SAFETY_LEVELS = {
    "click": 0,
    "type": 1,
    "key_press": 1,
    "scroll": 0,
    "drag": 1,
    "file_operation": 3,  # Requires confirmation
    "system_command": 3,  # Requires confirmation
    "password_entry": 3,  # Requires confirmation
}

# Sensitive keywords that trigger safety checks
SENSITIVE_KEYWORDS = [
    "password",
    "credit card",
    "delete",
    "format",
    "sudo",
    "admin",
    "system32",
    "registry",
    "rm -rf",
    "del /f",
    "format c:",
]
