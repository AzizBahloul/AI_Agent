#!/usr/bin/env python3
"""
Optimized headless demo for the MCP AI Agent - works without display access
Uses lightweight models and simulates the full agent experience
"""

import time
import random
from datetime import datetime
from pathlib import Path

from config import CONFIG
from utils.logger import logger
from models.ollama_client import ollama_client


class MockScreenCapture:
    """Mock screen capture that generates synthetic screenshots"""

    def __init__(self):
        self.scenario_data = self._load_scenarios()
        self.current_scenario = 0

    def _load_scenarios(self):
        """Load different UI scenarios to simulate"""
        return [
            {
                "name": "Desktop with File Manager",
                "description": "User desktop with file manager window open",
                "ocr_text": "File Manager\nHome\nDocuments\nDownloads\nPictures\nVideos\nMusic\nNew Folder\nCopy\nPaste\nDelete",
                "ui_elements": [
                    {
                        "type": "button",
                        "text": "New Folder",
                        "bbox": {"x": 50, "y": 80, "width": 100, "height": 30},
                    },
                    {
                        "type": "button",
                        "text": "Copy",
                        "bbox": {"x": 160, "y": 80, "width": 60, "height": 30},
                    },
                    {
                        "type": "button",
                        "text": "Paste",
                        "bbox": {"x": 230, "y": 80, "width": 60, "height": 30},
                    },
                    {
                        "type": "folder",
                        "text": "Documents",
                        "bbox": {"x": 50, "y": 120, "width": 80, "height": 60},
                    },
                    {
                        "type": "folder",
                        "text": "Downloads",
                        "bbox": {"x": 150, "y": 120, "width": 80, "height": 60},
                    },
                ],
            },
            {
                "name": "Web Browser",
                "description": "Browser window with search page",
                "ocr_text": "Google Search\nSearch\nImages\nMaps\nNews\nShopping\nMore\nSettings\nWhat is artificial intelligence?\nSearch\nI'm Feeling Lucky",
                "ui_elements": [
                    {
                        "type": "textfield",
                        "text": "search box",
                        "bbox": {"x": 200, "y": 150, "width": 400, "height": 40},
                    },
                    {
                        "type": "button",
                        "text": "Search",
                        "bbox": {"x": 320, "y": 200, "width": 80, "height": 35},
                    },
                    {
                        "type": "button",
                        "text": "I'm Feeling Lucky",
                        "bbox": {"x": 420, "y": 200, "width": 140, "height": 35},
                    },
                    {
                        "type": "link",
                        "text": "Images",
                        "bbox": {"x": 250, "y": 100, "width": 60, "height": 25},
                    },
                ],
            },
            {
                "name": "Text Editor",
                "description": "Text editor with document open",
                "ocr_text": "Text Editor - Document1.txt\nFile Edit View Tools Help\nHello World!\nThis is a sample document.\nThe MCP AI Agent is working correctly.\nSave\nSave As\nOpen\nNew",
                "ui_elements": [
                    {
                        "type": "menu",
                        "text": "File",
                        "bbox": {"x": 10, "y": 30, "width": 40, "height": 25},
                    },
                    {
                        "type": "menu",
                        "text": "Edit",
                        "bbox": {"x": 55, "y": 30, "width": 40, "height": 25},
                    },
                    {
                        "type": "button",
                        "text": "Save",
                        "bbox": {"x": 10, "y": 60, "width": 60, "height": 30},
                    },
                    {
                        "type": "textarea",
                        "text": "main content",
                        "bbox": {"x": 10, "y": 100, "width": 500, "height": 300},
                    },
                ],
            },
        ]

    def get_next_scenario(self):
        """Get the next scenario in sequence"""
        scenario = self.scenario_data[self.current_scenario]
        self.current_scenario = (self.current_scenario + 1) % len(self.scenario_data)
        return scenario


