"""
Open-WebUI Pipeline for Flux Integration

This module implements a custom Pipeline for Open-WebUI that connects to flux-server
for distributed image generation on Linux machines with NVIDIA GPUs.
"""

import os
import json
import base64
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Union, Generator, Iterator
from pydantic import BaseModel

class Pipeline:
    """
    A Pipeline implementation for Open-WebUI that connects to flux-server
    for image generation on Linux machines with NVIDIA GPUs.
    """
    
    class Valves(BaseModel):
        """Configuration parameters for the pipeline."""
        flux_server_url: str = os.getenv("FLUX_SERVER_URL", "http://localhost:4030")
        default_width: int = int(os.getenv("FLUX_DEFAULT_WIDTH", "1024"))
        default_height: int = int(os.getenv("FLUX_DEFAULT_HEIGHT", "1024"))
        default_steps: int = int(os.getenv("FLUX_DEFAULT_STEPS", "20"))
        #default_format: str = os.getenv("FLUX_DEFAULT_FORMAT", "PNG")
        #default_quality: int = int(os.getenv("FLUX_DEFAULT_QUALITY", "85"))
        #default_model: str = os.getenv("FLUX_DEFAULT_MODEL", "flux.1-schnell")
        default_guidance: float = float(os.getenv("FLUX_DEFAULT_GUIDANCE", "3.5"))
        polling_interval: float = float(os.getenv("FLUX_POLLING_INTERVAL", "1.0"))
        max_retries: int = int(os.getenv("FLUX_MAX_RETRIES", "3"))
        timeout_seconds: int = int(os.getenv("FLUX_TIMEOUT_SECONDS", "300"))
        #use_tensorrt: bool = os.getenv("FLUX_USE_TENSORRT", "true").lower() == "true"

    def __init__(self):
        """Initialize the pipeline with default configuration."""
        self.valves = self.Valves()
        self.name = "Flux Pipeline"
        
    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
    
        return asyncio.run(self.process_chat_completion(body))
        
    async def process_chat_completion(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a chat completion request from Open-WebUI.
        
        Args:
            request_data: The request data from Open-WebUI
            
        Returns:
            A response dictionary compatible with Open-WebUI
        """
        print(f"pipe:{__name__}")
        try:
            # Extract prompt from request
            prompt = self._extract_prompt(request_data)
            
            # Extract additional parameters if provided
            params = self._extract_parameters(request_data)
            
            print(prompt)
            # Submit generation request to flux-server
            print(params)
            task_id = await self._submit_generation(prompt, **params)
            
            # Poll for completion
            image_data = await self._poll_until_complete(task_id)
            
            # Format response for Open-WebUI
            return self._format_response(image_data, prompt)
            
        except Exception as e:
            # Handle errors and return an appropriate response
            return self._format_error_response(str(e))
    
    def _extract_prompt(self, request_data: Dict[str, Any]) -> str:
        """
        Extract the prompt from the request data.
        
        Args:
            request_data: The request data from Open-WebUI
            
        Returns:
            The extracted prompt
        """
        # Extract from messages if available
        if "messages" in request_data and request_data["messages"]:
            for message in reversed(request_data["messages"]):
                if message.get("role") == "user" and message.get("content"):
                    return message["content"]
        
        # Fall back to prompt if available
        if "prompt" in request_data:
            return request_data["prompt"]
        
        raise ValueError("No prompt found in request data")
    
    def _extract_parameters(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract additional parameters from the request data.
        
        Args:
            request_data: The request data from Open-WebUI
            
        Returns:
            A dictionary of parameters
        """
        params = {}
        
        # Check for parameters in the request data
        if "parameters" in request_data:
            params_data = request_data["parameters"]
            
            # Extract width if provided
            if "width" in params_data:
                params["width"] = int(params_data["width"])
            
            # Extract height if provided
            if "height" in params_data:
                params["height"] = int(params_data["height"])
            
            # Extract steps if provided
            if "steps" in params_data:
                params["steps"] = int(params_data["steps"])
            
            # Extract seed if provided
            if "seed" in params_data:
                params["seed"] = int(params_data["seed"])
            
            # Extract format if provided
            if "format" in params_data:
                params["format"] = params_data["format"]
            
            # Extract quality if provided
            if "quality" in params_data:
                params["quality"] = int(params_data["quality"])
                
            # Extract model if provided
            if "model" in params_data:
                params["model"] = params_data["model"]
                
            # Extract guidance if provided
            if "guidance" in params_data:
                params["guidance"] = float(params_data["guidance"])
                
            # Extract TensorRT settings if provided
            if "use_tensorrt" in params_data:
                params["use_tensorrt"] = bool(params_data["use_tensorrt"])
        
        return params
    
    async def _submit_generation(self, prompt: str, **kwargs) -> str:
        """
        Submit an image generation request to flux-server.
        
        Args:
            prompt: The prompt for image generation
            **kwargs: Additional parameters
            
        Returns:
            The task ID for the generation request
        """
        data = {
            "prompt": prompt,
            "width": kwargs.get("width", self.valves.default_width),
            "height": kwargs.get("height", self.valves.default_height),
            "num_inference_steps": kwargs.get("steps", self.valves.default_steps),
            #"format": kwargs.get("format", self.valves.default_format),
            #"quality": kwargs.get("quality", self.valves.default_quality),
            #"model": kwargs.get("model", self.valves.default_model),
            "guidance_scale": kwargs.get("guidance", self.valves.default_guidance),
            #"use_tensorrt": kwargs.get("use_tensorrt", self.valves.use_tensorrt)
        }
        
        # Add seed if provided
        if "seed" in kwargs:
            data["seed"] = kwargs["seed"]
        
        print(f"Submission params: {data}")
        
        # Try to submit the request with retries
        for attempt in range(self.valves.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.valves.flux_server_url}/api/generate", 
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        print(f"Response: {response.json}")
                        if response.status == 200:
                            result = await response.json()
                            return result["task_id"]
                        else:
                            error = await response.text()
                            raise Exception(f"Failed to submit generation: {error}")
            except Exception as e:
                if attempt == self.valves.max_retries - 1:
                    raise
                await asyncio.sleep(1)
        
        raise Exception("Failed to submit generation after multiple attempts")

    async def _poll_until_complete(self, task_id: str) -> bytes:
        """
        Poll flux-server until the image generation is complete.
        
        Args:
            task_id: The task ID to poll
            
        Returns:
            The generated image data
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check for timeout
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > self.valves.timeout_seconds:
                raise TimeoutError(f"Image generation timed out after {self.valves.timeout_seconds} seconds")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.valves.flux_server_url}/api/status/{task_id}",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            status_data = await response.json()
                            if status_data["status"] == "done":
                                return await self._retrieve_image(task_id)
                            elif status_data["status"] == "error":
                                error_msg = status_data.get("error", "Unknown error")
                                raise Exception(f"Image generation failed: {error_msg}")
                            else:
                                # Wait before polling again
                                wait_time = status_data.get("wait_remaining", self.valves.polling_interval)
                                await asyncio.sleep(min(max(wait_time, 0.5), 10))
                        else:
                            error = await response.text()
                            raise Exception(f"Failed to check status: {error}")
            except aiohttp.ClientError:
                # On connection error, wait a bit and retry
                await asyncio.sleep(2)

    async def _retrieve_image(self, task_id: str) -> bytes:
        """
        Retrieve the generated image from flux-server.
        
        Args:
            task_id: The task ID to retrieve
            
        Returns:
            The image data
        """
        for attempt in range(self.valves.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.valves.flux_server_url}/api/image/{task_id}?base64_format=true",
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            # The response is a base64-encoded image
                            image_data = await response.text()
                            return base64.b64decode(image_data)
                        else:
                            error = await response.text()
                            raise Exception(f"Failed to retrieve image: {error}")
            except Exception as e:
                if attempt == self.valves.max_retries - 1:
                    raise
                await asyncio.sleep(1)
        
        raise Exception("Failed to retrieve image after multiple attempts")
    
    def _format_response(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """
        Format the response for Open-WebUI.
        
        Args:
            image_data: The generated image data
            prompt: The original prompt
            
        Returns:
            A response dictionary compatible with Open-WebUI
        """
        # Encode the image as base64
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # Determine the image format
        #image_format = self.valves.default_format.lower()
        image_format = "jpeg"
        
        # Create a response with the image
        # return {
        #     "id": f"flux-{int(asyncio.get_event_loop().time())}",
        #     "object": "chat.completion",
        #     "created": int(asyncio.get_event_loop().time()),
        #     "model": "flux-generate",
        #     "choices": [
        #         {
        #             "index": 0,
        #             "message": {
        #                 "role": "assistant",
        #                 "content": f"![Image](data:image/{image_format};base64,{image_base64})",
        #             },
        #             "finish_reason": "stop"
        #         }
        #     ]
        # }
        return f"![Image](data:image/{image_format};base64,{image_base64})"
    
    def _format_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Format an error response for Open-WebUI.
        
        Args:
            error_message: The error message
            
        Returns:
            A response dictionary compatible with Open-WebUI
        """
        return {
            "id": "flux-generate-error",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": "flux-generate",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Error generating image: {error_message}",
                    },
                    "finish_reason": "stop"
                }
            ]
        }
