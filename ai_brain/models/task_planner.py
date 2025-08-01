"""
Task decomposition logic with context-aware planning
"""
import json
import logging
from typing import Dict, Any
from ai_brain.config.prompts import TASK_PLANNING_PROMPT

logger = logging.getLogger("desktop-genie")

class TaskPlanner:
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self.plan_cache = {}
        logger.info("Task planner initialized")

    async def generate_plan(
        self, 
        command: str, 
        context: Dict[str, Any],
        session_id: str,
        model: str = "mistral:latest"
    ) -> Dict:
        """Generate execution plan for a given command"""
        # Check cache first
        cache_key = f"{command}-{hash(json.dumps(context, sort_keys=True))}"
        if cache_key in self.plan_cache:
            return self.plan_cache[cache_key]
        
        # Build prompt
        prompt = TASK_PLANNING_PROMPT.format(
            command=command,
            context=json.dumps(context, indent=2)
        )
        
        # Generate plan
        response = ""
        async for chunk in self.ollama.generate_text(prompt, model=model):
            response += chunk
        
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            plan_json = response[start_idx:end_idx]
            plan = json.loads(plan_json)
            
            # Validate plan structure
            if "steps" not in plan or not isinstance(plan["steps"], list):
                raise ValueError("Invalid plan structure")
                
            # Cache and return
            self.plan_cache[cache_key] = plan
            return plan
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Plan generation failed: {e}\nResponse: {response}")
            # Fallback to simple plan
            return {
                "goal": command,
                "steps": [{
                    "agent": "system",
                    "action": "notify",
                    "parameters": {"message": f"Failed to plan: {e}"}
                }]
            }
