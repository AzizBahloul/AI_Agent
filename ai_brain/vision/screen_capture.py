"""
Screen capture and monitoring with change detection
"""
import os
import mss
import mss.tools
import cv2
import numpy as np
from PIL import Image
from typing import Optional
import logging

logger = logging.getLogger("desktop-genie")

class ScreenCapture:
    def __init__(self, monitor: int = 1):
        self.sct = mss.mss()
        self.monitors = self.sct.monitors
        self.monitor = self.monitors[monitor]
        self.last_screenshot = None
        self.last_hash = None
        logger.info("Screen capture initialized")

    def capture_screen(self, filename: str = "screenshot.png") -> str:
        """Capture full screen and save to file"""
        try:
            sct_img = self.sct.grab(self.monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            # Create directory if needed
            os.makedirs("screenshots", exist_ok=True)
            path = f"screenshots/{filename}"
            img.save(path)
            
            # Store for change detection
            self.last_screenshot = np.array(img)
            self.last_hash = self._image_hash(self.last_screenshot)
            
            return path
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return ""

    def capture_window(self, window_title: str, filename: str = "window.png") -> Optional[str]:
        """Capture specific window by title"""
        # Implementation varies by OS
        # Placeholder for platform-specific implementation
        return self.capture_screen(filename)

    def detect_changes(self, threshold: float = 0.1) -> bool:
        """Detect significant screen changes"""
        if self.last_screenshot is None:
            return False
            
        current = self.capture_screen("temp.png")
        current_img = cv2.imread(current)
        current_hash = self._image_hash(current_img)
        
        # Compare hashes
        return self._hash_distance(self.last_hash, current_hash) > threshold

    def _image_hash(self, image: np.ndarray) -> str:
        """Generate perceptual hash for image"""
        # Resize and convert to grayscale
        img = cv2.resize(image, (8, 8), interpolation=cv2.INTER_AREA)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Compute average value
        avg = img.mean()
        
        # Generate hash
        hash_str = ""
        for i in range(8):
            for j in range(8):
                hash_str += '1' if img[i, j] > avg else '0'
        return hash_str

    def _hash_distance(self, hash1: str, hash2: str) -> float:
        """Calculate normalized hamming distance"""
        if len(hash1) != len(hash2):
            return 1.0
            
        distance = sum(1 for i, j in zip(hash1, hash2) if i != j)
        return distance / len(hash1)
