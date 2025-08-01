#!/usr/bin/env python3
"""
Demo script for the MCP AI Agent - simulates functionality without screen capture
"""

import time
from datetime import datetime


def simulate_screen_perception():
    """Simulate screen perception without actual screenshot"""
    return {
        "timestamp": datetime.now().isoformat(),
        "ocr_text": "File Explorer - /home/user/Documents\nNew Folder\nDownloads\nDocuments\nPictures\nVideos",
        "ui_elements": [
            {
                "type": "button",
                "text": "New Folder",
                "bbox": {"x": 50, "y": 100, "width": 100, "height": 30},
            },
            {
                "type": "button",
                "text": "Downloads",
                "bbox": {"x": 50, "y": 140, "width": 100, "height": 30},
            },
            {
                "type": "button",
                "text": "Documents",
                "bbox": {"x": 50, "y": 180, "width": 100, "height": 30},
            },
        ],
        "vlm_description": "The screen shows a file explorer window with the main navigation panel on the left showing folders like Downloads, Documents, Pictures, and Videos. There's a 'New Folder' button visible at the top.",
        "confidence_score": 0.85,
    }


def simulate_model_reasoning(context):
    """Simulate LLM reasoning about the screen"""
    reasoning = {
        "analysis": "I can see a file explorer is open. The user appears to be browsing their home directory with access to standard folders.",
        "suggested_actions": [
            {
                "type": "click",
                "target": "Documents",
                "reason": "Navigate to documents folder to see files",
            },
            {
                "type": "key_press",
                "key": "ctrl+n",
                "reason": "Create a new folder if needed",
            },
        ],
        "confidence": 0.78,
    }
    return reasoning


def simulate_action_execution(action):
    """Simulate action execution"""
    print(f"🎬 Executing action: {action['type']}")
    if action["type"] == "click":
        print(f"   Clicking on: {action.get('target', 'unknown')}")
    elif action["type"] == "key_press":
        print(f"   Pressing key: {action.get('key', 'unknown')}")

    # Simulate success with some random failures
    import random

    success = random.random() > 0.1  # 90% success rate

    result = {
        "success": success,
        "action_type": action["type"],
        "timestamp": datetime.now().isoformat(),
        "error": None if success else "Simulated random failure",
    }

    if success:
        print("   ✅ Action completed successfully")
    else:
        print(f"   ❌ Action failed: {result['error']}")

    return result


def main_demo_loop():
    """Main demo loop showing agent functionality"""
    print("🚀 Starting MCP AI Agent Demo")
    print("=" * 60)

    cycle = 0
    while cycle < 5:  # Run 5 demo cycles
        cycle += 1
        print(f"\n🔄 Perception Cycle {cycle}")
        print("-" * 30)

        # 1. Perceive screen
        print("👁️  Capturing and analyzing screen...")
        context = simulate_screen_perception()
        print(f"   OCR Text: {context['ocr_text'][:50]}...")
        print(f"   UI Elements: {len(context['ui_elements'])} found")
        print(f"   Confidence: {context['confidence_score']:.2f}")

        # 2. Reason about what to do
        print("\n🧠 AI Reasoning...")
        reasoning = simulate_model_reasoning(context)
        print(f"   Analysis: {reasoning['analysis']}")
        print(f"   Suggested actions: {len(reasoning['suggested_actions'])}")

        # 3. Execute actions
        print("\n⚡ Executing Actions...")
        for i, action in enumerate(reasoning["suggested_actions"]):
            if i >= 1:  # Limit to 1 action per cycle for demo
                break
            result = simulate_action_execution(action)

            # Log the action
            print(
                f"   Logged action: {action['type']} -> {'Success' if result['success'] else 'Failed'}"
            )

        print(f"\n✨ Cycle {cycle} completed")
        time.sleep(2)  # Pause between cycles

    print("\n🏁 Demo completed!")
    print("=" * 60)
    print("In a real environment, the agent would:")
    print("• Take actual screenshots of your desktop")
    print("• Use OCR to extract text from the screen")
    print("• Use computer vision to detect UI elements")
    print("• Send context to a vision-language model for analysis")
    print("• Generate and execute real mouse/keyboard actions")
    print("• Monitor system performance and log all activities")


if __name__ == "__main__":
    try:
        main_demo_loop()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback

        traceback.print_exc()
