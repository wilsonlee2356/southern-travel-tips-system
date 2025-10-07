"""
Pollinations.ai API integration for generating scenic destination images
"""

import aiohttp
import json
import logging
import time
import io
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any
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

# Import PIL for image editing
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    log.warning("PIL/Pillow not available. Image editing features will be disabled.")

router = APIRouter()

# Initialize logger
log = logging.getLogger(__name__)

# Pollinations.ai API configuration
POLLINATIONS_BASE_URL = "https://image.pollinations.ai"
DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_STYLE = "realistic"

# Chinese to English destination mapper
DESTINATION_MAPPER = {
    # Asian cities
    "東京": "Tokyo",
    "首爾": "Seoul",
    "曼谷": "Bangkok",
    "新加坡": "Singapore",
    "香港": "Hong Kong",
    "台北": "Taipei",
    "大阪": "Osaka",
    "京都": "Kyoto",
    "上海": "Shanghai",
    "北京": "Beijing",
    "胡志明市": "Ho Chi Minh City",
    "河內": "Hanoi",
    "吉隆坡": "Kuala Lumpur",
    "馬尼拉": "Manila",
    "雅加達": "Jakarta",
    "峇里": "Bali",
    "普吉島": "Phuket",
    "清邁": "Chiang Mai",
    "芭堤雅": "Pattaya",
    "濟州島": "Jeju Island",
    
    # European cities
    "巴黎": "Paris",
    "倫敦": "London",
    "羅馬": "Rome",
    "巴塞隆納": "Barcelona",
    "阿姆斯特丹": "Amsterdam",
    "柏林": "Berlin",
    "維也納": "Vienna",
    "布拉格": "Prague",
    "威尼斯": "Venice",
    "佛羅倫斯": "Florence",
    "米蘭": "Milan",
    "馬德里": "Madrid",
    "里斯本": "Lisbon",
    "雅典": "Athens",
    "伊斯坦堡": "Istanbul",
    "布達佩斯": "Budapest",
    "慕尼黑": "Munich",
    "蘇黎世": "Zurich",
    "日內瓦": "Geneva",
    "愛丁堡": "Edinburgh",
    "都柏林": "Dublin",
    "哥本哈根": "Copenhagen",
    "斯德哥爾摩": "Stockholm",
    "奧斯陸": "Oslo",
    "赫爾辛基": "Helsinki",
    
    # North American cities
    "紐約": "New York",
    "洛杉磯": "Los Angeles",
    "舊金山": "San Francisco",
    "拉斯維加斯": "Las Vegas",
    "芝加哥": "Chicago",
    "西雅圖": "Seattle",
    "波士頓": "Boston",
    "邁阿密": "Miami",
    "溫哥華": "Vancouver",
    "多倫多": "Toronto",
    "蒙特婁": "Montreal",
    "墨西哥城": "Mexico City",
    "坎昆": "Cancun",
    
    # Oceania cities
    "雪梨": "Sydney",
    "墨爾本": "Melbourne",
    "奧克蘭": "Auckland",
    "黃金海岸": "Gold Coast",
    "布里斯本": "Brisbane",
    
    # Middle Eastern cities
    "杜拜": "Dubai",
    "阿布達比": "Abu Dhabi",
    "耶路撒冷": "Jerusalem",
    "特拉維夫": "Tel Aviv",
    
    # African cities
    "開普敦": "Cape Town",
    "約翰尼斯堡": "Johannesburg",
    "馬拉喀什": "Marrakech",
    "開羅": "Cairo",
    
    # South American cities
    "里約熱內盧": "Rio de Janeiro",
    "聖保羅": "Sao Paulo",
    "布宜諾斯艾利斯": "Buenos Aires",
    "利馬": "Lima",
    "聖地亞哥": "Santiago",
}

