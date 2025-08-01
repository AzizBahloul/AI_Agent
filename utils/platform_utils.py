"""
Platform-specific utilities for cross-platform compatibility
"""

import os
import sys
import platform
import subprocess
from typing import Dict, Any, Tuple

from config import PLATFORM_CONFIGS
from utils.logger import logger


class PlatformManager:
    """Manages platform-specific operations"""

    def __init__(self):
        self.platform = platform.system().lower()
        self.config = PLATFORM_CONFIGS.get(self.platform, {})
        self.display_scaling = self._detect_display_scaling()
        logger.info(f"Platform detected: {self.platform}")

    def get_screenshot_backend(self) -> str:
        """Get the preferred screenshot backend for this platform"""
        return self.config.get("screenshot_backend", "pyautogui")

    def get_automation_backend(self) -> str:
        """Get the preferred automation backend for this platform"""
        return self.config.get("automation_backend", "pyautogui")

    def get_tesseract_cmd(self) -> str:
        """Get the Tesseract command path for this platform"""
        tesseract_cmd = self.config.get("tesseract_cmd", "tesseract")

        # Verify Tesseract is available
        try:
            result = subprocess.run(
                [tesseract_cmd, "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Tesseract found: {tesseract_cmd}")
                return tesseract_cmd
        except Exception as e:
            logger.warning(f"Tesseract not found at {tesseract_cmd}: {e}")

        # Try common fallback locations
        fallback_paths = self._get_tesseract_fallbacks()
        for path in fallback_paths:
            try:
                result = subprocess.run(
                    [path, "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Tesseract found at fallback: {path}")
                    return path
            except Exception:
                continue

        logger.error("Tesseract not found. Please install Tesseract OCR.")
        return tesseract_cmd  # Return original, let OCR fail gracefully

    def _get_tesseract_fallbacks(self) -> list:
        """Get platform-specific fallback paths for Tesseract"""
        if self.platform == "windows":
            return [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                "tesseract.exe",
            ]
        elif self.platform == "linux":
            return [
                "/usr/bin/tesseract",
                "/usr/local/bin/tesseract",
                "/opt/tesseract/bin/tesseract",
            ]
        return ["tesseract"]

    def get_display_scaling(self) -> float:
        """Get display scaling factor"""
        return self.display_scaling

    def get_screen_info(self) -> Dict[str, Any]:
        """Get screen information including scaling"""
        return {"scaling": self.display_scaling, "platform": self.platform}

    def is_windows(self) -> bool:
        """Check if running on Windows"""
        return self.platform == "windows"

    def is_linux(self) -> bool:
        """Check if running on Linux"""
        return self.platform == "linux"

    def _detect_display_scaling(self) -> float:
        """Detect display scaling factor for high-DPI screens"""
        try:
            if self.platform == "windows":
                # Get actual screen resolution
                import tkinter

                root = tkinter.Tk()
                root.withdraw()
                dpi = root.winfo_fpixels("1i")
                root.destroy()
                scaling = dpi / 96.0  # Windows standard DPI
                return scaling
            elif self.platform == "linux":
                # Try to get scaling from environment or X11
                scale_env = os.environ.get("GDK_SCALE", "1")
                try:
                    return float(scale_env)
                except Exception:
                    return 1.0
        except Exception as e:
            logger.warning(f"Could not detect display scaling: {e}")
        return 1.0

    def adjust_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Adjust coordinates for display scaling"""
        scale = self.display_scaling
        return int(x * scale), int(y * scale)

    def get_temp_dir(self) -> str:
        """Get platform-appropriate temporary directory"""
        if self.platform == "windows":
            return os.environ.get("TEMP", r"C:\Temp")
        else:
            return "/tmp"

    def is_admin(self) -> bool:
        """Check if running with administrator/root privileges"""
        try:
            if self.platform == "windows":
                import ctypes

                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        import psutil

        try:
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "platform": self.platform,
                "platform_version": platform.platform(),
                "python_version": sys.version,
                "cpu_count": cpu_count,
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "display_scaling": self.display_scaling,
                "is_admin": self.is_admin(),
            }
        except ImportError:
            logger.warning("psutil not available, limited system info")
            return {
                "platform": self.platform,
                "platform_version": platform.platform(),
                "python_version": sys.version,
            }


# Global platform manager instance
platform_manager = PlatformManager()
