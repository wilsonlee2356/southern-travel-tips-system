/**
 * Web Content Extractor using Puppeteer
 * Extracts content from web pages with various options
 */

import puppeteer from 'puppeteer';

/**
 * Extract web content from a given URL using Puppeteer
 * @param {string} url - The URL to extract content from
 * @param {Object} options - Extraction options
 * @param {boolean} options.waitForSelector - CSS selector to wait for before extracting
 * @param {number} options.waitForTimeout - Timeout in milliseconds to wait for page load (default: 60000ms)
 * @param {boolean} options.takeScreenshot - Whether to take a screenshot
 * @param {string} options.screenshotPath - Path to save screenshot
 * @param {boolean} options.includeImages - Whether to include image URLs in extracted content
 * @param {boolean} options.includeLinks - Whether to include links in extracted content
 * @param {string} options.userAgent - Custom user agent string
 * @param {Object} options.viewport - Viewport configuration {width, height}
 * @param {boolean} options.headless - Whether to run browser in headless mode
 * @param {Object} options.extraHeaders - Additional headers to send with requests
 * @returns {Object} Extracted content with metadata
 */
export async function extractWebContent(url, options = {}) {
	const { maxRetries = 2 } = options; // Add retry mechanism

	// Try extraction with retries
	for (let attempt = 1; attempt <= maxRetries; attempt++) {
		console.log(`Extraction attempt ${attempt}/${maxRetries} for URL: ${url}`);
		
		try {
			return await performExtraction(url, options, attempt);
		} catch (error) {
			console.log(`Attempt ${attempt} failed:`, error.message);
			
			if (attempt === maxRetries) {
				// Last attempt failed, return error
				console.error('All extraction attempts failed');
				return {
					success: false,
					url,
					error: `Failed after ${maxRetries} attempts: ${error.message}`,
					attempts: maxRetries,
					extractedAt: new Date().toISOString()
				};
			}
			
			// Wait before retry
			console.log(`Waiting 3 seconds before retry...`);
			await new Promise(resolve => setTimeout(resolve, 3000));
		}
	}
}

