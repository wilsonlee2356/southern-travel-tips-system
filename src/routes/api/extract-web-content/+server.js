import { extractWebContent } from '$lib/utils/webContentExtractor.js';
import { json } from '@sveltejs/kit';

export async function POST({ request }) {
	try {
		const { url, options = {} } = await request.json();

		if (!url) {
			return json({ 
				success: false, 
				error: 'URL is required' 
			}, { status: 400 });
		}

		console.log(`Extracting content from: ${url}`);
		
		// Extract web content using the server-side extractor
		const result = await extractWebContent(url, {
			includeImages: true,
			includeLinks: true,
			waitForTimeout: 90000, // Extended to 90 seconds for problematic sites
			maxRetries: 3, // Allow 3 retry attempts
			...options
		});

		console.log(`Extraction result for ${url}:`, result.success ? 'Success' : 'Failed');

		return json(result);

	} catch (error) {
		console.error('Error in web content extraction API:', error);
		return json({
			success: false,
			error: error.message || 'Internal server error'
		}, { status: 500 });
	}
}
