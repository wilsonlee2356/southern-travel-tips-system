# Image Editing API Documentation

## Overview

The Image Editing API allows you to add overlays to images, including:
- **Rectangles** (with custom colors and opacity)
- **Text** (with custom fonts, sizes, and colors)
- **Logos** (with resizing and opacity control)

You can edit:
- ✅ Pollinations.ai generated images (from URL)
- ✅ Local project images (from file path)
- ✅ Base64 encoded images

---

## Backend Endpoint

### `POST /api/v1/pollinations/edit`

Edit an image by adding overlays (rectangles, text, logos).

**Authentication:** Required (Bearer token)

**Request Payload:**
```json
{
  "image_source": "url",              // "url", "file", or leave empty for base64
  "image_url": "https://...",         // Required if source is "url"
  "image_path": "static/logo.png",    // Required if source is "file"
  "image_base64": "data:image/...",   // Alternative: base64 string
  "edits": [
    {
      "type": "rectangle",
      "position": [x, y, width, height],
      "color": "purple",              // Color name or [R, G, B, A]
      "opacity": 0.8                  // 0-1
    },
    {
      "type": "text",
      "text": "特價優惠 HK$1,299",
      "position": [x, y],
      "color": "red",
      "font_size": 48,
      "font_family": "arial.ttf"      // Optional
    },
    {
      "type": "logo",
      "logo_path": "static/flyagainla.png",
      "position": [x, y],
      "size": [width, height],        // Optional, will resize
      "opacity": 1.0                  // Optional
    }
  ],
  "output_format": "base64",          // "base64" or "url"
  "quality": 95                       // JPEG quality 1-100
}
```

**Response:**
```json
{
  "success": true,
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "format": "jpeg",
  "size": [1024, 1024]
}
```

---

## Frontend API Client

### Import
```javascript
import { 
  editImage, 
  editPollinationsImage, 
  editLocalImage,
  addPriceOverlay,
  addLogoToImage 
} from '$lib/apis/images/edit.js';
```

### Basic Usage

#### 1. Edit Pollinations.ai Generated Image
```javascript
const token = localStorage.getItem('token');
const pollinationsImageUrl = 'https://image.pollinations.ai/prompt/...';

const edits = [
  {
    type: 'rectangle',
    position: [0, 900, 1024, 124],
    color: 'purple',
    opacity: 0.8
  },
  {
    type: 'text',
    text: '特價優惠 HK$1,299',
    position: [50, 950],
    color: 'red',
    font_size: 48
  }
];

const editedImageBase64 = await editPollinationsImage(token, pollinationsImageUrl, edits);
// Use editedImageBase64 in <img src={editedImageBase64} />
```

#### 2. Edit Local Project Image
```javascript
const token = localStorage.getItem('token');
const imagePath = 'static/flyagainla.png';

const edits = [
  {
    type: 'text',
    text: 'New Promotion!',
    position: [100, 100],
    color: 'red',
    font_size: 40
  }
];

const editedImageBase64 = await editLocalImage(token, imagePath, edits);
```

#### 3. Add Price Overlay (Helper Function)
```javascript
const token = localStorage.getItem('token');
const imageUrl = 'https://image.pollinations.ai/prompt/...';
const priceText = '特價優惠 HK$1,299';

const editedImage = await addPriceOverlay(token, imageUrl, priceText);
```

#### 4. Add Logo to Image (Helper Function)
```javascript
const token = localStorage.getItem('token');
const imageUrl = 'https://image.pollinations.ai/prompt/...';
const logoPath = 'static/flyagainla.png';

const editedImage = await addLogoToImage(
  token, 
  imageUrl, 
  logoPath, 
  [900, 20],    // position [x, y]
  [100, 100]    // size [width, height]
);
```

---

## Complete Example: Flight Post Page

Here's how to integrate image editing into your flight post page:

