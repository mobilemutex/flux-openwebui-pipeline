# Open-WebUI Integration with Local FLUX.1-dev Model

This documentation provides comprehensive information about the integration between Open-WebUI and a local FLUX.1-dev model using the diffusers library's FluxPipeline module.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)

## Overview

This integration allows Open-WebUI users to generate images using a local FLUX.1-dev model through a simplified server architecture. The integration consists of two main components:

1. **Flux Server**: A FastAPI-based server that loads the local FLUX.1-dev model using the diffusers library's FluxPipeline module and exposes a REST API for image generation.

2. **Open-WebUI Pipeline Connector**: A connector that integrates with Open-WebUI's pipeline system to send image generation requests to the Flux Server and display the results.

The integration is designed to be simple, efficient, and easy to set up, focusing on the core functionality of image generation without implementing all the features of the full Flux project.

## Architecture

The integration follows a client-server architecture:

```
┌─────────────┐     HTTP     ┌─────────────┐    Queue    ┌─────────────┐
│             │   Request    │             │   Request   │             │
│  Open-WebUI │ ───────────> │  Flux       │ ───────────>│  Task Queue │
│  Pipeline   │              │   Server    │             │             │
│             │ <───────────┐│             │<────────────│             │
└─────────────┘   Response   └─────────────┘   Results   └──────┬──────┘
                                                                │
                                                                │ Process
                                                                │ Request
                                                                ▼
                                                         ┌─────────────┐
                                                         │             │
                                                         │    Model    │
                                                         │   Manager   │
                                                         │             │
                                                         └──────┬──────┘
                                                                │
                                                                │ Load
                                                                │ Model
                                                                ▼
                                                         ┌─────────────┐
                                                         │             │
                                                         │   Local     │
                                                         │ FLUX.1-dev  │
                                                         │   Model     │
                                                         │             │
                                                         └─────────────┘
```

### Key Components:

1. **Open-WebUI Pipeline Connector**: Processes requests from Open-WebUI, extracts parameters, and communicates with the Flux Server.

2. **Flux Server**: Manages the image generation process, including:
   - **REST API**: Exposes endpoints for generation, status checking, and image retrieval.
   - **Task Queue**: Manages asynchronous image generation tasks.
   - **Model Manager**: Handles loading and using the local FLUX.1-dev model.

3. **FluxPipeline**: The diffusers library component that interfaces with the local FLUX.1-dev model.

## Requirements

### Server Requirements:

- Linux with NVIDIA GPU(s)
- CUDA drivers and toolkit
- Python 3.10 or higher
- PyTorch with CUDA support
- diffusers library (0.33.1 or newer)
- FastAPI and Uvicorn
- Local FLUX.1-dev model files

### Client Requirements:

- Open-WebUI installation
- Network connectivity to the Flux Server

## Installation

### 1. Install the Flux Server

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/simplified-flux-integration.git
   cd simplified-flux-integration
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install the server package:
   ```bash
   cd src
   pip install -e .
   ```

### 2. Install the Open-WebUI Pipeline Connector

1. Copy the pipeline connector to your Open-WebUI installation:
   ```bash
   cp -r src/open_webui_pipeline /path/to/open-webui/pipelines/flux_pipeline_connector
   ```

2. Register the pipeline in Open-WebUI's configuration:
   ```yaml
   # In Open-WebUI configuration file
   pipelines:
     flux:
       module: flux_pipeline_connector
       function: process_chat_completion
       models:
         - flux-generate
   ```

3. Add the model to the models configuration:
   ```yaml
   # In Open-WebUI models configuration
   models:
     - name: flux-generate
       type: external
       description: "Flux Image Generation (NVIDIA GPU)"
       context_length: 4096
       pipeline: flux
   ```

## Configuration

### Flux Server Configuration

The Flux Server can be configured using environment variables or command-line arguments:

| Environment Variable | Command-Line Argument | Description | Default |
|----------------------|----------------------|-------------|---------|
| `FLUX_MODEL_PATH` | `--model-path` | Path to the local FLUX.1-dev model | `./models/FLUX.1-dev` |
| `FLUX_DEVICE` | `--device` | Device to run the model on (cuda or cpu) | `cuda` |
| `FLUX_USE_BFLOAT16` | `--use-bfloat16` | Use bfloat16 precision | `true` |
| `FLUX_ENABLE_MODEL_CPU_OFFLOAD` | `--enable-model-cpu-offload` | Enable model CPU offloading | `true` |
| `FLUX_SERVER_HOST` | `--host` | Host to bind to | `0.0.0.0` |
| `FLUX_SERVER_PORT` | `--port` | Port to listen on | `8000` |
| `FLUX_SERVER_WORKERS` | `--workers` | Number of worker processes | `1` |
| `FLUX_TASK_TIMEOUT_SECONDS` | `--task-timeout-seconds` | Task timeout in seconds | `600` |
| `FLUX_MAX_QUEUE_SIZE` | `--max-queue-size` | Maximum queue size | `10` |

