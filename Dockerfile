# Use the specified PyTorch base image for RunPod
FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Set working directory
WORKDIR /

# Update system packages
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    runpod \
    requests \
    pillow \
    websocket-client

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI

# Install ComfyUI requirements
RUN cd /ComfyUI && pip install -r requirements.txt

# Create models directory structure
RUN mkdir -p /ComfyUI/models/checkpoints

# Download the AbyssOrangeMix2 model
RUN cd /ComfyUI/models/checkpoints && \
    wget -O AbyssOrangeMix2_sfw.safetensors \
    "https://huggingface.co/WarriorMama777/OrangeMixs/resolve/main/Models/AbyssOrangeMix2/AbyssOrangeMix2_sfw.safetensors"

# Copy the handler script
COPY handler.py /handler.py

# Set environment variables
ENV PYTHONPATH="/ComfyUI:${PYTHONPATH}"
ENV COMFYUI_PATH="/ComfyUI"

# Start the container
CMD ["python", "-u", "/handler.py"]