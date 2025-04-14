#!/bin/bash
# Startup script for the Flux Server

# Set default environment variables if not already set
export FLUX_MODEL_PATH=${FLUX_MODEL_PATH:-"path/to/FLUX.1-dev"}
export FLUX_DEVICE=${FLUX_DEVICE:-"mps"}
export FLUX_USE_BFLOAT16=${FLUX_USE_BFLOAT16:-"true"}
export FLUX_ENABLE_MODEL_CPU_OFFLOAD=${FLUX_ENABLE_MODEL_CPU_OFFLOAD:-"false"}
export FLUX_SERVER_HOST=${FLUX_SERVER_HOST:-"0.0.0.0"}
export FLUX_SERVER_PORT=${FLUX_SERVER_PORT:-"8000"}
export FLUX_SERVER_WORKERS=${FLUX_SERVER_WORKERS:-"1"}
export FLUX_TASK_TIMEOUT_SECONDS=${FLUX_TASK_TIMEOUT_SECONDS:-"600"}
export FLUX_MAX_QUEUE_SIZE=${FLUX_MAX_QUEUE_SIZE:-"10"}

# Print configuration
echo "Starting Flux Server with configuration:"
echo "  Model path: $FLUX_MODEL_PATH"
echo "  Device: $FLUX_DEVICE"
echo "  Use bfloat16: $FLUX_USE_BFLOAT16"
echo "  Enable model CPU offloading: $FLUX_ENABLE_MODEL_CPU_OFFLOAD"
echo "  Host: $FLUX_SERVER_HOST"
echo "  Port: $FLUX_SERVER_PORT"
echo "  Workers: $FLUX_SERVER_WORKERS"
echo "  Task timeout: $FLUX_TASK_TIMEOUT_SECONDS seconds"
echo "  Max queue size: $FLUX_MAX_QUEUE_SIZE"

# Start the server
python -m flux_server.server \
  --model-path "$FLUX_MODEL_PATH" \
  --device "$FLUX_DEVICE" \
  $([ "$FLUX_USE_BFLOAT16" = "true" ] && echo "--use-bfloat16") \
  $([ "$FLUX_ENABLE_MODEL_CPU_OFFLOAD" = "true" ] && echo "--enable-model-cpu-offload") \
  --host "$FLUX_SERVER_HOST" \
  --port "$FLUX_SERVER_PORT" \
  --workers "$FLUX_SERVER_WORKERS" \
  --task-timeout-seconds "$FLUX_TASK_TIMEOUT_SECONDS" \
  --max-queue-size "$FLUX_MAX_QUEUE_SIZE"
