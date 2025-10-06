"""
Pollinations.ai API integration for generating scenic destination images
"""

import aiohttp
import json
import logging
import time
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_SESSION_SSL,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)
from urllib.parse import quote

router = APIRouter()

# Initialize logger
log = logging.getLogger(__name__)

# Pollinations.ai API configuration
POLLINATIONS_BASE_URL = "https://image.pollinations.ai"
DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_STYLE = "realistic"

@router.post("/generate")
async def generate_scenic_image(
    request: Request,
    payload: dict,
    user: UserModel = Depends(get_verified_user),
):
    """
    Generate a scenic image for a destination using Pollinations.ai
    
    Expected payload:
    {
        "destination": "Santorini, Greece",
        "style": "realistic",  # realistic, artistic, cinematic, vintage
        "width": 1024,
        "height": 1024
    }
    """
    try:
        destination = payload.get("destination", "")
        style = payload.get("style", DEFAULT_STYLE)
        width = payload.get("width", 1024)
        height = payload.get("height", 1024)
        
        if not destination:
            raise HTTPException(status_code=400, detail="Destination is required")
        
        # Create a scenic prompt based on destination and style
        scenic_prompt = create_scenic_prompt(destination, style)
        
        # Construct Pollinations.ai URL with correct format
        # Pollinations.ai uses: https://image.pollinations.ai/prompt/{prompt}
        encoded_prompt = quote(scenic_prompt)
        full_url = f"{POLLINATIONS_BASE_URL}/prompt/{encoded_prompt}"
        
        log.info(f"Generating scenic image for destination: {destination}")
        log.info(f"Using prompt: {scenic_prompt}")
        
        # Make request to Pollinations.ai
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        ) as session:
            async with session.get(
                full_url,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                if response.status == 200:
                    # Get the image data
                    image_data = await response.read()
                    
                    # Return the image URL (Pollinations.ai returns the image directly)
                    return JSONResponse(content={
                        "success": True,
                        "image_url": full_url,
                        "destination": destination,
                        "prompt": scenic_prompt,
                        "style": style,
                        "dimensions": f"{width}x{height}"
                    })
                else:
                    log.error(f"Pollinations.ai API error: {response.status}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Failed to generate image: {response.status}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error generating scenic image: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating scenic image: {str(e)}"
        )

def create_scenic_prompt(destination: str, style: str) -> str:
    """Create a scenic prompt for the destination based on style"""
    
    # Base scenic elements
    scenic_elements = [
        "breathtaking landscape",
        "stunning scenery", 
        "beautiful view",
        "picturesque location",
        "majestic vista"
    ]
    
    # Style-specific modifiers
    style_modifiers = {
        "realistic": "photorealistic, high quality, detailed",
        "artistic": "artistic painting style, vibrant colors, creative",
        "cinematic": "cinematic lighting, dramatic atmosphere, movie-like",
        "vintage": "vintage film photography, retro colors, nostalgic"
    }
    
    # Get random scenic element
    import random
    scenic_element = random.choice(scenic_elements)
    
    # Build the prompt
    prompt_parts = [
        scenic_element,
        "of",
        destination,
        style_modifiers.get(style, style_modifiers["realistic"]),
        "travel photography",
        "professional quality"
    ]
    
    return ", ".join(prompt_parts)

@router.get("/styles")
async def get_available_styles():
    """Get available image generation styles"""
    return JSONResponse(content={
        "styles": [
            {
                "id": "realistic",
                "name": "Realistic",
                "description": "Photorealistic images with high detail"
            },
            {
                "id": "artistic", 
                "name": "Artistic",
                "description": "Creative artistic style with vibrant colors"
            },
            {
                "id": "cinematic",
                "description": "Cinematic lighting and dramatic atmosphere"
            },
            {
                "id": "vintage",
                "name": "Vintage",
                "description": "Retro film photography style"
            }
        ]
    })