### Open-WebUI Pipeline Connector Configuration

The pipeline connector can be configured using environment variables:

| Environment Variable | Description | Default |
|----------------------|-------------|---------|
| `FLUX_SERVER_URL` | URL of the Flux Server | `http://localhost:8000` |
| `FLUX_DEFAULT_WIDTH` | Default image width | `1024` |
| `FLUX_DEFAULT_HEIGHT` | Default image height | `1024` |
| `FLUX_DEFAULT_STEPS` | Default number of inference steps | `50` |
| `FLUX_DEFAULT_GUIDANCE` | Default guidance scale | `3.5` |
| `FLUX_POLLING_INTERVAL` | Interval for polling the server (seconds) | `1.0` |
| `FLUX_MAX_RETRIES` | Maximum number of retries | `60` |
| `FLUX_TIMEOUT_SECONDS` | Timeout for requests (seconds) | `30` |

## Usage

### Starting the Flux Server

1. Start the server using the provided script:
   ```bash
   cd simplified-flux-integration
   src/flux_server/start.sh
   ```

   Or manually:
   ```bash
   python -m flux_server.server --model-path /path/to/your/FLUX.1-dev
   ```

2. Verify the server is running by checking the health endpoint:
   ```bash
   curl http://localhost:8000/api/health
   ```

### Using the Integration in Open-WebUI

1. Open the Open-WebUI interface in your browser.

2. Select the "flux-generate" model from the model selection dropdown.

3. Enter a prompt to generate an image, for example:
   ```
   Generate an image of a beautiful sunset over mountains
   ```

4. For custom parameters, include them in your prompt:
   ```
   Generate an image of a beautiful sunset over mountains with parameters:
   width: 1024
   height: 768
   steps: 50
   guidance: 3.5
   seed: 42
   ```

5. Submit the prompt and wait for the image to be generated.

## API Reference

### Flux Server API

#### Generate an Image

```
POST /api/generate
```

Request body:
```json
{
  "prompt": "A beautiful sunset over mountains",
  "height": 1024,
  "width": 1024,
  "num_inference_steps": 50,
  "guidance_scale": 3.5,
  "negative_prompt": "blurry, low quality",
  "seed": 42
}
```

Response:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "expected_time_seconds": 30
}
```

#### Check Task Status

```
GET /api/status/{task_id}
```

Response:
```json
{
  "status": "processing",
  "progress": 50,
  "error": null,
  "created_at": 1618456789.0,
  "updated_at": 1618456799.0
}
```

#### Retrieve Generated Image

```
GET /api/image/{task_id}?base64_format=true
```

Response:
- If `base64_format=true`: Base64-encoded image data as text
- If `base64_format=false`: Binary image data with Content-Type: image/jpeg

#### Check Server Health

```
GET /api/health
```

Response:
```json
{
  "status": "ok",
  "model_loaded": true,
  "queue_size": 2
}
```

## Troubleshooting

### Common Issues

#### Server Won't Start

- Check if the model path is correct
- Verify CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`
- Check for sufficient GPU memory
- Look for error messages in the server logs

#### Generation Fails

- Check server logs for error messages
- Verify the model is loaded correctly
- Try reducing image dimensions or number of steps
- Check for CUDA out-of-memory errors

#### Open-WebUI Can't Connect to Server

- Verify the server is running
- Check the `FLUX_SERVER_URL` environment variable
- Ensure network connectivity between Open-WebUI and the server
- Check for firewall rules blocking the connection

#### Poor Image Quality

- Increase the number of inference steps (e.g., 50-100)
- Adjust the guidance scale (typically 3.0-7.0)
- Improve your prompt with more details
- Try different image dimensions

### Getting Help

If you encounter issues not covered here, please:

1. Check the server logs for error messages
2. Verify your configuration
3. Run the test scripts to diagnose issues
4. Open an issue on the GitHub repository with detailed information about your problem
