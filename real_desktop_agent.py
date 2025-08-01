#!/usr/bin/env python3
"""
REAL Desktop Control Agent - Actually interacts with your desktop
This version uses real screen capture and executes real actions
"""

import os
import time
import signal

# Force environment variable to allow screen capture
os.environ["DISPLAY"] = ":0"  # Try to use display

from utils.logger import logger
from models.ollama_client import ollama_client

# Import REAL components
from components.perceiver import Perceiver
from components.controller import Controller


def get_user_prompt():
    """Get user prompt once at the beginning"""
    try:
        print("\n" + "=" * 60)
        print("🖥️  REAL MCP AI Agent - Desktop Control Mode")
        print("=" * 60)
        print("⚠️  WARNING: This will control your REAL desktop!")
        print("   Press Ctrl+C anytime to stop immediately")
        print("=" * 60)
        print("Enter your automation request:")
        print("Examples:")
        print("  - 'Open Google Chrome'")
        print("  - 'Open file manager'")
        print("  - 'Click on Desktop'")
        print("  - 'Press Alt+Tab'")
        print("-" * 60)

        user_input = input("Your command: ").strip()

        if user_input:
            print(f"\n🎯 Will attempt: '{user_input}'")
            print("⚠️  Agent will try to execute this on your REAL desktop!")
            confirm = input("Continue? (y/N): ").strip().lower()
            if confirm in ["y", "yes"]:
                return user_input
            else:
                print("Cancelled by user")
                return None
        else:
            print("No command provided")
            return None

    except KeyboardInterrupt:
        print("\nCancelled by user")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


