#!/usr/bin/env python3
"""
Universal launcher for MCP AI Agent
Automatically detects environment and runs appropriate version
"""

import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are available"""
    # Map package names to their import names
    package_imports = {
        "pyautogui": "pyautogui",
        "pillow": "PIL",
        "opencv-python": "cv2",
        "pytesseract": "pytesseract",
        "requests": "requests",
        "mss": "mss",
        "psutil": "psutil",
        "numpy": "numpy",
        "pynput": "pynput",
    }

    missing = []
    for package, import_name in package_imports.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package)

    return missing


def check_display_available():
    """Check if display is available for GUI operations"""
    # Check for DISPLAY environment variable (Linux/X11)
    if "DISPLAY" in os.environ:
        return True

    # Check for Windows desktop
    if os.name == "nt":
        return True

    # Try to access display
    try:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        root.destroy()
        return True
    except:
        return False


def test_screenshot_capability():
    """Test if we can actually take screenshots"""
    try:
        import mss

        with mss.mss() as sct:
            # Try to capture primary monitor
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            return True
    except Exception as e:
        print(f"Screenshot test failed: {e}")
        return False


def show_options_menu():
    """Show user options for different agent modes"""
    print("\n🤖 MCP AI Agent - Choose Mode:")
    print("=" * 40)
    print("1. 🖥️  REAL Desktop Control (controls your actual desktop)")
    print("2. 🧪 Mock/Testing Mode (simulates actions)")
    print("3. 🔧 Auto-detect (tries real, falls back to mock)")
    print("4. ❌ Exit")
    print("-" * 40)

    while True:
        try:
            choice = input("Choose option (1-4): ").strip()
            if choice in ["1", "2", "3", "4"]:
                return choice
            else:
                print("Please enter 1, 2, 3, or 4")
        except KeyboardInterrupt:
            return "4"


def main():
    """Main entry point"""
    print("🚀 MCP AI Agent Launcher")
    print("=" * 40)

    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Please install with: pip install -r requirements.txt")
        return False

    print("✅ All dependencies available")

    # Check environment
    has_display = check_display_available()
    print(f"Display available: {'✅ Yes' if has_display else '❌ No'}")

    # Test actual screenshot capability
    can_screenshot = test_screenshot_capability() if has_display else False
    print(f"Screenshot capability: {'✅ Working' if can_screenshot else '❌ Failed'}")

    # Get user choice
    choice = show_options_menu()

    if choice == "1":
        # Real desktop control
        print("\n🖥️  Starting REAL Desktop Control Agent...")
        if not can_screenshot:
            print("⚠️  Warning: Screenshot test failed, but trying anyway...")
        run_real_desktop_agent()

    elif choice == "2":
        # Mock mode
        print("\n🧪 Starting Mock/Testing Mode...")
        run_headless_agent()

    elif choice == "3":
        # Auto-detect
        if has_display and can_screenshot:
            print("\n🖥️  Auto-detected: Running Real Desktop Control...")
            run_real_desktop_agent()
        else:
            print("\n🧪 Auto-detected: Running Mock Mode...")
            run_headless_agent()

    elif choice == "4":
        print("👋 Goodbye!")
        return True

    return True


def run_real_desktop_agent():
    """Run the real desktop control agent"""
    try:
        result = subprocess.run(
            [sys.executable, "real_desktop_agent.py"], cwd=Path(__file__).parent
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Real desktop agent failed: {e}")
        print("Falling back to mock mode...")
        run_headless_agent()
        return False


def run_headless_agent():
    """Run the headless agent with user prompt support"""
    try:
        result = subprocess.run(
            [sys.executable, "headless_main.py"], cwd=Path(__file__).parent
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Headless agent failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
