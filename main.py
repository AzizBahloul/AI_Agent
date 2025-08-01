#!/usr/bin/env python3
"""
Main entry point for the MCP AI Agent
"""

import os
import sys
import json
import time
import signal
import threading
import traceback
from datetime import datetime
import psutil

from config import CONFIG
from utils.logger import logger
from utils.platform_utils import platform_manager
from models.ollama_client import OllamaClient
from components.perceiver import Perceiver
from components.controller import Controller


class AgentMonitor:
    """Monitors system resources and agent health"""

    def __init__(self, config):
        self.monitoring = config.monitoring
        self.running = False
        self.monitor_thread = None
        self.metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "gpu_usage": [],
            "errors": [],
            "performance": {},
        }

    def start(self):
        """Start the monitoring thread"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("System monitoring started")

    def stop(self):
        """Stop the monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("System monitoring stopped")
        self._save_metrics()

    def _monitoring_loop(self):
        """Monitor system metrics periodically"""
        while self.running:
            try:
                self._check_system_metrics()
                time.sleep(self.monitoring.check_interval)
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(5)

    def _check_system_metrics(self):
        """Check and record system metrics"""
        # CPU and memory usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        mem_percent = memory.percent

        self.metrics["cpu_usage"].append(
            {"timestamp": datetime.now().isoformat(), "value": cpu_percent}
        )

        self.metrics["memory_usage"].append(
            {"timestamp": datetime.now().isoformat(), "value": mem_percent}
        )

        # Check for critical thresholds
        if mem_percent > self.monitoring.memory_threshold * 100:
            self._log_error("HIGH_MEMORY", f"Memory usage critical: {mem_percent:.1f}%")

        # Check other metrics like GPU if available (requires additional libraries)
        # This is a simplified version

    def _log_error(self, error_type, message):
        """Log an error to the monitoring system"""
        error = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": message,
        }
        self.metrics["errors"].append(error)

        # Write to error file
        if self.monitoring.error_file:
            try:
                with open(self.monitoring.error_file, "a") as f:
                    f.write(f"{error['timestamp']} | {error_type} | {message}\n")
            except Exception as e:
                logger.error(f"Failed to write error log: {e}")

    def _save_metrics(self):
        """Save collected metrics to file"""
        if not self.monitoring.metrics_file:
            return

        try:
            with open(self.monitoring.metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
            logger.info(f"Metrics saved to {self.monitoring.metrics_file}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")


class MCPAgent:
    """Main AI Agent class integrating all components"""

    def __init__(self):
        self.config = CONFIG
        self.running = False
        self.ollama_client = OllamaClient()
        self.perceiver = Perceiver()
        self.controller = Controller()
        self.monitor = AgentMonitor(self.config)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Make necessary directories
        os.makedirs(self.config.data_dir, exist_ok=True)
        os.makedirs(self.config.screenshots_dir, exist_ok=True)

        logger.info("MCP Agent initialized")

    def start(self):
        """Start the agent and all components"""
        try:
            logger.info("Starting MCP Agent...")

            # Check Ollama connectivity
            if not self.ollama_client.health_check():
                logger.error("Ollama not available. Please start Ollama service.")
                return False

            # Start monitoring
            self.monitor.start()

            # Start components
            self.perceiver.start()
            self.controller.start()

            self.running = True
            logger.info("✅ MCP Agent started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start MCP Agent: {e}")
            traceback.print_exc()
            return False

    def run(self):
        """Run the main agent loop"""
        if not self.start():
            logger.error("Failed to start agent")
            return

        logger.info("MCP Agent running. Press Ctrl+C to stop.")

        try:
            cycle_count = 0
            while self.running:
                cycle_count += 1
                logger.info(f"🔄 Agent Cycle {cycle_count}")

                # 1. Perceive screen
                context = self.perceiver.perceive_screen()
                if not context:
                    logger.warning("Perception failed, waiting...")
                    time.sleep(2)
                    continue

                # 2. Basic logging of what we see
                logger.info(
                    f"Perceived: {len(context.ocr_text)} chars OCR, {len(context.ui_elements)} UI elements"
                )

                # 3. Wait between cycles
                time.sleep(self.config.perceiver.screenshot_interval)

        except KeyboardInterrupt:
            logger.info("Agent interrupted by user")
        except Exception as e:
            logger.error(f"Agent runtime error: {e}")
            traceback.print_exc()
        finally:
            self.stop()

    def stop(self):
        """Stop the agent and all components"""
        logger.info("Stopping MCP Agent...")
        self.running = False

        # Stop components
        try:
            self.perceiver.stop()
        except Exception as e:
            logger.error(f"Error stopping perceiver: {e}")

        try:
            self.controller.stop()
        except Exception as e:
            logger.error(f"Error stopping controller: {e}")

        try:
            self.monitor.stop()
        except Exception as e:
            logger.error(f"Error stopping monitor: {e}")

        logger.info("MCP Agent stopped")

    def _handle_shutdown(self, sig, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {sig}, shutting down...")
        self.stop()
        sys.exit(0)


def main():
    """Main entry point"""
    try:
        logger.info("=" * 50)
        logger.info("Starting MCP AI Agent")
        logger.info(f"Platform: {platform_manager.platform}")
        logger.info("=" * 50)

        agent = MCPAgent()
        agent.run()

    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
