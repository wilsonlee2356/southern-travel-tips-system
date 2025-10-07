"""
Test script for the Image Editing API

This script demonstrates how to use the image editing endpoint
to add overlays to Pollinations.ai generated images.

Usage:
    python test_image_editing.py
"""

import requests
import json
import base64
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8080/api/v1/pollinations"
# You'll need to replace this with your actual auth token
AUTH_TOKEN = "your-auth-token-here"

def test_edit_pollinations_image():
    """Test editing a Pollinations.ai generated image"""
    
    # Example Pollinations.ai image URL
    image_url = "https://image.pollinations.ai/prompt/beautiful%20Paris?seed=1234567890&width=1024&height=1024&nologo=true"
    
    # Define edits
    payload = {
        "image_source": "url",
        "image_url": image_url,
        "edits": [
            {
                "type": "rectangle",
                "position": [0, 900, 1024, 124],
                "color": "purple",
                "opacity": 0.8
            },
            {
                "type": "text",
                "text": "特價優惠 HK$1,299",
                "position": [50, 950],
                "color": "red",
                "font_size": 48
            },
            {
                "type": "logo",
                "logo_path": "static/flyagainla.png",
                "position": [900, 20],
                "size": [100, 100],
                "opacity": 1.0
            }
        ],
        "output_format": "base64",
        "quality": 95
    }
    
    # Make request
    response = requests.post(
        f"{API_BASE_URL}/edit",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}"
        },
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Image edited successfully!")
        print(f"   Format: {result['format']}")
        print(f"   Size: {result['size']}")
        
        # Save the edited image
        base64_data = result['image_base64'].split(',')[1]
        image_bytes = base64.b64decode(base64_data)
        
        output_path = Path("edited_image.jpg")
        output_path.write_bytes(image_bytes)
        print(f"   Saved to: {output_path.absolute()}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")

def test_edit_local_image():
    """Test editing a local project image"""
    
    payload = {
        "image_source": "file",
        "image_path": "static/flyagainla.png",
        "edits": [
            {
                "type": "rectangle",
                "position": [0, 0, 500, 100],
                "color": "blue",
                "opacity": 0.5
            },
            {
                "type": "text",
                "text": "PROMOTION!",
                "position": [50, 30],
                "color": "white",
                "font_size": 60
            }
        ],
        "output_format": "base64",
        "quality": 95
    }
    
    response = requests.post(
        f"{API_BASE_URL}/edit",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}"
        },
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Local image edited successfully!")
        print(f"   Format: {result['format']}")
        print(f"   Size: {result['size']}")
        
        # Save the edited image
        base64_data = result['image_base64'].split(',')[1]
        image_bytes = base64.b64decode(base64_data)
        
        output_path = Path("edited_local_image.jpg")
        output_path.write_bytes(image_bytes)
        print(f"   Saved to: {output_path.absolute()}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")

def main():
    print("=" * 60)
    print("Image Editing API Test")
    print("=" * 60)
    print()
    
    if AUTH_TOKEN == "your-auth-token-here":
        print("⚠️  Warning: Please set your AUTH_TOKEN in the script")
        print("   You can get it from localStorage in your browser")
        print()
    
    print("Test 1: Editing Pollinations.ai Image")
    print("-" * 60)
    test_edit_pollinations_image()
    print()
    
    print("Test 2: Editing Local Project Image")
    print("-" * 60)
    test_edit_local_image()
    print()
    
    print("=" * 60)
    print("Tests complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()