def translate_destination(destination: str) -> str:
    """
    Translate Chinese destination names to English.
    If the destination is already in English or not in the mapper, return as-is.
    """
    # Check if the destination is in the mapper
    if destination in DESTINATION_MAPPER:
        translated = DESTINATION_MAPPER[destination]
        log.info(f"Translated destination: {destination} -> {translated}")
        return translated
    
    # Check if it contains Chinese characters
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in destination)
    if has_chinese:
        # Try to find partial matches in the mapper
        for chinese_key, english_value in DESTINATION_MAPPER.items():
            if chinese_key in destination:
                translated = destination.replace(chinese_key, english_value)
                log.info(f"Partially translated destination: {destination} -> {translated}")
                return translated
        
        log.warning(f"Chinese destination '{destination}' not found in mapper, using as-is")
    
    return destination

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
        
        # Translate Chinese destination to English if needed
        original_destination = destination
        destination_en = translate_destination(destination)
        
        # Create a scenic prompt based on destination and style (use English destination)
        scenic_prompt = create_scenic_prompt(destination_en, style)
        
        # Construct Pollinations.ai URL with correct format
        # Pollinations.ai uses: https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width={width}&height={height}&nologo=true
        # Add a seed based on current timestamp to ensure unique images for each request
        import time
        seed = int(time.time() * 1000)  # Use milliseconds for more uniqueness
        
        encoded_prompt = quote(scenic_prompt)
        full_url = f"{POLLINATIONS_BASE_URL}/prompt/{encoded_prompt}?seed={seed}&width={width}&height={height}&nologo=true"
        
        log.info(f"Generating scenic image for destination: {original_destination} (translated to: {destination_en})")
        log.info(f"Using seed: {seed}")
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
                    
                    # Automatically edit the image to add light blue rectangle at bottom
                    log.info(f"PIL_AVAILABLE: {PIL_AVAILABLE}")
                    log.info(f"Image data size: {len(image_data)} bytes")
                    
                    if PIL_AVAILABLE:
                        try:
                            log.info("Starting image editing process...")
                            edited_image_data = _add_bottom_banner(image_data, width, height)
                            log.info(f"Successfully added bottom banner to generated image. Edited size: {len(edited_image_data)} bytes")
                        except Exception as e:
                            log.error(f"Failed to edit image, using original: {e}")
                            log.exception("Full error details:")
                            edited_image_data = image_data
                    else:
                        log.warning("PIL not available, using original image")
                        edited_image_data = image_data
                    
                    # Return the edited image as base64
                    return JSONResponse(content={
                        "success": True,
                        "image_url": full_url,
                        "image_base64": f"data:image/jpeg;base64,{base64.b64encode(edited_image_data).decode()}",
                        "destination": original_destination,
                        "destination_en": destination_en,
                        "prompt": scenic_prompt,
                        "style": style,
                        "dimensions": f"{width}x{height}",
                        "seed": seed,
                        "edited": True
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
    """Create a detailed scenic prompt for the destination based on style"""
    
    # Use the detailed photorealistic prompt template in Chinese
    prompt = f"Generate a photorealistic daytime scene of a prominent tourist spot in {destination}, emphasizing its most iconic and distinct feature and authentic surroundings. Capture the full view of the landmark from its most famous vantage point, showcasing its unique architectural or natural details against a clear blue sky with a few scattered, fluffy white clouds. The foreground includes the actual surrounding environment—specific vegetation, pathways, water features, or nearby buildings as they exist around the landmark—populated with diverse tourists taking photos, walking, or relaxing. Integrate authentic local elements, such as street vendors selling regional food, local signage, or culturally relevant items like bicycles or vehicles parked naturally. The lighting is natural, with soft sunlight casting accurate shadows that highlight the textures of the landmark’s distinct feature and its surroundings, evoking a vivid springtime atmosphere. Ensure every element, from the landmark’s unique materials to the crowd’s clothing, accurately reflects the real-world setting of {destination} for maximum realism."
    
    return prompt

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

@router.get("/test-edit")
async def test_image_editing():
    """Test endpoint to verify image editing is working"""
    if not PIL_AVAILABLE:
        return JSONResponse(content={
            "success": False,
            "error": "PIL not available",
            "pil_available": False
        })
    
    try:
        # Create a simple test image
        test_image = Image.new('RGB', (400, 300), (255, 255, 255))
        draw = ImageDraw.Draw(test_image)
        
        # Add some content
        draw.rectangle([(50, 50), (350, 250)], fill=(200, 200, 200))
        draw.text((100, 150), "Test Image", fill=(0, 0, 0))
        
        # Convert to bytes
        output = io.BytesIO()
        test_image.save(output, format='JPEG')
        test_image_bytes = output.getvalue()
        
        # Test the banner function
        edited_bytes = _add_bottom_banner(test_image_bytes, 400, 300)
        
        # Convert to base64
        base64_data = base64.b64encode(edited_bytes).decode()
        
        return JSONResponse(content={
            "success": True,
            "pil_available": True,
            "original_size": len(test_image_bytes),
            "edited_size": len(edited_bytes),
            "test_image_base64": f"data:image/jpeg;base64,{base64_data}"
        })
        
    except Exception as e:
        log.exception("Test image editing failed:")
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "pil_available": True
        })

