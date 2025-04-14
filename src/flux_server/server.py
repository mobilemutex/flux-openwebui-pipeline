"""
Simplified Flux Server for Open-WebUI

This module implements a simplified Flux server that uses the diffusers library's
FluxPipeline module to generate images with a local FLUX.1-dev model.
"""

import os
import uuid
import time
import threading
import argparse
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import base64
from io import BytesIO

import torch
from diffusers import FluxPipeline
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("flux_server")


class TaskStatus(str, Enum):
    """Status of a generation task."""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class GenerationRequest(BaseModel):
    """Request model for image generation."""
    prompt: str
    height: int = 1024
    width: int = 1024
    num_inference_steps: int = 20
    guidance_scale: float = 3.5
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None


@dataclass
class ServerConfig:
    """Configuration for the Flux server."""
    # Model settings
    model_path: str = field(default_factory=lambda: os.environ.get("FLUX_MODEL_PATH", "./models/FLUX.1-dev"))
    device: str = field(default_factory=lambda: os.environ.get("FLUX_DEVICE", "mps"))
    use_bfloat16: bool = field(default_factory=lambda: os.environ.get("FLUX_USE_BFLOAT16", "true").lower() == "true")
    enable_model_cpu_offload: bool = field(default_factory=lambda: os.environ.get("FLUX_ENABLE_MODEL_CPU_OFFLOAD", "true").lower() == "true")
    
    # Server settings
    host: str = field(default_factory=lambda: os.environ.get("FLUX_SERVER_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.environ.get("FLUX_SERVER_PORT", "8000")))
    workers: int = field(default_factory=lambda: int(os.environ.get("FLUX_SERVER_WORKERS", "1")))
    
    # Task settings
    task_timeout_seconds: int = field(default_factory=lambda: int(os.environ.get("FLUX_TASK_TIMEOUT_SECONDS", "600")))
    max_queue_size: int = field(default_factory=lambda: int(os.environ.get("FLUX_MAX_QUEUE_SIZE", "10")))

    @classmethod
    def from_args(cls, args):
        """Create a configuration from command-line arguments."""
        return cls(
            model_path=args.model_path,
            device=args.device,
            use_bfloat16=args.use_bfloat16,
            enable_model_cpu_offload=args.enable_model_cpu_offload,
            host=args.host,
            port=args.port,
            workers=args.workers,
            task_timeout_seconds=args.task_timeout_seconds,
            max_queue_size=args.max_queue_size,
        )


class ModelManager:
    """Manager for the Flux model."""
    
    def __init__(self, config: ServerConfig):
        """
        Initialize the model manager.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.model = None
        self.model_lock = threading.RLock()
        
    def load_model(self):
        """
        Load the Flux model.
        
        Returns:
            The loaded model
        """
        with self.model_lock:
            if self.model is not None:
                return self.model
			
            logger.info(f"Loading model from {self.config.model_path}")

			# Determine torch dtype
            dtype = torch.bfloat16 if self.config.use_bfloat16 else torch.float16
			
			# Load the model
            self.model = FluxPipeline.from_pretrained(
                self.config.model_path,
                torch_dtype=dtype
            )
			
			# Move to device
            self.model.to(self.config.device)
			
			# Enable CPU offloading if configured
            if self.config.enable_model_cpu_offload:
                logger.info("Enabling model CPU offloading")
                self.model.enable_model_cpu_offload()
			
            logger.info("Model loaded successfully")
            return self.model
        
    def generate_image(self, prompt: str, params: Dict[str, Any]):
        """
        Generate an image with the Flux model.
        
        Args:
            prompt: Text prompt for image generation
            params: Generation parameters
            
        Returns:
            The generated image
        """
        with self.model_lock:
            if self.model is None:
                self.load_model()
            
            # Extract parameters
            height = params.get("height", 1024)
            width = params.get("width", 1024)
            num_inference_steps = params.get("num_inference_steps", 50)
            guidance_scale = params.get("guidance_scale", 3.5)
            negative_prompt = params.get("negative_prompt")
            seed = params.get("seed")
            
            # Set up generator for reproducibility if seed is provided
            generator = None
            if seed is not None:
                generator = torch.Generator(device="cpu").manual_seed(seed)
            
            logger.info(f"Generating image with prompt: {prompt}")
            
            # Generate the image
            result = self.model(
                prompt=prompt,
                height=height,
                width=width,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                negative_prompt=negative_prompt,
                generator=generator
            )
            
            logger.info("Image generation complete")
            result.images[0].save(f"flux-{time.time()}.jpeg")
            return result.images[0]
        
    def unload_model(self):
        """Unload the model to free memory."""
        with self.model_lock:
            if self.model is not None:
                logger.info("Unloading model")
                self.model = None
                # Force garbage collection
                import gc
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logger.info("Model unloaded")


class TaskQueue:
    """Queue for image generation tasks."""
    
    def __init__(self, config: ServerConfig):
        """
        Initialize the task queue.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.tasks = {}
        self.queue_lock = threading.RLock()
        
    def add_task(self, task_data: Dict[str, Any]) -> str:
        """
        Add a task to the queue.
        
        Args:
            task_data: Task data
            
        Returns:
            Task ID
        """
        with self.queue_lock:
            # Check if queue is full
            pending_tasks = sum(1 for task in self.tasks.values() 
                               if task["status"] in [TaskStatus.PENDING, TaskStatus.PROCESSING])
            
            if pending_tasks >= self.config.max_queue_size:
                raise Exception(f"Queue is full ({pending_tasks}/{self.config.max_queue_size})")
            
            # Create task ID
            task_id = str(uuid.uuid4())
            
            # Add task to queue
            self.tasks[task_id] = {
                "status": TaskStatus.PENDING,
                "data": task_data,
                "result": None,
                "error": None,
                "created_at": time.time(),
                "updated_at": time.time(),
                "progress": 0
            }
            
            logger.info(f"Added task {task_id} to queue")
            return task_id
        
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task from the queue.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task data or None if not found
        """
        with self.queue_lock:
            task = self.tasks.get(task_id)
            if task:
                return task.copy()
            return None
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status or None if not found
        """
        with self.queue_lock:
            if task_id not in self.tasks:
                return None
            
            task = self.tasks[task_id]
            return {
                "status": task["status"],
                "progress": task["progress"],
                "error": task["error"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"]
            }
        
    def update_task_status(self, task_id: str, status: Optional[TaskStatus] = None, 
                          progress: Optional[int] = None, result: Any = None, 
                          error: Optional[str] = None) -> bool:
        """
        Update the status of a task.
        
        Args:
            task_id: Task ID
            status: New status
            progress: New progress
            result: Task result
            error: Error message
            
        Returns:
            True if successful, False otherwise
        """
        print(f"Task Update for {task_id}")
        with self.queue_lock:
            if task_id not in self.tasks:
                logger.error(f"Attempted to update non-existent task: {task_id}")
                return False
            
            if status is not None:
                self.tasks[task_id]["status"] = status
                logger.debug(f"Updated task {task_id} status to {status}")
            
            if progress is not None:
                self.tasks[task_id]["progress"] = progress
            
            if result is not None:
                self.tasks[task_id]["result"] = result
            
            if error is not None:
                self.tasks[task_id]["error"] = error
                logger.error(f"Task {task_id} error: {error}")
            
            self.tasks[task_id]["updated_at"] = time.time()
            return True
        
    def clean_old_tasks(self):
        """Clean up old tasks to free memory."""
        with self.queue_lock:
            current_time = time.time()
            task_ids_to_remove = []
            
            for task_id, task in self.tasks.items():
                # Remove completed tasks after a timeout
                if task["status"] in [TaskStatus.DONE, TaskStatus.ERROR]:
                    if current_time - task["updated_at"] > 3600:  # 1 hour
                        task_ids_to_remove.append(task_id)
                # Remove stalled tasks
                elif current_time - task["updated_at"] > self.config.task_timeout_seconds:
                    self.update_task_status(
                        task_id, 
                        status=TaskStatus.ERROR, 
                        error="Task timed out"
                    )
                    task_ids_to_remove.append(task_id)
            
            for task_id in task_ids_to_remove:
                del self.tasks[task_id]
                logger.info(f"Removed old task {task_id}")
                print(f"Removed old task {task_id}")
                
    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        List all tasks in the queue.
        
        Returns:
            Dictionary of task IDs to task status
        """
        with self.queue_lock:
            return {
                task_id: {
                    "status": task["status"],
                    "progress": task["progress"],
                    "created_at": task["created_at"],
                    "updated_at": task["updated_at"]
                }
                for task_id, task in self.tasks.items()
            }


def create_app(config: ServerConfig):
    """
    Create the FastAPI application.
    
    Args:
        config: Server configuration
        
    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="Flux Server",
        description="API for generating images with a local FLUX.1-dev model",
        version="1.0.0",
    )
    
    # Initialize components
    model_manager = ModelManager(config)
    task_queue = TaskQueue(config)
    
    # Create a semaphore to limit concurrent generation tasks
    generation_semaphore = asyncio.Semaphore(1)
    
    # Background task for processing the queue
    async def process_generation_task(task_id: str):
        """
        Process a generation task.
        
        Args:
            task_id: Task ID
        """
        task = task_queue.get_task(task_id)
        print(f"Task({task_id}): {task}")
        if task is None:
            logger.error(f"Task {task_id} not found for processing")
            return
        
        # Update task status
        if not task_queue.update_task_status(task_id, status=TaskStatus.PROCESSING, progress=0):
            logger.error(f"Failed to update task {task_id} status to PROCESSING")
            return
        
        # Use semaphore to limit concurrent generation tasks
        async with generation_semaphore:
            try:
            	# Extract task data
                prompt = task["data"]["prompt"]
                print(f"Task prompt: {prompt}")
            
                def generate_in_thread():
                    try:
                        return model_manager.generate_image(prompt, task["data"])
                    except Exception as e:
                        logger.error(f"Error in generation thread for task {task_id}: {str(e)}")
                        raise e
                
                # Run generation in a thread pool
                loop = asyncio.get_event_loop()
                image = await loop.run_in_executor(None, generate_in_thread)
                
            
                # Update task with result
                if not task_queue.update_task_status(
                    task_id,
                    status=TaskStatus.DONE,
                    progress=100,
                    result=image
                ):
                    logger.error(f"Failed to update task {task_id} with result")
                    return
            
                logger.info(f"Task {task_id} completed successfully")
                
            except Exception as e:
                logger.error(f"Error processing task {task_id}: {str(e)}")
                
                # Update task with error
                if not task_queue.update_task_status(
                    task_id,
                    status=TaskStatus.ERROR,
                    error=str(e)
                ):
                    logger.error(f"Failed to update task {task_id} with error")
    
    # API endpoints
    @app.post("/api/generate")
    async def generate(request: GenerationRequest, background_tasks: BackgroundTasks):
        """
        Submit a generation request.
        
        Args:
            request: Generation request
            background_tasks: Background tasks
            
        Returns:
            Task ID and estimated completion time
        """
        try:
            # Add task to queue
            task_id = task_queue.add_task(request.model_dump())
            
            # Verify task was added successfully
            if task_queue.get_task(task_id) is None:
                raise Exception(f"Failed to add task {task_id} to queue")
            
            # Start generation in background
            background_tasks.add_task(process_generation_task, task_id)
            
            # Estimate completion time based on parameters
            steps = request.num_inference_steps
            resolution = request.width * request.height
            estimated_time = (steps * resolution) / (1024 * 1024) * 0.5  # Rough estimate
            
            return {
                "task_id": task_id,
                "expected_time_seconds": max(10, int(estimated_time))
            }
        except Exception as e:
            logger.error(f"Error submitting generation request: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/status/{task_id}")
    async def get_status(task_id: str):
        """
        Get the status of a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status
        """
        status = task_queue.get_task_status(task_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return status
    
    @app.get("/api/image/{task_id}")
    async def get_image(task_id: str, base64_format: bool = Query(False)):
        """
        Get the generated image for a task.
        
        Args:
            task_id: Task ID
            base64_format: Whether to return the image as base64
            
        Returns:
            Generated image
        """
        task = task_queue.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task["status"] != TaskStatus.DONE:
            raise HTTPException(
                status_code=400, 
                detail=f"Task is not done yet. Current status: {task['status']}"
            )
        
        if task["result"] is None:
            raise HTTPException(status_code=500, detail="Task result is missing")
        
        # Get the image
        image = task["result"]
        
        if base64_format:
            # Convert to base64
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return img_str
        else:
            # Return binary image
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            buffered.seek(0)
            return StreamingResponse(buffered, media_type="image/jpeg")
            
    @app.get("/api/tasks")
    async def list_tasks():
        """
        List all tasks in the queue.
        
        Returns:
            Dictionary of task IDs to task status
        """
        return task_queue.list_tasks()
    
    @app.get("/api/health")
    async def health_check():
        """
        Check the health of the server.
        
        Returns:
            Health status
        """
        return {
            "status": "ok",
            "model_loaded": model_manager.model is not None,
            "queue_size": len(task_queue.tasks),
            "task_queue": task_queue.tasks
        }
    
    # Periodic task cleanup
    @app.on_event("startup")
    async def startup_event():
        """Run on server startup."""
        logger.info(f"Starting Flux Server with configuration: {config}")
        
        # Start background thread for cleaning old tasks
        def clean_tasks_periodically():
            while True:
                time.sleep(60)  # Check every minute
                task_queue.clean_old_tasks()
        
        cleanup_thread = threading.Thread(target=clean_tasks_periodically, daemon=True)
        cleanup_thread.start()
    
    return app


#def main():

"""Main entry point for the server."""
# Parse command-line arguments
parser = argparse.ArgumentParser(description="Flux Server")

# Model settings
parser.add_argument("--model-path", type=str, default=os.environ.get("FLUX_MODEL_PATH", "./models/FLUX.1-dev"),
				   help="Path to the local FLUX.1-dev model")
parser.add_argument("--device", type=str, default=os.environ.get("FLUX_DEVICE", "mps"),
				   help="Device to run the model on (cuda or cpu)")
parser.add_argument("--use-bfloat16", action="store_true", 
				   default=os.environ.get("FLUX_USE_BFLOAT16", "true").lower() == "true",
				   help="Use bfloat16 precision")
parser.add_argument("--enable-model-cpu-offload", action="store_true",
				   default=os.environ.get("FLUX_ENABLE_MODEL_CPU_OFFLOAD", "true").lower() == "true",
				   help="Enable model CPU offloading")

# Server settings
parser.add_argument("--host", type=str, default=os.environ.get("FLUX_SERVER_HOST", "0.0.0.0"),
				   help="Host to bind to")
parser.add_argument("--port", type=int, default=int(os.environ.get("FLUX_SERVER_PORT", "8000")),
				   help="Port to listen on")
parser.add_argument("--workers", type=int, default=int(os.environ.get("FLUX_SERVER_WORKERS", "1")),
				   help="Number of worker processes")

# Task settings
parser.add_argument("--task-timeout-seconds", type=int, 
				   default=int(os.environ.get("FLUX_TASK_TIMEOUT_SECONDS", "600")),
				   help="Task timeout in seconds")
parser.add_argument("--max-queue-size", type=int,
				   default=int(os.environ.get("FLUX_MAX_QUEUE_SIZE", "10")),
				   help="Maximum queue size")

args = parser.parse_args()

# Create configuration
config = ServerConfig.from_args(args)

# Create app
app = create_app(config)




if __name__ == "__main__":
    # Run server
    uvicorn.run(
	    "__main__:app",
	    host=config.host,
	    port=config.port,
	    workers=config.workers,
    )
