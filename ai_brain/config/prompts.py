"""
LLM prompt templates for Desktop Genie
"""
TASK_PLANNING_PROMPT = """
You are a task planner AI. Given the following command and context, break it down into a JSON plan with steps, agents, actions, and parameters.

Command: {command}
Context: {context}

Return a JSON object with a 'steps' array.
"""