@router.post("/edit")
async def edit_image(
    request: Request,
    payload: dict,
    user: UserModel = Depends(get_verified_user),
):
    """
    Edit an image by adding overlays (rectangles, text, logos)
    
    Expected payload:
    {
        "image_source": "url" or "file",  # Source type
        "image_url": "https://...",       # If source is "url"
        "image_path": "path/to/image",    # If source is "file" (relative to project root)
        "image_base64": "data:image/...", # Alternative: base64 encoded image
        "edits": [
            {
                "type": "rectangle",
                "position": [x, y, width, height],
                "color": "purple" or [R, G, B, A],
                "opacity": 0.8  # Optional, 0-1
            },
            {
                "type": "text",
                "text": "Hello World",
                "position": [x, y],
                "color": "red" or [R, G, B],
                "font_size": 40,
                "font_family": "arial.ttf",  # Optional
                "align": "left"  # left, center, right
            },
            {
                "type": "logo",
                "logo_path": "path/to/logo.png",  # Relative to project root
                "logo_url": "https://...",        # Alternative: URL
                "position": [x, y],
                "size": [width, height],  # Optional, will resize
                "opacity": 1.0  # Optional, 0-1
            }
        ],
        "output_format": "base64" or "url",  # How to return the edited image
        "quality": 95  # JPEG quality, 1-100
    }
    """
    
    if not PIL_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="Image editing is not available. PIL/Pillow is not installed."
        )
    
    try:
        # Extract parameters
        image_source = payload.get("image_source", "url")
        image_url = payload.get("image_url")
        image_path = payload.get("image_path")
        image_base64_data = payload.get("image_base64")
        edits = payload.get("edits", [])
        output_format = payload.get("output_format", "base64")
        quality = payload.get("quality", 95)
        
        # Load the source image
        image = None
        
        if image_base64_data:
            # Load from base64
            if "," in image_base64_data:
                image_base64_data = image_base64_data.split(",")[1]
            image_bytes = base64.b64decode(image_base64_data)
            image = Image.open(io.BytesIO(image_bytes))
            log.info("Loaded image from base64 data")
            
        elif image_source == "url" and image_url:
            # Download from URL
            async with aiohttp.ClientSession(
                trust_env=True,
                timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
            ) as session:
                async with session.get(image_url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        image = Image.open(io.BytesIO(image_bytes))
                        log.info(f"Downloaded image from URL: {image_url}")
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to download image from URL: {response.status}"
                        )
                        
        elif image_source == "file" and image_path:
            # Load from local file
            # Security: Ensure path is within project directory
            project_root = Path(__file__).parent.parent.parent.parent
            full_path = (project_root / image_path).resolve()
            
            # Check if path is within project root (security)
            if not str(full_path).startswith(str(project_root)):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path. Path must be within project directory."
                )
            
            if not full_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Image file not found: {image_path}"
                )
            
            image = Image.open(full_path)
            log.info(f"Loaded image from file: {image_path}")
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide either image_url, image_path, or image_base64"
            )
        
        # Convert to RGBA for transparency support
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create a drawing context
        draw = ImageDraw.Draw(image)
        
        # Apply edits
        for edit in edits:
            edit_type = edit.get("type")
            
            if edit_type == "rectangle":
                position = edit.get("position", [0, 0, 100, 100])
                color = edit.get("color", "purple")
                opacity = edit.get("opacity", 1.0)
                
                # Convert color name to RGB if needed
                if isinstance(color, str):
                    color = _parse_color(color, opacity)
                elif isinstance(color, list) and len(color) == 3:
                    color = tuple(color + [int(opacity * 255)])
                
                # Draw rectangle
                x, y, w, h = position
                draw.rectangle([(x, y), (x + w, y + h)], fill=color)
                log.info(f"Added rectangle at {position} with color {color}")
                
            elif edit_type == "text":
                text = edit.get("text", "")
                position = edit.get("position", [0, 0])
                color = edit.get("color", "red")
                font_size = edit.get("font_size", 40)
                font_family = edit.get("font_family", None)
                
                # Convert color name to RGB if needed
                if isinstance(color, str):
                    color = _parse_color(color, 1.0)
                
                # Load font
                try:
                    if font_family:
                        font = ImageFont.truetype(font_family, font_size)
                    else:
                        # Try to use a default font
                        font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()
                    log.warning("Could not load custom font, using default")
                
                # Draw text
                draw.text(position, text, fill=color, font=font)
                log.info(f"Added text '{text}' at {position} with color {color}")
                
            elif edit_type == "logo":
                logo_path = edit.get("logo_path")
                logo_url = edit.get("logo_url")
                position = edit.get("position", [0, 0])
                size = edit.get("size")
                opacity = edit.get("opacity", 1.0)
                
                # Load logo
                logo = None
                if logo_url:
                    # Download logo from URL
                    async with aiohttp.ClientSession(
                        trust_env=True,
                        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
                    ) as session:
                        async with session.get(logo_url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as response:
                            if response.status == 200:
                                logo_bytes = await response.read()
                                logo = Image.open(io.BytesIO(logo_bytes))
                            else:
                                log.error(f"Failed to download logo from URL: {response.status}")
                                continue
                                
                elif logo_path:
                    # Load logo from local file
                    project_root = Path(__file__).parent.parent.parent.parent
                    full_path = (project_root / logo_path).resolve()
                    
                    if str(full_path).startswith(str(project_root)) and full_path.exists():
                        logo = Image.open(full_path)
                    else:
                        log.error(f"Logo file not found or invalid: {logo_path}")
                        continue
                
                if logo:
                    # Resize if size is specified
                    if size:
                        logo = logo.resize(size, Image.Resampling.LANCZOS)
                    
                    # Convert to RGBA for transparency
                    if logo.mode != 'RGBA':
                        logo = logo.convert('RGBA')
                    
                    # Apply opacity
                    if opacity < 1.0:
                        alpha = logo.split()[3]
                        alpha = alpha.point(lambda p: int(p * opacity))
                        logo.putalpha(alpha)
                    
                    # Paste logo onto image
                    image.paste(logo, position, logo)
                    log.info(f"Added logo at {position}")
        
        # Convert back to RGB for JPEG output
        if output_format != "png":
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3] if image.mode == 'RGBA' else None)
            image = rgb_image
        
        # Prepare output
        output = io.BytesIO()
        
        if output_format == "base64":
            # Return as base64
            image_format = "PNG" if output_format == "png" else "JPEG"
            image.save(output, format=image_format, quality=quality)
            output.seek(0)
            base64_data = base64.b64encode(output.getvalue()).decode()
            
            return JSONResponse(content={
                "success": True,
                "image_base64": f"data:image/{image_format.lower()};base64,{base64_data}",
                "format": image_format.lower(),
                "size": list(image.size)
            })
        else:
            # For now, return base64 (in future, could save to storage and return URL)
            image_format = "PNG" if output_format == "png" else "JPEG"
            image.save(output, format=image_format, quality=quality)
            output.seek(0)
            base64_data = base64.b64encode(output.getvalue()).decode()
            
            return JSONResponse(content={
                "success": True,
                "image_base64": f"data:image/{image_format.lower()};base64,{base64_data}",
                "format": image_format.lower(),
                "size": list(image.size),
                "note": "URL output not yet implemented, returning base64"
            })
            
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error editing image: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error editing image: {str(e)}"
        )

