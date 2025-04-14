# simplified-flux-integration

A simplified integration between Open-WebUI and a local FLUX.1-dev model using the diffusers library's FluxPipeline module.

## Overview

This project provides a streamlined way to use a local FLUX.1-dev model with Open-WebUI for image generation. It consists of two main components:

1. **Flux Server**: A FastAPI-based server that loads the local FLUX.1-dev model using the diffusers library's FluxPipeline module and exposes a REST API for image generation.

2. **Open-WebUI Pipeline Connector**: A connector that integrates with Open-WebUI's pipeline system to send image generation requests to the Flux Server and display the results.

## Documentation

For detailed information, please refer to the following documentation:

- [Installation Guide](docs/INSTALLATION.md): Step-by-step instructions for installing and setting up the integration
- [User Guide](docs/USER_GUIDE.md): Instructions for using the integration, including prompt engineering tips
- [Developer Guide](docs/DEVELOPER_GUIDE.md): Technical information for developers who want to understand or extend the integration
- [Main Documentation](docs/README.md): Comprehensive documentation covering all aspects of the integration

## Quick Start

1. **Install the Flux Server**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Flux Server**:
   ```bash
   export FLUX_MODEL_PATH="/path/to/your/FLUX.1-dev"
   cd src
   chmod +x flux_server/start.sh
   flux_server/start.sh
   ```

3. **Install the Open-WebUI Pipeline Connector**:
   ```bash
   cp -r src/open_webui_pipeline /path/to/open-webui/pipelines/flux_pipeline_connector
   ```

4. **Configure Open-WebUI** to use the pipeline connector (see Installation Guide for details)

5. **Generate images** using the "flux-generate" model in Open-WebUI

## Features

- Uses the local FLUX.1-dev model for image generation
- Simplified server architecture with efficient memory management
- Asynchronous task processing for better responsiveness
- Customizable generation parameters
- Comprehensive error handling and logging
- Extensive documentation and test suite

## Requirements

- Linux with NVIDIA GPU(s)
- CUDA drivers and toolkit
- Python 3.10 or higher
- PyTorch with CUDA support
- diffusers library (0.33.1 or newer)
- Open-WebUI installation

## License

This project is licensed under the MIT License - see the LICENSE file for details.
