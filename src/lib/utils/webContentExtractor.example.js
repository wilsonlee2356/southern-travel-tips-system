/**
 * Example usage of the Web Content Extractor
 */

import { 
	extractWebContent, 
	extractMultipleWebContents, 
	extractTextOnly, 
	extractAsMarkdown, 
	extractWithRetry 
} from './webContentExtractor.js';

// Example 1: Basic content extraction
async function basicExtraction() {
	try {
		const result = await extractWebContent('https://example.com');
		
		if (result.success) {
			console.log('Title:', result.content.title);
			console.log('Text content:', result.content.textContent);
			console.log('Word count:', result.content.wordCount);
		} else {
			console.error('Extraction failed:', result.error);
		}
	} catch (error) {
		console.error('Error:', error.message);
	}
}

// Example 2: Extract with custom options
async function customExtraction() {
	const options = {
		waitForSelector: '.main-content',
		waitForTimeout: 10000,
		takeScreenshot: true,
		screenshotPath: './screenshot.png',
		includeImages: true,
		includeLinks: true,
		headless: false, // Show browser window
		userAgent: 'Custom Bot 1.0',
		viewport: { width: 1280, height: 720 }
	};

	try {
		const result = await extractWebContent('https://news.ycombinator.com', options);
		console.log('Extraction result:', result);
	} catch (error) {
		console.error('Error:', error.message);
	}
}

// Example 3: Extract text only
async function textOnlyExtraction() {
	try {
		const text = await extractTextOnly('https://example.com');
		console.log('Extracted text:', text);
	} catch (error) {
		console.error('Error:', error.message);
	}
}

// Example 4: Extract as markdown
async function markdownExtraction() {
	try {
		const markdown = await extractAsMarkdown('https://example.com');
		console.log('Markdown content:', markdown);
	} catch (error) {
		console.error('Error:', error.message);
	}
}

// Example 5: Extract from multiple URLs
async function multipleExtraction() {
	const urls = [
		'https://example.com',
		'https://httpbin.org',
		'https://jsonplaceholder.typicode.com'
	];

	const options = {
		concurrency: 2, // Process 2 URLs at a time
		includeLinks: true,
		waitForTimeout: 15000
	};

	try {
		const results = await extractMultipleWebContents(urls, options);
		
		results.forEach((result, index) => {
			console.log(`URL ${index + 1}:`, result.url);
			if (result.success) {
				console.log(`  Title: ${result.content.title}`);
				console.log(`  Word count: ${result.content.wordCount}`);
			} else {
				console.log(`  Error: ${result.error}`);
			}
		});
	} catch (error) {
		console.error('Error:', error.message);
	}
}

// Example 6: Extract with retry mechanism
async function retryExtraction() {
	const options = {
		maxRetries: 3,
		retryDelay: 2000,
		waitForTimeout: 10000,
		includeLinks: true
	};

	try {
		const result = await extractWithRetry('https://example.com', options);
		
		if (result.success) {
			console.log(`Extraction successful after ${result.attempts} attempts`);
			console.log('Content:', result.content.textContent);
		} else {
			console.error('Extraction failed:', result.error);
		}
	} catch (error) {
		console.error('Error:', error.message);
	}
}

// Example 7: Extract with custom headers
async function customHeadersExtraction() {
	const options = {
		extraHeaders: {
			'Authorization': 'Bearer your-token-here',
			'X-Custom-Header': 'custom-value'
		},
		includeImages: true,
		includeLinks: true
	};

	try {
		const result = await extractWebContent('https://api.example.com/protected', options);
		console.log('Protected content extracted:', result);
	} catch (error) {
		console.error('Error:', error.message);
	}
}

// Export examples for use in other files
export {
	basicExtraction,
	customExtraction,
	textOnlyExtraction,
	markdownExtraction,
	multipleExtraction,
	retryExtraction,
	customHeadersExtraction
};

// Run examples if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
	console.log('Running web content extraction examples...');
	
	// Uncomment the examples you want to run:
	// basicExtraction();
	// customExtraction();
	// textOnlyExtraction();
	// markdownExtraction();
	// multipleExtraction();
	// retryExtraction();
	// customHeadersExtraction();
}
