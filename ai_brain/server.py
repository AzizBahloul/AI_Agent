"""
Main AI orchestrator that coordinates all components
"""
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from ai_brain.models.ollama_client import OllamaClient
from ai_brain.models.task_planner import TaskPlanner
from ai_brain.vision.screen_capture import ScreenCapture
from ai_brain.agents import FileAgent, BrowserAgent, SystemAgent
from ai_brain.memory.session_manager import SessionManager
from ai_brain.safety.permission_manager import PermissionManager
from pydantic import BaseModel

logger = logging.getLogger("desktop-genie")

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DesktopGenie:
    def __init__(self):
        self.ollama = OllamaClient()
        self.task_planner = TaskPlanner(self.ollama)
        self.screen_capture = ScreenCapture()
        self.session_manager = SessionManager()
        self.permission_manager = PermissionManager()
        self.agents = {
            'file': FileAgent(),
            'browser': BrowserAgent(),
            'system': SystemAgent()
        }
        self.active_tasks = {}
        logger.info("Desktop Genie initialized")

# Initialize DesktopGenie instance
genie = DesktopGenie()

class CommandRequest(BaseModel):
    command: str
    session_id: str = None

import time

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = f"ws-{int(time.time())}"
    try:
        while True:
            data = await websocket.receive_text()
            await genie.process_command(data, session_id, websocket)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")


@app.post("/command")
async def handle_command(request: CommandRequest):
    session_id = request.session_id or f"cmd-{int(time.time())}"
    return await genie.process_command(request.command, session_id)


# Add process_command as a method of DesktopGenie
def _add_process_command_to_genie():
    async def process_command(self, command: str, session_id: str, websocket: WebSocket = None):
        session = self.session_manager.start_session(session_id, command)
        # Try to capture screen, but don't fail if it errors
        try:
            screenshot_path = self.screen_capture.capture_screen(session_id)
            session.add_context("screenshot", screenshot_path)
        except Exception as e:
            logger.warning(f"Screen capture failed: {e}")
            session.add_context("screenshot", None)

        # Try to generate task plan, but catch Ollama API errors
        try:
            plan = await self.task_planner.generate_plan(
                command, 
                session.context,
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"Task planning failed: {e}")
            return {"status": "error", "message": f"Task planning failed: {e}"}

        # Execute plan
        results = []
        # Handle plan structure: sometimes it's {"plan": {...}}, sometimes just {...}
        if isinstance(plan, dict) and 'plan' in plan:
            plan = plan['plan']
        
        steps = plan.get('steps') if isinstance(plan, dict) else getattr(plan, 'steps', None)
        if not steps or not isinstance(steps, list):
            logger.error(f"No valid steps found in plan: {plan}")
            return {"status": "error", "message": "No valid steps found in plan."}
        # Agent name mapping for LLM synonyms
        agent_name_map = {
            'user': 'system',
            'os': 'system',
            'filesystem': 'file',
            'fileagent': 'file',
            'systemagent': 'system',
            'browseragent': 'browser',
            'computer': 'system',
            'desktop': 'system',
        }
        for step in steps:
            # step is likely a dict, not an object
            agent_name = step.get('agent') if isinstance(step, dict) else getattr(step, 'agent', None)
            agent_name_key = agent_name.strip().lower() if agent_name else None
            # Map synonyms to actual agent keys
            mapped_agent_key = agent_name_map.get(agent_name_key, agent_name_key)
            # Make agent lookup case-insensitive
            agent = None
            if mapped_agent_key:
                for k, v in self.agents.items():
                    if k.lower() == mapped_agent_key:
                        agent = v
                        break
            if not agent:
                logger.warning(f"Agent '{agent_name}' (mapped: '{mapped_agent_key}') not found. Skipping step: {step}")
                continue
            action = step.get('action') if isinstance(step, dict) else getattr(step, 'action', None)
            parameters = step.get('parameters') if isinstance(step, dict) else getattr(step, 'parameters', None)
            # Check permissions
            if not self.permission_manager.check_permission(action, parameters):
                logger.warning(f"Permission denied for action {action}")
                continue
            # ...rest of your code for executing the plan...
    DesktopGenie.process_command = process_command

_add_process_command_to_genie()
