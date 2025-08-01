#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server for AI Agent Computer Use
Provides standardized computer use tools for AI models
"""

import json
import asyncio
import base64
from typing import Dict, Any, List

# MCP Server Protocol imports
try:
    from mcp import Server, McpError
    from mcp.server import NotificationOptions, InitializationOptions
    from mcp.server.models import (
        InitializeResult,
        ServerCapabilities,
        Tool,
        TextContent,
        ImageContent,
        EmbeddedResource,
    )
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
        TextResourceContents,
        ImageResourceContents,
    )

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

    # Fallback types for when MCP is not available
    class Server:
        def __init__(self, name: str, version: str):
            pass

    class McpError(Exception):
        pass


from config import CONFIG
from utils.logger import logger
from components.perceiver import Perceiver
from components.controller import Controller
from models.ollama_client import ollama_client


class MCPComputerUseServer:
    """MCP Server providing computer use capabilities"""

    def __init__(self):
        self.server_name = "mcp-computer-use-server"
        self.server_version = "1.0.0"
        self.perceiver = None
        self.controller = None
        self.last_screenshot = None
        self.last_context = None

        if MCP_AVAILABLE:
            self.server = Server(self.server_name, self.server_version)
            self._setup_mcp_handlers()
        else:
            logger.warning(
                "MCP library not available. Server will run in fallback mode."
            )
            self.server = None

    def _setup_mcp_handlers(self):
        """Setup MCP protocol handlers"""
        if not self.server:
            return

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available computer use tools"""
            return [
                Tool(
                    name="screenshot",
                    description="Take a screenshot of the current screen",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_analysis": {
                                "type": "boolean",
                                "description": "Whether to include AI analysis of the screenshot",
                                "default": True,
                            }
                        },
                    },
                ),
                Tool(
                    name="click",
                    description="Click at specified coordinates on the screen",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "X coordinate"},
                            "y": {"type": "integer", "description": "Y coordinate"},
                            "button": {
                                "type": "string",
                                "enum": ["left", "right", "middle"],
                                "default": "left",
                            },
                            "clicks": {"type": "integer", "default": 1},
                        },
                        "required": ["x", "y"],
                    },
                ),
                Tool(
                    name="type",
                    description="Type text at the current cursor position",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to type"}
                        },
                        "required": ["text"],
                    },
                ),
                Tool(
                    name="key_press",
                    description="Press keyboard keys or key combinations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "Key or key combination (e.g., 'Enter', 'ctrl+c', 'alt+tab')",
                            }
                        },
                        "required": ["key"],
                    },
                ),
                Tool(
                    name="scroll",
                    description="Scroll the screen in a specified direction",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "direction": {
                                "type": "string",
                                "enum": ["up", "down", "left", "right"],
                                "description": "Direction to scroll",
                            },
                            "clicks": {"type": "integer", "default": 3},
                            "x": {
                                "type": "integer",
                                "description": "X coordinate for scroll position",
                            },
                            "y": {
                                "type": "integer",
                                "description": "Y coordinate for scroll position",
                            },
                        },
                        "required": ["direction"],
                    },
                ),
                Tool(
                    name="drag",
                    description="Drag from one point to another",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_x": {
                                "type": "integer",
                                "description": "Starting X coordinate",
                            },
                            "start_y": {
                                "type": "integer",
                                "description": "Starting Y coordinate",
                            },
                            "end_x": {
                                "type": "integer",
                                "description": "Ending X coordinate",
                            },
                            "end_y": {
                                "type": "integer",
                                "description": "Ending Y coordinate",
                            },
                            "duration": {"type": "number", "default": 1.0},
                        },
                        "required": ["start_x", "start_y", "end_x", "end_y"],
                    },
                ),
                Tool(
                    name="get_screen_text",
                    description="Extract text from the screen using OCR",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "region": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "integer"},
                                    "y": {"type": "integer"},
                                    "width": {"type": "integer"},
                                    "height": {"type": "integer"},
                                },
                                "description": "Optional region to extract text from",
                            }
                        },
                    },
                ),
                Tool(
                    name="find_element",
                    description="Find UI elements on the screen",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "element_type": {
                                "type": "string",
                                "enum": [
                                    "button",
                                    "text_field",
                                    "link",
                                    "image",
                                    "icon",
                                    "menu",
                                ],
                                "description": "Type of element to find",
                            },
                            "text": {
                                "type": "string",
                                "description": "Text content to search for",
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the element",
                            },
                        },
                    },
                ),
                Tool(
                    name="analyze_screen",
                    description="Use AI to analyze and describe the current screen",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "focus": {
                                "type": "string",
                                "description": "Specific aspect to focus on in the analysis",
                            },
                            "include_actions": {
                                "type": "boolean",
                                "description": "Whether to suggest possible actions",
                                "default": True,
                            },
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[TextContent | ImageContent]:
            """Handle tool calls"""
            try:
                # Initialize components if not already done
                if not self.perceiver:
                    await self._initialize_components()

                # Route to appropriate handler
                if name == "screenshot":
                    return await self._handle_screenshot(arguments)
                elif name == "click":
                    return await self._handle_click(arguments)
                elif name == "type":
                    return await self._handle_type(arguments)
                elif name == "key_press":
                    return await self._handle_key_press(arguments)
                elif name == "scroll":
                    return await self._handle_scroll(arguments)
                elif name == "drag":
                    return await self._handle_drag(arguments)
                elif name == "get_screen_text":
                    return await self._handle_get_screen_text(arguments)
                elif name == "find_element":
                    return await self._handle_find_element(arguments)
                elif name == "analyze_screen":
                    return await self._handle_analyze_screen(arguments)
                else:
                    raise McpError(f"Unknown tool: {name}")

            except Exception as e:
                logger.error(f"Tool call failed: {name} - {e}")
                raise McpError(f"Tool execution failed: {str(e)}")

    async def _initialize_components(self):
        """Initialize perceiver and controller components"""
        try:
            self.perceiver = Perceiver()
            self.controller = Controller()

            self.perceiver.start()
            self.controller.start()

            logger.info("MCP Server components initialized")
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise McpError("Failed to initialize computer use components")

    async def _handle_screenshot(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent]:
        """Handle screenshot tool"""
        include_analysis = arguments.get("include_analysis", True)

        # Take screenshot and get context
        context = self.perceiver.perceive_screen()
        if not context:
            raise McpError("Failed to capture screenshot")

        self.last_context = context
        self.last_screenshot = context.screenshot_path

        # Read screenshot as base64
        with open(context.screenshot_path, "rb") as f:
            screenshot_data = base64.b64encode(f.read()).decode()

        results = [
            ImageContent(type="image", data=screenshot_data, mimeType="image/png")
        ]

        if include_analysis:
            analysis_text = f"""Screen Analysis:
- Resolution: {context.screen_resolution[0]}x{context.screen_resolution[1]}
- OCR Text Found: {len(context.ocr_text)} characters
- UI Elements Detected: {len(context.ui_elements)}
- Confidence Score: {context.confidence_score:.2f}

OCR Text Extract:
{context.ocr_text[:500]}{"..." if len(context.ocr_text) > 500 else ""}

UI Elements:
{json.dumps(context.ui_elements[:10], indent=2) if context.ui_elements else "None detected"}

Vision Analysis:
{context.vlm_description}
"""
            results.append(TextContent(type="text", text=analysis_text))

        return results

    async def _handle_click(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle click tool"""
        action = {
            "type": "click",
            "x": arguments["x"],
            "y": arguments["y"],
            "button": arguments.get("button", "left"),
            "clicks": arguments.get("clicks", 1),
        }

        result = self.controller.execute_action(action)

        return [
            TextContent(
                type="text",
                text=f"Click executed at ({action['x']}, {action['y']}) - {'Success' if result.success else 'Failed'}",
            )
        ]

    async def _handle_type(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle type tool"""
        action = {"type": "type", "text": arguments["text"]}

        result = self.controller.execute_action(action)

        return [
            TextContent(
                type="text",
                text=f"Text typed: '{arguments['text'][:50]}...' - {'Success' if result.success else 'Failed'}",
            )
        ]

    async def _handle_key_press(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle key press tool"""
        action = {"type": "key_press", "key": arguments["key"]}

        result = self.controller.execute_action(action)

        return [
            TextContent(
                type="text",
                text=f"Key pressed: '{arguments['key']}' - {'Success' if result.success else 'Failed'}",
            )
        ]

    async def _handle_scroll(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle scroll tool"""
        action = {
            "type": "scroll",
            "direction": arguments["direction"],
            "clicks": arguments.get("clicks", 3),
        }

        if "x" in arguments and "y" in arguments:
            action["x"] = arguments["x"]
            action["y"] = arguments["y"]

        result = self.controller.execute_action(action)

        return [
            TextContent(
                type="text",
                text=f"Scrolled {arguments['direction']} - {'Success' if result.success else 'Failed'}",
            )
        ]

    async def _handle_drag(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle drag tool"""
        action = {
            "type": "drag",
            "start_x": arguments["start_x"],
            "start_y": arguments["start_y"],
            "end_x": arguments["end_x"],
            "end_y": arguments["end_y"],
            "duration": arguments.get("duration", 1.0),
        }

        result = self.controller.execute_action(action)

        return [
            TextContent(
                type="text",
                text=f"Drag from ({action['start_x']}, {action['start_y']}) to ({action['end_x']}, {action['end_y']}) - {'Success' if result.success else 'Failed'}",
            )
        ]

    async def _handle_get_screen_text(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle get screen text tool"""
        if not self.last_context:
            # Take new screenshot if needed
            context = self.perceiver.perceive_screen()
            if not context:
                raise McpError("Failed to capture screen for text extraction")
            self.last_context = context

        text = self.last_context.ocr_text
        region = arguments.get("region")

        if region:
            # TODO: Implement region-specific OCR
            text = f"[Region OCR not implemented yet] Full screen text:\n{text}"

        return [TextContent(type="text", text=f"Screen text extracted:\n{text}")]

    async def _handle_find_element(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle find element tool"""
        if not self.last_context:
            context = self.perceiver.perceive_screen()
            if not context:
                raise McpError("Failed to capture screen for element detection")
            self.last_context = context

        element_type = arguments.get("element_type")
        text_query = arguments.get("text")
        description = arguments.get("description")

        # Search through detected UI elements
        found_elements = []
        for element in self.last_context.ui_elements:
            if element_type and element.get("type") != element_type:
                continue
            if text_query and text_query.lower() not in element.get("text", "").lower():
                continue
            found_elements.append(element)

        if found_elements:
            result_text = f"Found {len(found_elements)} matching elements:\n"
            for i, elem in enumerate(found_elements[:5]):  # Limit to 5 results
                result_text += f"{i + 1}. {elem}\n"
        else:
            result_text = f"No elements found matching criteria: type={element_type}, text={text_query}"

        return [TextContent(type="text", text=result_text)]

    async def _handle_analyze_screen(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle analyze screen tool"""
        focus = arguments.get("focus")
        include_actions = arguments.get("include_actions", True)

        if not self.last_context:
            context = self.perceiver.perceive_screen()
            if not context:
                raise McpError("Failed to capture screen for analysis")
            self.last_context = context

        # Use AI to analyze the screen
        analysis_prompt = f"""Analyze this desktop screen and provide insights.

Screen Information:
- Resolution: {self.last_context.screen_resolution}
- OCR Text: {self.last_context.ocr_text[:300]}...
- UI Elements: {len(self.last_context.ui_elements)} detected
- VLM Description: {self.last_context.vlm_description}

Focus: {focus if focus else "General analysis"}

Please provide:
1. What applications or windows are visible
2. What the user might be trying to do
3. Current state of the interface
{"4. Suggested actions the user could take" if include_actions else ""}
"""

        # Get AI analysis
        response = ollama_client.generate_text(
            model=CONFIG.models.reasoning_model, prompt=analysis_prompt, temperature=0.3
        )

        if response.success:
            analysis = response.content
        else:
            analysis = f"AI analysis failed: {response.error}"

        return [TextContent(type="text", text=analysis)]

    async def run_stdio(self):
        """Run the MCP server using stdio transport"""
        if not MCP_AVAILABLE:
            logger.error("MCP library not available. Cannot start server.")
            return

        logger.info(f"Starting {self.server_name} v{self.server_version}")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.server_name,
                    server_version=self.server_version,
                    capabilities=ServerCapabilities(tools={}),
                ),
            )

    def run_fallback_mode(self):
        """Run in fallback mode when MCP is not available"""
        logger.info("Running MCP Computer Use Server in fallback mode")
        logger.info("Available tools:")
        tools = [
            "screenshot",
            "click",
            "type",
            "key_press",
            "scroll",
            "drag",
            "get_screen_text",
            "find_element",
            "analyze_screen",
        ]
        for tool in tools:
            logger.info(f"  - {tool}")

        # In fallback mode, we could provide a simple JSON-RPC interface
        # or integrate directly with the existing agent
        logger.info("Use the main agent interfaces for computer use capabilities")


async def main():
    """Main entry point for MCP server"""
    server = MCPComputerUseServer()

    if MCP_AVAILABLE:
        await server.run_stdio()
    else:
        server.run_fallback_mode()


if __name__ == "__main__":
    asyncio.run(main())
