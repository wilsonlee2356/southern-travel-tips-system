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
        full_url = f"{POLLINATIONS_BASE_URL}/prompt/{encoded_prompt}?seed={seed}&width={width}&height={height}&nologo=true"
        
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
                    
                    # Return both images as base64
                    return JSONResponse(content={
                        "success": True,
                        "image_url": full_url,
                        "image_base64": f"data:image/jpeg;base64,{base64.b64encode(edited_image_data).decode()}",
                        "flight_info_image_base64": flight_info_image_base64,
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

def _draw_text_on_image(draw, text: str, x: int, y: int, font, color=(0, 0, 0)):
    """
    Helper function to draw text on an image
    
    Args:
        draw: ImageDraw object
        text: Text to draw
        x: X coordinate
        y: Y coordinate
        font: Font object
        color: RGB color tuple (default: black)
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
    log.info(f"Flight data received: {flight_data}")
    log.info(f"AI analysis received: {ai_analysis}")
    
    default_font_size = 30

    # Load image from bytes
    image = Image.open(io.BytesIO(image_data))
    log.info(f"Loaded flight info image: size {image.size}, mode: {image.mode}")
    
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Create a drawing context
    draw = ImageDraw.Draw(image)
    
    # Extract data from flight_data and ai_analysis with fallbacks
    if not flight_data:
        flight_data = {}
    if not ai_analysis:
        ai_analysis = {}
    
    # Check if flight_data contains multiple flights (as a list/array indicator)
    flights_list = flight_data.get("flights", [])
    is_multiple_flights = len(flights_list) > 0
    
    if is_multiple_flights:
        # Multiple flights scenario
        log.info(f"Processing multiple flights: {len(flights_list)} flights")
        
        # Get all unique places involved
        all_places = set()
        for flight in flights_list:
            all_places.add(flight.get("startingPlace"))
            all_places.add(flight.get("destination"))
        
        log.info(f"Unique places involved: {all_places}")
        
        if len(all_places) == 2:
            # Two places: treat as round trip (first flight = outbound, second flight = return)
            log.info("Two places detected - treating as round trip")
            first_flight = flights_list[0]
            second_flight = flights_list[1] if len(flights_list) > 1 else flights_list[0]
            
            # Outbound trip (first flight)
            start_date = first_flight.get("departureDate", "2026年2月18日")
            start_time = first_flight.get("departureTime", "09:30")
            start_place = first_flight.get("startingPlace", "香港")
            start_arrival_time = first_flight.get("arrivalTime", "12:50")
            destination = first_flight.get("destination", "東京")
            
            # Return trip (second flight)
            return_date = second_flight.get("departureDate", start_date)
            return_time = second_flight.get("departureTime", "15:30")
            return_start_place = second_flight.get("startingPlace", destination)
            return_arrival_time = second_flight.get("arrivalTime", "19:45")
            return_destination = second_flight.get("destination", start_place)
            
            # Total cost
            flight_price = str(sum(f.get("cost", 0) for f in flights_list))
            
        else:
            # 3+ places: use only first flight and treat as round trip
            log.info(f"3+ places detected ({len(all_places)} places) - using first flight only")
            first_flight = flights_list[0]
            
            # Outbound trip
            start_date = first_flight.get("departureDate", "2026年2月18日")
            start_time = first_flight.get("departureTime", "09:30")
            start_place = first_flight.get("startingPlace", "香港")
            start_arrival_time = first_flight.get("arrivalTime", "12:50")
            destination = first_flight.get("destination", "東京")
            
            # Return trip (reverse of first flight)
            return_date = first_flight.get("returnDate", start_date)
            return_time = first_flight.get("returnDepartureTime", "15:30")
            return_start_place = destination
            return_arrival_time = first_flight.get("returnArrivalTime", "19:45")
            return_destination = start_place
            
            # Use first flight cost
            flight_price = str(first_flight.get("cost", 3500))
    else:
        # Single flight scenario - treat as round trip
        log.info("Processing single flight as round trip")
        
        # Outbound trip
        start_date = flight_data.get("departureDate", "2026年2月18日")
        start_time = flight_data.get("departureTime", "09:30")
        start_place = flight_data.get("startingPlace", "香港")
        start_arrival_time = flight_data.get("arrivalTime", "12:50")
        destination = flight_data.get("destination", "東京")
        
        # Return trip
        return_date = flight_data.get("returnDate", start_date)
        return_time = flight_data.get("returnDepartureTime", "15:30")
        return_start_place = destination  # Return starts from the destination
        return_arrival_time = flight_data.get("returnArrivalTime", "19:45")
        return_destination = start_place  # Return ends at starting place
        
        flight_price = str(flight_data.get("cost", 3500))
    
    # Get GMT timezone strings for all locations
    # Translate Chinese city names to English for timezone lookup
    start_place_en = translate_destination(start_place)
    destination_en = translate_destination(destination)
    return_start_place_en = translate_destination(return_start_place)
    return_destination_en = translate_destination(return_destination)
    
    start_place_gmt = get_city_gmt_string(start_place_en) or ""
    destination_gmt = get_city_gmt_string(destination_en) or ""
    return_start_place_gmt = get_city_gmt_string(return_start_place_en) or ""
    return_destination_gmt = get_city_gmt_string(return_destination_en) or ""
    
    log.info(f"GMT timezones - Start: {start_place_en}={start_place_gmt}, Dest: {destination_en}={destination_gmt}, Return Start: {return_start_place_en}={return_start_place_gmt}, Return Dest: {return_destination_en}={return_destination_gmt}")
    
    # Define text configurations (text, x, y, color, font_size)
    # font_size is optional, defaults to default_font_size if not specified
    texts_to_add = [
        {"text": "出發", "x": 60, "y": 20, "color": (0, 0, 0), "font_size": 30}, #do not change this text
        {"text": start_date, "x": 150, "y": 20, "color": (0, 0, 0), "font_size": 30}, #start date
        {"text": "回程", "x": 60, "y": 270, "color": (0, 0, 0), "font_size": 30}, #do not change this text
        {"text": return_date, "x": 150, "y": 270, "color": (0, 0, 0), "font_size": 30},#return date
        {"text": start_time, "x": 60, "y": 70, "color": (0, 0, 0), "font_size": 30},#start time
        {"text": start_place_gmt, "x": 62, "y": 105, "color": (222, 103, 18), "font_size": 20},#GMT of start_place
        {"text": start_place, "x": 160, "y": 70, "color": (0, 0, 0), "font_size": 30},#start place
        {"text": start_arrival_time, "x": 60, "y": 190, "color": (0, 0, 0), "font_size": 30},#start arrival time
        {"text": destination_gmt, "x": 62, "y": 225, "color": (222, 103, 18), "font_size": 20},#GMT of destination
        {"text": destination, "x": 160, "y": 190, "color": (0, 0, 0), "font_size": 30},#start destination place

        {"text": return_time, "x": 60, "y": 330, "color": (0, 0, 0), "font_size": 30},#return time
        {"text": return_start_place_gmt, "x": 62, "y": 365, "color": (222, 103, 18), "font_size": 20},#GMT of return_start_place
        {"text": return_start_place, "x": 160, "y": 330, "color": (0, 0, 0), "font_size": 30},#return start place
        {"text": return_arrival_time, "x": 60, "y": 445, "color": (0, 0, 0), "font_size": 30},#return arrival time
        {"text": return_destination_gmt, "x": 62, "y": 480, "color": (222, 103, 18), "font_size": 20},#GMT of return_destination
        {"text": return_destination, "x": 160, "y": 445, "color": (0, 0, 0), "font_size": 30},#return destination place

        {"text": "1", "x": 190, "y": 592, "color": (0, 0, 0), "font_size": 25},#do not change this text
    ]
    
    # Define multipart text configurations (for text with different sizes/colors in one line)
    multipart_texts = [
        {
            "x": 40, 
            "y": 510, 
            "parts": [
                {"text": "HK$ ", "font_size": 30, "color": (49, 98, 210)}, #do not change this text
                {"text": flight_price, "font_size": 50, "color": (49, 98, 210)}, #flight price
                {"text": " /人", "font_size": 30, "color": (128, 128, 128)}, #do not change this text
            ]
        },
    ]
    
    # Draw all regular texts
    for text_config in texts_to_add:
        # Get font size for this text (use default if not specified)
        font_size = text_config.get("font_size", default_font_size)
        # Load font with the specified size
        font = _load_chinese_font(font_size)
        
        _draw_text_on_image(
            draw, 
            text_config["text"], 
            text_config["x"], 
            text_config["y"], 
            font, 
            text_config["color"]
        )
    
    # Draw all multipart texts
    for multipart_config in multipart_texts:
        _draw_multipart_text(
            draw,
            multipart_config["parts"],
            multipart_config["x"],
            multipart_config["y"]
        )
    
    # Convert back to bytes
    result = io.BytesIO()
    image.save(result, format='PNG')
    result_bytes = result.getvalue()
    
    log.info(f"Flight info image with text: {len(result_bytes)} bytes")
    return result_bytes

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
    log.info(f"Adding bottom banner: requested {width}x{height} image")
    log.info(f"Destination for special text: {destination}")
    log.info(f"Airline: {airline}, Price: {price}")
    
    # Load generated image from bytes
    generated_image = Image.open(io.BytesIO(image_data))
    log.info(f"Loaded generated image: size {generated_image.size}, mode: {generated_image.mode}")
    
    # Convert to RGB for simpler handling
    if generated_image.mode != 'RGB':
        generated_image = generated_image.convert('RGB')
        log.info(f"Converted to RGB: {generated_image.size}, mode: {generated_image.mode}")
    
    # Create FIXED 1024x1024 canvas
    target_width = 1024
    target_height = 1024
    actual_width = target_width
    actual_height = target_height
    
    # Create empty white canvas
    final_image = Image.new('RGB', (target_width, target_height), (255, 255, 255))
    log.info(f"Created 1024x1024 canvas")
    
    # Paste the generated image at the very top of the canvas
    # The generated image is always 1024px wide, only height varies
    generated_width, generated_height = generated_image.size
    
    # Resize generated image to exactly 1024px width if needed (should already be 1024)
    if generated_width != target_width:
        generated_image = generated_image.resize((target_width, generated_height), Image.Resampling.LANCZOS)
        log.info(f"Resized generated image width from {generated_width} to {target_width}")
        generated_width = target_width
    
    # Paste the generated image at the top, full width (0, 0)
    # If generated height is less than 1024, it will show on white background
    # If generated height is more than 1024, it will be cropped at bottom (banner will overlay)
    paste_height = min(generated_height, target_height)
    if generated_height > target_height:
        # Crop to fit canvas height
        cropped_image = generated_image.crop((0, 0, target_width, target_height))
        final_image.paste(cropped_image, (0, 0))
        log.info(f"Cropped generated image to {target_width}x{target_height} and pasted at (0, 0)")
    else:
        # Paste as-is from top
        final_image.paste(generated_image, (0, 0))
        log.info(f"Pasted generated image {generated_width}x{generated_height} at (0, 0)")
    
    # Fixed banner dimensions (always the same on 1024x1024 canvas)
    banner_height = 256  # Fixed 256px (1/4 of 1024)
    banner_width = 1024  # Fixed 1024px (full width)
    banner_y = 768  # Fixed position (1024 - 256)
    
    log.info(f"Using FIXED canvas: {actual_width}x{actual_height}")
    log.info(f"Fixed banner: {banner_width}x{banner_height} at y={banner_y}")
    
    # Create light blue banner area and overlay it on top of the canvas
    light_blue = (135, 206, 250)  # LightSkyBlue RGB
    banner_area = Image.new('RGB', (banner_width, banner_height), light_blue)
    final_image.paste(banner_area, (0, banner_y))
    log.info(f"Added banner area: {banner_area.size} at y={banner_y}")
    
    # Add a small purple rectangle on top of the blue banner
    draw = ImageDraw.Draw(final_image)
    
    # Use provided airline or fallback to "中華航空"
    display_airline = airline if airline else "中華航空"
    
    # Use provided price or fallback to "3,222"
    display_price = price if price else "3,222"
    
    # Calculate purple rectangle width dynamically based on airline text length
    # Load font first to measure text width
    airline_font_size = 80  # Increased by 1/3 (60 * 1.33)
    airline_font = _load_chinese_font(airline_font_size, bold=True)
    
    # Measure airline text width
    temp_bbox = draw.textbbox((0, 0), display_airline, font=airline_font)
    airline_text_width = temp_bbox[2] - temp_bbox[0]
    
    # Add padding to the text width (20px on each side)
    text_padding = 40
    purple_width = airline_text_width + text_padding
    
    # Ensure minimum width (at least 35% of banner width)
    min_purple_width = int(banner_width * 0.35)
    purple_width = max(purple_width, min_purple_width)
    
    # Purple rectangle dimensions
    purple_height = int(banner_height * 0.45)
    right_padding = 25  # Fixed distance from right edge
    purple_x = actual_width - purple_width - right_padding  # Extends left based on text width
    purple_y = banner_y - 35  # Small padding from top of banner
    
    purple = (128, 0, 128)  # Purple RGB
    draw.rectangle(
        [(purple_x, purple_y), (purple_x + purple_width, purple_y + purple_height)],
        fill=purple
    )
    log.info(f"Added purple rectangle at ({purple_x}, {purple_y}) size {purple_width}x{purple_height} for airline '{display_airline}' (text width: {airline_text_width})")
    
    # Define texts to add (reusable configuration)
    texts_to_add = [
        {
            "text": display_airline, #change this airline name
            "x": purple_x + (purple_width // 2),  # Center horizontally in purple rectangle
            "y": purple_y + (purple_height // 2) - 15,  # Center vertically in purple rectangle, moved up 10px
            "color": (255, 255, 255),  # White
            "font_size": 80  # Increased by 1/3 (60 * 1.33)
        }
    ]
    
    # Calculate dynamic font size for prefix/suffix based on price length
    # Longer prices need smaller prefix/suffix to prevent touching border
    price_length = len(display_price)
    
    if price_length <= 5:  # e.g., "3,222" or "12,345"
        prefix_suffix_font_size = 88  # Reduced by 5% (93 * 0.95)
    elif price_length <= 6:  # e.g., "123,456"
        prefix_suffix_font_size = 76  # Reduced by 5% (80 * 0.95)
    elif price_length <= 7:  # e.g., "1,234,567"
        prefix_suffix_font_size = 69  # Reduced by 5% (73 * 0.95)
    else:  # Very long prices
        prefix_suffix_font_size = 64  # Reduced by 5% (67 * 0.95)
    
    log.info(f"Price length: {price_length}, using prefix/suffix font size: {prefix_suffix_font_size}")
    
    # Define multipart texts (for text with different sizes in one line)
    multipart_texts = [
        {
            "x": actual_width // 2,  # Center of entire image width
            "y": banner_y + (banner_height // 2) - 60,  # Center vertically in blue banner, moved down 10px
            "parts": [
                {"text": "來回連稅$", "font_size": prefix_suffix_font_size, "color": (255, 255, 255)}, #smaller this size if display_price is longer
                {"text": display_price, "font_size": 133, "color": (255, 255, 255)}, #Reduced by 5% (140 * 0.95)
                {"text": "起", "font_size": prefix_suffix_font_size, "color": (255, 255, 255)}, #smaller this size if display_price is longer
            ]
        }
    ]
    
    # Add all regular texts using the helper function with bold fonts
    for text_config in texts_to_add:
        font = _load_chinese_font(text_config['font_size'], bold=True)
        
        # Calculate text dimensions to center properly
        text = text_config['text']
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Adjust coordinates to center the text
        centered_x = text_config['x'] - (text_width // 2)
        centered_y = text_config['y'] - (text_height // 2)
        
        _draw_text_on_image(draw, text, centered_x, centered_y, font, text_config['color'])
        log.info(f"Added text: '{text}' at ({centered_x}, {centered_y}) - centered from ({text_config['x']}, {text_config['y']})")
    
    # Add multipart texts using the helper function
    for multipart_config in multipart_texts:
        # Calculate total width to center the entire multipart text
        total_width = 0
        for part in multipart_config["parts"]:
            font = _load_chinese_font(part["font_size"], bold=True)
            bbox = draw.textbbox((0, 0), part["text"], font=font)
            total_width += bbox[2] - bbox[0]
        
        # Center the multipart text
        start_x = multipart_config["x"] - (total_width // 2)
        
        _draw_multipart_text(
            draw,
            multipart_config["parts"],
            start_x,
            multipart_config["y"],
            align_baseline=True
        )
        log.info(f"Added multipart text at ({start_x}, {multipart_config['y']}) - centered from ({multipart_config['x']}, {multipart_config['y']})")
    
    # Add flyagainla_icon.png to the banner
    try:
        icon_path = Path(__file__).parent.parent.parent.parent / "flyagainla_icon.png"
        if icon_path.exists():
            icon = Image.open(icon_path).convert("RGBA")  # Convert to RGBA to handle transparency
            
            # Resize icon to be appropriately sized for the scenic area (increased by 1/3)
            icon_height = int(actual_height * 0.11)  # Increased from 0.08 to 0.11 (8% * 1.33)
            icon_width = int(icon.width * (icon_height / icon.height))
            icon = icon.resize((icon_width, icon_height), Image.Resampling.LANCZOS)
            
            # Position icon in the top-right corner of the entire image with padding
            padding = 15
            icon_x = actual_width - icon_width - padding - 10
            icon_y = padding + 15  # Top of the entire image, not just banner
            
            # Paste the icon onto the final image, using its alpha channel for transparency
            final_image.paste(icon, (icon_x, icon_y), icon)
            log.info(f"Added flyagainla_icon.png at ({icon_x}, {icon_y}) with size {icon.size}")
        else:
            log.warning(f"flyagainla_icon.png not found at {icon_path}")
    except Exception as e:
        log.error(f"Failed to add flyagainla_icon.png: {e}")
    
    # Add special text with destination name, with border and rotation
    # Calculate safe positioning to ensure text stays within image bounds
    # Account for larger font size (120) and rotation
    safe_margin = 100  # Extra margin to account for rotation and border
    
    # Use provided destination or fallback to "東京"
    display_destination = destination if destination else "東京"
    
    # Calculate safe x position for destination text to prevent it from going outside left edge
    destination_font_size = 160  # Increased by 1/3 (120 * 1.33)
    destination_font = _load_chinese_font(destination_font_size, bold=True)
    temp_draw = ImageDraw.Draw(final_image)
    dest_bbox = temp_draw.textbbox((0, 0), display_destination, font=destination_font)
    dest_text_width = dest_bbox[2] - dest_bbox[0]
    
    # Calculate minimum safe x position (accounting for rotation and border)
    rotation_margin = int(max(dest_text_width, destination_font_size) * 0.3)  # 30% margin for rotation
    border_width = 6
    min_safe_x = rotation_margin + border_width + 50  # Extra 50px buffer
    
    # Calculate desired center position
    desired_center_x = (actual_width // 2) - 100
    
    # Use the larger of desired position or minimum safe position
    safe_dest_center_x = max(desired_center_x, min_safe_x + (dest_text_width // 2))
    
    log.info(f"Destination text width: {dest_text_width}, min_safe_x: {min_safe_x}, using center_x: {safe_dest_center_x}")
    
    special_text_config = {
        "text": display_destination, #destination change here
        "x": safe_dest_center_x,  # Safe center position that keeps text within bounds
        "y": actual_height // 5,  # Move higher up in the image (was // 3, now // 5)
        "font_size": 120,
        "text_color": (122, 40, 156),  # #7a289c color
        "border_color": (255, 255, 255),  # White border
        "border_width": 6,
        "center": True,
        "bold": True,
        "rotation_angle": -7  # 10 degrees counter-clockwise (positive value)
    }
    
    # Skip adding the original destination text since we'll add it as part of the combined text
    # try:
    #     final_image = _add_special_text_to_image(final_image, special_text_config)
    #     log.info(f"Successfully added special text '{display_destination}' with border")
    # except Exception as e:
    #     log.error(f"Failed to add special text '{display_destination}': {e}")
    
    # Add combined text with different styling for destination and promote_text
    # Extract promote_text from ai_analysis, fallback to default text
    if ai_analysis and ai_analysis.get("promote_text"):
        promote_text = ai_analysis.get("promote_text")
        log.info(f"Using promote_text from AI analysis: {promote_text}")
    else:
        promote_text = "多航班及日子選擇！\n凌晨去晚返都有！"
        log.info("Using default promote_text")
    
    # Combine destination and promote_text into one text with different styling
    # Use \n to separate them visually (reduced spacing)
    combined_text = f"{display_destination}\n{promote_text}"
    
    # Calculate safe x position for the combined text
    combined_font_size = 160  # Increased by 1/3 (120 * 1.33)
    combined_font = _load_chinese_font(combined_font_size, bold=True)
    combined_bbox = temp_draw.textbbox((0, 0), combined_text, font=combined_font)
    combined_text_width = combined_bbox[2] - combined_bbox[0]
    
    # Calculate minimum safe x position for combined text (accounting for rotation and border)
    combined_rotation_margin = int(max(combined_text_width, combined_font_size) * 0.3)  # 30% margin for rotation
    combined_border_width = 6
    min_safe_combined_x = combined_rotation_margin + combined_border_width + 50  # Extra 50px buffer
    
    # Use the exact same x position as the destination text for perfect alignment
    # Calculate the destination's left edge from its safe center position
    dest_left_edge = safe_dest_center_x - (dest_text_width // 2)
    
    # Use the destination's left edge as the x position for all lines
    combined_text_x = dest_left_edge
    
    log.info(f"Combined text: '{combined_text}'")
    log.info(f"Combined text width: {combined_text_width}, min_safe_x: {min_safe_combined_x}, using combined_text x: {combined_text_x}")
    
    # Create custom multiline text with different styling for each line
    # Split the combined text and handle promote_text's internal line breaks
    lines = [display_destination] + promote_text.split('\n')
    
    try:
        final_image = _add_multiline_text_with_styles(
            final_image,
            '\n'.join(lines),  # Rejoin with single \n
            30,  # X position: 50px from left edge
            90,  # Y position: 50px from top edge
            -7,  # Same rotation as destination
            [
                {
                    "line_index": 0,  # First line (destination)
                    "font_size": 160,  # Increased by 1/3 (120 * 1.33)
                    "text_color": (122, 40, 156),  # Purple color for destination
                    "border_color": (255, 255, 255),  # White border
                    "border_width": 8,  # Increased by 1/3 (6 * 1.33)
                    "bold": True
                },
                {
                    "line_index": 1,  # Second line (first line of promote_text)
                    "font_size": 47,  # Increased by 1/3 (35 * 1.33)
                    "text_color": (79, 201, 226),  # Light blue color for promote_text
                    "border_color": (255, 255, 255),  # White border
                    "border_width": 5,  # Increased by 1/3 (4 * 1.33)
                    "bold": True
                },
                {
                    "line_index": 2,  # Third line (second line of promote_text if exists)
                    "font_size": 47,  # Increased by 1/3 (35 * 1.33)
                    "text_color": (79, 201, 226),  # Light blue color for promote_text
                    "border_color": (255, 255, 255),  # White border
                    "border_width": 5,  # Increased by 1/3 (4 * 1.33)
                    "bold": True
                }
            ]
        )
        log.info("Successfully added multiline text with different styles")
    except Exception as e:
        log.error(f"Failed to add multiline text: {e}")
    
    # # Add third special text "brah brah 2" under "Brah brah 1"
    # special_text_config_3 = {
    #     "text": "凌晨去晚返都有！",
    #     "x": (actual_width // 2) - 150,  # Same horizontal position as "Brah brah 1"
    #     "y": (actual_height // 5) + 140,  # Under "Brah brah 1" with spacing
    #     "font_size": 45,
    #     "text_color": (79, 201, 226),  # #4fc9e2 color
    #     "border_color": (255, 255, 255),  # White border
    #     "border_width": 4,
    #     "center": False,  # Don't center, use exact positioning
    #     "bold": True,
    #     "rotation_angle": -7  # Same rotation as others
    # }
    
    # try:
    #     final_image = _add_special_text_to_image(final_image, special_text_config_3)
    #     log.info("Successfully added special text 'brah brah 2' with border")
    # except Exception as e:
    #     log.error(f"Failed to add special text 'brah brah 2': {e}")
    
    # Add thin white rectangular border around the content
    # Create a new draw object to ensure we're working with the latest image
    draw = ImageDraw.Draw(final_image)
    
    # Define border properties
    border_width = 8  # Thin border (3 pixels)
    border_margin = 15  # Small space between image edge and border
    border_color = (255, 255, 255)  # White
    
    # Calculate border coordinates (inset from edges by margin)
    border_x1 = border_margin
    border_y1 = border_margin
    border_x2 = actual_width - border_margin
    border_y2 = actual_height - border_margin
    
    # Draw the border rectangle (outline only, no fill)
    for i in range(border_width):
        draw.rectangle(
            [(border_x1 + i, border_y1 + i), (border_x2 - i, border_y2 - i)],
            outline=border_color,
            width=1
        )
    
    log.info(f"Added white border: margin={border_margin}px, width={border_width}px")
    
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
