# Progress Tracking in Flux Server

This document explains the progress tracking feature implemented in the Flux Server integration for Open-WebUI.

## Overview

The progress tracking feature allows users to see real-time progress updates during image generation. Instead of showing 0% until completion and then jumping to 100%, the progress is now updated incrementally based on the number of inference steps completed.

## Implementation Details

### Callback Mechanism

The progress tracking is implemented using the diffusers library's callback mechanism. The `FluxPipeline` class supports a `callback_on_step_end` parameter that allows a function to be executed at the end of each inference step.

```python
def create_progress_callback(task_id: str, task_queue: TaskQueue, num_inference_steps: int):
    """
    Create a callback function for tracking progress during image generation.
    
    Args:
        task_id: Task ID
        task_queue: Task queue
        num_inference_steps: Total number of inference steps
        
    Returns:
        Callback function
    """
    def callback_fn(pipe, step_index, timestep, callback_kwargs):
        # Calculate progress percentage (0-100)
        progress = int((step_index + 1) / num_inference_steps * 100)
        
        # Update task progress
        task_queue.update_task_status(task_id, progress=progress)
        
        # Return callback_kwargs to continue the pipeline
        return callback_kwargs
    
    return callback_fn
```

### Integration with ModelManager

The `ModelManager.generate_image` method has been updated to accept and use a callback function:

```python
def generate_image(self, prompt: str, params: Dict[str, Any], callback: Optional[Callable] = None):
    # ... existing code ...
    
    # Generate the image
    result = self.model(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        negative_prompt=negative_prompt,
        generator=generator,
        callback_on_step_end=callback if callback else None,
        callback_on_step_end_tensor_inputs=["latents", "prompt_embeds"] if callback else None
    )
    
    # ... existing code ...
```

### Task Processing

The `process_generation_task` function creates and uses the progress callback:

```python
async def process_generation_task(task_id: str):
    # ... existing code ...
    
    # Create progress callback
    num_inference_steps = task["data"].get("num_inference_steps", 50)
    progress_callback = create_progress_callback(task_id, task_queue, num_inference_steps)
    
    # Run generation in a thread pool with callback
    def generate_in_thread():
        try:
            return model_manager.generate_image(prompt, task["data"], callback=progress_callback)
        except Exception as e:
            logger.error(f"Error in generation thread for task {task_id}: {str(e)}")
            raise e
    
    # ... existing code ...
```

## User Experience

With this implementation, users will see the progress percentage increase incrementally as the image generation proceeds. The progress updates are available through the `/api/status/{task_id}` endpoint, which returns the current progress percentage along with other task status information.

For example, a task with 50 inference steps will show progress updates approximately as follows:
- 0% (task started)
- 2% (after 1 step)
- 4% (after 2 steps)
- ...
- 98% (after 49 steps)
- 100% (task completed)

This provides a much better user experience compared to the previous implementation, which only showed 0% until completion and then jumped to 100%.

## Technical Considerations

1. **Thread Safety**: The progress updates happen in a separate thread from the main server thread, so all operations on the task queue are protected by a reentrant lock (`RLock`) to ensure thread safety.

2. **Performance Impact**: The progress tracking adds minimal overhead to the image generation process, as the callback function only performs a simple calculation and updates a value in memory.

3. **Error Handling**: If an error occurs during image generation, the task status is updated to `ERROR` and the error message is stored in the task data.

4. **Concurrency**: The server uses a semaphore to limit concurrent generation tasks, but status requests can still be processed while generation is in progress.

## Testing

The progress tracking implementation has been thoroughly tested using a mock implementation of the FluxPipeline. The tests verify that:

1. Progress values are updated incrementally during image generation
2. Progress values increase monotonically from 0% to 100%
3. The final progress value is 100% when the task is completed
4. Multiple concurrent tasks can be tracked independently

## Conclusion

The progress tracking feature significantly improves the user experience by providing real-time feedback during image generation. Users can now see the progress of their generation tasks incrementally, rather than waiting for the entire process to complete before seeing any progress.