def _add_bottom_banner(image_data: bytes, width: int, height: int) -> bytes:
    """
    Add a light blue rectangle at the bottom of the image (1/4 height, 100% width)
    Similar to the Mongolia travel advertisement example
    """
    log.info(f"Adding bottom banner: requested {width}x{height} image")
    
    # Load image from bytes
    image = Image.open(io.BytesIO(image_data))
    log.info(f"Loaded image: actual size {image.size}, mode: {image.mode}")
    
    # Use ACTUAL image dimensions, not requested dimensions
    actual_width, actual_height = image.size
    
    # Calculate banner dimensions based on actual image size
    banner_height = actual_height // 4  # 1/4 of actual image height
    banner_width = actual_width         # 100% of actual image width
    banner_y = actual_height - banner_height  # Position at bottom
    
    log.info(f"Banner dimensions: {banner_width}x{banner_height} at y={banner_y}")
    
    # Convert to RGB for simpler handling
    if image.mode != 'RGB':
        image = image.convert('RGB')
        log.info(f"Converted to RGB: {image.size}, mode: {image.mode}")
    
    # Create a new image with the banner area
    # Crop the top 75% of the original image
    scenic_area = image.crop((0, 0, actual_width, banner_y))
    log.info(f"Cropped scenic area: {scenic_area.size}")
    
    # Create light blue banner area
    light_blue = (135, 206, 250)  # LightSkyBlue RGB
    banner_area = Image.new('RGB', (banner_width, banner_height), light_blue)
    log.info(f"Created banner area: {banner_area.size} with color {light_blue}")
    
    # Combine scenic area and banner area
    final_image = Image.new('RGB', (actual_width, actual_height), (255, 255, 255))
    final_image.paste(scenic_area, (0, 0))
    final_image.paste(banner_area, (0, banner_y))
    log.info(f"Combined final image: {final_image.size}")
    
    # Save to bytes
    output = io.BytesIO()
    final_image.save(output, format='JPEG', quality=95)
    output.seek(0)
    
    result_bytes = output.getvalue()
    log.info(f"Saved edited image: {len(result_bytes)} bytes")
    
    return result_bytes

def _parse_color(color_name: str, opacity: float = 1.0) -> tuple:
    """Parse color name to RGBA tuple"""
    color_map = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "purple": (128, 0, 128),
        "yellow": (255, 255, 0),
        "orange": (255, 165, 0),
        "pink": (255, 192, 203),
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "gray": (128, 128, 128),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "light_blue": (135, 206, 250),  # LightSkyBlue
    }
    
    rgb = color_map.get(color_name.lower(), (128, 0, 128))
    return rgb + (int(opacity * 255),)
