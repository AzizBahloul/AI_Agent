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
import time

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

    async def process_command(self, command: str, session_id: str, websocket: WebSocket = None):
        # Start new session
        session = self.session_manager.start_session(session_id, command)
        
        # Capture current screen state
        screenshot_path = self.screen_capture.capture_screen(session_id)
        session.add_context("screenshot", screenshot_path)
        
        # Generate task plan
        plan = await self.task_planner.generate_plan(
            command, 
            session.context,
            session_id=session_id
        )
        
        # Execute plan
        results = []
        for step in plan.steps:
            agent = self.agents.get(step.agent)
            if not agent:
                logger.error(f"Agent {step.agent} not found")
                continue
                
            # Check permissions
            if not self.permission_manager.check_permission(step.action, step.parameters):
                logger.warning(f"Permission denied for: {step.action}")
                continue
                
            # Execute step
            try:
                result = await agent.execute(step, session.context, websocket)
                results.append(result)
                session.add_step(step, result)
                
                # Update context if needed
                if result.get('context_update'):
                    session.context.update(result['context_update'])
                    
            except Exception as e:
                logger.exception(f"Task execution failed: {e}")
                session.add_error(step, str(e))
        
        # Finalize session
        session.complete()
        return {
            "status": "completed",
            "session_id": session_id,
            "results": results
        }

# Initialize DesktopGenie instance
genie = DesktopGenie()

class CommandRequest(BaseModel):
    command: str
    session_id: str = None

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
