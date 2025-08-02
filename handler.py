import runpod
import json
import os
import sys
import uuid
import time
import base64
import io
from PIL import Image
import requests
import subprocess
import websocket
import threading
from runpod.serverless.utils.rp_cleanup import clean

# Add ComfyUI to Python path
sys.path.append('/ComfyUI')

# ComfyUI server settings
COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_WS_URL = "ws://127.0.0.1:8188/ws"

class ComfyUIClient:
    def __init__(self):
        self.client_id = str(uuid.uuid4())
        self.ws = None
        
    def start_comfyui_server(self):
        """Start ComfyUI server in background"""
        print("Starting ComfyUI server...")
        try:
            # Start ComfyUI server
            cmd = [
                "python", "/ComfyUI/main.py",
                "--listen", "127.0.0.1",
                "--port", "8188",
                "--dont-upcast-attention",
                "--use-split-cross-attention"
            ]
            
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd="/ComfyUI"
            )
            
            # Wait for server to start
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
                    if response.status_code == 200:
                        print("ComfyUI server started successfully")
                        return True
                except:
                    time.sleep(2)
                    print(f"Waiting for ComfyUI server... ({i+1}/{max_retries})")
            
            print("Failed to start ComfyUI server")
            return False
            
        except Exception as e:
            print(f"Error starting ComfyUI server: {e}")
            return False
    
    def connect_websocket(self):
        """Connect to ComfyUI WebSocket"""
        try:
            self.ws = websocket.WebSocket()
            self.ws.connect(f"{COMFYUI_WS_URL}?clientId={self.client_id}")
            return True
        except Exception as e:
            print(f"Error connecting to WebSocket: {e}")
            return False
    
    def queue_prompt(self, prompt):
        """Queue a prompt for execution"""
        try:
            data = {"prompt": prompt, "client_id": self.client_id}
            response = requests.post(f"{COMFYUI_URL}/prompt", json=data)
            return response.json()
        except Exception as e:
            print(f"Error queuing prompt: {e}")
            return None
    
    def get_image(self, filename, subfolder, folder_type):
        """Get generated image"""
        try:
            data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
            response = requests.get(f"{COMFYUI_URL}/view", params=data)
            return response.content
        except Exception as e:
            print(f"Error getting image: {e}")
            return None
    
    def wait_for_completion(self, prompt_id):
        """Wait for prompt completion via WebSocket"""
        try:
            while True:
                out = self.ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            break  # Execution is done
            return True
        except Exception as e:
            print(f"Error waiting for completion: {e}")
            return False
    
    def get_history(self, prompt_id):
        """Get execution history"""
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
            return response.json()
        except Exception as e:
            print(f"Error getting history: {e}")
            return None

# Initialize ComfyUI client
comfy_client = ComfyUIClient()

def create_default_workflow(prompt_text, model_name="AbyssOrangeMix2_sfw.safetensors"):
    """Create a default text-to-image workflow"""
    workflow = {
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
            "class_type": "KSampler",
            "_meta": {
                "title": "KSampler"
            }
        },
        "4": {
            "inputs": {
                "ckpt_name": model_name
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {
                "title": "Load Checkpoint"
            }
        },
        "5": {
            "inputs": {
                "width": 512,
                "height": 512,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage",
            "_meta": {
                "title": "Empty Latent Image"
            }
        },
        "6": {
            "inputs": {
                "text": prompt_text,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "CLIP Text Encode (Prompt)"
            }
        },
        "7": {
            "inputs": {
                "text": "nsfw, nude, naked, porn, explicit",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "CLIP Text Encode (Negative)"
            }
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode",
            "_meta": {
                "title": "VAE Decode"
            }
        },
        "9": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["8", 0]
            },
            "class_type": "SaveImage",
            "_meta": {
                "title": "Save Image"
            }
        }
    }
    return workflow

def handler(event):
    """
    RunPod serverless handler for ComfyUI
    """
    try:
        input_data = event.get("input", {})
        
        # Extract parameters
        prompt = input_data.get("prompt", "beautiful landscape")
        workflow = input_data.get("workflow")
        model = input_data.get("model", "AbyssOrangeMix2_sfw.safetensors")
        width = input_data.get("width", 512)
        height = input_data.get("height", 512)
        steps = input_data.get("steps", 20)
        cfg = input_data.get("cfg", 7.0)
        seed = input_data.get("seed", 42)
        negative_prompt = input_data.get("negative_prompt", "nsfw, nude, naked, porn, explicit")
        
        print(f"Processing request with prompt: {prompt}")
        
        # Start ComfyUI server if not already running
        if not comfy_client.start_comfyui_server():
            return {"error": "Failed to start ComfyUI server"}
        
        # Connect to WebSocket
        if not comfy_client.connect_websocket():
            return {"error": "Failed to connect to ComfyUI WebSocket"}
        
        # Use provided workflow or create default one
        if workflow is None:
            workflow = create_default_workflow(prompt, model)
            
            # Update workflow parameters
            workflow["3"]["inputs"]["seed"] = seed
            workflow["3"]["inputs"]["steps"] = steps
            workflow["3"]["inputs"]["cfg"] = cfg
            workflow["5"]["inputs"]["width"] = width
            workflow["5"]["inputs"]["height"] = height
            workflow["6"]["inputs"]["text"] = prompt
            workflow["7"]["inputs"]["text"] = negative_prompt
        
        # Queue the prompt
        prompt_response = comfy_client.queue_prompt(workflow)
        if not prompt_response:
            return {"error": "Failed to queue prompt"}
        
        prompt_id = prompt_response['prompt_id']
        print(f"Prompt queued with ID: {prompt_id}")
        
        # Wait for completion
        if not comfy_client.wait_for_completion(prompt_id):
            return {"error": "Failed to complete generation"}
        
        # Get the result
        history = comfy_client.get_history(prompt_id)
        if not history:
            return {"error": "Failed to get generation history"}
        
        # Extract images from history
        images = []
        if prompt_id in history:
            for node_id in history[prompt_id]['outputs']:
                node_output = history[prompt_id]['outputs'][node_id]
                if 'images' in node_output:
                    for image_info in node_output['images']:
                        image_data = comfy_client.get_image(
                            image_info['filename'], 
                            image_info['subfolder'], 
                            image_info['type']
                        )
                        if image_data:
                            # Convert to base64
                            image_base64 = base64.b64encode(image_data).decode('utf-8')
                            images.append({
                                "filename": image_info['filename'],
                                "type": "base64",
                                "data": image_base64
                            })
        
        # Close WebSocket connection
        if comfy_client.ws:
            comfy_client.ws.close()
        
        # Cleanup
        clean(["temp", "output"])
        
        return {
            "images": images,
            "prompt_id": prompt_id,
            "parameters": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "model": model,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg": cfg,
                "seed": seed
            }
        }
        
    except Exception as e:
        print(f"Error in handler: {e}")
        # Cleanup on error
        clean(["temp", "output"])
        return {"error": str(e)}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})