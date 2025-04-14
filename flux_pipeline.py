"""
Flux Pipeline Connector for Open-WebUI

This module provides a pipeline connector for Open-WebUI to generate images
using a local FLUX.1-dev model through the simplified Flux server.
"""

import os
import time
import json
import base64
import aiohttp
import asyncio
import re
from typing import Dict, Any, List, Optional, Tuple


class FluxConfig:
    """Configuration for the Flux pipeline connector."""
    
    def __init__(self):
        # Server connection settings
        self.server_url = os.environ.get("FLUX_SERVER_URL", "http://localhost:8000")
        
        # Default generation parameters
        self.default_params = {
            "width": int(os.environ.get("FLUX_DEFAULT_WIDTH", "1024")),
            "height": int(os.environ.get("FLUX_DEFAULT_HEIGHT", "1024")),
            "num_inference_steps": int(os.environ.get("FLUX_DEFAULT_STEPS", "50")),
            "guidance_scale": float(os.environ.get("FLUX_DEFAULT_GUIDANCE", "3.5")),
        }
        
        # Connection parameters
        self.polling_interval = float(os.environ.get("FLUX_POLLING_INTERVAL", "1.0"))
        self.max_retries = int(os.environ.get("FLUX_MAX_RETRIES", "60"))
        self.timeout_seconds = int(os.environ.get("FLUX_TIMEOUT_SECONDS", "30"))


class FluxPipelineConnector:
    """
    Pipeline connector for Open-WebUI to generate images using a local FLUX.1-dev model.
    """
    
    def __init__(self, config=None):
        """
        Initialize the connector with the given configuration.
        
        Args:
            config: Configuration object (optional)
        """
        self.config = config or FluxConfig()
        
    async def process_chat_completion(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a chat completion request from Open-WebUI.
        
        Args:
            request_data: Request data from Open-WebUI
            
        Returns:
            Response data for Open-WebUI
        """
        try:
            # Extract messages from request
            messages = request_data.get("messages", [])
            
            # Extract prompt and parameters
            prompt, params = self._extract_parameters(messages)
            
            # Check if we have a valid prompt
            if not prompt.strip():
                return self._format_error_response("Please provide a prompt for image generation.")
            
            # Submit generation request
            task_id = await self._submit_generation(prompt, params)
            
            # Poll until complete
            success = await self._poll_until_complete(task_id)
            
            if not success:
                return self._format_error_response("Image generation failed or timed out.")
            
            # Retrieve image
            image_data = await self._retrieve_image(task_id)
            
            if not image_data:
                return self._format_error_response("Failed to retrieve generated image.")
            
            # Format response
            return self._format_response(image_data, prompt)
        except Exception as e:
            # Catch any unexpected errors
            return self._format_error_response(f"An error occurred: {str(e)}")
    
    def _extract_parameters(self, messages: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        Extract prompt and parameters from messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Tuple of (prompt, parameters)
        """
        # Get the last user message
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return "", {}
        
        last_user_message = user_messages[-1]["content"]
        
        # Check if the message contains parameters
        params = {}
        
        # Extract parameters using regex
        param_pattern = r"with parameters?:?\s*\n([\s\S]+?)(?:\n\n|$)"
        param_match = re.search(param_pattern, last_user_message, re.IGNORECASE)
        
        if param_match:
            param_text = param_match.group(1)
            # Extract individual parameters
            for line in param_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    # Convert values to appropriate types
                    if key in ["width", "height", "steps", "num_inference_steps", "seed"]:
                        try:
                            params[key] = int(value)
                        except ValueError:
                            pass
                    elif key in ["guidance", "guidance_scale"]:
                        try:
                            params[key] = float(value)
                        except ValueError:
                            pass
                    else:
                        params[key] = value
            
            # Remove parameter section from prompt
            prompt = last_user_message.replace(param_match.group(0), "").strip()
        else:
            prompt = last_user_message
        
        # Map parameters to API expected format
        if "steps" in params:
            params["num_inference_steps"] = params.pop("steps")
        if "guidance" in params:
            params["guidance_scale"] = params.pop("guidance")
            
        # Merge with default parameters
        merged_params = {**self.config.default_params, **params}
        
        return prompt, merged_params
    
    async def _submit_generation(self, prompt: str, params: Dict[str, Any]) -> str:
        """
        Submit a generation request to the Flux server.
        
        Args:
            prompt: Text prompt for image generation
            params: Generation parameters
            
        Returns:
            Task ID from the server
        """
        async with aiohttp.ClientSession() as session:
            try:
                # Prepare request data
                request_data = {
                    "prompt": prompt,
                    **params
                }
                
                # Send request to server
                async with session.post(
                    f"{self.config.server_url}/api/generate",
                    json=request_data,
                    timeout=self.config.timeout_seconds
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Error submitting generation request: {error_text}")
                    
                    response_data = await response.json()
                    return response_data["task_id"]
            except Exception as e:
                raise Exception(f"Failed to submit generation request: {str(e)}")
    
    async def _poll_until_complete(self, task_id: str) -> bool:
        """
        Poll the server until the task is complete.
        
        Args:
            task_id: Task ID to poll for
            
        Returns:
            True if successful, False otherwise
        """
        retries = 0
        while retries < self.config.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.config.server_url}/api/status/{task_id}",
                        timeout=self.config.timeout_seconds
                    ) as response:
                        if response.status != 200:
                            retries += 1
                            await asyncio.sleep(self.config.polling_interval)
                            continue
                        
                        status_data = await response.json()
                        status = status_data.get("status")
                        
                        if status == "done":
                            return True
                        elif status == "error":
                            return False
                        
                        # Still processing, wait and try again
                        await asyncio.sleep(self.config.polling_interval)
            except Exception:
                retries += 1
                await asyncio.sleep(self.config.polling_interval)
        
        return False
    
    async def _retrieve_image(self, task_id: str) -> Optional[str]:
        """
        Retrieve the generated image from the server.
        
        Args:
            task_id: Task ID to retrieve image for
            
        Returns:
            Base64-encoded image data or None if failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.server_url}/api/image/{task_id}?base64_format=true",
                    timeout=self.config.timeout_seconds
                ) as response:
                    if response.status != 200:
                        return None
                    
                    # Response is the base64-encoded image
                    return await response.text()
        except Exception:
            return None
    
    def _format_response(self, image_data: str, prompt: str) -> Dict[str, Any]:
        """
        Format the response for Open-WebUI.
        
        Args:
            image_data: Base64-encoded image data
            prompt: Original prompt
            
        Returns:
            Formatted response for Open-WebUI
        """
        # Format as markdown with embedded image
        content = f"Generated image for: \"{prompt}\"\n\n![Generated Image](data:image/jpeg;base64,{image_data})"
        
        return {
            "id": f"flux-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "flux-generate",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }
            ]
        }
    
    def _format_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Format an error response for Open-WebUI.
        
        Args:
            error_message: Error message
            
        Returns:
            Formatted error response
        """
        return {
            "id": f"flux-error-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "flux-generate",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Error: {error_message}"
                    },
                    "finish_reason": "stop"
                }
            ]
        }


# Main entry point for Open-WebUI
async def process_chat_completion(request_data):
    """
    Process a chat completion request from Open-WebUI.
    
    This is the main entry point that Open-WebUI will call.
    
    Args:
        request_data: Request data from Open-WebUI
        
    Returns:
        Response data for Open-WebUI
    """
    connector = FluxPipelineConnector()
    return await connector.process_chat_completion(request_data)