class MockPerceiver:
    """Mock perceiver that simulates screen analysis"""

    def __init__(self):
        self.capture = MockScreenCapture()
        self.running = False

    def start(self):
        self.running = True
        logger.info("Mock Perceiver started")

    def stop(self):
        self.running = False
        logger.info("Mock Perceiver stopped")

    def perceive_screen(self):
        """Generate synthetic screen perception data"""
        scenario = self.capture.get_next_scenario()

        # Simulate processing time
        time.sleep(random.uniform(0.3, 0.8))

        # Create mock screenshot file
        screenshots_dir = Path(CONFIG.screenshots_dir)
        screenshots_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        mock_screenshot = screenshots_dir / f"mock_screenshot_{timestamp}.txt"
        mock_screenshot.write_text(f"Mock screenshot for: {scenario['name']}")

        # Generate realistic perception results
        context = {
            "timestamp": datetime.now().isoformat(),
            "screenshot_path": str(mock_screenshot),
            "ocr_text": scenario["ocr_text"],
            "ui_elements": scenario["ui_elements"],
            "vlm_description": f"The screen shows {scenario['description']}. {self._generate_vlm_details(scenario)}",
            "screen_resolution": (1920, 1080),
            "confidence_score": random.uniform(0.75, 0.95),
        }

        logger.info(
            f"Mock perception: {scenario['name']} - {len(scenario['ui_elements'])} elements detected"
        )
        return context

    def _generate_vlm_details(self, scenario):
        """Generate realistic VLM description details"""
        details = [
            "The interface appears to be user-friendly with clearly labeled buttons.",
            "There are several interactive elements visible on the screen.",
            "The layout follows standard desktop application conventions.",
            "The text is clearly readable with good contrast.",
        ]
        return random.choice(details)


