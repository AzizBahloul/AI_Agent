"""
Ollama API integration with streaming and image support
"""
import httpx
import base64
import json
import logging
import subprocess
from typing import AsyncGenerator, List

logger = logging.getLogger("desktop-genie")

class OllamaClient:
    # NOTE: GPU usage is determined by the Ollama server itself, not by API options.
    # To use GPU, ensure:
    #   1. You have a supported GPU and drivers (CUDA) installed.
    #   2. You are running the GPU-enabled version of Ollama.
    #   3. Ollama will automatically use the GPU if available and supported by the model.
    #   4. There is currently NO API option (like 'device' or 'gpu') to force GPU usage per request.
    # See: https://github.com/ollama/ollama/blob/main/docs/gpu.md
    def __init__(self, base_url: str = "http://localhost:11434"):
        # Check for GPU (NVIDIA CUDA) availability
        try:
            result = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise RuntimeError("No NVIDIA GPU detected. This application requires a GPU to run.")
        except FileNotFoundError:
            raise RuntimeError("nvidia-smi not found. This application requires an NVIDIA GPU and drivers installed.")
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.model_cache = {}
        logger.info(f"Ollama client initialized at {base_url}")

    async def generate_text(
        self, 
        prompt: str, 
        model: str = "mistral:latest",
        system: str = None,
        context: List[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text response from LLM
        Attempts to force GPU usage by including 'num_gpu' in options, but Ollama manages device selection automatically as of 2025.
        """
        endpoint = f"{self.base_url}/api/generate"
        # Always include 'num_gpu': 1 in options for future compatibility, though Ollama currently ignores it
        options = dict(kwargs) if kwargs else {}
        options.setdefault("num_gpu", 1)
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "context": context,
            "system": system,
            "options": options
        }
        try:
            async with self.client.stream("POST", endpoint, json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if chunk:
                        data = json.loads(chunk)
                        if "response" in data:
                            yield data["response"]
                        if "context" in data:
                            context = data["context"]
        except httpx.RequestError as e:
            logger.error(f"Request failed: {e}")
            raise
        except json.JSONDecodeError:
            logger.error("Invalid JSON response")
            raise

    async def analyze_image(
        self, 
        image_path: str, 
        prompt: str,
        model: str = "llava",
        **kwargs
    ) -> str:
        """Analyze image with multimodal model"""
        endpoint = f"{self.base_url}/api/generate"
        
        # Read and encode image
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [encoded_image],
            "stream": False
        }
        
        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except httpx.RequestError as e:
            logger.error(f"Image analysis failed: {e}")
            return ""
    
    async def generate_code(
        self, 
        description: str,
        context: str = None,
        model: str = "codellama",
        **kwargs
    ) -> str:
        """Generate code from description"""
        system_prompt = "You are an expert programmer. Return ONLY valid code without explanations."
        full_prompt = f"# Task\n{description}\n\n# Context\n{context or 'No context provided'}\n\n# Code\n"
        
        response = ""
        async for chunk in self.generate_text(
            full_prompt, 
            model=model, 
            system=system_prompt,
            **kwargs
        ):
            response += chunk
        
        return response
    
    async def close(self):
        await self.client.aclose()
