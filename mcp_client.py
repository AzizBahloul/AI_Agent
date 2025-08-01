#!/usr/bin/env python3
"""
MCP Client Integration for AI Agent
Provides computer use capabilities through MCP protocol
"""

import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from config import CONFIG
from utils.logger import logger
from models.ollama_client import ollama_client


class MCPComputerUseClient:
    """Client for interacting with MCP computer use servers"""

    def __init__(self, server_path: Optional[str] = None):
        self.server_path = server_path or str(Path(__file__).parent / "mcp_server.py")
        self.server_process = None
        self.connected = False

    async def start_server(self):
        """Start the MCP server process"""
        try:
            self.server_process = await asyncio.create_subprocess_exec(
                "python",
                self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self.connected = True
            logger.info("MCP Computer Use Server started")
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False

    async def stop_server(self):
        """Stop the MCP server process"""
        if self.server_process:
            self.server_process.terminate()
            await self.server_process.wait()
            self.connected = False
            logger.info("MCP Computer Use Server stopped")

    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server"""
        if not self.connected:
            await self.start_server()

        request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}

        try:
            # Send request
            request_data = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_data.encode())
            await self.server_process.stdin.drain()

            # Read response
            response_data = await self.server_process.stdout.readline()
            response = json.loads(response_data.decode())

            if "error" in response:
                raise Exception(f"MCP Server error: {response['error']}")

            return response.get("result", {})

        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            raise

    async def screenshot(self, include_analysis: bool = True) -> Dict[str, Any]:
        """Take a screenshot using MCP"""
        return await self.send_request(
            "tools/call",
            {"name": "screenshot", "arguments": {"include_analysis": include_analysis}},
        )

    async def click(
        self, x: int, y: int, button: str = "left", clicks: int = 1
    ) -> Dict[str, Any]:
        """Click at coordinates using MCP"""
        return await self.send_request(
            "tools/call",
            {
                "name": "click",
                "arguments": {"x": x, "y": y, "button": button, "clicks": clicks},
            },
        )

    async def type_text(self, text: str) -> Dict[str, Any]:
        """Type text using MCP"""
        return await self.send_request(
            "tools/call", {"name": "type", "arguments": {"text": text}}
        )

    async def key_press(self, key: str) -> Dict[str, Any]:
        """Press key using MCP"""
        return await self.send_request(
            "tools/call", {"name": "key_press", "arguments": {"key": key}}
        )

    async def scroll(
        self, direction: str, clicks: int = 3, x: int = None, y: int = None
    ) -> Dict[str, Any]:
        """Scroll using MCP"""
        args = {"direction": direction, "clicks": clicks}
        if x is not None and y is not None:
            args.update({"x": x, "y": y})

        return await self.send_request(
            "tools/call", {"name": "scroll", "arguments": args}
        )

    async def drag(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 1.0
    ) -> Dict[str, Any]:
        """Drag using MCP"""
        return await self.send_request(
            "tools/call",
            {
                "name": "drag",
                "arguments": {
                    "start_x": start_x,
                    "start_y": start_y,
                    "end_x": end_x,
                    "end_y": end_y,
                    "duration": duration,
                },
            },
        )

    async def get_screen_text(self, region: Dict[str, int] = None) -> Dict[str, Any]:
        """Get screen text using MCP"""
        args = {}
        if region:
            args["region"] = region

        return await self.send_request(
            "tools/call", {"name": "get_screen_text", "arguments": args}
        )

    async def find_element(
        self, element_type: str = None, text: str = None, description: str = None
    ) -> Dict[str, Any]:
        """Find UI element using MCP"""
        args = {}
        if element_type:
            args["element_type"] = element_type
        if text:
            args["text"] = text
        if description:
            args["description"] = description

        return await self.send_request(
            "tools/call", {"name": "find_element", "arguments": args}
        )

    async def analyze_screen(
        self, focus: str = None, include_actions: bool = True
    ) -> Dict[str, Any]:
        """Analyze screen using MCP"""
        args = {"include_actions": include_actions}
        if focus:
            args["focus"] = focus

        return await self.send_request(
            "tools/call", {"name": "analyze_screen", "arguments": args}
        )


class MCPEnhancedAgent:
    """Enhanced agent that uses MCP for computer use"""

    def __init__(self):
        self.mcp_client = MCPComputerUseClient()
        self.conversation_history = []
        self.last_screenshot = None

    async def start(self):
        """Start the MCP enhanced agent"""
        logger.info("🚀 Starting MCP Enhanced AI Agent")

        # Start MCP server
        success = await self.mcp_client.start_server()
        if not success:
            logger.error("Failed to start MCP server")
            return False

        # Check AI models
        if not ollama_client.health_check():
            logger.error("❌ Ollama not available")
            return False

        logger.info("✅ MCP Enhanced Agent started successfully")
        return True

    async def stop(self):
        """Stop the MCP enhanced agent"""
        await self.mcp_client.stop_server()
        logger.info("🏁 MCP Enhanced Agent stopped")

    async def process_user_request(self, user_request: str) -> Dict[str, Any]:
        """Process a user request using MCP tools"""
        logger.info(f"🎯 Processing user request: {user_request}")

        # Add to conversation history
        self.conversation_history.append(
            {
                "role": "user",
                "content": user_request,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Take screenshot and analyze current state
        screenshot_result = await self.mcp_client.screenshot(include_analysis=True)

        # Use AI to plan actions
        planning_prompt = f"""
You are an AI agent controlling a desktop computer. Your goal is to help the user accomplish their request.

User Request: "{user_request}"

Current screen analysis is available. Based on the user's request, plan the necessary actions.

Available MCP tools:
- screenshot(include_analysis=bool): Take a screenshot with optional AI analysis
- click(x, y, button="left", clicks=1): Click at coordinates
- type(text): Type text
- key_press(key): Press keyboard keys (e.g., "Enter", "ctrl+c", "alt+tab")
- scroll(direction, clicks=3, x=None, y=None): Scroll in direction
- drag(start_x, start_y, end_x, end_y, duration=1.0): Drag between points
- get_screen_text(region=None): Extract text from screen
- find_element(element_type=None, text=None, description=None): Find UI elements
- analyze_screen(focus=None, include_actions=True): AI analysis of screen

Respond with a JSON plan:
{{
    "reasoning": "Why you chose this approach",
    "actions": [
        {{"tool": "tool_name", "arguments": {{}}, "description": "What this does"}},
        ...
    ],
    "expected_outcome": "What should happen"
}}
"""

        response = ollama_client.generate_text(
            model=CONFIG.models.reasoning_model, prompt=planning_prompt, temperature=0.3
        )

        if not response.success:
            return {"error": f"Planning failed: {response.error}"}

        try:
            plan = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback to simple action if JSON parsing fails
            plan = {
                "reasoning": "Fallback plan due to parsing error",
                "actions": [
                    {
                        "tool": "analyze_screen",
                        "arguments": {},
                        "description": "Analyze current state",
                    }
                ],
                "expected_outcome": "Understanding current screen state",
            }

        # Execute the planned actions
        results = []
        for action in plan.get("actions", []):
            tool_name = action.get("tool")
            arguments = action.get("arguments", {})
            description = action.get("description", "")

            logger.info(f"⚡ Executing: {tool_name} - {description}")

            try:
                if tool_name == "screenshot":
                    result = await self.mcp_client.screenshot(**arguments)
                elif tool_name == "click":
                    result = await self.mcp_client.click(**arguments)
                elif tool_name == "type":
                    result = await self.mcp_client.type_text(**arguments)
                elif tool_name == "key_press":
                    result = await self.mcp_client.key_press(**arguments)
                elif tool_name == "scroll":
                    result = await self.mcp_client.scroll(**arguments)
                elif tool_name == "drag":
                    result = await self.mcp_client.drag(**arguments)
                elif tool_name == "get_screen_text":
                    result = await self.mcp_client.get_screen_text(**arguments)
                elif tool_name == "find_element":
                    result = await self.mcp_client.find_element(**arguments)
                elif tool_name == "analyze_screen":
                    result = await self.mcp_client.analyze_screen(**arguments)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                results.append(
                    {"tool": tool_name, "description": description, "result": result}
                )

                # Brief pause between actions
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Action failed: {tool_name} - {e}")
                results.append(
                    {"tool": tool_name, "description": description, "error": str(e)}
                )

        # Record in conversation history
        self.conversation_history.append(
            {
                "role": "assistant",
                "plan": plan,
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return {
            "plan": plan,
            "results": results,
            "conversation_length": len(self.conversation_history),
        }

    async def autonomous_mode(self, goal: str, max_cycles: int = 10):
        """Run in autonomous mode towards a goal"""
        logger.info(f"🎯 Starting autonomous mode with goal: {goal}")

        for cycle in range(max_cycles):
            logger.info(f"🔄 Autonomous cycle {cycle + 1}/{max_cycles}")

            # Analyze current state
            analysis = await self.mcp_client.analyze_screen(
                focus=f"Progress towards goal: {goal}", include_actions=True
            )

            # Generate next action based on goal and current state
            action_prompt = f"""
Goal: {goal}
Current Analysis: {analysis}
Cycle: {cycle + 1}/{max_cycles}

What is the next single action to take towards the goal?
Respond with JSON: {{"tool": "name", "arguments": {{}}, "reasoning": "why"}}
"""

            response = ollama_client.generate_text(
                model=CONFIG.models.reasoning_model,
                prompt=action_prompt,
                temperature=0.4,
            )

            if response.success:
                try:
                    action_plan = json.loads(response.content)

                    # Execute the action
                    tool_name = action_plan.get("tool")
                    arguments = action_plan.get("arguments", {})
                    reasoning = action_plan.get("reasoning", "")

                    logger.info(f"💭 Reasoning: {reasoning}")
                    logger.info(f"⚡ Action: {tool_name} with {arguments}")

                    # Route to appropriate MCP tool
                    if hasattr(self.mcp_client, tool_name):
                        method = getattr(self.mcp_client, tool_name)
                        if tool_name == "type_text":
                            await method(arguments.get("text", ""))
                        elif tool_name == "key_press":
                            await method(arguments.get("key", ""))
                        elif tool_name == "click":
                            await method(arguments.get("x", 0), arguments.get("y", 0))
                        else:
                            await method(**arguments)

                    # Pause between cycles
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"Action execution failed: {e}")
                    continue
            else:
                logger.error(f"Action planning failed: {response.error}")
                continue

        logger.info("🏁 Autonomous mode completed")


async def main():
    """Main entry point for MCP enhanced agent"""
    agent = MCPEnhancedAgent()

    try:
        # Start the agent
        if not await agent.start():
            return

        print("\n🤖 MCP Enhanced AI Agent")
        print("=" * 50)
        print("Choose mode:")
        print("1. Process single request")
        print("2. Autonomous mode")
        print("3. Interactive mode")

        choice = input("Choice (1-3): ").strip()

        if choice == "1":
            request = input("Enter your request: ").strip()
            if request:
                result = await agent.process_user_request(request)
                print(f"\nResult: {json.dumps(result, indent=2)}")

        elif choice == "2":
            goal = input("Enter your goal: ").strip()
            if goal:
                await agent.autonomous_mode(goal)

        elif choice == "3":
            print("\nInteractive mode - type 'quit' to exit")
            while True:
                request = input("\nYour request: ").strip()
                if request.lower() in ["quit", "exit"]:
                    break
                if request:
                    result = await agent.process_user_request(request)
                    print(
                        f"✅ Completed: {result.get('plan', {}).get('reasoning', 'Done')}"
                    )

    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