async function performExtraction(url, options, attempt) {
	const {
		waitForSelector = null,
		waitForTimeout = 60000,
		takeScreenshot = false,
		includeImages = false,
		includeLinks = true,
		userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
		viewport = { width: 1920, height: 1080 },
		headless = true,
		extraHeaders = {}
	} = options;

	let browser = null;
	let page = null;

	try {
		// Decode URL to handle Chinese characters and other encoded characters
		const decodedUrl = decodeURIComponent(url);
		console.log(`Original URL: ${url}`);
		console.log(`Decoded URL: ${decodedUrl}`);
		
		// Validate URL
		if (!isValidUrl(decodedUrl)) {
			throw new Error('Invalid URL provided');
		}
		
		// Use the decoded URL for navigation
		const navigationUrl = decodedUrl;

		// Launch browser with more aggressive settings for problematic sites
		const browserArgs = [
			'--no-sandbox',
			'--disable-setuid-sandbox',
			'--disable-dev-shm-usage',
			'--disable-accelerated-2d-canvas',
			'--no-first-run',
			'--no-zygote',
			'--disable-gpu',
			'--disable-blink-features=AutomationControlled',
			'--disable-features=VizDisplayCompositor',
			'--disable-extensions',
			'--disable-plugins',
			'--disable-images',
			'--disable-javascript-harmony-shipping',
			'--disable-background-timer-throttling',
			'--disable-backgrounding-occluded-windows',
			'--disable-renderer-backgrounding',
			'--disable-field-trial-config',
			'--disable-back-forward-cache',
			'--disable-ipc-flooding-protection',
			'--disable-hang-monitor',
			'--disable-prompt-on-repost',
			'--disable-domain-reliability',
			'--disable-component-extensions-with-background-pages',
			'--disable-default-apps',
			'--disable-sync',
			'--disable-translate',
			'--hide-scrollbars',
			'--mute-audio',
			'--no-default-browser-check',
			'--no-pings',
			'--password-store=basic',
			'--use-mock-keychain',
			'--user-data-dir=/tmp/chrome-user-data',
			'--disable-web-security',
			'--allow-running-insecure-content',
			'--disable-features=TranslateUI',
			'--disable-ipc-flooding-protection'
		];

		// Add more aggressive settings for retry attempts
		if (attempt > 1) {
			browserArgs.push(
				'--disable-features=VizDisplayCompositor,TranslateUI',
				'--disable-background-networking',
				'--disable-background-timer-throttling',
				'--disable-client-side-phishing-detection',
				'--disable-default-apps',
				'--disable-hang-monitor',
				'--disable-prompt-on-repost',
				'--disable-sync',
				'--disable-component-extensions-with-background-pages',
				'--disable-extensions',
				'--disable-plugins-discovery',
				'--disable-print-preview',
				'--disable-ipc-flooding-protection',
				'--aggressive-cache-discard',
				'--memory-pressure-off',
				'--max_old_space_size=4096'
			);
		}

		browser = await puppeteer.launch({
			headless,
			args: browserArgs,
			timeout: waitForTimeout + 30000 // Add extra timeout for browser launch
		});

		page = await browser.newPage();

		// Hide automation indicators
		await page.evaluateOnNewDocument(() => {
			// Remove webdriver property
			Object.defineProperty(navigator, 'webdriver', {
				get: () => undefined,
			});

			// Override the plugins property to use a custom getter
			Object.defineProperty(navigator, 'plugins', {
				get: () => [1, 2, 3, 4, 5], // fake plugins
			});

			// Override the languages property to use a custom getter
			Object.defineProperty(navigator, 'languages', {
				get: () => ['en-US', 'en', 'zh-CN', 'zh'],
			});

			// Override the permissions property
			const originalQuery = window.navigator.permissions.query;
			window.navigator.permissions.query = (parameters) => (
				parameters.name === 'notifications' ?
					Promise.resolve({ state: Notification.permission }) :
					originalQuery(parameters)
			);

			// Mock chrome object
			window.chrome = {
				runtime: {},
			};

			// Override Date.prototype.getTimezoneOffset
			Date.prototype.getTimezoneOffset = function() {
				return -480; // GMT+8 (Asia/Taipei)
			};

			// Mock screen properties
			Object.defineProperty(screen, 'availHeight', { get: () => 1040 });
			Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
			Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
			Object.defineProperty(screen, 'height', { get: () => 1080 });
			Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
			Object.defineProperty(screen, 'width', { get: () => 1920 });
		});

		// Set viewport
		await page.setViewport(viewport);

		// Set user agent
		await page.setUserAgent(userAgent);

		// Set realistic browser headers to mimic a real browser
		const realisticHeaders = {
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
			'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
			'Accept-Encoding': 'gzip, deflate, br',
			'Cache-Control': 'no-cache',
			'Pragma': 'no-cache',
			'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
			'Sec-Ch-Ua-Mobile': '?0',
			'Sec-Ch-Ua-Platform': '"Windows"',
			'Sec-Fetch-Dest': 'document',
			'Sec-Fetch-Mode': 'navigate',
			'Sec-Fetch-Site': 'none',
			'Sec-Fetch-User': '?1',
			'Upgrade-Insecure-Requests': '1',
			'DNT': '1',
			'Connection': 'keep-alive',
			...extraHeaders
		};

		await page.setExtraHTTPHeaders(realisticHeaders);

		// Navigate to URL with more flexible strategy
		console.log('Navigating to URL with flexible loading strategy...');
		try {
			// Try networkidle2 first (most reliable for content)
			await page.goto(navigationUrl, { 
				waitUntil: 'networkidle2',
				timeout: waitForTimeout 
			});
			console.log('Navigation successful with networkidle2');
		} catch {
			console.log('networkidle2 failed, trying domcontentloaded...');
			try {
				// Fallback to domcontentloaded (faster, less reliable)
				await page.goto(navigationUrl, { 
					waitUntil: 'domcontentloaded',
					timeout: waitForTimeout 
				});
				console.log('Navigation successful with domcontentloaded');
			} catch {
				console.log('domcontentloaded failed, trying load...');
				// Last resort: just wait for load event
				await page.goto(navigationUrl, { 
					waitUntil: 'load',
					timeout: waitForTimeout 
				});
				console.log('Navigation successful with load');
			}
		}

		// Wait additional 2 seconds after networkidle2 to ensure full rendering
		console.log('Waiting additional 2 seconds for full page rendering...');
		await page.waitForTimeout(2000);

		// Wait for specific selector if provided
		if (waitForSelector) {
			await page.waitForSelector(waitForSelector, { timeout: waitForTimeout });
		}

		// Wait for common content elements to ensure page is fully loaded
		const commonContentSelectors = [
			'article',
			'.caas-body',
			'.story-body', 
			'.entry-content',
			'main',
			'.content',
			'.post-content',
			'.article-content',
			'.news-content',
			'.page-content',
			'[role="main"]',
			'.main-content'
		];

		console.log('Waiting for content elements to load...');
		for (const selector of commonContentSelectors) {
			try {
				await page.waitForSelector(selector, { timeout: 5000 });
				console.log(`Found content element: ${selector}`);
				break; // Exit loop once we find at least one content element
			} catch {
				// Continue to next selector if this one doesn't exist
				continue;
			}
		}

		// Additional wait to ensure dynamic content is loaded
		console.log('Waiting for dynamic content to load...');
		await page.waitForTimeout(3000);

		// Scroll to trigger lazy loading
		console.log('Scrolling to trigger lazy loading...');
		await page.evaluate(() => {
			window.scrollTo(0, document.body.scrollHeight / 2);
		});
		await page.waitForTimeout(1000);
		
		await page.evaluate(() => {
			window.scrollTo(0, document.body.scrollHeight);
		});
		await page.waitForTimeout(1000);

		// Scroll back to top
		await page.evaluate(() => {
			window.scrollTo(0, 0);
		});
		await page.waitForTimeout(1000);

		// Extract content
		const content = await page.evaluate((options) => {
			const { includeImages, includeLinks } = options;

			// Remove script and style elements
			const scripts = document.querySelectorAll('script, style, noscript');
			scripts.forEach(el => el.remove());

			// Remove navigation, sidebar, ad, and other irrelevant elements
			const elementsToRemove = document.querySelectorAll(`
				nav, header, footer, aside,
				.ad, .advertisement, .ads, .banner, .promo,
				.navigation, .navbar, .menu, .sidebar,
				.comments, .comment-section,
				.social-share, .share-buttons,
				.related, .recommended, .similar,
				.popup, .modal, .overlay,
				.cookie-banner, .newsletter,
				[class*="ad-"], [class*="banner-"],
				[class*="nav-"], [class*="menu-"],
				[class*="sidebar"], [class*="aside"]
			`);
			elementsToRemove.forEach(el => el.remove());

			// Extract basic content
			const title = document.title || '';
			const description = document.querySelector('meta[name="description"]')?.content || '';
			const keywords = document.querySelector('meta[name="keywords"]')?.content || '';
			const canonicalUrl = document.querySelector('link[rel="canonical"]')?.href || window.location.href;

			// Extract main text content with multiple strategies
			let textContent = '';
			
			// Strategy 1: Try to find main content containers first
			const mainContentSelectors = [
				'article', '.caas-body', '.story-body', '.entry-content', 
				'main', '.content', '.post-content', '.article-content',
				'.news-content', '.page-content', '[role="main"]', '.main-content'
			];
			
			let mainContentElement = null;
			for (const selector of mainContentSelectors) {
				const element = document.querySelector(selector);
				if (element && element.textContent && element.textContent.trim().length > 100) {
					mainContentElement = element;
					console.log(`Found main content in: ${selector}`);
					break;
				}
			}
			
			if (mainContentElement) {
				textContent = mainContentElement.innerText || mainContentElement.textContent || '';
			} else {
				// Strategy 2: Fallback to body content
				const body = document.body || document.documentElement;
				textContent = body.innerText || body.textContent || '';
			}
			
			// Strategy 3: If content is too short, try extracting from all paragraphs
			if (textContent.length < 200) {
				console.log('Content too short, trying paragraph extraction...');
				const paragraphs = Array.from(document.querySelectorAll('p'))
					.map(p => p.textContent.trim())
					.filter(p => p.length > 20)
					.join(' ');
				if (paragraphs.length > textContent.length) {
					textContent = paragraphs;
				}
			}
			
			// Strategy 4: If still short, try extracting from all text nodes
			if (textContent.length < 200) {
				console.log('Still too short, trying text node extraction...');
				const textNodes = [];
				const walker = document.createTreeWalker(
					document.body,
					NodeFilter.SHOW_TEXT,
					{
						acceptNode: function(node) {
							const text = node.textContent.trim();
							if (text.length > 10 && !text.match(/^(cookie|privacy|terms|advertisement|subscribe|newsletter)/i)) {
								return NodeFilter.FILTER_ACCEPT;
							}
							return NodeFilter.FILTER_REJECT;
						}
					}
				);
				
				let node;
				while ((node = walker.nextNode())) {
					textNodes.push(node.textContent.trim());
				}
				
				const extractedText = textNodes.join(' ');
				if (extractedText.length > textContent.length) {
					textContent = extractedText;
				}
			}

			// Clean up text content
			textContent = textContent
				.replace(/廣告/g, '')
				.replace(/Advertisement/gi, '')
				.replace(/Cookie/gi, '')
				.replace(/Privacy/gi, '')
				.replace(/Subscribe/gi, '')
				.replace(/Newsletter/gi, '')
				.replace(/Related Articles/gi, '')
				.replace(/You may also like/gi, '')
				.replace(/Share this article/gi, '')
				.replace(/Follow us/gi, '')
				.replace(/\s+/g, ' ')
				.replace(/\n\s*\n/g, '\n')
				.trim();

			// Extract headings
			const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'))
				.map(h => ({
					tag: h.tagName.toLowerCase(),
					text: h.textContent.trim(),
					id: h.id || null
				}));

			// Extract paragraphs
			const paragraphs = Array.from(document.querySelectorAll('p'))
				.map(p => p.textContent.trim())
				.filter(p => p.length > 0);

			// Extract links if requested
			let links = [];
			if (includeLinks) {
				links = Array.from(document.querySelectorAll('a[href]'))
					.map(a => ({
						text: a.textContent.trim(),
						href: a.href,
						title: a.title || null
					}))
					.filter(link => link.text && link.href);
			}

			// Extract images if requested
			let images = [];
			if (includeImages) {
				images = Array.from(document.querySelectorAll('img[src]'))
					.map(img => ({
						src: img.src,
						alt: img.alt || '',
						title: img.title || '',
						width: img.naturalWidth || null,
						height: img.naturalHeight || null
					}));
			}

			// Extract meta information
			const metaTags = Array.from(document.querySelectorAll('meta'))
				.reduce((acc, meta) => {
					const name = meta.name || meta.property;
					const content = meta.content;
					if (name && content) {
						acc[name] = content;
					}
					return acc;
				}, {});

			// Extract structured data (JSON-LD)
			const structuredData = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
				.map(script => {
					try {
						return JSON.parse(script.textContent);
					} catch {
						return null;
					}
				})
				.filter(data => data !== null);

			// Assess content quality
			const contentQuality = textContent.length > 500 ? 'good' : 'poor';
			console.log(`Content quality: ${contentQuality} (${textContent.length} characters)`);

			return {
				title,
				description,
				keywords,
				canonicalUrl,
				textContent,
				headings,
				paragraphs,
				links,
				images,
				metaTags,
				structuredData,
				wordCount: textContent.split(/\s+/).length,
				characterCount: textContent.length,
				contentQuality
			};
		}, { includeImages, includeLinks });

		// Take screenshot if requested or if content quality is poor
		let screenshot = null;
		if (takeScreenshot || content.contentQuality === 'poor') {
			const screenshotPath = options.screenshotPath || `screenshot-${Date.now()}.png`;
			console.log(`Taking screenshot: ${screenshotPath}`);
			await page.screenshot({ 
				path: screenshotPath, 
				fullPage: true 
			});
			screenshot = screenshotPath;
		}

		// Get page metrics
		const metrics = await page.metrics();

		// Get final URL (in case of redirects)
		const finalUrl = page.url();

		return {
			success: true,
			url: finalUrl,
			originalUrl: url,
			decodedUrl: decodedUrl,
			content,
			screenshot,
			metrics: {
				loadTime: metrics.LoadEventEnd - metrics.NavigationStart,
				domContentLoaded: metrics.DOMContentLoadedEventEnd - metrics.NavigationStart,
				firstPaint: metrics.FirstPaint || null,
				firstContentfulPaint: metrics.FirstContentfulPaint || null
			},
			extractionInfo: {
				contentLength: content.characterCount,
				contentQuality: content.contentQuality,
				wordCount: content.wordCount,
				headingCount: content.headings.length,
				paragraphCount: content.paragraphs.length,
				linkCount: content.links.length,
				imageCount: content.images.length
			},
			extractedAt: new Date().toISOString()
		};

	} catch (error) {
		console.error('Error extracting web content:', error);
		return {
			success: false,
			url,
			error: error.message,
			extractedAt: new Date().toISOString()
		};
	} finally {
		// Clean up
		if (page) {
			await page.close();
		}
		if (browser) {
			await browser.close();
		}
	}
}

