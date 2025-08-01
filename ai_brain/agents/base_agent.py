"""
Abstract base class for all agents
"""
from abc import ABC, abstractmethod
from typing import Dict

class BaseAgent(ABC):
    @abstractmethod
    async def execute(self, task: Dict, context: Dict, websocket) -> Dict:
        pass
