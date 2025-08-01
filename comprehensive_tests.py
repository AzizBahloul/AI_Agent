#!/usr/bin/env python3
"""
Comprehensive test suite for MCP AI Agent
"""

import pytest
import tempfile
from unittest.mock import patch

import sys

sys.path.insert(0, "/home/siaziz/Desktop/agentv2")

from config import CONFIG
from utils.logger import logger
from utils.ollama_client import ollama_client


class TestMCPAgent:
    """Test suite for MCP Agent components"""

    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()

    def test_config_validation(self):
        """Test configuration validation"""
        assert CONFIG is not None
        assert hasattr(CONFIG, "models")
        assert hasattr(CONFIG, "data_dir")

    def test_logger_functionality(self):
        """Test logger functionality"""
        logger.info("Test message")
        logger.error("Test error", Exception("test"))
        assert True  # If no exception, logger works

    def test_ollama_health_check(self):
        """Test Ollama connectivity"""
        # This will depend on Ollama being available
        status = ollama_client.health_check()
        assert isinstance(status, bool)

    @patch("subprocess.run")
    def test_platform_detection(self, mock_run):
        """Test platform detection"""
        from utils.platform_utils import platform_manager

        assert platform_manager.platform in ["linux", "windows", "darwin"]

    def test_memory_system(self):
        """Test memory system if available"""
        try:
            from enhanced_agent import AgentMemory

            memory = AgentMemory(":memory:")  # Use in-memory DB for testing

            # Test storing and retrieving memory
            memory_id = memory.store_memory(
                {"test": "context"}, {"type": "test"}, {"success": True}
            )
            assert memory_id is not None
        except ImportError:
            pytest.skip("Enhanced agent not available")

    def test_safety_validation(self):
        """Test safety validation"""
        try:
            from advanced_features import SafetyMonitor

            safety = SafetyMonitor()

            # Test safe action
            safe, msg = safety.validate_action(
                {"type": "click", "target": "button"}, {}
            )
            assert safe == True

            # Test dangerous action
            safe, msg = safety.validate_action(
                {"type": "click", "target": "delete system"}, {}
            )
            assert safe == False
        except ImportError:
            pytest.skip("Advanced features not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
