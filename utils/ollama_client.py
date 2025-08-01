"""
Ollama client for interacting with local LLMs
"""

import requests
import subprocess
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from config import CONFIG
from utils.logger import logger


@dataclass
class ModelResponse:
    """Response from a model call"""

    content: str
    model: str
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OllamaClient:
    """Client for interacting with Ollama models"""

    def __init__(self, host: str = None):
        self.host = host or CONFIG.models.ollama_host
        self.session = requests.Session()
        self.available_models = []
        self._check_ollama_status()

    def _check_ollama_status(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [
                    model["name"] for model in data.get("models", [])
                ]
                logger.info(
                    f"Ollama connected. Available models: {self.available_models}"
                )
                return True
        except Exception as e:
            logger.error(f"Cannot connect to Ollama at {self.host}: {e}")
            self._try_start_ollama()
        return False

    def _try_start_ollama(self):
        """Attempt to start Ollama service"""
        try:
            logger.info("Attempting to start Ollama service...")
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)  # Wait for service to start
            return self._check_ollama_status()
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False

    def pull_model(self, model_name: str) -> bool:
        """Pull a model if not available"""
        if model_name in self.available_models:
            return True

        try:
            logger.info(f"Pulling model: {model_name}")
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode == 0:
                self.available_models.append(model_name)
                logger.info(f"Successfully pulled model: {model_name}")
                return True
            else:
                logger.error(f"Failed to pull model {model_name}: {result.stderr}")
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
        return False

    def generate_text(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        timeout: int = None,  # Allow custom timeout override
    ) -> ModelResponse:
        """Generate text using a language model"""
        if model not in self.available_models:
            if not self.pull_model(model):
                return ModelResponse(
                    content="",
                    model=model,
                    success=False,
                    error=f"Model {model} not available",
                )
                
        # Use default timeout or adjust based on prompt length
        if timeout is None:
            # Adaptive timeout based on prompt length
            prompt_length = len(prompt)
            if prompt_length > 3000:
                timeout = CONFIG.models.timeout * 2  # Double timeout for very long prompts
            elif prompt_length > 1000:
                timeout = int(CONFIG.models.timeout * 1.5)  # 1.5x timeout for long prompts
            else:
                timeout = CONFIG.models.timeout
        
        logger.debug(f"Using timeout of {timeout}s for prompt length {len(prompt)}")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            logger.debug(f"Calling model {model} with prompt length: {len(prompt)}")
            # Use exponential backoff for request retries with progressive prompt reduction
            max_retries = CONFIG.models.max_retries
            retry_delay = 2
            attempt = 0
            original_prompt = prompt
            current_prompt = prompt
            
            while attempt < max_retries:
                try:
                    response = self.session.post(
                        f"{self.host}/api/generate", 
                        json=payload, 
                        timeout=timeout
                    )
                    break  # Success, exit retry loop
                except requests.exceptions.Timeout:
                    attempt += 1
                    logger.warning(f"Request timeout, retry {attempt}/{max_retries} (timeout={timeout}s)...")
                    
                    if attempt >= max_retries:
                        # Final attempt failed, try with significantly simplified prompt
                        logger.warning("All retries failed with standard prompt, trying simplified version...")
                        
                        # Extract just the core instruction and user input for a minimal prompt
                        lines = original_prompt.split('\n')
                        simplified_prompt = ""
                        for line in lines:
                            if "USER COMMAND" in line or "command:" in line.lower():
                                command_line = line
                                simplified_prompt = f"Break this command into numbered steps: {command_line}\n"
                                simplified_prompt += "Be concise. Just list the steps."
                                break
                        
                        # If we couldn't extract a simplified version, use the last 20% of the prompt
                        if not simplified_prompt:
                            # Take just last 20% of the prompt which often contains the key instruction
                            simplified_prompt = original_prompt[-int(len(original_prompt)*0.2):]
                        
                        logger.info(f"Trying with simplified prompt ({len(simplified_prompt)} chars)")
                        payload["prompt"] = simplified_prompt
                        
                        try:
                            response = self.session.post(
                                f"{self.host}/api/generate", 
                                json=payload, 
                                timeout=timeout
                            )
                            break  # Success with simplified prompt
                        except requests.exceptions.Timeout:
                            logger.error("Simplified prompt also timed out")
                            raise  # Re-raise the timeout error
                    
                    # Progressive prompt reduction strategy
                    if len(current_prompt) > 1000:
                        # Reduce prompt size for next retry by removing examples but keeping structure
                        reduction_percentage = 0.25 * (attempt + 1)  # 25%, 50%, 75% reduction
                        if reduction_percentage > 0.75:
                            reduction_percentage = 0.75  # Cap at 75% reduction
                            
                        # Keep the beginning and end of the prompt, remove from middle
                        keep_chars = int(len(original_prompt) * (1 - reduction_percentage))
                        start_portion = int(keep_chars * 0.4)  # 40% from start
                        end_portion = keep_chars - start_portion  # 60% from end
                        
                        reduced_prompt = original_prompt[:start_portion] + "\n...[examples omitted for brevity]...\n" + original_prompt[-end_portion:]
                        current_prompt = reduced_prompt
                        payload["prompt"] = current_prompt
                        logger.info(f"Reduced prompt to {len(current_prompt)} chars for next attempt")
                    
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    
                except Exception as e:
                    logger.error(f"Error during model call: {e}")
                    raise  # Re-raise other exceptions immediately

            if response.status_code == 200:
                data = response.json()
                content = data.get("response", "")
                logger.log_model_call(model, prompt, content)

                return ModelResponse(
                    content=content,
                    model=model,
                    success=True,
                    metadata={
                        "eval_count": data.get("eval_count"),
                        "eval_duration": data.get("eval_duration"),
                        "used_simplified_prompt": prompt != original_prompt,
                    },
                )
            else:
                error = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Model call failed: {error}")
                return ModelResponse(
                    content="", model=model, success=False, error=error
                )

        except Exception as e:
            error = f"Exception during model call: {e}"
            logger.error(error)
            return ModelResponse(content="", model=model, success=False, error=error)

    def analyze_image(
        self, model: str, image_path: str, prompt: str = "Describe this image in detail", timeout: int = None
    ) -> ModelResponse:
        """Analyze an image using a vision model"""
        if model not in self.available_models:
            if not self.pull_model(model):
                return ModelResponse(
                    content="",
                    model=model,
                    success=False,
                    error=f"Vision model {model} not available",
                )

        # Use default timeout or custom value
        if timeout is None:
            timeout = CONFIG.models.timeout

        try:
            import base64

            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode()

            payload = {
                "model": model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False,
            }

            logger.debug(f"Analyzing image with {model}, timeout: {timeout}s")
            # Use exponential backoff for request retries
            max_retries = CONFIG.models.max_retries
            retry_delay = 2
            attempt = 0
            response = None
            
            while attempt < max_retries:
                try:
                    response = self.session.post(
                        f"{self.host}/api/generate", 
                        json=payload, 
                        timeout=timeout
                    )
                    break  # Success, exit retry loop
                except requests.exceptions.Timeout:
                    attempt += 1
                    logger.warning(f"Image analysis timeout, retry {attempt}/{max_retries}...")
                    
                    if attempt >= max_retries:
                        # Final attempt with simplified prompt
                        if len(prompt) > 100:
                            # Try with a much simpler prompt on final attempt
                            simplified_prompt = "What's in this image? Be brief."
                            payload["prompt"] = simplified_prompt
                            logger.warning(f"Trying with simplified image prompt: '{simplified_prompt}'")
                            try:
                                response = self.session.post(
                                    f"{self.host}/api/generate", 
                                    json=payload, 
                                    timeout=timeout
                                )
                                break  # Success with simplified prompt
                            except requests.exceptions.Timeout:
                                logger.error("Simplified image prompt also timed out")
                                raise  # Re-raise the timeout error
                        else:
                            raise  # Re-raise if all retries failed with already simple prompt
                    
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                except Exception as e:
                    logger.error(f"Error during image analysis: {e}")
                    raise  # Re-raise other exceptions immediately

            if response.status_code == 200:
                data = response.json()
                content = data.get("response", "")
                logger.debug(f"Vision analysis complete: {content[:100]}...")

                return ModelResponse(
                    content=content,
                    model=model,
                    success=True,
                    metadata={"image_analyzed": True},
                )
            else:
                error = f"HTTP {response.status_code}: {response.text}"
                return ModelResponse(
                    content="", model=model, success=False, error=error
                )

        except Exception as e:
            error = f"Exception during image analysis: {e}"
            logger.error(error)
            return ModelResponse(content="", model=model, success=False, error=error)

    def health_check(self) -> bool:
        """Check if the Ollama service is healthy"""
        return self._check_ollama_status()

    def check_server(self) -> bool:
        """Check if the Ollama server is running (alias for health_check)"""
        return self.health_check()


# Global Ollama client instance
ollama_client = OllamaClient()