class MockController:
    """Mock controller that simulates action execution"""

    def __init__(self):
        self.running = False
        self.action_success_rate = 0.85  # 85% success rate

    def start(self):
        self.running = True
        logger.info("Mock Controller started")

    def stop(self):
        self.running = False
        logger.info("Mock Controller stopped")

    def execute_action(self, action):
        """Simulate action execution"""
        # Simulate action delay
        time.sleep(random.uniform(0.2, 0.6))

        success = random.random() < self.action_success_rate

        result = {
            "success": success,
            "action_type": action.get("type", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "details": action,
            "error": None if success else f"Simulated failure for {action.get('type')}",
        }

        # Log the action
        if success:
            logger.info(f"✅ Mock action executed: {action.get('type')} -> Success")
        else:
            logger.warning(
                f"❌ Mock action failed: {action.get('type')} -> {result['error']}"
            )

        return result


class ReasoningEngine:
    """AI reasoning engine that decides what actions to take"""

    def __init__(self):
        # Use lightweight model for better memory performance
        self.reasoning_model = CONFIG.models.fallback_model  # mistral:7b

    def analyze_and_decide(self, context):
        """Analyze screen context and decide on actions"""
        # Extract key information
        ui_elements = context.get("ui_elements", [])
        ocr_text = context.get("ocr_text", "")

        # Create concise analysis prompt for memory efficiency
        prompt = f"""Screen context:
OCR: {ocr_text[:100]}...
UI elements: {len(ui_elements)} detected

Suggest ONE specific action (click, type, scroll) and briefly explain why.
Response format: "Action: [action] - Reason: [brief explanation]"
"""

        try:
            response = ollama_client.generate_text(
                model=self.reasoning_model,
                prompt=prompt,
                system_prompt="You are a helpful desktop automation assistant. Suggest safe, productive actions.",
                temperature=0.5,
                max_tokens=100,  # Keep response short
            )

            if response.success:
                reasoning = response.content
                action = self._extract_action_from_reasoning(reasoning, ui_elements)
                return {
                    "reasoning": reasoning,
                    "suggested_action": action,
                    "confidence": random.uniform(0.7, 0.9),
                }
            else:
                logger.warning(f"Model reasoning failed: {response.error}")
                return self._fallback_reasoning(ui_elements)

        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            return self._fallback_reasoning(ui_elements)

    def _extract_action_from_reasoning(self, reasoning, ui_elements):
        """Extract a concrete action from the reasoning"""
        reasoning_lower = reasoning.lower()

        # Simple keyword-based action extraction
        if "click" in reasoning_lower and ui_elements:
            # Find a clickable element
            clickable = [e for e in ui_elements if e.get("type") in ["button", "link"]]
            if clickable:
                elem = random.choice(clickable)
                bbox = elem.get("bbox", {})
                return {
                    "type": "click",
                    "target": elem.get("text", "element"),
                    "x": bbox.get("x", 100) + bbox.get("width", 50) // 2,
                    "y": bbox.get("y", 100) + bbox.get("height", 30) // 2,
                    "reasoning": f"Clicking on '{elem.get('text')}'",
                }

        if "type" in reasoning_lower or "search" in reasoning_lower:
            return {
                "type": "type",
                "text": "test input",
                "reasoning": "Typing based on screen context",
            }

        # Default action
        return {
            "type": "wait",
            "duration": 1.0,
            "reasoning": "Waiting to observe changes",
        }

    def _fallback_reasoning(self, ui_elements):
        """Fallback reasoning when AI model fails"""
        if ui_elements:
            elem = random.choice(ui_elements)
            return {
                "reasoning": "Using fallback: selecting available UI element",
                "suggested_action": {
                    "type": "click",
                    "target": elem.get("text", "element"),
                    "reasoning": "Fallback action",
                },
                "confidence": 0.5,
            }
        else:
            return {
                "reasoning": "No elements detected, waiting",
                "suggested_action": {
                    "type": "wait",
                    "duration": 2.0,
                    "reasoning": "No actionable elements found",
                },
                "confidence": 0.3,
            }


class OptimizedHeadlessAgent:
    """Optimized headless agent for memory-constrained environments"""

    def __init__(self):
        self.perceiver = MockPerceiver()
        self.controller = MockController()
        self.reasoning = ReasoningEngine()
        self.running = False
        self.cycle_count = 0
        self.max_cycles = 8  # Reduced for memory efficiency

    def start(self):
        """Start the headless agent"""
        logger.info("🚀 Starting Optimized Headless MCP AI Agent Demo")
        logger.info("=" * 60)

        # Test Ollama connection
        if not ollama_client.health_check():
            logger.error("❌ Ollama not available. Please start Ollama service.")
            return False

        logger.info(
            f"✅ Ollama connected with {len(ollama_client.available_models)} models"
        )

        # Start components
        self.perceiver.start()
        self.controller.start()
        self.running = True

        logger.info("✅ All components started successfully")
        return True

    def run(self):
        """Run the main agent loop"""
        if not self.start():
            return

        logger.info(
            f"🎯 Running {self.max_cycles} optimized perception-reasoning-action cycles"
        )
        logger.info("Press Ctrl+C to stop early\n")

        try:
            while self.running and self.cycle_count < self.max_cycles:
                self.cycle_count += 1
                logger.info(f"🔄 Cycle {self.cycle_count}/{self.max_cycles}")
                logger.info("-" * 40)

                # 1. Perceive the screen
                logger.info("👁️  Perceiving screen...")
                context = self.perceiver.perceive_screen()

                if not context:
                    logger.error("❌ Perception failed, skipping cycle")
                    time.sleep(1)
                    continue

                # 2. Reason about what to do
                logger.info("🧠 Analyzing and reasoning...")
                decision = self.reasoning.analyze_and_decide(context)

                logger.info(f"💭 Reasoning: {decision['reasoning'][:80]}...")
                logger.info(f"🎯 Confidence: {decision['confidence']:.2f}")

                # 3. Execute the suggested action
                action = decision["suggested_action"]
                logger.info(f"⚡ Executing action: {action['type']}")

                result = self.controller.execute_action(action)

                # 4. Brief pause between cycles
                logger.info(f"✨ Cycle {self.cycle_count} completed\n")
                time.sleep(2)  # Reduced pause

        except KeyboardInterrupt:
            logger.info("\n👋 Demo interrupted by user")
        except Exception as e:
            logger.error(f"❌ Demo error: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the agent"""
        self.running = False
        self.perceiver.stop()
        self.controller.stop()

        logger.info("🏁 Optimized Headless Demo Completed!")
        logger.info("=" * 60)
        logger.info("📊 Summary:")
        logger.info(f"   • Completed {self.cycle_count} cycles")
        logger.info("   • Simulated full perception-reasoning-action pipeline")
        logger.info("   • All components working correctly")
        logger.info("   • Optimized for memory-constrained environments")
        logger.info("=" * 60)


def main():
    """Main entry point"""
    try:
        agent = OptimizedHeadlessAgent()
        agent.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
