import { WEBUI_API_BASE_URL } from '$lib/constants';

/**
 * Edit an image by adding overlays (rectangles, text, logos)
 * @param {string} token - Authentication token
 * @param {Object} payload - Edit configuration
 * @returns {Promise<Object>} - Edited image data
 */
export const editImage = async (token, payload) => {
	try {
		const response = await fetch(`${WEBUI_API_BASE_URL}/pollinations/edit`, {
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
	} catch (error) {
		console.error('Error in editImage:', error);
		throw error;
	}
};

/**
 * Helper function to edit a Pollinations.ai generated image
 * @param {string} token - Authentication token
 * @param {string} imageUrl - URL of the Pollinations.ai image
 * @param {Array} edits - Array of edit operations
 * @returns {Promise<string>} - Base64 encoded edited image
 */
export const editPollinationsImage = async (token, imageUrl, edits) => {
	const payload = {
		image_source: 'url',
		image_url: imageUrl,
		edits: edits,
		output_format: 'base64',
		quality: 95
	};

	const result = await editImage(token, payload);
	return result.image_base64;
};

/**
 * Helper function to edit a local project image
 * @param {string} token - Authentication token
 * @param {string} imagePath - Relative path to image file
 * @param {Array} edits - Array of edit operations
 * @returns {Promise<string>} - Base64 encoded edited image
 */
export const editLocalImage = async (token, imagePath, edits) => {
	const payload = {
		image_source: 'file',
		image_path: imagePath,
		edits: edits,
		output_format: 'base64',
		quality: 95
	};

	const result = await editImage(token, payload);
	return result.image_base64;
};

/**
 * Example usage helper - Add purple rectangle with red text
 * @param {string} token - Authentication token
 * @param {string} imageUrl - URL of the image
 * @param {string} text - Text to add
 * @returns {Promise<string>} - Base64 encoded edited image
 */
export const addPriceOverlay = async (token, imageUrl, text) => {
	const edits = [
		{
			type: 'rectangle',
			position: [0, 900, 1024, 124], // Bottom of 1024x1024 image
			color: 'purple',
			opacity: 0.8
		},
		{
			type: 'text',
			text: text,
			position: [50, 950],
			color: 'red',
			font_size: 48
		}
	];

	return editPollinationsImage(token, imageUrl, edits);
};

/**
 * Add logo to image
 * @param {string} token - Authentication token
 * @param {string} imageUrl - URL of the image
 * @param {string} logoPath - Path to logo file
 * @param {Array} position - [x, y] position
 * @param {Array} size - [width, height] size
 * @returns {Promise<string>} - Base64 encoded edited image
 */
export const addLogoToImage = async (token, imageUrl, logoPath, position = [900, 20], size = [100, 100]) => {
	const edits = [
		{
			type: 'logo',
			logo_path: logoPath,
			position: position,
			size: size,
			opacity: 1.0
		}
	];

	return editPollinationsImage(token, imageUrl, edits);
};

