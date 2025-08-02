# RunPod ComfyUI Serverless API

A RunPod serverless API for generating images using ComfyUI with the AbyssOrangeMix2 model.

## Features

- ComfyUI integration with custom workflow support
- AbyssOrangeMix2_sfw.safetensors model pre-installed
- 16GB GPU support (RTX 4090)
- Base64 image output
- Configurable parameters (prompt, steps, CFG, seed, etc.)

## API Parameters

### Input

```json
{
  "input": {
    "prompt": "your positive prompt here",
    "negative_prompt": "optional negative prompt",
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg": 7.0,
    "seed": 42,
    "model": "AbyssOrangeMix2_sfw.safetensors",
    "workflow": null
  }
}
```

### Parameters

- **prompt** (string): Positive prompt for image generation
- **negative_prompt** (string, optional): Negative prompt to avoid certain elements
- **width** (int, default: 512): Image width
- **height** (int, default: 512): Image height  
- **steps** (int, default: 20): Number of sampling steps
- **cfg** (float, default: 7.0): CFG scale for prompt adherence
- **seed** (int, default: 42): Random seed for reproducible results
- **model** (string, default: "AbyssOrangeMix2_sfw.safetensors"): Model checkpoint to use
- **workflow** (object, optional): Custom ComfyUI workflow JSON

### Output

```json
{
  "images": [
    {
      "filename": "ComfyUI_00001_.png",
      "type": "base64", 
      "data": "iVBORw0KGgoAAAANSUhEUg..."
    }
  ],
  "prompt_id": "unique-prompt-id",
  "parameters": {
    "prompt": "...",
    "negative_prompt": "...",
    "model": "...",
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg": 7.0,
    "seed": 42
  }
}
```

## Deployment Instructions

### 1. Build and Push Docker Image

```bash
# Build the image
docker build --platform linux/amd64 -t yourusername/comfyui-abyssorangemix2:latest .

# Push to registry
docker push yourusername/comfyui-abyssorangemix2:latest
```

### 2. Create RunPod Template

1. Go to [RunPod Templates](https://www.runpod.io/console/serverless/user/templates)
2. Click "New Template"
3. Configure:
   - **Template Name**: ComfyUI AbyssOrangeMix2
   - **Container Image**: `yourusername/comfyui-abyssorangemix2:latest`
   - **Container Disk**: 20GB minimum
   - **Volume Path**: `/runpod-volume` (optional)
   - **Expose HTTP Ports**: 8188 (for ComfyUI web interface)
   - **Environment Variables**: None required

### 3. Create Serverless Endpoint

1. Go to [Serverless Endpoints](https://www.runpod.io/console/serverless/user/endpoints)
2. Click "New Endpoint"
3. Configure:
   - **Endpoint Name**: ComfyUI AbyssOrangeMix2 API
   - **Select Template**: Choose your created template
   - **Min Workers**: 0
   - **Max Workers**: 3
   - **Idle Timeout**: 5 minutes
   - **GPU Type**: RTX 4090 (16GB VRAM)
   - **Max Execution Time**: 300 seconds

### 4. Test the Endpoint

#### Using cURL:

```bash
curl -X POST \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "input": {
      "prompt": "beautiful anime girl, detailed face, high quality, masterpiece",
      "negative_prompt": "nsfw, nude, naked, porn, explicit, low quality, blurry",
      "width": 512,
      "height": 512,
      "steps": 20,
      "cfg": 7.0,
      "seed": 42
    }
  }' \\
  https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync
```

#### Using Python:

```python
import requests
import base64
import json

def generate_image(prompt, api_key, endpoint_id):
    url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "input": {
            "prompt": prompt,
            "negative_prompt": "nsfw, nude, naked, porn, explicit, low quality, blurry",
            "width": 512,
            "height": 512,
            "steps": 20,
            "cfg": 7.0,
            "seed": 42
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        if 'output' in result and 'images' in result['output']:
            # Decode base64 image
            image_data = base64.b64decode(result['output']['images'][0]['data'])
            with open('generated_image.png', 'wb') as f:
                f.write(image_data)
            print("Image saved as generated_image.png")
        return result
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Usage
api_key = "YOUR_API_KEY"
endpoint_id = "YOUR_ENDPOINT_ID"
prompt = "beautiful anime girl, detailed face, high quality, masterpiece"

result = generate_image(prompt, api_key, endpoint_id)
```

## Local Testing

Test locally before deployment:

```bash
# Install dependencies
pip install runpod requests pillow websocket-client

# Run local test
python handler.py --test_input '{"input": {"prompt": "beautiful anime girl, detailed face, high quality, masterpiece"}}'
```

## Custom Workflows

You can also provide custom ComfyUI workflows by including the `workflow` parameter in your request:

```json
{
  "input": {
    "workflow": {
      "3": {
        "inputs": {
          "seed": 42,
          "steps": 20,
          "cfg": 7.0,
          "sampler_name": "euler",
          "scheduler": "normal", 
          "denoise": 1.0,
          "model": ["4", 0],
          "positive": ["6", 0],
          "negative": ["7", 0],
          "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
      }
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Model not found**: Ensure the model file is properly downloaded during Docker build
2. **Memory errors**: Use appropriate GPU with sufficient VRAM (16GB recommended)
3. **Timeout errors**: Increase max execution time for complex generations
4. **WebSocket connection failed**: Check ComfyUI server startup logs

### Logs

Check RunPod endpoint logs for detailed error information and debugging.

## Model Information

**AbyssOrangeMix2_sfw.safetensors**
- Type: Stable Diffusion 1.5 checkpoint
- Size: ~4GB
- Source: [WarriorMama777/OrangeMixs](https://huggingface.co/WarriorMama777/OrangeMixs)
- License: Check model repository for license terms
- Specialty: Anime-style image generation (SFW version)

## Cost Estimation

- GPU: RTX 4090 (~$0.30-0.50 per minute)
- Typical generation: 20-60 seconds
- Cost per image: ~$0.10-0.50
- Idle timeout: 5 minutes (helps reduce costs)# runpoditoTESTE
