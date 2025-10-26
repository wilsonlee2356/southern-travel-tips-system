import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface PollinationsGenerateRequest {
	destination: string;
	style?: string;
	width?: number;
	height?: number;
}

export interface PollinationsGenerateResponse {
	success: boolean;
	image_url: string;
	destination: string;
	prompt: string;
	style: string;
	dimensions: string;
}

export interface PollinationsStyle {
	id: string;
	name: string;
	description: string;
}

export interface PollinationsStylesResponse {
	styles: PollinationsStyle[];
}

/**
 * Generate a scenic image for a destination using Pollinations.ai
 */
export const generateScenicImage = async (
	token: string = '',
	payload: PollinationsGenerateRequest
): Promise<PollinationsGenerateResponse> => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/pollinations/generate`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(payload)
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => ({}));
		throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
	}

	return response.json();
};

/**
 * Regenerate scenic image with custom text overlays
 */
export const regenerateImageWithText = async (
	token: string = '',
	payload: {
		original_image_base64: string;
		destination: string;
		promote_text: string;
		airline?: string;
		price?: string;
	}
): Promise<any> => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/pollinations/regenerate-with-text`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(payload)
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => ({}));
		throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
	}

	return response.json();
};

/**
 * Get available image generation styles
 */
export const getAvailableStyles = async (token: string = ''): Promise<PollinationsStylesResponse> => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/pollinations/styles`, {
		method: 'GET',
		headers: {
			...(token && { Authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => ({}));
		throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
	}

	return response.json();
};

/**
 * Extract destination from generated content
 */
export const extractDestination = (content: string): string | null => {
	// Common destination patterns
	const destinationPatterns = [
		// City, Country format
		/(?:to|in|from|visit|travel to|destination)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)?)/gi,
		// Popular destinations
		/(?:Paris|London|Tokyo|New York|Rome|Barcelona|Amsterdam|Prague|Vienna|Budapest|Istanbul|Dubai|Singapore|Bangkok|Bali|Santorini|Mykonos|Santorini|Greece|Italy|France|Spain|Japan|Thailand|Indonesia)/gi,
		// After "in" or "to"
		/(?:in|to)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)?)/gi
	];

	for (const pattern of destinationPatterns) {
		const matches = content.match(pattern);
		if (matches && matches.length > 0) {
			// Clean up the destination
			let destination = matches[0].replace(/(?:to|in|from|visit|travel to|destination)\s+/gi, '').trim();
			
			// Capitalize properly
			destination = destination.split(', ').map(part => 
				part.split(' ').map(word => 
					word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
				).join(' ')
			).join(', ');
			
			return destination;
		}
	}

	return null;
};

/**
 * Create a scenic prompt for the destination
 */
export const createScenicPrompt = (destination: string, style: string = 'realistic'): string => {
	const styleModifiers = {
		realistic: 'photorealistic, high quality, detailed',
		artistic: 'artistic painting style, vibrant colors, creative',
		cinematic: 'cinematic lighting, dramatic atmosphere, movie-like',
		vintage: 'vintage film photography, retro colors, nostalgic'
	};

	const scenicElements = [
		'breathtaking landscape',
		'stunning scenery',
		'beautiful view',
		'picturesque location',
		'majestic vista'
	];

	const randomElement = scenicElements[Math.floor(Math.random() * scenicElements.length)];
	const modifier = styleModifiers[style as keyof typeof styleModifiers] || styleModifiers.realistic;

	return `${randomElement} of ${destination}, ${modifier}, travel photography, professional quality`;
};
