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
                    
                    # Return the image URL (Pollinations.ai returns the image directly)
                    return JSONResponse(content={
                        "success": True,
                        "image_url": full_url,
                        "destination": original_destination,
                        "destination_en": destination_en,
                        "prompt": scenic_prompt,
                        "style": style,
                        "dimensions": f"{width}x{height}",
                        "seed": seed
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