/**
 * Extract content from multiple URLs
 * @param {string[]} urls - Array of URLs to extract content from
 * @param {Object} options - Extraction options (same as extractWebContent)
 * @param {number} options.concurrency - Number of concurrent extractions
 * @returns {Object[]} Array of extraction results
 */
export async function extractMultipleWebContents(urls, options = {}) {
	const { concurrency = 3, ...extractOptions } = options;
	
	const results = [];
	
	// Process URLs in batches
	for (let i = 0; i < urls.length; i += concurrency) {
		const batch = urls.slice(i, i + concurrency);
		const batchPromises = batch.map(url => extractWebContent(url, extractOptions));
		const batchResults = await Promise.all(batchPromises);
		results.push(...batchResults);
	}
	
	return results;
}

/**
 * Extract only text content from a URL (simplified version)
 * @param {string} url - The URL to extract content from
 * @param {Object} options - Extraction options
 * @returns {string} Extracted text content
 */
export async function extractTextOnly(url, options = {}) {
	const result = await extractWebContent(url, options);
	
	if (result.success) {
		return result.content.textContent;
	} else {
		throw new Error(result.error);
	}
}

/**
 * Extract content and return as markdown format
 * @param {string} url - The URL to extract content from
 * @param {Object} options - Extraction options
 * @returns {string} Content formatted as markdown
 */
