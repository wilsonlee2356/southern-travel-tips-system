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

# Import timezone utility
from open_webui.utils.timezone import get_city_gmt_string

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
    
    # Japanese cities and regions
    "名古屋": "Nagoya",
    "橫濱": "Yokohama",
    "福岡": "Fukuoka",
    "札幌": "Sapporo",
    "仙台": "Sendai",
    "廣島": "Hiroshima",
    "神戶": "Kobe",
    "沖繩": "Okinawa",
    "北海道": "Hokkaido",
    "箱根": "Hakone",
    "奈良": "Nara",
    "鎌倉": "Kamakura",
    "日光": "Nikko",
    "輕井澤": "Karuizawa",
    "河口湖": "Kawaguchiko",
    "金澤": "Kanazawa",
    "松本": "Matsumoto",
    "長崎": "Nagasaki",
    "熊本": "Kumamoto",
    "鹿兒島": "Kagoshima",
    "青森": "Aomori",
    "秋田": "Akita",
    "山形": "Yamagata",
    "福島": "Fukushima",
    "茨城": "Ibaraki",
    "栃木": "Tochigi",
    "群馬": "Gunma",
    "埼玉": "Saitama",
    "千葉": "Chiba",
    "神奈川": "Kanagawa",
    "新潟": "Niigata",
    "富山": "Toyama",
    "石川": "Ishikawa",
    "福井": "Fukui",
    "山梨": "Yamanashi",
    "長野": "Nagano",
    "岐阜": "Gifu",
    "靜岡": "Shizuoka",
    "愛知": "Aichi",
    "三重": "Mie",
    "滋賀": "Shiga",
    "和歌山": "Wakayama",
    "鳥取": "Tottori",
    "島根": "Shimane",
    "岡山": "Okayama",
    "廣島": "Hiroshima",
    "山口": "Yamaguchi",
    "德島": "Tokushima",
    "香川": "Kagawa",
    "愛媛": "Ehime",
    "高知": "Kochi",
    "佐賀": "Saga",
    "大分": "Oita",
    "宮崎": "Miyazaki",
    "高知": "Kochi",
    
    # Taiwanese cities and regions
    "高雄": "Kaohsiung",
    "台中": "Taichung",
    "台南": "Tainan",
    "新竹": "Hsinchu",
    "桃園": "Taoyuan",
    "基隆": "Keelung",
    "嘉義": "Chiayi",
    "彰化": "Changhua",
    "屏東": "Pingtung",
    "宜蘭": "Yilan",
    "花蓮": "Hualien",
    "台東": "Taitung",
    "澎湖": "Penghu",
    "金門": "Kinmen",
    "馬祖": "Matsu",
    "南投": "Nantou",
    "雲林": "Yunlin",
    "苗栗": "Miaoli",
    "新北": "New Taipei",
    
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
        "height": 1024,
        "flight_data": {  # Optional flight information
            "airline": "China Airlines",
            "startingPlace": "Hong Kong",
            "destination": "Tokyo",
            "departureDate": "2026-02-18",
            "returnDate": "2026-02-25",
            "cost": 3500,
            ...
        },
        "ai_analysis": {  # Optional AI-generated content
            "header": "【東京】春季賞櫻特惠",
            "content": "...",
            "summary": "..."
        }
    }
    """
    try:
        destination = payload.get("destination", "")
        tourist_spot = payload.get("tourist_spot", "")
        style = payload.get("style", DEFAULT_STYLE)
        width = payload.get("width", 1024)
        height = payload.get("height", 1024)
        flight_data = payload.get("flight_data", {})
        ai_analysis = payload.get("ai_analysis", {})
        
        if not destination:
            raise HTTPException(status_code=400, detail="Destination is required")
        
        # Translate Chinese destination to English if needed
        original_destination = destination
        destination_en = translate_destination(destination)
        
        # Create a scenic prompt based on destination, tourist_spot and style (use English destination)
        scenic_prompt = create_scenic_prompt(destination_en, style, tourist_spot)
        
        # Construct Pollinations.ai URL with correct format
        # Pollinations.ai uses: https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width={width}&height={height}&nologo=true
        # Add a seed based on current timestamp to ensure unique images for each request
        import time
        seed = int(time.time() * 1000)  # Use milliseconds for more uniqueness
        
        encoded_prompt = quote(scenic_prompt)
        full_url = f"{POLLINATIONS_BASE_URL}/prompt/{encoded_prompt}?seed={seed}&width={width}&height={800}&nologo=true"
        
        log.info(f"Generating scenic image for destination: {original_destination} (translated to: {destination_en})")
        log.info(f"Tourist spot received: '{tourist_spot}' (empty: {not tourist_spot})")
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
                            
                            # Extract airline and price from flight_data
                            airline_name = None
                            flight_price = None
                            
                            if flight_data:
                                # Check if it's a single flight or multiple flights
                                flights_list = flight_data.get("flights", [])
                                if flights_list:
                                    # Multiple flights - get airline from first flight and total price
                                    first_flight = flights_list[0]
                                    airline_name = first_flight.get("airline")
                                    # Calculate total price for 2-place trips, first flight price for 3+ places
                                    all_places = set()
                                    for flight in flights_list:
                                        all_places.add(flight.get("startingPlace"))
                                        all_places.add(flight.get("destination"))
                                    
                                    if len(all_places) == 2:
                                        # Total price for round trip with 2 places
                                        total_cost = sum(f.get("cost", 0) for f in flights_list)
                                        flight_price = f"{total_cost:,}" if total_cost else None
                                    else:
                                        # First flight price for 3+ places
                                        cost = first_flight.get("cost")
                                        flight_price = f"{cost:,}" if cost else None
                                else:
                                    # Single flight
                                    airline_name = flight_data.get("airline")
                                    cost = flight_data.get("cost")
                                    flight_price = f"{cost:,}" if cost else None
                            
                            log.info(f"Extracted airline: {airline_name}, price: {flight_price}")
                            
                            # Pass original Chinese destination, airline, price, and ai_analysis for display on image
                            edited_image_data = _add_bottom_banner(
                                image_data, 
                                width, 
                                height, 
                                destination=original_destination,
                                airline=airline_name,
                                price=flight_price,
                                ai_analysis=ai_analysis
                            )
                            log.info(f"Successfully added bottom banner to generated image. Edited size: {len(edited_image_data)} bytes")
                        except Exception as e:
                            log.error(f"Failed to edit image, using original: {e}")
                            log.exception("Full error details:")
                            edited_image_data = image_data
                    else:
                        log.warning("PIL not available, using original image")
                        edited_image_data = image_data
                    
                    # Load flight info image from file
                    flight_info_image_base64 = None
                    try:
                        # Try multiple possible paths for the flight info image
                        possible_paths = [
                            Path(__file__).parent.parent.parent.parent / "flight_info_screenshot.png",  # Project root
                            Path(__file__).parent.parent.parent / "flight_info_screenshot.png",  # Backend root
                            Path("/app/flight_info_screenshot.png"),  # Docker app root
                            Path("/app/backend/flight_info_screenshot.png"),  # Docker backend
                            Path("/app/backend/open_webui/static/flight_info_screenshot.png"),  # Static assets
                        ]
                        
                        flight_info_path = None
                        for path in possible_paths:
                            if path.exists():
                                flight_info_path = path
                                break
                        
                        if flight_info_path:
                            with open(flight_info_path, "rb") as f:
                                flight_info_data = f.read()
                                
                                # Add text overlay to flight info image with flight data and AI analysis
                                if PIL_AVAILABLE:
                                    try:
                                        flight_info_data = _add_text_to_flight_info(
                                            flight_info_data, 
                                            flight_data=flight_data, 
                                            ai_analysis=ai_analysis
                                        )
                                        log.info("Successfully added text to flight info image")
                                    except Exception as e:
                                        log.error(f"Failed to add text to flight info image: {e}")
                                        # Continue with original image if text addition fails
                                
                                flight_info_image_base64 = f"data:image/png;base64,{base64.b64encode(flight_info_data).decode()}"
                                log.info(f"Loaded flight info image: {flight_info_path}")
                        else:
                            log.warning(f"Flight info image not found in any of the expected locations: {possible_paths}")
                    except Exception as e:
                        log.error(f"Failed to load flight info image: {e}")
                    
                    # Return both images as base64, including original for re-editing
                    return JSONResponse(content={
                        "success": True,
                        "image_url": full_url,
                        "image_base64": f"data:image/jpeg;base64,{base64.b64encode(edited_image_data).decode()}",
                        "original_image_base64": f"data:image/jpeg;base64,{base64.b64encode(image_data).decode()}",  # Original without overlays
                        "flight_info_image_base64": flight_info_image_base64,
                        "destination": original_destination,
                        "destination_en": destination_en,
                        "prompt": scenic_prompt,
                        "style": style,
                        "dimensions": f"{width}x{height}",
                        "seed": seed,
                        "edited": True,
                        "airline": airline_name,
                        "price": flight_price
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

def create_scenic_prompt(destination: str, style: str, tourist_spot: str = "") -> str:
    """Create a detailed scenic prompt for the destination based on style"""
    
    # Use the detailed photorealistic prompt template
    # Important: The bottom 1/4 of the image will be covered by a banner, so the main subject should be in the upper portion
    
    # If tourist_spot is provided, use it in the prompt with a comma before destination
    log.info(f"🔍 create_scenic_prompt called with: destination='{destination}', tourist_spot='{tourist_spot}', style='{style}'")
    
    if tourist_spot and tourist_spot.strip():
        location_description = f"{tourist_spot}, {destination}"
        log.info(f"✅ Using tourist spot in prompt: '{tourist_spot}' → location_description: '{location_description}'")
    else:
        location_description = destination
        log.info(f"⚠️ No tourist spot provided, using only destination: '{location_description}'")
    
    prompt = f"Generate a photorealistic daytime scene of the most iconic architectural landmark of {location_description}, with the full structure prominently centered in the upper two-thirds to three-quarters of the image, highlighting its distinctive architectural details (e.g., roof design, textures, materials). Ensure the landmark occupies the upper and middle 75% of the frame as the primary focus, with its base no lower than the middle of the image.Position a vibrant blue sky with a few soft, fluffy white clouds in the top 15-20% of the image, serving as a backdrop that enhances but does not dominate the landmark. Maintain a serene, tranquil atmosphere by excluding people, vehicles, or modern distractions, focusing solely on the landmark’s beauty.Incorporate the real-world surrounding environment of {location_description}, such as distant mountains, native vegetation, or pathways, positioned to frame the landmark in the upper and middle portions of the image without overshadowing it. The bottom one-quarter to one-third of the frame should feature contextual foreground elements (e.g., grass, cobblestone paths, or rocky terrain) that complement the scene but do not rise above the middle of the image or obscure the landmark.Use soft, natural sunlight consistent with a bright springtime day (mid-morning or early afternoon), casting accurate shadows to emphasize the landmark’s textures and depth. Reflect any seasonal characteristics of {location_description} (e.g., spring blossoms, lush greenery) for a vivid, location-specific atmosphere.Ensure hyper-realistic details, with every element—from the roof tiles to the surrounding landscape—accurately reflecting the real-world setting of {location_description}. Strictly place the landmark in the upper two-thirds to three-quarters of the frame, ensuring it is not pushed below the middle, cropped, or diminished by foreground elements."
    
    return prompt

@router.post("/regenerate-with-text")
async def regenerate_image_with_custom_text(
    request: Request,
    payload: dict,
    user: UserModel = Depends(get_verified_user),
):
    """
    Regenerate the scenic image with custom text overlays
    Keeps the original Pollinations.ai image but updates the text overlays
    
    Expected payload:
    {
        "original_image_base64": "data:image/jpeg;base64,...",  # Original Pollinations image (without overlays)
        "destination": "Tokyo",
        "promote_text": "多航班及日子選擇！\n凌晨去晚返都有！",
        "airline": "中華航空",
        "price": "3,500"
    }
    """
    try:
        # Extract parameters
        original_image_base64 = payload.get("original_image_base64")
        destination = payload.get("destination", "")
        promote_text = payload.get("promote_text", "")
        airline = payload.get("airline")
        price = payload.get("price")
        
        if not original_image_base64:
            raise HTTPException(status_code=400, detail="Original image is required")
        
        # Decode the base64 image
        if "," in original_image_base64:
            original_image_base64 = original_image_base64.split(",")[1]
        image_bytes = base64.b64decode(original_image_base64)
        
        # Regenerate the image with new text overlays
        edited_image_bytes = _add_bottom_banner(
            image_bytes,
            1024,  # width
            1024,  # height
            destination=destination,
            airline=airline,
            price=price,
            ai_analysis={"promote_text": promote_text}
        )
        
        # Return the edited image
        return JSONResponse(content={
            "success": True,
            "image_base64": f"data:image/jpeg;base64,{base64.b64encode(edited_image_bytes).decode()}",
            "destination": destination,
            "promote_text": promote_text,
            "airline": airline,
            "price": price
        })
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error regenerating image with custom text: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerating image: {str(e)}"
        )

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
        edited_bytes = _add_bottom_banner(test_image_bytes, 400, 300, destination="Test Destination", airline="Test Airline", price="1,234")
        
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

def _add_multiline_text_with_styles(image: Image.Image, text: str, x: int, y: int, rotation_angle: int, line_styles: list) -> Image.Image:
    """
    Add multiline text with different styling for each line
    
    Args:
        image: PIL Image object
        text: Multiline text (separated by \n)
        x: X position for the text
        y: Y position for the text
        rotation_angle: Rotation angle in degrees
        line_styles: List of style dictionaries for each line
            [
                {
                    "line_index": 0,  # Which line (0-based)
                    "font_size": 120,
                    "text_color": (122, 40, 156),
                    "border_color": (255, 255, 255),
                    "border_width": 6,
                    "bold": True
                }
            ]
    
    Returns:
        PIL Image object with multiline text added
    """
    if not PIL_AVAILABLE:
        log.warning("PIL not available, cannot add multiline text")
        return image
    
    draw = ImageDraw.Draw(image)
    
    # Split text into lines
    lines = text.split('\n')
    
    # Calculate line height for spacing
    line_height = 0
    current_y = y
    
    for line_index, line in enumerate(lines):
        if not line.strip():  # Skip empty lines
            current_y += 20  # Small spacing for empty lines
            continue
        
        # Find style for this line
        line_style = None
        for style in line_styles:
            if style.get("line_index") == line_index:
                line_style = style
                break
        
        if not line_style:
            # Use default style if no specific style found
            line_style = {
                "font_size": 50,
                "text_color": (0, 0, 0),
                "border_color": (255, 255, 255),
                "border_width": 2,
                "bold": True
            }
        
        # Load font for this line
        font_size = line_style["font_size"]
        is_bold = line_style.get("bold", True)
        
        # Use proper font loading for Chinese characters
        if is_bold:
            # Use the main font loading function with bold=True
            font = _load_chinese_font(font_size, bold=True)
            log.info(f"Loading BOLD font for line '{line}' (size: {font_size})")
        else:
            font = _load_chinese_font(font_size, bold=False)
            log.info(f"Loading REGULAR font for line '{line}' (size: {font_size})")
        
        # Calculate text dimensions
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Draw text with border and rotation
        # Adjust x position for promote_text lines to align better with destination
        adjusted_x = x
        if line_index > 0:  # promote_text lines (not destination)
            adjusted_x = x + 25  # Move promote_text slightly to the right
        
        # Draw text with border and rotation
        if is_bold:
            # Check if we have a true bold font by checking the font path
            font_path = getattr(font, 'path', '')
            is_true_bold = any(bold_font in font_path for bold_font in ['Bold', 'bold', 'Black', 'black'])
            
            if is_true_bold:
                # Use true bold font - draw once normally
                log.info(f"Using TRUE BOLD font for '{line}' - drawing once")
                _draw_text_with_border(
                    draw, 
                    line, 
                    adjusted_x, 
                    current_y, 
                    font, 
                    line_style["text_color"], 
                    line_style["border_color"], 
                    line_style["border_width"], 
                    rotation_angle
                )
            else:
                # Fallback to manual bold effect for fonts without true bold
                log.info(f"Using MANUAL BOLD effect for '{line}' - drawing multiple times")
                offsets = [(0, 0), (1, 0), (0, 1), (1, 1)]
                for offset_x, offset_y in offsets:
                    _draw_text_with_border(
                        draw, 
                        line, 
                        adjusted_x + offset_x,  # Use adjusted x position with offset
                        current_y + offset_y, 
                        font, 
                        line_style["text_color"], 
                        line_style["border_color"], 
                        line_style["border_width"], 
                        rotation_angle
                    )
        else:
            # Regular text - draw once normally
            _draw_text_with_border(
                draw, 
                line, 
                adjusted_x,  # Use adjusted x position
                current_y, 
                font, 
                line_style["text_color"], 
                line_style["border_color"], 
                line_style["border_width"], 
                rotation_angle
            )
        
        # Move to next line position
        # Use appropriate spacing based on current line's font size
        if line_index == 0:
            # After destination (120px font), use moderate spacing
            current_y += text_height + 10
        else:
            # Between promote_text lines (35px font), use more spacing for better readability
            current_y += text_height + 8
        
        log.info(f"Added line {line_index}: '{line}' at ({x}, {current_y - text_height - (10 if line_index == 0 else 2)}) with style {line_style}")
    
    return image

def _load_chinese_font_specific(font_size: int, font_path: str):
    """
    Load a specific Chinese font from a given path
    Returns the font object or default font if not found
    """
    try:
        font = ImageFont.truetype(font_path, font_size)
        log.info(f"Successfully loaded specific font: {font_path} (size: {font_size})")
        return font
    except Exception as e:
        log.warning(f"Could not load specific font {font_path}: {e}")
        # Fallback to default font
        return ImageFont.load_default()

def _load_chinese_font(font_size: int, bold: bool = False):
    """
    Load a Chinese-compatible font with the specified size
    Returns the font object or default font if none found
    """
    if bold:
        # Prioritize bold fonts when bold is requested
        font_paths = [
            # Linux bold fonts (Docker environment) - prioritize fonts with true bold variants
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",  # Noto Sans CJK Bold (true bold)
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",  # Noto Sans CJK Bold (alternative path)
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Black.ttc",  # Noto Sans CJK Black (extra bold)
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # WQY ZenHei (fallback - not truly bold)
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # WQY MicroHei (fallback)
            # Windows bold fonts
            "C:/Windows/Fonts/msyhbd.ttc",  # Microsoft YaHei Bold
            "C:/Windows/Fonts/simhei.ttf",  # SimHei (bold by default)
            "C:/Windows/Fonts/msjh.ttc",  # Microsoft JhengHei (can appear bold)
            # WSL Windows bold fonts access
            "/mnt/c/Windows/Fonts/msyhbd.ttc",
            "/mnt/c/Windows/Fonts/simhei.ttf",
            # Fallback to regular fonts if bold not available
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/msjh.ttc",
        ]
    else:
        # Regular fonts
        font_paths = [
            # Linux fonts (Docker environment) - prioritize available fonts
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            # Windows fonts
            "C:/Windows/Fonts/msyh.ttc",  # Microsoft YaHei
            "C:/Windows/Fonts/msjh.ttc",  # Microsoft JhengHei
            "C:/Windows/Fonts/simsun.ttc",  # SimSun
            "C:/Windows/Fonts/simhei.ttf",  # SimHei
            # WSL Windows fonts access
            "/mnt/c/Windows/Fonts/msyh.ttc",
            "/mnt/c/Windows/Fonts/simsun.ttc",
            "/mnt/c/Windows/Fonts/simhei.ttf",
        ]
    
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, font_size)
            log.info(f"Successfully loaded font: {font_path} (size: {font_size}, bold: {bold})")
            return font
        except Exception as e:
            log.debug(f"Could not load font {font_path}: {e}")
            continue
    
    # Fallback to default font
    log.warning("Could not load any Chinese font, using default")
    return ImageFont.load_default()

def draw_text_on_image(
    image_or_draw,
    text: str = None,
    x: int = 0,
    y: int = 0,
    font_size: int = 30,
    text_color: tuple = (0, 0, 0),
    border_color: tuple = None,
    border_width: int = 0,
    bold: bool = False,
    rotation_angle: int = 0,
    center: bool = False,
    align: str = "left",
    max_width: int = None,
    line_spacing: int = 5,
    multipart: list = None,
    align_baseline: bool = True,
    line_styles: list = None
):
    """
    Comprehensive reusable function for drawing text on images with full customization
    
    Args:
        image_or_draw: PIL Image object or ImageDraw object
        text: Text to draw (supports multiline with \n) - optional if using multipart
        x: X coordinate (left edge or center depending on 'center' parameter)
        y: Y coordinate (top edge or center depending on 'center' parameter)
        font_size: Font size in pixels (default: 30)
        text_color: RGB or RGBA tuple for text color (default: black)
        border_color: RGB or RGBA tuple for border/outline (default: None = no border)
        border_width: Width of the border in pixels (default: 0)
        bold: Whether to use bold font (default: False)
        rotation_angle: Rotation angle in degrees, positive = clockwise (default: 0)
        center: Whether to center the text at (x, y) coordinates (default: False)
        align: Text alignment for multiline text: "left", "center", "right" (default: "left")
        max_width: Maximum width before text wrapping (default: None = no wrapping)
        line_spacing: Spacing between lines in pixels for multiline text (default: 5)
        multipart: List of dicts for multipart text (different sizes/colors in one line)
                  Format: [{"text": "HK$ ", "font_size": 30, "color": (49, 98, 210)}, ...]
        align_baseline: Align multipart text by baseline (default: True)
        line_styles: List of style dicts for each line in multiline text
                    Format: [{"line_index": 0, "font_size": 120, "text_color": (122, 40, 156),
                             "border_color": (255, 255, 255), "border_width": 6, "bold": True}, ...]
    
    Returns:
        PIL Image object with text drawn
    
    Example usage:
        # Simple text
        image = draw_text_on_image(image, text="Hello", x=100, y=100, font_size=40)
        
        # Text with white border
        image = draw_text_on_image(image, text="Tokyo", x=200, y=150, font_size=80, 
                                   text_color=(128, 0, 128), border_color=(255, 255, 255), 
                                   border_width=4, bold=True)
        
        # Rotated text
        image = draw_text_on_image(image, text="Special Offer", x=300, y=200, 
                                   rotation_angle=-15, center=True)
        
        # Multiline centered text
        image = draw_text_on_image(image, text="Line 1\nLine 2\nLine 3", x=400, y=300,
                                   center=True, align="center")
        
        # Multipart text (different font sizes in one line)
        image = draw_text_on_image(image, x=500, y=400, multipart=[
            {"text": "HK$ ", "font_size": 30, "color": (49, 98, 210)},
            {"text": "3,500", "font_size": 50, "color": (49, 98, 210)},
            {"text": " /人", "font_size": 30, "color": (128, 128, 128)}
        ])
    """
    # Determine if we're working with an Image or Draw object
    if isinstance(image_or_draw, Image.Image):
        image = image_or_draw
        draw = ImageDraw.Draw(image)
    else:
        draw = image_or_draw
        image = draw._image
    
    # Handle multipart text (different font sizes/colors in one line)
    if multipart:
        # Find the largest font size for baseline alignment
        max_font_size = max(part.get("font_size", 30) for part in multipart)
        
        # Calculate total width for centering
        total_width = 0
        for part in multipart:
            part_font = _load_chinese_font(part.get("font_size", 30), bold=True)
            bbox = draw.textbbox((0, 0), part["text"], font=part_font)
            total_width += bbox[2] - bbox[0]
        
        # Apply centering if requested
        start_x = x
        if center:
            start_x = x - (total_width // 2)
        
        # Draw each part
        current_x = start_x
        for part in multipart:
            part_text = part["text"]
            part_font_size = part.get("font_size", 30)
            part_color = part.get("color", (0, 0, 0))
            part_bold = part.get("bold", True)
            
            # Load font for this part
            part_font = _load_chinese_font(part_font_size, bold=part_bold)
            
            # Calculate y offset for baseline alignment
            if align_baseline:
                y_offset = (max_font_size - part_font_size) * 0.8  # 0.8 is baseline ratio
                adjusted_y = y + y_offset
            else:
                adjusted_y = y
            
            # Draw this part
            draw.text((current_x, adjusted_y), part_text, font=part_font, fill=part_color)
            
            # Calculate width to position next part
            bbox = draw.textbbox((current_x, adjusted_y), part_text, font=part_font)
            part_width = bbox[2] - bbox[0]
            current_x += part_width
            
            log.info(f"Drew multipart '{part_text}' at ({current_x - part_width}, {adjusted_y}), size: {part_font_size}")
        
        return image
    
    # Load font for regular text
    font = _load_chinese_font(font_size, bold=bold)
    
    # Handle multiline text
    if text:
        lines = text.split('\n')
    else:
        lines = []
    
    # Calculate text dimensions for positioning
    if len(lines) == 1:
        # Single line text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Apply centering if requested
        if center:
            x = x - (text_width // 2)
            y = y - (text_height // 2)
        
        # Draw text with or without border and rotation
        if border_color and border_width > 0:
            _draw_text_with_border(draw, text, x, y, font, text_color, border_color, border_width, rotation_angle)
        else:
            if rotation_angle != 0:
                # Use border function with transparent border for rotation
                _draw_text_with_border(draw, text, x, y, font, text_color, text_color, 0, rotation_angle)
            else:
                draw.text((x, y), text, font=font, fill=text_color)
        
        log.info(f"Drew text '{text}' at ({x}, {y}), size: {font_size}, color: {text_color}, border: {border_width}, rotation: {rotation_angle}")
    else:
        # Multiline text with optional different styles per line
        current_y = y
        
        for line_index, line in enumerate(lines):
            if not line.strip():  # Skip empty lines
                current_y += line_spacing
                continue
            
            # Get style for this line if line_styles is provided
            if line_styles:
                line_style = None
                for style in line_styles:
                    if style.get("line_index") == line_index:
                        line_style = style
                        break
                
                if line_style:
                    # Use specific style for this line
                    line_font_size = line_style.get("font_size", font_size)
                    line_text_color = line_style.get("text_color", text_color)
                    line_border_color = line_style.get("border_color", border_color)
                    line_border_width = line_style.get("border_width", border_width)
                    line_bold = line_style.get("bold", bold)
                    line_font = _load_chinese_font(line_font_size, bold=line_bold)
                else:
                    # Use default style
                    line_font = font
                    line_text_color = text_color
                    line_border_color = border_color
                    line_border_width = border_width
            else:
                # Use default style
                line_font = font
                line_text_color = text_color
                line_border_color = border_color
                line_border_width = border_width
            
            # Calculate line dimensions
            bbox = draw.textbbox((0, 0), line, font=line_font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            
            # Apply line alignment
            line_x = x
            if line_index > 0 and line_styles:  # Offset promote text lines slightly
                line_x = x + 25
            
            # Draw this line with its specific style
            if line_border_color and line_border_width > 0:
                _draw_text_with_border(draw, line, line_x, current_y, line_font, line_text_color, line_border_color, line_border_width, rotation_angle)
            else:
                if rotation_angle != 0:
                    _draw_text_with_border(draw, line, line_x, current_y, line_font, line_text_color, line_text_color, 0, rotation_angle)
                else:
                    draw.text((line_x, current_y), line, font=line_font, fill=line_text_color)
            
            # Move to next line with appropriate spacing
            if line_index == 0:
                current_y += line_height + 10  # More spacing after destination
            else:
                current_y += line_height + 8  # Normal spacing between promote text lines
        
        log.info(f"Drew multiline text ({len(lines)} lines) at ({x}, {y}), with line_styles: {bool(line_styles)}")
    
    return image

def _draw_text_on_image(draw, text: str, x: int, y: int, font, color=(0, 0, 0)):
    """
    Legacy helper function - kept for backward compatibility
    Use draw_text_on_image() instead for new code
    """
    draw.text((x, y), text, font=font, fill=color)
    log.info(f"Drew text '{text}' at position ({x}, {y}) with color {color}, font size: {getattr(font, 'size', 'default')}")

def _draw_text_with_border(draw, text: str, x: int, y: int, font, text_color=(0, 0, 0), border_color=(255, 255, 255), border_width=2, rotation_angle=0):
    """
    Draw text with a white border (outline effect) and optional rotation
    
    Args:
        draw: ImageDraw object
        text: Text to draw
        x: X coordinate
        y: Y coordinate
        font: Font object
        text_color: RGB color tuple for the text (default: black)
        border_color: RGB color tuple for the border (default: white)
        border_width: Width of the border in pixels (default: 2)
        rotation_angle: Rotation angle in degrees (default: 0, positive = clockwise)
    """
    if rotation_angle != 0:
        # Create a temporary image to draw the text with rotation
        # Calculate text size first
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Create a larger temporary image to accommodate rotation
        temp_size = max(text_width, text_height) + border_width * 2 + 20
        temp_image = Image.new('RGBA', (temp_size, temp_size), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_image)
        
        # Center the text in the temporary image
        temp_x = (temp_size - text_width) // 2
        temp_y = (temp_size - text_height) // 2
        
        # Draw border on temporary image
        for dx in range(-border_width, border_width + 1):
            for dy in range(-border_width, border_width + 1):
                if dx != 0 or dy != 0:  # Skip the center position
                    temp_draw.text((temp_x + dx, temp_y + dy), text, font=font, fill=border_color)
        
        # Draw main text on temporary image
        temp_draw.text((temp_x, temp_y), text, font=font, fill=text_color)
        
        # Rotate the temporary image (negative angle for counter-clockwise)
        rotated_image = temp_image.rotate(-rotation_angle, expand=True)
        
        # Paste the rotated text onto the main image
        # Calculate the position to maintain left alignment
        rot_width, rot_height = rotated_image.size
        # For left alignment, we need to adjust for the rotation
        # Calculate the offset needed to maintain left edge alignment
        rotation_offset_x = int(rot_width * 0.05)  # Smaller adjustment to move text slightly right
        paste_x = x - rotation_offset_x
        paste_y = y - rot_height // 2
        
        draw._image.paste(rotated_image, (paste_x, paste_y), rotated_image)
        log.info(f"Drew rotated text with border '{text}' at position ({x}, {y}) with rotation {rotation_angle}°")
    else:
        # Draw border by drawing the text multiple times in different positions
        for dx in range(-border_width, border_width + 1):
            for dy in range(-border_width, border_width + 1):
                if dx != 0 or dy != 0:  # Skip the center position
                    draw.text((x + dx, y + dy), text, font=font, fill=border_color)
        
        # Draw the main text on top
        draw.text((x, y), text, font=font, fill=text_color)
        log.info(f"Drew text with border '{text}' at position ({x}, {y}) with text color {text_color}, border color {border_color}, border width: {border_width}")

def _add_special_text_to_image(image: Image.Image, text_config: dict) -> Image.Image:
    """
    Add special text with customizable color and white border to an image
    
    Args:
        image: PIL Image object
        text_config: Dictionary containing text configuration
            {
                "text": "Your text here",
                "x": 100,  # X position
                "y": 100,  # Y position
                "font_size": 50,
                "text_color": (255, 0, 0),  # RGB color for text
                "border_color": (255, 255, 255),  # RGB color for border (default: white)
                "border_width": 3,  # Border width in pixels (default: 2)
                "center": True,  # Whether to center the text at x,y coordinates
                "bold": True  # Whether to use bold font
            }
    
    Returns:
        PIL Image object with text added
    """
    if not PIL_AVAILABLE:
        log.warning("PIL not available, cannot add special text")
        return image
    
    draw = ImageDraw.Draw(image)
    
    # Extract configuration with defaults
    text = text_config.get("text", "")
    x = text_config.get("x", 0)
    y = text_config.get("y", 0)
    font_size = text_config.get("font_size", 50)
    text_color = tuple(text_config.get("text_color", (0, 0, 0)))
    border_color = tuple(text_config.get("border_color", (255, 255, 255)))
    border_width = text_config.get("border_width", 2)
    center = text_config.get("center", True)
    bold = text_config.get("bold", True)
    rotation_angle = text_config.get("rotation_angle", 0)
    
    # Load font
    font = _load_chinese_font(font_size, bold=bold)
    
    # Calculate text dimensions first (needed for boundary checking)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate position if centering is requested
    if center:
        x = x - (text_width // 2)
        y = y - (text_height // 2)
    
    # Ensure text stays within image boundaries (account for rotation and border)
    image_width, image_height = image.size
    rotation_angle = text_config.get("rotation_angle", 0)
    border_width = text_config.get("border_width", 2)
    
    # Calculate extra space needed for rotation (approximate)
    if rotation_angle != 0:
        # For rotation, we need extra space around the text
        rotation_margin = int(max(text_width, text_height) * 0.3)  # 30% extra margin for rotation
        min_x = rotation_margin + border_width
        min_y = rotation_margin + border_width
        max_x = image_width - rotation_margin - border_width
        max_y = image_height - rotation_margin - border_width
    else:
        # For non-rotated text, smaller margin
        min_x = border_width
        min_y = border_width
        max_x = image_width - border_width
        max_y = image_height - border_width
    
    # Clamp coordinates to stay within bounds (ensure they are integers)
    x = int(max(min_x, min(x, max_x)))
    y = int(max(min_y, min(y, max_y)))
    
    # Draw text with border
    _draw_text_with_border(draw, text, x, y, font, text_color, border_color, border_width, rotation_angle)
    
    log.info(f"Added special text: '{text}' at ({x}, {y}) with color {text_color}, border {border_color}")
    return image

def _draw_multipart_text(draw, parts: list, x: int, y: int, align_baseline: bool = True):
    """
    Draw text with multiple parts, each with different font size and color
    
    Args:
        draw: ImageDraw object
        parts: List of dicts with {"text": str, "font_size": int, "color": tuple}
        x: Starting X coordinate
        y: Starting Y coordinate (baseline for alignment)
        align_baseline: If True, align all parts by their baseline
    
    Example:
        parts = [
            {"text": "HK$ ", "font_size": 30, "color": (49, 98, 210)},
            {"text": "3,500", "font_size": 50, "color": (49, 98, 210)},
            {"text": " /人", "font_size": 30, "color": (128, 128, 128)},
        ]
    """
    # Find the largest font size for baseline alignment
    max_font_size = max(part["font_size"] for part in parts)
    
    current_x = x
    for part in parts:
        text = part["text"]
        font_size = part["font_size"]
        color = part.get("color", (0, 0, 0))
        
        # Load font for this part
        font = _load_chinese_font(font_size, bold=True)
        
        # Calculate y offset for baseline alignment
        if align_baseline:
            # Adjust y position so larger text sits on the same baseline as smaller text
            # Larger fonts need to be moved up to align their baseline
            y_offset = (max_font_size - font_size) * 0.8  # 0.8 is an approximation for baseline ratio
            adjusted_y = y + y_offset
        else:
            adjusted_y = y
        
        # Draw this part
        draw.text((current_x, adjusted_y), text, font=font, fill=color)
        
        # Calculate width of this text to position next part
        bbox = draw.textbbox((current_x, adjusted_y), text, font=font)
        text_width = bbox[2] - bbox[0]
        current_x += text_width
        
        log.info(f"Drew multipart text '{text}' at ({current_x - text_width}, {adjusted_y}), size: {font_size}, color: {color}")

def _parse_flight_data_for_display(flight_data: dict) -> dict:
    """
    Parse flight data and determine display format.
    
    Returns a dict with standardized flight information for display:
    - outbound: {date, time, place, arrival_time, gmt}
    - return: {date, time, place, arrival_time, gmt}
    - price: str
    """
    if not flight_data:
        flight_data = {}
    
    # Check if flight_data contains multiple flights
    flights_list = flight_data.get("flights", [])
    is_multiple_flights = len(flights_list) > 0
    
    if is_multiple_flights:
        log.info(f"Processing multiple flights: {len(flights_list)} flights")
        
        # Get all unique places involved
        all_places = set()
        for flight in flights_list:
            all_places.add(flight.get("startingPlace"))
            all_places.add(flight.get("destination"))
        
        log.info(f"Unique places involved: {all_places}")
        
        if len(all_places) == 2:
            # Two places: treat as round trip
            log.info("Two places detected - treating as round trip")
            first_flight = flights_list[0]
            second_flight = flights_list[1] if len(flights_list) > 1 else flights_list[0]
            
            outbound = {
                "date": first_flight.get("departureDate", "2026年2月18日"),
                "time": first_flight.get("departureTime", "09:30"),
                "place": first_flight.get("startingPlace", "香港"),
                "arrival_time": first_flight.get("arrivalTime", "12:50"),
                "destination": first_flight.get("destination", "東京")
            }
            
            return_trip = {
                "date": second_flight.get("departureDate", outbound["date"]),
                "time": second_flight.get("departureTime", "15:30"),
                "place": second_flight.get("startingPlace", outbound["destination"]),
                "arrival_time": second_flight.get("arrivalTime", "19:45"),
                "destination": second_flight.get("destination", outbound["place"])
            }
            
            price = str(sum(f.get("cost", 0) for f in flights_list))
        else:
            # 3+ places: use only first flight
            log.info(f"3+ places detected ({len(all_places)} places) - using first flight only")
            first_flight = flights_list[0]
            
            outbound = {
                "date": first_flight.get("departureDate", "2026年2月18日"),
                "time": first_flight.get("departureTime", "09:30"),
                "place": first_flight.get("startingPlace", "香港"),
                "arrival_time": first_flight.get("arrivalTime", "12:50"),
                "destination": first_flight.get("destination", "東京")
            }
            
            return_trip = {
                "date": first_flight.get("returnDate", outbound["date"]),
                "time": first_flight.get("returnDepartureTime", "15:30"),
                "place": outbound["destination"],
                "arrival_time": first_flight.get("returnArrivalTime", "19:45"),
                "destination": outbound["place"]
            }
            
            price = str(first_flight.get("cost", 3500))
    else:
        # Single flight scenario - treat as round trip
        log.info("Processing single flight as round trip")
        
        outbound = {
            "date": flight_data.get("departureDate", "2026年2月18日"),
            "time": flight_data.get("departureTime", "09:30"),
            "place": flight_data.get("startingPlace", "香港"),
            "arrival_time": flight_data.get("arrivalTime", "12:50"),
            "destination": flight_data.get("destination", "東京")
        }
        
        return_trip = {
            "date": flight_data.get("returnDate", outbound["date"]),
            "time": flight_data.get("returnDepartureTime", "15:30"),
            "place": outbound["destination"],
            "arrival_time": flight_data.get("returnArrivalTime", "19:45"),
            "destination": outbound["place"]
        }
        
        price = str(flight_data.get("cost", 3500))
    
    # Get GMT timezone strings for all locations
    outbound["gmt"] = get_city_gmt_string(translate_destination(outbound["place"])) or ""
    outbound["dest_gmt"] = get_city_gmt_string(translate_destination(outbound["destination"])) or ""
    return_trip["gmt"] = get_city_gmt_string(translate_destination(return_trip["place"])) or ""
    return_trip["dest_gmt"] = get_city_gmt_string(translate_destination(return_trip["destination"])) or ""
    
    log.info(f"GMT timezones - Outbound: {outbound['place']}={outbound['gmt']}, Return: {return_trip['place']}={return_trip['gmt']}")
    
    return {
        "outbound": outbound,
        "return": return_trip,
        "price": price
    }

def _build_flight_text_config(flight_info: dict) -> list:
    """Build text configuration for flight information display"""
    outbound = flight_info["outbound"]
    return_trip = flight_info["return"]
    
    return [
        {"text": "出發", "x": 60, "y": 20, "color": (0, 0, 0), "font_size": 30},
        {"text": outbound["date"], "x": 150, "y": 20, "color": (0, 0, 0), "font_size": 30},
        {"text": "回程", "x": 60, "y": 270, "color": (0, 0, 0), "font_size": 30},
        {"text": return_trip["date"], "x": 150, "y": 270, "color": (0, 0, 0), "font_size": 30},
        {"text": outbound["time"], "x": 60, "y": 70, "color": (0, 0, 0), "font_size": 30},
        {"text": outbound["gmt"], "x": 62, "y": 105, "color": (222, 103, 18), "font_size": 20},
        {"text": outbound["place"], "x": 160, "y": 70, "color": (0, 0, 0), "font_size": 30},
        {"text": outbound["arrival_time"], "x": 60, "y": 190, "color": (0, 0, 0), "font_size": 30},
        {"text": outbound["dest_gmt"], "x": 62, "y": 225, "color": (222, 103, 18), "font_size": 20},
        {"text": outbound["destination"], "x": 160, "y": 190, "color": (0, 0, 0), "font_size": 30},
        {"text": return_trip["time"], "x": 60, "y": 330, "color": (0, 0, 0), "font_size": 30},
        {"text": return_trip["gmt"], "x": 62, "y": 365, "color": (222, 103, 18), "font_size": 20},
        {"text": return_trip["place"], "x": 160, "y": 330, "color": (0, 0, 0), "font_size": 30},
        {"text": return_trip["arrival_time"], "x": 60, "y": 445, "color": (0, 0, 0), "font_size": 30},
        {"text": return_trip["dest_gmt"], "x": 62, "y": 480, "color": (222, 103, 18), "font_size": 20},
        {"text": return_trip["destination"], "x": 160, "y": 445, "color": (0, 0, 0), "font_size": 30},
        {"text": "1", "x": 190, "y": 592, "color": (0, 0, 0), "font_size": 25},
    ]

def _build_price_multipart_config(price: str, x: int, y: int) -> dict:
    """Build multipart text configuration for price display"""
    return {
        "x": x,
        "y": y,
        "parts": [
            {"text": "HK$ ", "font_size": 30, "color": (49, 98, 210)},
            {"text": price, "font_size": 50, "color": (49, 98, 210)},
            {"text": " /人", "font_size": 30, "color": (128, 128, 128)},
        ]
    }

def _add_text_to_flight_info(image_data: bytes, flight_data: dict = None, ai_analysis: dict = None) -> bytes:
    """
    Add text overlays to the flight info image
    Adds flight details from flight_data and ai_analysis
    
    Args:
        image_data: Image bytes
        flight_data: Dictionary containing flight information (can be single flight or list of flights)
        ai_analysis: Dictionary containing AI-generated analysis
        
    Flight data processing logic:
    - Single flight: Treat as round trip
    - Multiple flights with 2 places: Treat as round trip (outbound + return)
    - Multiple flights with 3+ places: Use only first flight as round trip
    """
    log.info(f"Adding text overlays to flight info image")
    
    # Load and prepare image
    image = Image.open(io.BytesIO(image_data))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    log.info(f"Loaded flight info image: size {image.size}, mode: {image.mode}")
    
    # Parse flight data into display format
    flight_info = _parse_flight_data_for_display(flight_data)
    
    # Build text configurations
    texts_to_add = _build_flight_text_config(flight_info)
    price_config = _build_price_multipart_config(flight_info["price"], 40, 510)
    
    # Draw all text overlays
    for text_config in texts_to_add:
        image = draw_text_on_image(
            image,
            text=text_config["text"],
            x=text_config["x"],
            y=text_config["y"],
            font_size=text_config.get("font_size", 30),
            text_color=text_config["color"],
            bold=False
        )
    
    # Draw price
    image = draw_text_on_image(
        image,
        x=price_config["x"],
        y=price_config["y"],
        multipart=price_config["parts"],
        align_baseline=True
    )
    
    # Convert to bytes and return
    with io.BytesIO() as output:
        image.save(output, format='PNG')
        result_bytes = output.getvalue()
    
    log.info(f"Flight info image with text: {len(result_bytes)} bytes")
    return result_bytes

def _prepare_canvas_with_image(image_data: bytes, target_width: int = 1024, target_height: int = 1024) -> Image.Image:
    """
    Prepare a 1024x1024 canvas with the generated image pasted at the top.
    
    Args:
        image_data: Raw image bytes
        target_width: Canvas width (default: 1024)
        target_height: Canvas height (default: 1024)
        
    Returns:
        PIL Image with generated image pasted on canvas
    """
    # Load generated image
    generated_image = Image.open(io.BytesIO(image_data))
    log.info(f"Loaded generated image: size {generated_image.size}, mode: {generated_image.mode}")

    # Convert to RGB
    if generated_image.mode != 'RGB':
        generated_image = generated_image.convert('RGB')

    # Resize image to fill the canvas width without stretching height
    gen_width, gen_height = generated_image.size
    if gen_width != target_width:
        scale_factor = target_width / gen_width
        new_height = int(gen_height * scale_factor)
        log.info(
            "Resizing generated image from %sx%s to %sx%s to match canvas width",
            gen_width,
            gen_height,
            target_width,
            new_height,
        )
        generated_image = generated_image.resize((target_width, new_height), Image.Resampling.LANCZOS)
        gen_height = new_height
    else:
        log.info("Generated image already matches target width")

    # Create canvas and paste the resized image at the top-left corner
    canvas = Image.new('RGB', (target_width, target_height), (255, 255, 255))
    canvas.paste(generated_image, (0, 0))
    log.info(f"Pasted resized image onto canvas: {generated_image.size}")

    return canvas

def _add_blue_banner_area(image: Image.Image, banner_y: int, banner_height: int) -> Image.Image:
    """Add light blue banner rectangle at specified position"""
    light_blue = (135, 206, 250)
    banner_width = image.size[0]
    banner_area = Image.new('RGB', (banner_width, banner_height), light_blue)
    image.paste(banner_area, (0, banner_y))
    log.info(f"Added blue banner: {banner_width}x{banner_height} at y={banner_y}")
    return image

def _add_purple_airline_rectangle(
    image: Image.Image, 
    airline: str, 
    purple_y: int, 
    banner_width: int, 
    banner_height: int
) -> Image.Image:
    """
    Add purple rectangle with airline name.
    
    Rectangle width is calculated dynamically based on airline text length.
    """
    draw = ImageDraw.Draw(image)
    
    # Calculate rectangle dimensions
    airline_font_size = 80
    airline_font = _load_chinese_font(airline_font_size, bold=True)
    temp_bbox = draw.textbbox((0, 0), airline, font=airline_font)
    airline_text_width = temp_bbox[2] - temp_bbox[0]
    
    # Add padding and ensure minimum width
    text_padding = 40
    purple_width = max(airline_text_width + text_padding, int(banner_width * 0.35))
    purple_height = int(banner_height * 0.45)
    
    # Position from right edge
    right_padding = 25
    purple_x = image.size[0] - purple_width - right_padding
    
    # Draw purple rectangle
    purple = (128, 0, 128)
    draw.rectangle(
        [(purple_x, purple_y), (purple_x + purple_width, purple_y + purple_height)],
        fill=purple
    )
    log.info(f"Added purple rectangle at ({purple_x}, {purple_y}) size {purple_width}x{purple_height}")
    
    # Draw airline text (centered in rectangle)
    image = draw_text_on_image(
        image,
        text=airline,
        x=purple_x + (purple_width // 2),
        y=purple_y + (purple_height // 2) - 20,
        font_size=airline_font_size,
        text_color=(255, 255, 255),
        bold=True,
        center=True
    )
    
    return image

def _calculate_price_font_size(price: str) -> int:
    """Calculate appropriate font size for price prefix/suffix based on price length"""
    price_length = len(price)
    
    if price_length <= 5:
        return 88
    elif price_length <= 6:
        return 76
    elif price_length <= 7:
        return 69
    else:
        return 64

def _add_price_display(
    image: Image.Image,
    price: str,
    banner_y: int,
    banner_height: int
) -> Image.Image:
    """Add price display in the center of the banner"""
    prefix_suffix_size = _calculate_price_font_size(price)
    
    price_multipart = {
        "x": image.size[0] // 2,
        "y": banner_y + (banner_height // 2) - 65,
        "parts": [
            {"text": "來回連稅$", "font_size": prefix_suffix_size, "color": (255, 255, 255)},
            {"text": price, "font_size": 133, "color": (255, 255, 255)},
            {"text": "起", "font_size": prefix_suffix_size, "color": (255, 255, 255)},
        ]
    }
    
    image = draw_text_on_image(
        image,
        x=price_multipart["x"],
        y=price_multipart["y"],
        multipart=price_multipart["parts"],
        align_baseline=True,
        center=True
    )
    
    log.info(f"Added price display: {price}")
    return image

def _add_flyagain_icon(image: Image.Image) -> Image.Image:
    """Add flyagainla icon to top-right corner"""
    try:
        icon_path = Path(__file__).parent.parent.parent.parent / "flyagainla_icon.png"
        if icon_path.exists():
            icon = Image.open(icon_path).convert("RGBA")
            
            # Resize icon
            icon_height = int(image.size[1] * 0.11)
            icon_width = int(icon.width * (icon_height / icon.height))
            icon = icon.resize((icon_width, icon_height), Image.Resampling.LANCZOS)
            
            # Position in top-right corner
            padding = 15
            icon_x = image.size[0] - icon_width - padding - 10
            icon_y = padding + 15
            
            image.paste(icon, (icon_x, icon_y), icon)
            log.info(f"Added flyagainla icon at ({icon_x}, {icon_y})")
        else:
            log.warning(f"Icon not found: {icon_path}")
    except Exception as e:
        log.error(f"Failed to add icon: {e}")
    
    return image

def _add_destination_overlay(
    image: Image.Image,
    destination: str,
    ai_analysis: dict
) -> Image.Image:
    """Add destination and promotional text overlay"""
    # Extract promotional text
    if ai_analysis and ai_analysis.get("promote_text"):
        promote_text = ai_analysis.get("promote_text")
    else:
        promote_text = "多航班及日子選擇！\n凌晨去晚返都有！"
    
    # Combine destination and promote text
    lines = [destination] + promote_text.split('\n')
    
    # Create line-specific styles
    line_styles = [
        {
            "line_index": 0,
            "font_size": 160,
            "text_color": (122, 40, 156),
            "border_color": (255, 255, 255),
            "border_width": 8,
            "bold": True
        },
        {
            "line_index": 1,
            "font_size": 47,
            "text_color": (79, 201, 226),
            "border_color": (255, 255, 255),
            "border_width": 5,
            "bold": True
        },
        {
            "line_index": 2,
            "font_size": 47,
            "text_color": (79, 201, 226),
            "border_color": (255, 255, 255),
            "border_width": 5,
            "bold": True
        }
    ]
    
    image = draw_text_on_image(
        image,
        text='\n'.join(lines),
        x=30,
        y=110,
        rotation_angle=-7,
        line_styles=line_styles
    )
    
    log.info(f"Added destination overlay: {destination}")
    return image

def _add_border_frame(image: Image.Image, border_width: int = 8, margin: int = 15) -> Image.Image:
    """Add white border frame around the image"""
    draw = ImageDraw.Draw(image)
    border_color = (255, 255, 255)
    
    x1, y1 = margin, margin
    x2, y2 = image.size[0] - margin, image.size[1] - margin
    
    for i in range(border_width):
        draw.rectangle(
            [(x1 + i, y1 + i), (x2 - i, y2 - i)],
            outline=border_color,
            width=1
        )
    
    log.info(f"Added border frame: margin={margin}px, width={border_width}px")
    return image

def _add_bottom_banner(image_data: bytes, width: int, height: int, destination: str = None, airline: str = None, price: str = None, special_text_config: dict = None, ai_analysis: dict = None) -> bytes:
    """
    Add a light blue rectangle at the bottom of the image (1/4 height, 100% width)
    Similar to the Mongolia travel advertisement example
    
    Args:
        image_data: Image bytes
        width: Requested image width
        height: Requested image height
        destination: Destination name to display in special text
        airline: Airline name to display in purple rectangle
        price: Flight price to display in blue banner
        special_text_config: Optional custom text configuration
    """
    log.info(f"Adding bottom banner: {width}x{height}, dest={destination}, airline={airline}, price={price}")
    
    # Use defaults if values not provided
    destination = destination or "東京"
    airline = airline or "中華航空"
    price = price or "3,222"
    
    # Banner configuration
    banner_height = 256  # 1/4 of 1024
    banner_y = 768  # 1024 - 256
    purple_y = banner_y - 35
    
    # Step 1: Prepare canvas with image
    final_image = _prepare_canvas_with_image(image_data, 1024, 1024)
    
    # Step 2: Add blue banner
    final_image = _add_blue_banner_area(final_image, banner_y, banner_height)
    
    # Step 3: Add purple airline rectangle
    final_image = _add_purple_airline_rectangle(final_image, airline, purple_y, 1024, banner_height)
    
    # Step 4: Add price display
    final_image = _add_price_display(final_image, price, banner_y, banner_height)
    
    # Step 5: Add flyagain icon
    final_image = _add_flyagain_icon(final_image)
    
    # Step 6: Add destination overlay
    final_image = _add_destination_overlay(final_image, destination, ai_analysis)
    
    # Step 7: Add border frame
    final_image = _add_border_frame(final_image)
    
    # Convert to bytes and return
    with io.BytesIO() as output:
        final_image.save(output, format='JPEG', quality=95)
        result_bytes = output.getvalue()
    
    log.info(f"Completed banner: {len(result_bytes)} bytes")
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
