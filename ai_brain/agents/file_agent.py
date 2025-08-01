"""
File operations specialist with safety features
"""
import os
import shutil
import hashlib
import magic
import logging
import time
from pathlib import Path
from typing import Dict, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ai_brain.safety.action_validator import validate_file_operation

logger = logging.getLogger("desktop-genie")

class FileAgent:
    def __init__(self):
        self.file_type_detector = magic.Magic(mime=True)
        self.observer = Observer()
        self.watched_paths = {}
        logger.info("File agent initialized")

    async def execute(self, task: Dict, context: Dict, websocket) -> Dict:
        """Execute file operation task"""
        action = task.get("action")
        params = task.get("parameters", {})
        
        # Validate action
        if not validate_file_operation(action, params):
            return {"status": "denied", "reason": "Invalid operation"}
        
        try:
            # Dispatch to appropriate handler
            if action == "organize":
                result = await self.organize_files(
                    Path(params["directory"]), 
                    params.get("criteria", "type")
                )
            elif action == "find_duplicates":
                result = await self.find_duplicates(Path(params["directory"]))
            elif action == "bulk_rename":
                result = await self.bulk_rename(
                    Path(params["directory"]), 
                    params["pattern"]
                )
            elif action == "monitor":
                self.start_monitoring(
                    Path(params["directory"]), 
                    params["event_types"],
                    context.get("session_id")
                )
                result = {"status": "monitoring_started"}
            else:
                result = {"status": "unsupported_action"}
            
            result["action"] = action
            return result
        except Exception as e:
            logger.exception(f"File operation failed: {e}")
            return {"status": "error", "error": str(e)}

    async def organize_files(self, directory: Path, criteria: str) -> Dict:
        """Organize files by specified criteria"""
        if not directory.exists():
            return {"status": "error", "error": "Directory not found"}
        
        organized = {}
        for item in directory.iterdir():
            if item.is_file():
                # Get organization target
                if criteria == "type":
                    mime = self.file_type_detector.from_file(str(item))
                    category = mime.split('/')[0]  # e.g., image, video
                elif criteria == "extension":
                    category = item.suffix[1:] if item.suffix else "other"
                else:
                    category = "other"
                
                # Create category directory
                target_dir = directory / category
                target_dir.mkdir(exist_ok=True)
                
                # Move file
                new_path = target_dir / item.name
                if new_path.exists():
                    # Handle conflicts
                    base_name = item.stem
                    counter = 1
                    while new_path.exists():
                        new_path = target_dir / f"{base_name}_{counter}{item.suffix}"
                        counter += 1
                
                shutil.move(str(item), str(new_path))
                organized[str(item)] = str(new_path)
        
        return {
            "status": "success",
            "organized": organized,
            "context_update": {"directory_structure": self._scan_directory(directory)}
        }

    async def find_duplicates(self, directory: Path) -> Dict:
        """Find duplicate files in directory"""
        hashes = {}
        duplicates = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                path = Path(root) / file
                try:
                    file_hash = self._file_hash(path)
                    if file_hash in hashes:
                        duplicates.append((str(hashes[file_hash]), str(path)))
                    else:
                        hashes[file_hash] = path
                except OSError as e:
                    logger.warning(f"Skipping {path}: {e}")
        
        return {"status": "success", "duplicates": duplicates}

    def _file_hash(self, path: Path, block_size=65536) -> str:
        """Generate file hash"""
        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()

    async def bulk_rename(self, directory: Path, pattern: str) -> Dict:
        """Rename files in directory using pattern"""
        if not directory.exists():
            return {"status": "error", "error": "Directory not found"}
        
        renamed = {}
        for i, item in enumerate(directory.iterdir()):
            if item.is_file():
                new_name = pattern.format(index=i+1, name=item.stem, ext=item.suffix[1:])
                new_path = directory / new_name
                
                # Handle conflicts
                if new_path.exists():
                    base_name = new_path.stem
                    counter = 1
                    while new_path.exists():
                        new_path = directory / f"{base_name}_{counter}{new_path.suffix}"
                        counter += 1
                
                item.rename(new_path)
                renamed[str(item)] = str(new_path)
        
        return {"status": "success", "renamed": renamed}

    def start_monitoring(self, directory: Path, event_types: List[str], session_id: str):
        """Start monitoring directory for changes"""
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        class Handler(FileSystemEventHandler):
            def __init__(self, callback):
                self.callback = callback
            
            def on_any_event(self, event):
                if event.is_directory:
                    return
                self.callback(event)
        
        def callback(event):
            # event_data assigned but not used, so just log for now
            logging.debug(f"File event: {event.event_type} {event.src_path}")
        
        handler = Handler(callback)
        self.observer.schedule(handler, str(directory), recursive=True)
        if not self.observer.is_alive():
            self.observer.start()
        
        self.watched_paths[str(directory)] = handler

    def _scan_directory(self, directory: Path) -> Dict:
        """Scan directory and return structure"""
        structure = {"path": str(directory), "type": "directory", "children": []}
        
        for item in directory.iterdir():
            if item.is_dir():
                structure["children"].append(self._scan_directory(item))
            else:
                structure["children"].append({
                    "path": str(item),
                    "type": "file",
                    "size": item.stat().st_size
                })
        
        return structure