class RealDesktopAgent:
    """Agent that actually controls your desktop"""

    def __init__(self):
        self.perceiver = None
        self.controller = None
        self.running = False
        self.cycle_count = 0
        self.max_cycles = 5  # Limit for safety
        self.user_prompt = None
        self.last_search_term = None  # track last searched term

    def start(self):
        """Start the real desktop agent"""
        logger.info("🖥️  Starting REAL Desktop Control Agent")
        logger.info("=" * 60)

        # Check Ollama
        if not ollama_client.health_check():
            logger.error("❌ Ollama not available")
            return False

        logger.info(
            f"✅ Ollama connected: {len(ollama_client.available_models)} models"
        )

        try:
            # Initialize REAL components
            self.perceiver = Perceiver()
            self.controller = Controller()

            # Start components
            self.perceiver.start()
            self.controller.start()

            self.running = True
            logger.info("✅ Real desktop agent started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start real agent: {e}")
            return False

    def run(self):
        """Run the agent with real desktop control"""
        if not self.start():
            print("❌ Failed to start agent")
            return

        # Get user command
        self.user_prompt = get_user_prompt()
        if not self.user_prompt:
            print("No command to execute")
            self.stop()
            return
        # Refactor user prompt into ordered tasks for clarity
        steps = self.refactor_user_prompt(self.user_prompt)
        logger.info(f"🔄 Refactored user prompt into ordered tasks: {steps}")
        print("\n🔄 Refactored Steps:")
        for i, step in enumerate(steps, start=1):
            print(f"  {i}. {step}")
        print()
        logger.info(f"🎯 Executing user command: '{self.user_prompt}'")
        print("\n🚀 Starting execution in 3 seconds...")
        print("   Press Ctrl+C to abort!")

        try:
            # Give user time to abort
            for i in [3, 2, 1]:
                print(f"   Starting in {i}...")
                time.sleep(1)

            print("\n🎬 EXECUTING ON REAL DESKTOP!")

            # Execute based on user command
            success = self.execute_user_command(self.user_prompt)

            if success:
                print("\n✅ Command executed successfully!")
            else:
                print("\n❌ Command execution failed")

        except KeyboardInterrupt:
            print("\n🛑 Execution stopped by user")
        except Exception as e:
            print(f"\n❌ Execution error: {e}")
        finally:
            self.stop()

    def refactor_user_prompt(self, command: str) -> list[str]:
        """Use LLM to transform user command into an ordered list of atomic actions"""
        try:
            # Check command length and complexity to determine approach
            is_complex = len(command) > 100 or "," in command or " and " in command or " then " in command
            
            # Track if we're using a reduced prompt due to previous failures
            using_reduced_prompt = False
            
            # First approach - comprehensive refactoring with context and reasoning
            if is_complex:
                logger.info("🔄 Using comprehensive prompt for complex command")
                prompt = (
                    "Task: Refactor the following user command into a clear, step-by-step list of executable actions.\n\n"
                    "Guidelines:\n"
                    "1. Break complex tasks into atomic operations (each step should accomplish ONE specific thing)\n"
                    "2. Each step must be clear, specific, and unambiguous\n"
                    "3. Include waiting steps between actions that need time to complete\n"
                    "4. Handle website navigation comprehensively (address bar focus, URL typing, loading time)\n"
                    "5. Account for typos in the user's command\n"
                    "6. Ensure ALL parts of the command are included in the steps\n\n"
                    
                    "Examples of good refactoring:\n"
                    "* 'open chorme and serch for facbook and enter the webiste' should become:\n"
                    "  1. Open Google Chrome\n"
                    "  2. Wait for Chrome to load (3 seconds)\n"
                    "  3. Focus on the address bar (press Ctrl+L)\n"
                    "  4. Type 'facebook' in the address bar\n"
                    "  5. Press Enter to search\n"
                    "  6. Wait for search results to load (3 seconds)\n"
                    "  7. Look for and click on the Facebook result\n"
                    "  8. Wait for Facebook to load (3 seconds)\n\n"
                    
                    "* 'open chrome and visit youtube and search for cats' should become:\n"
                    "  1. Open Google Chrome\n"
                    "  2. Wait for Chrome to load (3 seconds)\n"
                    "  3. Focus on the address bar (press Ctrl+L)\n"
                    "  4. Type 'youtube.com' in the address bar\n"
                    "  5. Press Enter to navigate\n"
                    "  6. Wait for YouTube to load (3 seconds)\n"
                    "  7. Click on the YouTube search bar\n"
                    "  8. Type 'cats' in the search bar\n"
                    "  9. Press Enter to search\n"
                    "  10. Wait for search results to load (2 seconds)\n\n"
                    
                    f"USER COMMAND: \"{command}\"\n\n"
                    "STEP-BY-STEP ACTIONS (return numbered steps only, no additional text):"
                )
                
                # Use adaptive timeout based on command complexity
                command_timeout = 90 if len(command) > 150 else 60
                
                response = ollama_client.generate_text(
                    model="mistral:7b", prompt=prompt, max_tokens=400, temperature=0.2, timeout=command_timeout
                )
            else:
                # Use simplified prompt for simple commands to avoid timeouts
                logger.info("🔄 Using simplified prompt for basic command")
                prompt = (
                    f"Break this command into clear steps: \"{command}\"\n\n"
                    "Number each step (1., 2., etc). Be specific. Include waiting steps."
                )
                response = ollama_client.generate_text(
                    model="mistral:7b", prompt=prompt, max_tokens=300, temperature=0.2
                )
                using_reduced_prompt = True
            
            # Process response regardless of which prompt was used
            if response.success:
                # Check if the response indicates a simplified prompt was used
                if response.metadata and response.metadata.get('used_simplified_prompt'):
                    logger.info("ℹ️ Using results from simplified prompt due to timeout")
                    using_reduced_prompt = True
                
                lines = []
                for line in response.content.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        continue
                    # Extract step content, removing numbering
                    if stripped[0].isdigit():
                        parts = stripped.split('.', 1)
                        if len(parts) > 1:
                            lines.append(parts[1].strip())
                    elif not stripped.startswith(('#', '-', '*')):
                        lines.append(stripped)
                
                # Ensure the steps are meaningful and comprehensive
                if lines and len(set(lines)) >= 2:
                    logger.info(f"✅ LLM refactoring successful: {len(lines)} steps generated")
                    # Log the first few steps for debugging
                    for i, step in enumerate(lines[:3], 1):
                        logger.debug(f"Step {i}: {step}")
                    if len(lines) > 3:
                        logger.debug(f"...plus {len(lines) - 3} more steps")
                    return lines
            
            # If first attempt failed or produced insufficient results, try second approach
            # but skip if we were already using a reduced prompt due to complexity
            if not using_reduced_prompt:
                logger.warning("⚠️ Primary LLM refactoring failed, trying secondary approach...")
                
                # Second approach - simplify the prompt for better reliability
                backup_prompt = (
                    f"Break this command into clear, atomic steps: \"{command}\"\n\n"
                    "For browser-related tasks, include these steps:\n"
                    "- Open the browser\n"
                    "- Wait for it to load\n"
                    "- Focus the address bar (Ctrl+L)\n"
                    "- Type the website or search term\n"
                    "- Press Enter\n"
                    "- Wait for page to load\n"
                    "- Click on relevant results if needed\n\n"
                    "Number each step. Be specific. Focus on executable actions.\n"
                )
                
                response = ollama_client.generate_text(
                    model="mistral:7b", prompt=backup_prompt, max_tokens=300, temperature=0.1
                )
                
                if response.success:
                    lines = []
                    for line in response.content.splitlines():
                        stripped = line.strip()
                        if not stripped:
                            continue
                        # Extract step content, removing numbering
                        if stripped[0].isdigit():
                            parts = stripped.split('.', 1)
                            if len(parts) > 1:
                                lines.append(parts[1].strip())
                        elif not stripped.startswith(('#', '-', '*')):
                            lines.append(stripped)
                    
                    if lines and len(set(lines)) >= 2:
                        logger.info(f"✅ Secondary LLM refactoring successful: {len(lines)} steps")
                        return lines
            
            logger.warning("⚠️ LLM refactoring attempts failed, using rule-based fallback")
            
        except Exception as e:
            logger.warning(f"❌ Prompt refactor failed: {e}. Using fallback parsing.")
        
        # Enhanced fallback: rule-based parsing for complex commands
        logger.info("🔄 Using rule-based command parsing...")
        steps = []
        cmd_lower = command.lower()
        
        # Fix common typos in the command
        typo_fixes = {
            'googel': 'google', 'gogle': 'google', 'googl': 'google',
            'serch': 'search', 'serach': 'search', 'sreach': 'search', 'srch': 'search',
            'webiste': 'website', 'websit': 'website', 'webste': 'website',
            'facbook': 'facebook', 'fb': 'facebook', 'faecbook': 'facebook',
            'youutbe': 'youtube', 'ytube': 'youtube', 'utube': 'youtube',
            'instgram': 'instagram', 'insta': 'instagram',
            'tweeter': 'twitter', 'twiter': 'twitter'
        }
        
        for typo, correction in typo_fixes.items():
            cmd_lower = cmd_lower.replace(typo, correction)
        
        # Extract actions based on common patterns
        if 'open' in cmd_lower:
            if 'chrome' in cmd_lower or 'browser' in cmd_lower:
                steps.append('Open Google Chrome')
                steps.append('Wait for Chrome to load (3 seconds)')
        
        # Handle website navigation
        site_matches = [
            ('facebook', 'facebook.com'), ('twitter', 'twitter.com'), 
            ('youtube', 'youtube.com'), ('instagram', 'instagram.com'),
            ('amazon', 'amazon.com'), ('reddit', 'reddit.com'),
            ('wikipedia', 'wikipedia.org'), ('linkedin', 'linkedin.com'),
            ('github', 'github.com'), ('netflix', 'netflix.com')
        ]
        
        direct_site_visit = False
        for site_keyword, site_domain in site_matches:
            if f"visit {site_keyword}" in cmd_lower or f"go to {site_keyword}" in cmd_lower:
                if not any(s in steps for s in ['Open Google Chrome', 'Wait for Chrome']):
                    steps.append('Open Google Chrome')
                    steps.append('Wait for Chrome to load (3 seconds)')
                steps.append('Focus on the address bar (press Ctrl+L)')
                steps.append(f"Type '{site_domain}' in the address bar")
                steps.append('Press Enter to navigate')
                steps.append(f"Wait for {site_keyword} to load (3 seconds)")
                direct_site_visit = True
                break
        
        # Handle search operations if not directly visiting a site
        if not direct_site_visit and ('search' in cmd_lower or 'find' in cmd_lower or 'look up' in cmd_lower):
            search_term = self.extract_search_term(command)
            if not any(s in steps for s in ['Focus on the address bar', 'press Ctrl+L']):
                steps.append('Focus on the address bar (press Ctrl+L)')
            steps.append(f"Type '{search_term}' in the search bar")
            steps.append('Press Enter to search')
            steps.append('Wait for search results to load (3 seconds)')
        
        # Handle result selection/clicking
        if any(term in cmd_lower for term in ['enter', 'visit', 'go to', 'click', 'access', 'open website', 'first result']):
            for site in ['facebook', 'twitter', 'youtube', 'instagram', 'amazon', 'reddit', 'github']:
                if site in cmd_lower:
                    steps.append(f"Look for and click on the {site} result")
                    steps.append(f"Wait for {site} to load (3 seconds)")
                    break
            else:
                if any(term in cmd_lower for term in ['first', 'top', 'result', 'website']):
                    steps.append("Click on the first search result")
                    steps.append("Wait for the page to load (3 seconds)")
        
        # If we still couldn't generate steps, fall back to simple splitting
        if not steps:
            logger.warning("⚠️ Rule-based parsing found no patterns, using simple split")
            sep = ' and ' if ' and ' in cmd_lower else ' then ' if ' then ' in cmd_lower else None
            if sep:
                steps = [c.strip() for c in cmd_lower.split(sep) if c.strip()]
            else:
                steps = [command]  # Just use the whole command as one step
        
        logger.info(f"🔄 Rule-based parsing generated {len(steps)} steps")
        return steps

    def execute_user_command(self, command):
        """Execute user command with real actions - uses refactored steps with progress tracking"""
        # Import the task tracker
        try:
            from utils.task_tracker import task_tracker
        except ImportError:
            logger.warning("⚠️ Task tracker not available, proceeding without progress tracking")
            task_tracker = None
            
        # Get ordered task list with improved refactoring
        steps = self.refactor_user_prompt(command)
        if not steps:
            logger.error("❌ Failed to refactor command into steps")
            return False
            
        logger.info(f"🔍 Refactored into {len(steps)} steps:")
        for i, step in enumerate(steps, 1):
            logger.info(f"  {i}. {step}")
            
        print("\n📋 Execution Plan:")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")
        print("\n")
        
        # Start task tracking if available
        if task_tracker:
            session_id = task_tracker.start_new_task(command, steps)
            logger.info(f"📊 Started tracking session: {session_id}")
        
        # Track progress
        total_steps = len(steps)
        successful_steps = 0
        failed_steps = 0
        progress_bar_length = 30
        max_retries = 2  # Allow retries for failed steps
        start_time = time.time()
        
        # Execute each step in sequence
        for idx, step in enumerate(steps, start=1):
            # Show progress
            percent = idx / total_steps
            filled_length = int(progress_bar_length * percent)
            progress_bar = "■" * filled_length + "□" * (progress_bar_length - filled_length)
            elapsed = time.time() - start_time
            logger.info(f"[{progress_bar}] {idx}/{total_steps} ({percent:.1%}) • {elapsed:.1f}s elapsed")
            
            # Log current step with clear indication of progress
            step_start_time = time.time()
            logger.info(f"🔄 Executing Step {idx}/{total_steps}: {step}")
            print(f"\n🔄 Step {idx}/{total_steps}: {step}")
            
            # Execute step with retry capability
            success = False
            retry_count = 0
            
            while not success and retry_count <= max_retries:
                if retry_count > 0:
                    logger.warning(f"⚠️ Retrying step {idx} (attempt {retry_count+1}/{max_retries+1})...")
                    print(f"⚠️ Retrying... (attempt {retry_count+1})")
                    time.sleep(1)  # Brief pause before retry
                
                # Execute the step with the complex handler
                success = self.handle_complex_open_command(step)
                
                if not success:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(f"❌ Failed step {idx} after {max_retries+1} attempts: {step}")
                        print(f"❌ Failed: {step}")
                        failed_steps += 1
                        
                        # Update task tracker
                        if task_tracker:
                            task_tracker.mark_step_complete(idx-1, step, success=False)
                        
                        # For critical failures, abort the whole process
                        if idx <= 2 or idx >= total_steps - 1:  # First, second, or last steps are critical
                            logger.error("❌ Critical step failed - aborting execution")
                            print("❌ Critical step failed - stopping execution")
                            
                            # Complete task tracking with failure
                            if task_tracker:
                                summary = task_tracker.complete_task(success=False)
                                logger.info("📊 Task summary: {}".format(summary))
                            
                            return False
                        
                        # For non-critical failures in the middle, we can try to continue
                        logger.warning("⚠️ Non-critical step failed - attempting to continue...")
                        print("⚠️ Attempting to continue with next step...")
                        break
                else:
                    successful_steps += 1
                    step_duration = time.time() - step_start_time
                    print(f"✅ Completed: {step} ({step_duration:.1f}s)")
                    
                    # Update task tracker
                    if task_tracker:
                        task_tracker.mark_step_complete(idx-1, step, success=True)
            
            # Show overall progress if task tracker is available
            if task_tracker and idx < total_steps:
                progress_info = task_tracker.get_formatted_progress()
                print(f"\n{progress_info}")
            
            # Additional wait between steps for stability
            time.sleep(1)
        
        # Report completion status
        if successful_steps == total_steps:
            logger.info("✅ All {} steps completed successfully!".format(total_steps))
            print(f"\n✅ Success! Completed all {total_steps} steps.")
            
            # Complete task tracking with success
            if task_tracker:
                summary = task_tracker.complete_task(success=True)
                logger.info("📊 Task summary: {}".format(summary))
                
                # Calculate statistics
                total_time = time.time() - start_time
                avg_time_per_step = total_time / total_steps
                print(f"\n📊 Statistics:")
                print(f"   - Total time: {total_time:.2f} seconds")
                print(f"   - Steps: {successful_steps} completed, {failed_steps} failed")
                print(f"   - Average time per step: {avg_time_per_step:.2f} seconds")
                
            return True
        else:
            completion_rate = successful_steps / total_steps
            logger.info("⚠️ Partial completion: {}/{} steps ({:.1%})".format(successful_steps, total_steps, completion_rate))
            print(f"\n⚠️ Partial completion: {successful_steps}/{total_steps} steps ({completion_rate:.1%})")
            
            # Complete task tracking with partial success
            if task_tracker:
                summary = task_tracker.complete_task(success=completion_rate >= 0.75)
                logger.info("📊 Task summary: {}".format(summary))
            
            # Consider it successful if we completed at least 75% of steps
            return completion_rate >= 0.75

    def handle_complex_open_command(self, command):
        """Handle complex multi-step commands, normalizing fillers and typos"""
        try:
            # Normalize typos
            cmd = command.lower()
            typo_map = {
                'serch': 'search',
                'serach': 'search',
                'sreach': 'search',
                'webiste': 'website',
                'googel': 'google'
            }
            for w, r in typo_map.items():
                cmd = cmd.replace(w, r)
            logger.info(f"🔄 Handling complex command: {command}")
            # Split on conjunctions 'and' or 'then'
            parts = []
            for sep in [' and ', ' then ']:
                for p in cmd.split(sep):
                    parts.append(p.strip())
            # Remove empty and duplicates while preserving order
            seen = set()
            steps = []
            for part in parts:
                if part and part not in seen:
                    seen.add(part)
                    steps.append(part)
            # Execute each step with dedicated handlers
            for idx, part in enumerate(steps):
                step_no = idx + 1
                # Remove filler phrases one by one
                clean = part
                fillers = ["i want you to ", "please ", "kindly ", "could you "]
                for filler in fillers:
                    if clean.startswith(filler):
                        clean = clean[len(filler):].strip()
                logger.info(f"🔄 Step {step_no}/{len(steps)}: {clean}")
                success = False
                # Opening applications
                if 'open' in clean and ('chrome' in clean or 'browser' in clean):
                    success = self.open_application('google-chrome')
                # Search actions
                elif 'search' in clean or 'find' in clean or 'look up' in clean:
                    term = self.extract_search_term(clean)
                    success = self.search_in_current_context(term, clean)
                # Navigate to website or click first result
                elif 'enter' in clean or 'visit' in clean or 'website' in clean:
                    success = self.navigate_to_website(clean)
                else:
                    # Fallback to intelligent execution
                    success = self.try_intelligent_execution(clean)
                if not success:
                    logger.error(f"❌ Step {step_no} failed: {clean}")
                    return False
                # Pause and capture screenshot for verification
                time.sleep(1)
                try:
                    ctx = self.perceiver.perceive_screen()
                    if ctx and hasattr(ctx, 'image'):
                        timestamp = int(time.time())
                        filename = f"step_{step_no}_{timestamp}.png"
                        ctx.image.save(filename)
                        logger.info(f"📸 Screenshot captured after step {step_no}: {filename}")
                except Exception as sk:
                    logger.warning(f"⚠️ Screenshot after step {step_no} failed: {sk}")
                time.sleep(1)
            logger.info("✅ All steps completed successfully!")
            return True
        except Exception as e:
            logger.error(f"Complex command handling failed: {e}")
            return False

    def execute_simple_command(self, command_part):
        """Execute a simple command part"""
        if "chrome" in command_part or "browser" in command_part:
            return self.open_application("google-chrome")
        elif "file manager" in command_part or "files" in command_part:
            return self.open_application("nautilus")
        elif "terminal" in command_part:
            return self.open_application("gnome-terminal")
        else:
            # Try intelligent execution for unknown simple commands
            return self.try_intelligent_execution(command_part)

    def execute_followup_action(self, action_part, full_command):
        """Execute a followup action after opening an application"""
        # website navigation in follow-up
        if "website" in action_part or "site" in action_part:
            logger.info(f"🎯 Follow-up navigate: {action_part}")
            return self.navigate_to_website(action_part)

        if "search" in action_part or "find" in action_part:
            # Extract search term from the full command context
            search_term = self.extract_search_term(full_command)
            if search_term:
                return self.search_in_current_context(search_term, action_part)

        # Use intelligent execution for other followup actions
        return self.try_intelligent_execution(action_part)

    def open_chrome_and_search(self, command):
        """Open Chrome and perform a search with optional result navigation"""
        try:
            # Step 1: Open Chrome
            logger.info("🚀 Step 1: Opening Google Chrome...")
            if not self.open_application("google-chrome"):
                logger.error("Failed to open Chrome")
                return False

            # Wait for Chrome to fully load
            logger.info("⏳ Waiting for Chrome to load...")
            time.sleep(4)
            # Screenshot after opening Chrome
            try:
                ctx1 = self.perceiver.perceive_screen()
                filename1 = f"screenshot_step1_open_{int(time.time())}.png"
                ctx1.image.save(filename1)
                logger.info(f"📸 Screenshot saved: {filename1}")
            except Exception:
                logger.warning("⚠️ Could not capture screenshot after opening Chrome")

            # Step 2: Extract search term from command
            search_term = self.extract_search_term(command)
            if not search_term:
                logger.error("Could not extract search term")
                return False

            logger.info(f"🔍 Step 2: Searching for '{search_term}'...")

            # Step 3: Focus on address bar (Ctrl+L)
            logger.info("📍 Focusing on address bar...")
            if not self.press_key("ctrl+l"):
                logger.error("Failed to focus address bar")
                return False

            time.sleep(1)
            
            # Clear any existing content (Ctrl+A then Delete)
            logger.info("🧹 Clearing address bar...")
            if not self.press_key("ctrl+a"):
                logger.error("Failed to select all text")
                return False
            time.sleep(0.5)
            # Screenshot after clearing address bar
            try:
                ctx2 = self.perceiver.perceive_screen()
                filename2 = f"screenshot_step2_clear_{int(time.time())}.png"
                ctx2.image.save(filename2)
                logger.info(f"📸 Screenshot saved: {filename2}")
            except Exception:
                logger.warning("⚠️ Could not capture screenshot after clearing bar")

            # Step 4: Type search query
            search_query = (
                f"https://www.google.com/search?q={search_term.replace(' ', '+')}"
            )
            logger.info(f"⌨️  Typing search URL: {search_query[:50]}...")
            if not self.type_text(search_query):
                logger.error("Failed to type search query")
                return False
            # Screenshot after typing query
            try:
                ctx3 = self.perceiver.perceive_screen()
                filename3 = f"screenshot_step3_type_{int(time.time())}.png"
                ctx3.image.save(filename3)
                logger.info(f"📸 Screenshot saved: {filename3}")
            except Exception:
                logger.warning("⚠️ Could not capture screenshot after typing query")

            time.sleep(1)

            # Step 5: Press Enter
            logger.info("⏎ Pressing Enter to search...")
            if not self.press_key("Return"):
                logger.error("Failed to press Enter")
                return False

            # Wait for search results to load
            logger.info("⏳ Waiting for search results...")
            time.sleep(4)

            # Capture screenshot for verification
            try:
                img_ctx = self.perceiver.perceive_screen()
                if img_ctx and hasattr(img_ctx, 'image'):
                    ts = int(time.time())
                    fname = f"search_results_{ts}.png"
                    img_ctx.image.save(fname)
                    logger.info(f"📸 Screenshot after search: {fname}")
            except Exception as se:
                logger.warning(f"⚠️ Screenshot after search failed: {se}")

            # Step 6: Check if user wants to enter/click first result
            command_lower = command.lower()
            if any(phrase in command_lower for phrase in [
                "enter the first", "click the first", "open the first", 
                "go to the first", "visit the first", "access the first",
                "enter the forst", "click the forst", "open the forst",  # Handle typos
                "enter first", "click first", "open first",  # Without "the"
                "first page", "first result", "first link",  # Alternative phrasing
                "enter the facebook website", "enter facebook", "go to facebook",  # Specific to Facebook
                "visit facebook", "access facebook", "open facebook website",
                "enter the website", "go to the website", "visit the website"  # General website access
            ]):
                logger.info("🎯 Step 6: Clicking on first search result...")
                result = self.click_first_search_result()
                # Screenshot after click
                try:
                    ctx5 = self.perceiver.perceive_screen()
                    filename5 = f"screenshot_step5_click_{int(time.time())}.png"
                    ctx5.image.save(filename5)
                    logger.info(f"📸 Screenshot saved: {filename5}")
                except Exception:
                    logger.warning("⚠️ Could not capture screenshot after clicking result")
                return result

            logger.info(
                f"✅ Successfully opened Chrome and searched for '{search_term}'!"
            )
            return True

        except Exception as e:
            logger.error(f"Chrome and search failed: {e}")
            return False

    def click_first_search_result(self):
        """Click on the first search result with enhanced reliability"""
        try:
            logger.info("🔍 Attempting to click on first search result...")
            max_attempts = 3
            
            # First attempt: Take screenshot and use AI analysis for precise clicking
            for attempt in range(1, max_attempts + 1):
                logger.info(f"🔄 Attempt {attempt}/{max_attempts} to find search result...")
                
                # Try to take screenshot to analyze search results
                context = self.perceiver.perceive_screen()
                
                if context and context.ocr_text:
                    logger.info("📸 Screen captured, analyzing content...")
                    
                    # Save screenshot for debugging
                    try:
                        if hasattr(context, 'image'):
                            timestamp = int(time.time())
                            filename = f"search_results_analysis_{timestamp}.png"
                            context.image.save(filename)
                            logger.info(f"📸 Search results screenshot saved: {filename}")
                    except Exception as se:
                        logger.warning(f"⚠️ Failed to save search results screenshot: {se}")
                    
                    # Use AI with improved prompt to find the first search result
                    prompt = f"""
Analyzing a Google search results page to find the FIRST organic search result (not an ad).

OCR text from the page (first 600 chars): {context.ocr_text[:600]}...

IMPORTANT INSTRUCTIONS:
1. Look for blue link titles that are part of the main search results
2. First search results are usually 250-400 pixels from the top of the page
3. Avoid clicking on:
   - "Ad" or "Sponsored" results at the top
   - Navigation elements or Google logo
   - Search filters or tabs
4. The main organic results are typically left-aligned

Find the X,Y coordinates to click on the FIRST NON-AD search result link.
Respond ONLY with: click <x> <y>
Where x,y are the pixel coordinates (e.g., "click 400 300")
"""

                    response = ollama_client.generate_text(
                        model="mistral:7b", 
                        prompt=prompt, 
                        max_tokens=30,
                        temperature=0.2  # Lower temperature for more deterministic response
                    )

                    if response.success and "click" in response.content:
                        ai_action = response.content.strip()
                        logger.info(f"🤖 AI analysis found result: {ai_action}")
                        
                        # Extract coordinates for verification
                        try:
                            parts = ai_action.split()
                            x, y = int(parts[1]), int(parts[2])
                            
                            # Sanity check on coordinates
                            if 100 < x < 800 and 150 < y < 600:
                                logger.info(f"✓ Coordinates look reasonable: ({x}, {y})")
                                
                                # Execute the click
                                if self.execute_ai_action(ai_action):
                                    logger.info("✅ Successfully clicked first search result!")
                                    
                                    # Wait and verify page load
                                    logger.info("⏳ Waiting for page to load...")
                                    time.sleep(4)
                                    
                                    # Take verification screenshot
                                    try:
                                        after_ctx = self.perceiver.perceive_screen()
                                        if hasattr(after_ctx, 'image'):
                                            ts = int(time.time())
                                            after_fname = f"after_click_result_{ts}.png"
                                            after_ctx.image.save(after_fname)
                                            logger.info(f"📸 Post-click screenshot: {after_fname}")
                                    except Exception as ae:
                                        logger.warning(f"⚠️ Post-click screenshot failed: {ae}")
                                    
                                    return True
                            else:
                                logger.warning(f"⚠️ AI suggested unusual coordinates: ({x}, {y}), trying next method")
                        except (ValueError, IndexError) as e:
                            logger.warning(f"⚠️ Could not parse AI coordinates: {e}")
                
                # Brief pause before next attempt
                time.sleep(1)
            
            # Second approach: Search for common site-specific text in the page
            logger.info("🔎 Using text search approach to find result...")
            common_sites = ["facebook", "twitter", "youtube", "instagram", "linkedin", "github", "amazon", 
                           "reddit", "wikipedia", "netflix", "microsoft", "apple"]
            
            if context and context.ocr_text:
                for site in common_sites:
                    if site in context.ocr_text.lower():
                        logger.info(f"📌 Found '{site}' text in search results")
                        # Use AI to find this specific text
                        site_prompt = f"""
Looking at a Google search results page. Find the coordinates to click on the search result that contains the text "{site}".

OCR text contains: {context.ocr_text[:500]}...

Respond with only: click <x> <y>
Where x,y are the coordinates where "{site}" appears in a clickable result.
"""
                        site_response = ollama_client.generate_text(
                            model="mistral:7b", prompt=site_prompt, max_tokens=30
                        )
                        
                        if site_response.success and "click" in site_response.content:
                            site_action = site_response.content.strip()
                            logger.info(f"🤖 AI found {site} result: {site_action}")
                            
                            if self.execute_ai_action(site_action):
                                logger.info(f"✅ Successfully clicked on {site} result!")
                                time.sleep(3)
                                return True
            
            # Third approach: Use expanded fallback locations with more variations
            logger.info("🎯 Using expanded fallback click locations...")
            
            # Expanded set of fallback locations covering more of the page
            fallback_locations = [
                {"x": 400, "y": 300, "desc": "Center-left typical result location"},
                {"x": 350, "y": 270, "desc": "Slightly higher result location"},
                {"x": 450, "y": 330, "desc": "Slightly lower result location"},
                {"x": 300, "y": 290, "desc": "Further left result location"},
                {"x": 400, "y": 250, "desc": "Higher result for compact layouts"},
                {"x": 400, "y": 350, "desc": "Lower result when ads present"},
                {"x": 500, "y": 300, "desc": "Further right result location"},
                {"x": 400, "y": 400, "desc": "Much lower result location"}
            ]
            
            # Try each location with a short pause between attempts
            for i, location in enumerate(fallback_locations):
                logger.info(f"🎯 Trying fallback location {i+1}/{len(fallback_locations)}: {location['desc']}")
                action = {"type": "click", "x": location["x"], "y": location["y"]}
                result = self.controller.execute_action(action)
                
                if result.success:
                    logger.info(f"✅ Clicked using fallback location {i+1}!")
                    time.sleep(4)  # Longer wait to ensure page loads
                    
                    # Take verification screenshot
                    try:
                        verify_ctx = self.perceiver.perceive_screen()
                        if hasattr(verify_ctx, 'image'):
                            ts = int(time.time())
                            verify_fname = f"verify_click_{ts}.png"
                            verify_ctx.image.save(verify_fname)
                            logger.info(f"📸 Verification screenshot: {verify_fname}")
                    except Exception:
                        logger.warning(f"⚠️ Verification screenshot failed")
                    
                    return True
                else:
                    logger.warning(f"⚠️ Fallback location {i+1} failed")
                    time.sleep(0.8)  # Brief pause before trying next location
            
            # Fourth approach: Try Tab + Enter method (works in many browsers)
            logger.info("⌨️ Trying Tab + Enter approach...")
            
            # Press Tab to navigate to first result, then Enter to click it
            if self.press_key("Tab") and self.press_key("Tab"):
                time.sleep(1)
                if self.press_key("Return"):
                    logger.info("⌨️ Used Tab + Enter to access first result")
                    time.sleep(4)
                    return True
            
            logger.error("❌ All result-clicking methods failed")
            return False
        
        except Exception as e:
            logger.error(f"❌ Failed to click first search result: {e}")
            return False

        except Exception as e:
            logger.error(f"Failed to click first search result: {e}")
            return False

    def extract_search_term(self, command):
        """Extract search term from command, handling complex multi-step commands"""
        command_lower = command.lower()

        # Clean up common multi-step phrases that aren't part of the search term
        clean_command = command_lower
        cleanup_phrases = [
            " and enter the first page", " and click the first", " and open the first",
            " and go to the first", " and visit the first", " and access the first",
            " you find", " result", " page you find", " link you find"
        ]
        
        for phrase in cleanup_phrases:
            clean_command = clean_command.replace(phrase, "")

        # Look for "search for X" pattern
        if "search for " in clean_command:
            start = clean_command.find("search for ") + len("search for ")
            end_pos = len(clean_command)
            # Stop at common connectors
            for connector in [" and ", " then ", " after "]:
                if connector in clean_command[start:]:
                    end_pos = start + clean_command[start:].find(connector)
                    break
            search_term = command[clean_command.find("search for ") + len("search for "):end_pos].strip()
            return search_term

        # Look for "find X" pattern
        elif "find " in clean_command:
            start = clean_command.find("find ") + len("find ")
            end_pos = len(clean_command)
            for connector in [" and ", " then ", " after "]:
                if connector in clean_command[start:]:
                    end_pos = start + clean_command[start:].find(connector)
                    break
            search_term = command[clean_command.find("find ") + len("find "):end_pos].strip()
            return search_term

        # Look for "look up X" pattern
        elif "look up " in clean_command:
            start = clean_command.find("look up ") + len("look up ")
            end_pos = len(clean_command)
            for connector in [" and ", " then ", " after "]:
                if connector in clean_command[start:]:
                    end_pos = start + clean_command[start:].find(connector)
                    break
            search_term = command[clean_command.find("look up ") + len("look up "):end_pos].strip()
            return search_term

        # Look for keywords at the end
        keywords = [
            "facebook", "google", "youtube", "github", "stackoverflow", "reddit",
            "wikipedia", "twitter", "instagram", "linkedin", "amazon", "netflix"
        ]
        for keyword in keywords:
            if keyword in clean_command:
                return keyword

        # Fallback: use AI to extract search term
        return self.ai_extract_search_term(command)

    def ai_extract_search_term(self, command):
        """Use AI to extract search term from command"""
        try:
            prompt = f"""
Extract the search term from this command: "{command}"

Examples:
- "open chrome and search for facebook" -> "facebook"
- "browse to youtube" -> "youtube"
- "look up python tutorials" -> "python tutorials"
- "find information about artificial intelligence" -> "artificial intelligence"

Just respond with the search term, nothing else.
"""

            response = ollama_client.generate_text(
                model="mistral:7b", prompt=prompt, max_tokens=20
            )

            if response.success:
                search_term = response.content.strip().strip("\"'")
                logger.info(f"🤖 AI extracted search term: '{search_term}'")
                return search_term

        except Exception as e:
            logger.error(f"AI search term extraction failed: {e}")

        return "facebook"  # Fallback default

    def try_intelligent_execution(self, command):
        """Try to intelligently execute unknown commands"""
        try:
            logger.info("🧠 Using AI to interpret command...")

            # Take screenshot first
            context = self.perceiver.perceive_screen()
            if not context:
                logger.warning("No screen context available")
                return False

            # Ask AI what to do with more context about multi-step commands
            prompt = f"""
User command: "{command}"

Current screen has:
- OCR text: {context.ocr_text[:200]}...
- UI elements: {len(context.ui_elements)} detected

This could be a multi-step command. Suggest the NEXT action to take:
- click <x> <y> (click coordinates)
- key_press <key> (press key/combo like 'ctrl+l', 'alt+tab', 'Return')
- type <text> (type text)
- app <name> (open application)
- search <term> (search for something)

If this is a search command and Chrome is already open, suggest focusing address bar with 'key_press ctrl+l'

Respond with just the action, nothing else.
"""

            response = ollama_client.generate_text(
                model="mistral:7b", prompt=prompt, max_tokens=50
            )

            if response.success:
                ai_action = response.content.strip()
                logger.info(f"🤖 AI suggested: {ai_action}")

                # Parse and execute AI suggestion
                return self.execute_ai_action(ai_action)
            else:
                logger.error("AI reasoning failed")
                return False

        except Exception as e:
            logger.error(f"Intelligent execution failed: {e}")
            return False

    def execute_ai_action(self, ai_action):
        """Execute action suggested by AI"""
        try:
            parts = ai_action.split()
            if not parts:
                return False

            action_type = parts[0].lower()

            if action_type == "click" and len(parts) >= 3:
                x, y = int(parts[1]), int(parts[2])
                action = {"type": "click", "x": x, "y": y}
                return self.controller.execute_action(action).success

            elif action_type == "key_press" and len(parts) >= 2:
                key = "+".join(parts[1:])  # Handle multi-part keys like ctrl+l
                action = {"type": "key_press", "key": key}
                return self.controller.execute_action(action).success

            elif action_type == "type" and len(parts) >= 2:
                text = " ".join(parts[1:])
                action = {"type": "type", "text": text}
                return self.controller.execute_action(action).success

            elif action_type == "app" and len(parts) >= 2:
                app_name = parts[1]
                return self.open_application(app_name)

            elif action_type == "search" and len(parts) >= 2:
                search_term = " ".join(parts[1:])
                # Try to search in current browser
                return self.search_in_browser(search_term)

            else:
                logger.warning(f"Unknown AI action format: {ai_action}")
                return False

        except Exception as e:
            logger.error(f"AI action execution failed: {e}")
            return False

    def search_in_current_context(self, search_term, action_part):
        """Search in the currently open application context"""
        try:
            logger.info(f"🔍 Searching for '{search_term}' in current context...")
            
            # Check if this includes clicking first result
            should_click_first = any(phrase in action_part.lower() for phrase in [
                "enter the first", "click the first", "open the first", 
                "go to the first", "visit the first", "access the first",
                "enter first", "click first", "open first",
                "enter the ", "visit the ", "go to the ",  # General website access indicators
                "enter facebook", "go to facebook", "visit facebook"  # Specific site indicators
            ])
            
            # Focus address bar and search
            logger.info("⌨️ Pressing Ctrl+L to focus address bar...")
            if not self.press_key("ctrl+l"):
                logger.error("Failed to focus address bar")
                # Try Alt+D as an alternate way to focus the address bar
                logger.info("⌨️ Trying Alt+D as alternate address bar shortcut...")
                if not self.press_key("alt+d"):
                    logger.error("Failed to focus address bar with Alt+D")
                    return False
            
            time.sleep(1.5)  # Longer pause to ensure address bar is focused
            
            # Clear address bar (Ctrl+A to select all text, then Delete)
            logger.info("⌨️ Clearing address bar with Ctrl+A and Delete...")
            if not self.press_key("ctrl+a"):
                logger.error("Failed to select all text in address bar")
                return False
                
            time.sleep(0.5)
            
            if not self.press_key("Delete"):
                logger.error("Failed to delete text in address bar")
                return False
                
            time.sleep(0.5)
            
            # Determine if we're doing a direct search or navigating to a website
            if 'facebook.com' in search_term.lower() or '.com' in search_term.lower() or '.org' in search_term.lower():
                # This is likely a URL, format it accordingly
                if not search_term.startswith(('http://', 'https://')):
                    url = f"https://{search_term}"
                else:
                    url = search_term
                logger.info(f"⌨️ Typing direct URL: {url}")
                if not self.type_text(url):
                    logger.error("Failed to type URL")
                    return False
            else:
                # This is a search term, use Google search
                # Type the search term directly (let browser handle the search)
                logger.info(f"⌨️ Typing search term: {search_term}")
                if not self.type_text(search_term):
                    logger.error("Failed to type search term")
                    return False
            
            time.sleep(1)
            
            # Press Enter
            logger.info("⌨️ Pressing Enter to execute search...")
            if not self.press_key("Return"):
                logger.error("Failed to press Enter")
                # Try "enter" key as alternative
                if not self.press_key("enter"):
                    return False
            
            # Wait for results
            logger.info("⏳ Waiting for results to load...")
            time.sleep(5)  # Increased wait time for better reliability

            # Take screenshot for verification
            try:
                ctx = self.perceiver.perceive_screen()
                if ctx and hasattr(ctx, 'image'):
                    timestamp = int(time.time())
                    filename = f"search_results_{timestamp}.png"
                    ctx.image.save(filename)
                    logger.info(f"📸 Screenshot of search results: {filename}")
            except Exception as se:
                logger.warning(f"⚠️ Screenshot failed but continuing: {se}")
            
            # Click first result if requested
            if should_click_first:
                logger.info("🎯 Clicking first search result as requested...")
                return self.click_first_search_result()
            
            return True
            
        except Exception as e:
            logger.error(f"Context search failed: {e}")
            return False

    def search_in_browser(self, search_term):
        """Search for term in current browser"""
        try:
            logger.info(f"🔍 Searching for '{search_term}' in current browser...")

            # Focus address bar
            if not self.press_key("ctrl+l"):
                return False

            time.sleep(1)

            # Type search URL
            search_url = (
                f"https://www.google.com/search?q={search_term.replace(' ', '+')}"
            )
            if not self.type_text(search_url):
                return False

            time.sleep(1)

            # Press Enter
            return self.press_key("Return")

        except Exception as e:
            logger.error(f"Browser search failed: {e}")
            return False

    def stop(self):
        """Stop the agent"""
        self.running = False

        if self.perceiver:
            self.perceiver.stop()
        if self.controller:
            self.controller.stop()

        logger.info("🏁 Real Desktop Agent stopped")

    def _handle_shutdown(self, sig, frame):
        """Handle shutdown signals"""
        logger.info("🛑 Emergency stop activated")
        self.stop()
        exit(0)

    def open_application(self, app_name: str) -> bool:
        """Launch an application by name"""
        return self.controller.app_manager.launch_application(app_name)

    def press_key(self, key: str) -> bool:
        """Press a key or key combination"""
        return self.controller.interaction.press_key(key)

    def intelligent_click(self, command):
        """Intelligently handle click commands"""
        try:
            logger.info(f"🖱️  Handling click command: {command}")
            
            # Take screenshot for context
            context = self.perceiver.perceive_screen()
            if not context:
                logger.error("Could not capture screen for click analysis")
                return False
            
            # Use AI to determine where to click
            prompt = f"""
User wants to: "{command}"

Current screen has:
- OCR text: {context.ocr_text[:300]}...
- UI elements: {len(context.ui_elements)} detected

Determine where to click based on the command. Look for buttons, links, or clickable elements.

Respond with just: click <x> <y>
Where x,y are the coordinates to click.
"""
            
            response = ollama_client.generate_text(
                model="mistral:7b", prompt=prompt, max_tokens=30
            )
            
            if response.success and "click" in response.content:
                return self.execute_ai_action(response.content.strip())
            else:
                logger.error("Could not determine click location")
                return False
                
        except Exception as e:
            logger.error(f"Intelligent click failed: {e}")
            return False

    def type_text(self, text: str) -> bool:
        """Type text on the keyboard"""
        return self.controller.interaction.type_text(text)

    def navigate_to_website(self, command):
        """Open Chrome if needed and navigate to the specified website URL with improved reliability"""
        try:
            logger.info("🚀 Navigating to website via Chrome...")
            
            # Ensure Chrome is open
            if 'chrome' not in command.lower():
                logger.info("Opening Chrome for website navigation...")
                if not self.open_application("google-chrome"):
                    logger.error("Failed to open Chrome for navigation")
                    return False
                time.sleep(3)  # Wait for Chrome to fully load
            
            # Take screenshot before navigation for debugging
            try:
                pre_ctx = self.perceiver.perceive_screen()
                if pre_ctx and hasattr(pre_ctx, 'image'):
                    ts = int(time.time())
                    pre_fname = f"pre_navigation_{ts}.png"
                    pre_ctx.image.save(pre_fname)
                    logger.info(f"📸 Screenshot before navigation: {pre_fname}")
            except Exception as se:
                logger.warning(f"⚠️ Pre-navigation screenshot failed: {se}")
            
            # Enhanced URL determination with expanded site mapping
            cmd_lower = command.lower()
            
            # Comprehensive mapping of common websites
            site_map = {
                'facebook': 'https://facebook.com',
                'fb': 'https://facebook.com',
                'google': 'https://www.google.com',
                'youtube': 'https://www.youtube.com',
                'yt': 'https://www.youtube.com',
                'github': 'https://github.com',
                'wikipedia': 'https://en.wikipedia.org',
                'wiki': 'https://en.wikipedia.org',
                'twitter': 'https://twitter.com',
                'x': 'https://twitter.com',
                'instagram': 'https://instagram.com',
                'insta': 'https://instagram.com',
                'linkedin': 'https://linkedin.com',
                'reddit': 'https://reddit.com',
                'amazon': 'https://amazon.com',
                'netflix': 'https://netflix.com',
                'gmail': 'https://mail.google.com',
                'maps': 'https://maps.google.com'
            }
            
            # Try to find a match in our site map
            url = None
            for key, site_url in site_map.items():
                if key in cmd_lower:
                    url = site_url
                    logger.info(f"📌 Matched '{key}' to URL: {site_url}")
                    break
            
            # If no predefined site found, try to extract a domain
            if not url:
                logger.info("📝 No predefined site matched, attempting to extract domain...")
                # First check for .com, .org etc. domains in the command
                domain_extensions = ['.com', '.org', '.net', '.edu', '.io', '.gov']
                for ext in domain_extensions:
                    if ext in cmd_lower:
                        # Extract the domain
                        parts = cmd_lower.split()
                        for part in parts:
                            if ext in part:
                                url = part
                                break
                        break
                
                # If still no URL found, use generic extraction
                if not url:
                    tokens = cmd_lower.split()
                    # Look for tokens that might be domains
                    for tok in tokens:
                        if '.' in tok and tok not in ['open', 'enter', 'visit', 'go', 'to', 'on', 'the']:
                            url = tok
                            break
                    
                    # Last resort: use final word as potential site name
                    if not url:
                        # Remove common command words
                        filtered_tokens = [t for t in tokens if t not in ['open', 'enter', 'visit', 'go', 'to', 'the', 'website', 'site', 'page', 'and']]
                        if filtered_tokens:
                            url = filtered_tokens[-1]
                            
                # Ensure URL has proper format
                if url and not url.startswith(('http://', 'https://')):
                    url = f"https://{url}"
                    
                # Final fallback - if we still don't have a URL, use the last token
                if not url:
                    url = "https://www.google.com"  # Default to Google if we can't determine URL
            
            logger.info(f"🌐 Navigation target URL: {url}")
            
            # Focus address bar (try multiple approaches for reliability)
            logger.info("📍 Focusing address bar...")
            focus_success = False
            
            for shortcut in ["ctrl+l", "alt+d", "F6"]:
                if self.press_key(shortcut):
                    logger.info(f"✅ Successfully focused address bar with {shortcut}")
                    focus_success = True
                    break
                time.sleep(0.5)
            
            if not focus_success:
                logger.error("❌ Failed to focus address bar using all known shortcuts")
                return False
            
            # Give browser time to focus the address bar
            time.sleep(1.5)
            
            # Clear address bar (select all + delete)
            logger.info("🧹 Clearing address bar...")
            if not self.press_key("ctrl+a") or not self.press_key("Delete"):
                logger.warning("⚠️ Address bar clearing may have failed")
            
            time.sleep(0.5)
            
            # Use clipboard for more reliable URL entry
            try:
                import pyperclip
                logger.info("📋 Using clipboard method for URL...")
                
                # Save original clipboard content
                original_clipboard = pyperclip.paste()
                
                # Copy URL to clipboard
                pyperclip.copy(url)
                time.sleep(0.5)
                
                # Paste into address bar
                if not self.press_key("ctrl+v"):
                    logger.error("❌ Failed to paste URL from clipboard")
                    # Fall back to direct typing
                    if not self.type_text(url):
                        logger.error("❌ Both clipboard and typing methods failed")
                        return False
                
                # Restore original clipboard if needed
                if original_clipboard:
                    time.sleep(0.2)
                    pyperclip.copy(original_clipboard)
                    
            except ImportError:
                # Fallback if pyperclip is not available
                logger.warning("⚠️ Clipboard module not available, using direct typing")
                if not self.type_text(url):
                    logger.error("❌ Failed to type URL for navigation")
                    return False
                    
            except Exception as clip_error:
                logger.warning(f"⚠️ Clipboard error: {clip_error}, falling back to direct typing")
                if not self.type_text(url):
                    logger.error("❌ Failed to type URL for navigation")
                    return False
            
            # Wait briefly before pressing Enter
            time.sleep(1)
            
            # Press Enter to navigate (try multiple variants for reliability)
            logger.info("⏎ Pressing Enter to navigate...")
            enter_success = False
            
            for enter_key in ["Return", "enter", "Enter"]:
                if self.press_key(enter_key):
                    logger.info(f"✅ Successfully used {enter_key} key")
                    enter_success = True
                    break
                time.sleep(0.5)
            
            if not enter_success:
                logger.error("❌ Failed to press Enter for navigation")
                return False
            
            # Wait longer for page to load
            logger.info("⏳ Waiting for page to load...")
            time.sleep(5)
            
            # Take screenshot after navigation
            try:
                post_ctx = self.perceiver.perceive_screen()
                if post_ctx and hasattr(post_ctx, 'image'):
                    ts = int(time.time())
                    post_fname = f"post_navigation_{ts}.png"
                    post_ctx.image.save(post_fname)
                    logger.info(f"📸 Screenshot after navigation: {post_fname}")
            except Exception as se:
                logger.warning(f"⚠️ Post-navigation screenshot failed: {se}")
                
            logger.info("✅ Website navigation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return False

def main():
    """Main entry point"""
    try:
        print("🖥️  REAL MCP AI Desktop Control Agent")
        print("=" * 50)
        print("⚠️  WARNING: This will control your actual desktop!")
        print("   Make sure you're ready and can press Ctrl+C to stop")
        print("=" * 50)

        agent = RealDesktopAgent()

        # Register emergency stop
        signal.signal(signal.SIGINT, agent._handle_shutdown)
        signal.signal(signal.SIGTERM, agent._handle_shutdown)

        agent.run()

    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