export async function extractAsMarkdown(url, options = {}) {
	const result = await extractWebContent(url, options);
	
	if (!result.success) {
		throw new Error(result.error);
	}

	const { content } = result;
	let markdown = '';

	// Add title
	if (content.title) {
		markdown += `# ${content.title}\n\n`;
	}

	// Add description
	if (content.description) {
		markdown += `*${content.description}*\n\n`;
	}

	// Add headings
	content.headings.forEach(heading => {
		const level = '#'.repeat(parseInt(heading.tag.slice(1)));
		markdown += `${level} ${heading.text}\n\n`;
	});

	// Add paragraphs
	content.paragraphs.forEach(paragraph => {
		markdown += `${paragraph}\n\n`;
	});

	// Add links
	if (content.links.length > 0) {
		markdown += '## Links\n\n';
		content.links.forEach(link => {
			markdown += `- [${link.text}](${link.href})\n`;
		});
		markdown += '\n';
	}

	return markdown.trim();
}

/**
 * Validate if a string is a valid URL
 * @param {string} string - String to validate
 * @returns {boolean} True if valid URL
 */
function isValidUrl(string) {
	try {
		new URL(string);
		return true;
	} catch {
		return false;
	}
}

/**
 * Extract content from a URL with retry mechanism
 * @param {string} url - The URL to extract content from
 * @param {Object} options - Extraction options
 * @param {number} options.maxRetries - Maximum number of retries
 * @param {number} options.retryDelay - Delay between retries in milliseconds
 * @returns {Object} Extraction result
 */
export async function extractWithRetry(url, options = {}) {
	const { maxRetries = 3, retryDelay = 1000, ...extractOptions } = options;
	
	let lastError = null;
	
	for (let attempt = 1; attempt <= maxRetries; attempt++) {
		try {
			const result = await extractWebContent(url, extractOptions);
			
			if (result.success) {
				return {
					...result,
					attempts: attempt
				};
			} else {
				lastError = new Error(result.error);
			}
		} catch (error) {
			lastError = error;
		}
		
		if (attempt < maxRetries) {
			await new Promise(resolve => setTimeout(resolve, retryDelay));
		}
	}
	
	return {
		success: false,
		url,
		error: `Failed after ${maxRetries} attempts: ${lastError.message}`,
		attempts: maxRetries,
		extractedAt: new Date().toISOString()
	};
}
