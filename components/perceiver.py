"""
Perceiver component - handles screenshot capture, OCR, and vision analysis
"""

import os
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import pytesseract
import mss

from config import CONFIG
from utils.logger import logger
from utils.platform_utils import platform_manager
from models.ollama_client import ollama_client


@dataclass
class ScreenContext:
    """Container for screen perception data"""

    timestamp: datetime
    screenshot_path: str
    ocr_text: str
    ui_elements: List[Dict[str, Any]]
    vlm_description: str
    screen_resolution: Tuple[int, int]
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScreenCapture:
    """Handles screenshot capture with multiple backends"""

    def __init__(self):
        self.backend = platform_manager.get_screenshot_backend()
        self.sct = mss.mss() if self.backend == "mss" else None
        self.scaling_factor = platform_manager.get_display_scaling()
        logger.info(f"Screen capture initialized with backend: {self.backend}")

    def capture_screenshot(self, save_path: str = None) -> Optional[str]:
        """Capture screenshot and save to file"""
        try:
            if self.backend == "mss":
                # Use MSS for fast screenshot
                monitor = self.sct.monitors[1]  # Primary monitor
                screenshot = self.sct.grab(monitor)
                img = Image.frombytes(
                    "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
                )
            else:
                # Fallback to PyAutoGUI
                import pyautogui

                img = pyautogui.screenshot()

            # Resize if too large
            max_size = CONFIG.perceiver.max_screenshot_size
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save screenshot
            if save_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                save_path = os.path.join(
                    CONFIG.screenshots_dir, f"screenshot_{timestamp}.png"
                )

            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            img.save(save_path)
            logger.debug(f"Screenshot saved: {save_path}")
            return save_path

        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None


