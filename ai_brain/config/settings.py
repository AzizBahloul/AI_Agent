"""
Configuration management for AI Brain
"""
import yaml
import os

class Settings:
    def __init__(self, config_path=None):
        self.config_path = config_path or os.getenv("GENIE_CONFIG", "config/default.yaml")
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)
