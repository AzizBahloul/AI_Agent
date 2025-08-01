#!/usr/bin/env python3
"""
Unified Launcher for MCP AI Agent
Provides easy access to all components and modes
"""

import os
import sys
import subprocess
from pathlib import Path


class MCPLauncher:
    """Unified launcher for MCP AI Agent"""

    def __init__(self):
        self.project_root = Path("/home/siaziz/Desktop/agentv2")

    def show_menu(self):
        """Show main menu"""
        print("\n" + "=" * 60)
        print("🤖 MCP AI Agent - Unified Launcher")
        print("=" * 60)
        print("Select mode:")
        print("1. 🖥️  Real Desktop Agent (requires display)")
        print("2. 🎭 Headless Agent (mock mode)")
        print("3. 🧠 Enhanced Agent (with memory & learning)")
        print("4. 🧪 Test Suite")
        print("5. 📊 Performance Monitor")
        print("6. 🔧 System Validation")
        print("7. 📈 Analysis & Reports")
        print("8. ⚙️  Configuration")
        print("9. 📚 Help & Documentation")
        print("0. 🚪 Exit")
        print("=" * 60)

    def run(self):
        """Run the launcher"""
        while True:
            self.show_menu()

            try:
                choice = input("Enter your choice (0-9): ").strip()

                if choice == "0":
                    print("👋 Goodbye!")
                    break
                elif choice == "1":
                    self.launch_real_agent()
                elif choice == "2":
                    self.launch_headless_agent()
                elif choice == "3":
                    self.launch_enhanced_agent()
                elif choice == "4":
                    self.run_tests()
                elif choice == "5":
                    self.run_performance_monitor()
                elif choice == "6":
                    self.run_validation()
                elif choice == "7":
                    self.run_analysis()
                elif choice == "8":
                    self.configure_system()
                elif choice == "9":
                    self.show_help()
                else:
                    print("❌ Invalid choice. Please try again.")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def launch_real_agent(self):
        """Launch real desktop agent"""
        print("🖥️  Launching Real Desktop Agent...")
        user_prompt = input(
            "Enter your automation goal (or press Enter for auto mode): "
        ).strip()

        cmd = ["python", "real_desktop_agent.py"]
        if user_prompt:
            cmd.append(user_prompt)

        self._run_command(cmd)

    def launch_headless_agent(self):
        """Launch headless agent"""
        print("🎭 Launching Headless Agent...")
        self._run_command(["python", "headless_main.py"])

    def launch_enhanced_agent(self):
        """Launch enhanced agent with memory"""
        print("🧠 Launching Enhanced Agent...")
        if Path("enhanced_agent.py").exists():
            user_prompt = input("Enter your goal: ").strip()
            cmd = ["python", "enhanced_agent.py"]
            if user_prompt:
                cmd.append(user_prompt)
            self._run_command(cmd)
        else:
            print("❌ Enhanced agent not available. Use option 2 instead.")

    def run_tests(self):
        """Run test suite"""
        print("🧪 Running Tests...")
        self._run_command(["python", "test_components.py"])

        if Path("comprehensive_tests.py").exists():
            print("\nRunning comprehensive tests...")
            self._run_command(["python", "comprehensive_tests.py"])

    def run_performance_monitor(self):
        """Run performance monitor"""
        print("📊 Starting Performance Monitor...")
        if Path("performance_monitor.py").exists():
            self._run_command(["python", "performance_monitor.py"])
        else:
            print("❌ Performance monitor not available.")

    def run_validation(self):
        """Run system validation"""
        print("🔧 Running System Validation...")
        self._run_command(["python", "final_validation.py"])

    def run_analysis(self):
        """Run analysis and generate reports"""
        print("📈 Running Analysis...")
        self._run_command(["python", "analyze_agent.py"])

    def configure_system(self):
        """System configuration"""
        print("⚙️  System Configuration")
        print("Current configuration:")
        print(f"  Project root: {self.project_root}")
        print(f"  Python: {sys.executable}")

        # Show available models
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                print("  Available Ollama models:")
                print("   ", result.stdout.strip())
        except:
            print("  ⚠️  Ollama not available")

    def show_help(self):
        """Show help and documentation"""
        print("📚 MCP AI Agent Help")
        print("=" * 40)
        print("Available components:")
        print("• Real Desktop Agent: Controls actual desktop")
        print("• Headless Agent: Simulated mode for testing")
        print("• Enhanced Agent: With memory and learning")
        print("• Test Suite: Validates system functionality")
        print("• Performance Monitor: Tracks system metrics")
        print("")
        print("Requirements:")
        print("• Python 3.8+")
        print("• Ollama with AI models")
        print("• Required Python packages (see requirements.txt)")
        print("")
        print("For real desktop control:")
        print("• Display environment (X11/Wayland)")
        print("• Tesseract OCR")
        print("• GUI automation libraries")

    def _run_command(self, cmd):
        """Run a command in the project directory"""
        try:
            os.chdir(self.project_root)
            subprocess.run(cmd)
            print("\n⏎ Press Enter to continue...")
            input()
        except Exception as e:
            print(f"❌ Error running command: {e}")
            print("⏎ Press Enter to continue...")
            input()


if __name__ == "__main__":
    launcher = MCPLauncher()
    launcher.run()
