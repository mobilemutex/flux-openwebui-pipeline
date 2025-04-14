# Installation Guide

This guide provides detailed instructions for installing and setting up the Open-WebUI integration with a local FLUX.1-dev model.

## Prerequisites

Before installation, ensure you have the following prerequisites:

### Server Machine (with NVIDIA GPU)

- Linux operating system (Ubuntu 20.04 or newer recommended)
- NVIDIA GPU with at least 8GB VRAM
- CUDA drivers and toolkit (11.8 or newer)
- Python 3.10 or higher
- Git

### Client Machine (running Open-WebUI)

- Open-WebUI installation
- Network connectivity to the server machine

## Step 1: Download the FLUX.1-dev Model

If you haven't already downloaded the FLUX.1-dev model from Hugging Face, you'll need to do so:

1. Ensure you have git-lfs installed:
   ```bash
   apt-get install git-lfs
   git lfs install
   ```

2. Clone the FLUX.1-dev model repository:
   ```bash
   mkdir -p models
   git clone https://huggingface.co/black-forest-labs/FLUX.1-dev models/FLUX.1-dev
   ```

## Step 2: Install the Flux Server

1. Clone the simplified-flux-integration repository:
   ```bash
   git clone https://github.com/yourusername/simplified-flux-integration.git
   cd simplified-flux-integration
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   pip install diffusers transformers accelerate fastapi uvicorn
   ```

4. Install the Flux Server package:
   ```bash
   pip install -e src/
   ```

5. Configure the server by setting environment variables or editing the start script:
   ```bash
   export FLUX_MODEL_PATH="/path/to/your/models/FLUX.1-dev"
   export FLUX_SERVER_PORT="8000"
   ```

6. Start the server:
   ```bash
   chmod +x src/flux_server/start.sh
   src/flux_server/start.sh
   ```

7. Verify the server is running:
   ```bash
   curl http://localhost:8000/api/health
   ```

## Step 3: Install the Open-WebUI Pipeline Connector

1. Navigate to your Open-WebUI installation directory:
   ```bash
   cd /path/to/open-webui
   ```

2. Create a directory for the Flux pipeline connector:
   ```bash
   mkdir -p pipelines/flux_pipeline_connector
   ```

3. Copy the pipeline connector files:
   ```bash
   cp -r /path/to/simplified-flux-integration/src/open_webui_pipeline/* pipelines/flux_pipeline_connector/
   ```

4. Install required dependencies for the connector:
   ```bash
   pip install aiohttp
   ```

5. Configure the connector by setting environment variables:
   ```bash
   export FLUX_SERVER_URL="http://your-server-ip:8000"
   ```

## Step 4: Configure Open-WebUI

1. Edit the Open-WebUI configuration file to register the pipeline:
   ```yaml
   # In config.yaml or similar
   pipelines:
     flux:
       module: flux_pipeline_connector
       function: process_chat_completion
       models:
         - flux-generate
   ```

2. Add the model to the models configuration:
   ```yaml
   # In models.yaml or similar
   models:
     - name: flux-generate
       type: external
       description: "Flux Image Generation (NVIDIA GPU)"
       context_length: 4096
       pipeline: flux
   ```

3. Restart Open-WebUI to apply the changes.

## Step 5: Verify the Installation

1. Open the Open-WebUI interface in your browser.

2. Select the "flux-generate" model from the model selection dropdown.

3. Enter a test prompt:
   ```
   Generate an image of a beautiful sunset over mountains
   ```

4. Submit the prompt and verify that an image is generated.

## Troubleshooting Installation Issues

### Server Installation Issues

- **CUDA not found**: Ensure CUDA is properly installed and visible to Python:
  ```bash
  python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name())"
  ```

- **Model loading fails**: Check that the model path is correct and all model files are present:
  ```bash
  ls -la $FLUX_MODEL_PATH
  ```

- **Port already in use**: Change the port in the configuration:
  ```bash
  export FLUX_SERVER_PORT="8001"
  ```

### Pipeline Connector Issues

- **Cannot connect to server**: Verify network connectivity and server URL:
  ```bash
  curl http://your-server-ip:8000/api/health
  ```

- **Module not found errors**: Ensure all dependencies are installed:
  ```bash
  pip install aiohttp
  ```

- **Pipeline not registered**: Check Open-WebUI configuration files for correct syntax.

## System Requirements

### Minimum Requirements

- **CPU**: 4 cores
- **RAM**: 16GB
- **GPU**: NVIDIA GPU with 8GB VRAM
- **Storage**: 10GB free space for the model and software

### Recommended Requirements

- **CPU**: 8+ cores
- **RAM**: 32GB
- **GPU**: NVIDIA GPU with 16GB+ VRAM (RTX 3080 or better)
- **Storage**: 20GB+ SSD storage

## Next Steps

After installation, refer to the [User Guide](./USER_GUIDE.md) for information on how to use the integration effectively, including prompt engineering tips and parameter optimization.