class OCRProcessor:
    """Handles text extraction from screenshots"""

    def __init__(self):
        self.tesseract_cmd = platform_manager.get_tesseract_cmd()
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        logger.info(f"OCR initialized with Tesseract: {self.tesseract_cmd}")

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image using OCR"""
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return {"text": "", "confidence": 0.0, "words": []}

            # Preprocess image for better OCR
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply adaptive thresholding
            processed = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # Extract text with confidence data
            config = CONFIG.perceiver.ocr_config
            data = pytesseract.image_to_data(
                processed, config=config, output_type=pytesseract.Output.DICT
            )

            # Filter confident text
            words = []
            text_parts = []
            confidences = []

            for i in range(len(data["text"])):
                word = data["text"][i].strip()
                conf = float(data["conf"][i])

                if word and conf > CONFIG.perceiver.min_ocr_confidence * 100:
                    words.append(
                        {
                            "text": word,
                            "confidence": conf / 100.0,
                            "bbox": {
                                "x": data["left"][i],
                                "y": data["top"][i],
                                "width": data["width"][i],
                                "height": data["height"][i],
                            },
                        }
                    )
                    text_parts.append(word)
                    confidences.append(conf / 100.0)

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            full_text = " ".join(text_parts)

            return {
                "text": full_text,
                "confidence": avg_confidence,
                "words": words,
                "word_count": len(words),
            }

        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return {"text": "", "confidence": 0.0, "words": []}


class UIElementParser:
    """Parses UI elements from screenshots"""

    def __init__(self):
        self.last_elements = []
        logger.info("UI Element Parser initialized")

    def detect_elements(self, image_path: str) -> List[Dict[str, Any]]:
        """Detect UI elements using computer vision"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            elements = []

            # Detect buttons using contour detection
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                # Filter by area and aspect ratio
                area = cv2.contourArea(contour)
                if area < 100:  # Too small
                    continue

                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h

                # Classify element type based on properties
                element_type = self._classify_element(area, aspect_ratio, w, h)

                if element_type:
                    elements.append(
                        {
                            "type": element_type,
                            "bbox": {"x": x, "y": y, "width": w, "height": h},
                            "center": {"x": x + w // 2, "y": y + h // 2},
                            "area": area,
                            "confidence": min(
                                1.0, area / 10000
                            ),  # Normalize confidence
                        }
                    )

            # Sort by confidence and return top elements
            elements.sort(key=lambda x: x["confidence"], reverse=True)
            self.last_elements = elements[:50]  # Keep top 50

            return self.last_elements

        except Exception as e:
            logger.error(f"UI element detection failed: {e}")
            return []

    def _classify_element(
        self, area: float, aspect_ratio: float, width: int, height: int
    ) -> Optional[str]:
        """Classify UI element type based on properties"""
        # Button-like elements
        if 1000 < area < 50000 and 0.2 < aspect_ratio < 5:
            if 20 < width < 400 and 15 < height < 100:
                return "button"

        # Input field-like elements
        if 500 < area < 100000 and aspect_ratio > 2:
            if height < 50:
                return "input"

        # Image/icon-like elements
        if 400 < area < 10000 and 0.5 < aspect_ratio < 2:
            return "icon"

        # Large content areas
        if area > 50000:
            return "panel"

        return None


class VisionLanguageProcessor:
    """Handles vision-language model analysis"""

    def __init__(self):
        self.vision_model = CONFIG.models.vision_model

    def analyze_screenshot(self, image_path: str, context: str = "") -> str:
        """Analyze screenshot using vision-language model"""
        if not CONFIG.perceiver.enable_vlm_description:
            return ""

        try:
            prompt = self._build_analysis_prompt(context)
            response = ollama_client.analyze_image(
                self.vision_model, image_path, prompt
            )

            if response.success:
                logger.debug(f"VLM analysis complete: {len(response.content)} chars")
                return response.content
            else:
                logger.warning(f"VLM analysis failed: {response.error}")
                return f"Vision analysis unavailable: {response.error}"

        except Exception as e:
            logger.error(f"VLM processing failed: {e}")
            return f"Vision analysis error: {e}"

    def _build_analysis_prompt(self, context: str = "") -> str:
        """Build prompt for vision analysis"""
        base_prompt = """Analyze this desktop screenshot and describe:
1. What applications or windows are visible
2. The main UI elements (buttons, menus, text fields)
3. The current state or context
4. Any dialogs, pop-ups, or notifications
5. What the user might want to do next

Be concise but thorough. Focus on actionable elements."""

        if context:
            base_prompt += f"\n\nAdditional context: {context}"

        return base_prompt


class Perceiver:
    """Main Perceiver component that orchestrates screen perception"""

    def __init__(self):
        self.screen_capture = ScreenCapture()
        self.ocr_processor = OCRProcessor()
        self.ui_parser = UIElementParser()
        self.vlm_processor = VisionLanguageProcessor()
        self.last_screenshot_path = None
        self.running = False
        self.current_context = None
        logger.info("Perceiver component initialized")

    def start(self):
        """Start the perceiver component"""
        self.running = True
        logger.info("Perceiver started")

    def stop(self):
        """Stop the perceiver component"""
        self.running = False
        logger.info("Perceiver stopped")

    def get_current_context(self) -> Optional[ScreenContext]:
        """Get the current screen context"""
        if self.current_context is None:
            self.current_context = self.perceive_screen()
        return self.current_context

    def perceive_screen(self, save_screenshot: bool = True) -> Optional[ScreenContext]:
        """Complete screen perception pipeline"""
        try:
            timestamp = datetime.now()

            # 1. Capture screenshot
            if save_screenshot:
                screenshot_path = self.screen_capture.capture_screenshot()
            else:
                screenshot_path = self.last_screenshot_path

            if not screenshot_path or not os.path.exists(screenshot_path):
                logger.error("Screenshot capture failed")
                return None

            self.last_screenshot_path = screenshot_path

            # 2. Extract text with OCR
            ocr_data = self.ocr_processor.extract_text(screenshot_path)

            # 3. Detect UI elements
            ui_elements = []
            if CONFIG.perceiver.enable_ui_parsing:
                ui_elements = self.ui_parser.detect_elements(screenshot_path)

            # 4. Get vision-language description
            vlm_description = ""
            if CONFIG.perceiver.enable_vlm_description:
                vlm_description = self.vlm_processor.analyze_screenshot(screenshot_path)

            # 5. Get screen resolution
            img = Image.open(screenshot_path)
            resolution = img.size

            # 6. Calculate overall confidence
            confidence = self._calculate_confidence(
                ocr_data, ui_elements, vlm_description
            )

            # Create context object
            context = ScreenContext(
                timestamp=timestamp,
                screenshot_path=screenshot_path,
                ocr_text=ocr_data["text"],
                ui_elements=ui_elements,
                vlm_description=vlm_description,
                screen_resolution=resolution,
                confidence_score=confidence,
            )

            logger.log_perception(
                {
                    "timestamp": timestamp.isoformat(),
                    "ocr_words": len(ocr_data.get("words", [])),
                    "ui_elements": len(ui_elements),
                    "vlm_length": len(vlm_description),
                    "confidence": confidence,
                }
            )

            return context

        except Exception as e:
            logger.error(f"Screen perception failed: {e}")
            return None

    def _calculate_confidence(
        self,
        ocr_data: Dict[str, Any],
        ui_elements: List[Dict[str, Any]],
        vlm_description: str,
    ) -> float:
        """Calculate overall perception confidence"""
        scores = []

        # OCR confidence
        if ocr_data.get("confidence", 0) > 0:
            scores.append(min(ocr_data["confidence"] / 100.0, 1.0))

        # UI elements confidence
        if ui_elements:
            ui_conf = np.mean([elem.get("confidence", 50) for elem in ui_elements])
            scores.append(min(ui_conf / 100.0, 1.0))

        # VLM success (binary)
        if vlm_description and not vlm_description.startswith("Vision analysis"):
            scores.append(0.8)

        return np.mean(scores) if scores else 0.0

    def get_ui_element_by_text(
        self, context: ScreenContext, text: str
    ) -> Optional[Dict[str, Any]]:
        """Find UI element by text content"""
        text_lower = text.lower()
        for element in context.ui_elements:
            if text_lower in element.get("text", "").lower():
                return element
        return None

    def get_clickable_elements(self, context: ScreenContext) -> List[Dict[str, Any]]:
        """Get all clickable UI elements"""
        clickable_types = ["button", "link", "menu_item"]
        return [
            elem for elem in context.ui_elements if elem.get("type") in clickable_types
        ]