```javascript
// In src/routes/(app)/post/+page.svelte

import { onMount } from 'svelte';
import { editPollinationsImage } from '$lib/apis/images/edit.js';

let scenicImage = '';
let editedScenicImage = '';
let flightPrice = 1299;

onMount(async () => {
  // Get the scenic image from sessionStorage
  const postData = JSON.parse(sessionStorage.getItem('flightPostData') || '{}');
  scenicImage = postData.scenicImage;
  
  // Edit the image to add price overlay
  if (scenicImage) {
    const token = localStorage.getItem('token') || '';
    
    const edits = [
      // Purple rectangle at bottom
      {
        type: 'rectangle',
        position: [0, 900, 1024, 124],
        color: 'purple',
        opacity: 0.8
      },
      // Red price text
      {
        type: 'text',
        text: `特價優惠 HK$${flightPrice}`,
        position: [50, 950],
        color: 'red',
        font_size: 48
      },
      // Logo in top-right
      {
        type: 'logo',
        logo_path: 'static/flyagainla.png',
        position: [900, 20],
        size: [100, 100],
        opacity: 1.0
      }
    ];
    
    try {
      editedScenicImage = await editPollinationsImage(token, scenicImage, edits);
      console.log('Image edited successfully!');
    } catch (error) {
      console.error('Error editing image:', error);
      // Fallback to original image
      editedScenicImage = scenicImage;
    }
  }
});
```

```html
<!-- Display the edited image -->
{#if editedScenicImage}
  <img src={editedScenicImage} alt="Destination with price overlay" />
{:else if scenicImage}
  <img src={scenicImage} alt="Destination" />
{/if}
```

---

## Available Colors

Predefined color names you can use:
- `red`, `green`, `blue`
- `purple`, `yellow`, `orange`, `pink`
- `black`, `white`, `gray`
- `cyan`, `magenta`

Or use custom RGB: `[255, 0, 0]` for red

Or use custom RGBA: `[255, 0, 0, 128]` for red with 50% opacity

---

## Edit Types Reference

### Rectangle
```javascript
{
  type: 'rectangle',
  position: [x, y, width, height],  // [0, 0, 100, 50] = rectangle at top-left
  color: 'purple',                  // Color name or [R, G, B, A]
  opacity: 0.8                      // 0 (transparent) to 1 (opaque)
}
```

### Text
```javascript
{
  type: 'text',
  text: 'Your text here',
  position: [x, y],                 // [100, 100] = text position
  color: 'red',                     // Color name or [R, G, B]
  font_size: 40,                    // Font size in pixels
  font_family: 'arial.ttf',         // Optional: custom font file
  align: 'left'                     // Optional: 'left', 'center', 'right'
}
```

### Logo
```javascript
{
  type: 'logo',
  logo_path: 'static/logo.png',     // Path relative to project root
  logo_url: 'https://...',          // Alternative: URL to logo
  position: [x, y],                 // [900, 20] = top-right corner
  size: [width, height],            // Optional: [100, 100] = 100x100px
  opacity: 1.0                      // 0 (transparent) to 1 (opaque)
}
```

---

## Tips & Best Practices

### 1. Position Calculation for Bottom Overlays
For a 1024x1024 image, to place a rectangle at the bottom:
```javascript
position: [0, 900, 1024, 124]
// x=0, y=900, width=1024, height=124
// This creates a 124px tall bar at the bottom
```

### 2. Text Positioning
Text position is the top-left corner of the text. Add some padding:
```javascript
// For text inside a rectangle at bottom (y=900)
position: [50, 950]  // 50px from left, 50px below rectangle start
```

### 3. Multiple Edits
You can chain multiple edits - they apply in order:
```javascript
const edits = [
  { type: 'logo', ... },        // First: add logo
  { type: 'rectangle', ... },   // Second: add background
  { type: 'text', ... }         // Third: add text on top
];
```

### 4. Performance
- Image editing happens server-side, so it's fast
- Returns base64 which can be used immediately in `<img>` tags
- For production, consider caching edited images

---

## Installation

The image editing feature requires PIL/Pillow in the backend:

```bash
cd backend
pip install Pillow
```

That's it! The endpoint is already integrated into the pollinations router.

---

## Error Handling

```javascript
try {
  const editedImage = await editPollinationsImage(token, imageUrl, edits);
  // Use edited image
} catch (error) {
  console.error('Failed to edit image:', error);
  // Fallback to original image or show error message
}
```

---

## Security Notes

- ✅ File paths are restricted to project directory
- ✅ Authentication required for all requests
- ✅ URL downloads have timeout protection
- ✅ Invalid paths are rejected

---

## Future Enhancements

Planned features:
- [ ] Save edited images to storage and return URLs
- [ ] Batch image editing
- [ ] More edit types (filters, borders, gradients)
- [ ] Template-based editing
- [ ] Image cropping and resizing

