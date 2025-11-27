/**
 * Google AI Mode API Service (SearchAPI.io)
 * Documentation: https://www.searchapi.io/docs/google-ai-mode-api
 */

const GOOGLE_AI_MODE_ENDPOINT = 'https://www.searchapi.io/api/v1/search';

/**
 * Convert Google AI Mode text_blocks entries into a single string for UI display/logging.
 * @param {Array<{answer?: string, items?: Array<{answer?: string}>}>} textBlocks
 * @returns {string}
 */
export function formatGoogleAiModeTextBlocks(textBlocks) {
	if (!Array.isArray(textBlocks) || textBlocks.length === 0) {
		return '';
	}

	const segments = [];

	const visitBlock = (block) => {
		if (!block || typeof block !== 'object') {
			return;
		}

		const cleanedAnswer = typeof block.answer === 'string' ? block.answer.trim() : '';
		const pushIfText = (text) => {
			if (text) {
				segments.push(text);
			}
		};

		switch (block.type) {
			case 'header':
				pushIfText(cleanedAnswer.toUpperCase());
				break;
			case 'paragraph':
				pushIfText(cleanedAnswer);
				break;
			case 'unordered_list': {
				if (cleanedAnswer) {
					pushIfText(cleanedAnswer);
				}
				(block.items || []).forEach((item) => {
					const itemText = formatListItemText(item, '•');
					pushIfText(itemText);
				});
				break;
			}
			case 'ordered_list': {
				if (cleanedAnswer) {
					pushIfText(cleanedAnswer);
				}
				(block.items || []).forEach((item, idx) => {
					const itemText = formatListItemText(item, `${idx + 1}.`);
					pushIfText(itemText);
				});
				break;
			}
			case 'table': {
				const headers = block.table?.headers;
				const rows = block.table?.rows;
				if (Array.isArray(headers) && headers.length > 0) {
					pushIfText(headers.join(' | '));
				}
				if (Array.isArray(rows)) {
					rows.forEach((row) => {
						pushIfText(Array.isArray(row) ? row.join(' | ') : '');
					});
				}
				break;
			}
			case 'code_blocks': {
				const lang = block.language ? `${block.language}:\n` : '';
				pushIfText(`${lang}${block.code ?? ''}`.trim());
				break;
			}
			default:
				if (cleanedAnswer) {
					pushIfText(cleanedAnswer);
				}
		}

		if (Array.isArray(block.items) && block.type !== 'unordered_list' && block.type !== 'ordered_list') {
			block.items.forEach((item, idx) => visitBlock(item, idx));
		}
	};

	const formatListItemText = (itemBlock, prefix) => {
		if (!itemBlock || typeof itemBlock !== 'object') {
			return '';
		}
		const textParts = [];
		if (typeof itemBlock.answer === 'string' && itemBlock.answer.trim()) {
			textParts.push(`${prefix} ${itemBlock.answer.trim()}`);
		}
		if (Array.isArray(itemBlock.items) && itemBlock.items.length > 0) {
			itemBlock.items.forEach((nestedItem, idx) => {
				const nestedText = formatListItemText(nestedItem, prefix === '•' ? '◦' : `${idx + 1})`);
				if (nestedText) {
					textParts.push(nestedText);
				}
			});
		}
		return textParts.join('\n');
	};

	textBlocks.forEach((block) => visitBlock(block));

	return segments.filter(Boolean).join('\n\n');
}

/**
 * Supported Google AI Mode parameters documented by SearchAPI.io.
 * Exposed for discoverability and potential validation in UI layers.
 */
export const GOOGLE_AI_MODE_SUPPORTED_PARAMS = new Set([
	'engine',
	'q',
	'url',
	'location',
	'uule',
	'api_key',
	'zero_retention',
	'hl',
	'gl'
]);

/**
 * @typedef {Object} GoogleAiModeParams
 * @property {string} [q] - Search query text. Required unless `url` is provided.
 * @property {string} [url] - Public image URL for Google Lens-style queries. Optional if `q` is provided.
 * @property {string} [location] - Canonical search location (e.g., "New York"). Mutually exclusive with `uule`.
 * @property {string} [uule] - Google-encoded location string. Mutually exclusive with `location`.
 * @property {string} [hl] - Interface language (e.g., "en").
 * @property {string} [gl] - Geolocation country code (e.g., "us").
 * @property {boolean|string} [zero_retention] - Enterprise-only zero retention flag.
 * @property {string} [engine] - SearchAPI engine. Defaults to "google_ai_mode".
 * @property {string} [api_key] - SearchAPI API key. Optional when using backend proxy.
 */

/**
 * Call SearchAPI's Google AI Mode endpoint with full parameter coverage.
 * @param {GoogleAiModeParams} params - Search parameters accepted by the API.
 * @param {AbortSignal} [signal] - Optional AbortController signal for cancellation.
 * @returns {Promise<Object>} - Parsed JSON response from SearchAPI.
 */
export async function fetchGoogleAiModeResults(params = {}, signal) {
	if (!params || typeof params !== 'object') {
		throw new Error('Parameters object is required');
	}

	const {
		q,
		url,
		location,
		uule,
		api_key: apiKey,
		engine = 'google_ai_mode',
		zero_retention: zeroRetention,
		hl,
		gl
	} = params;

	if (!q && !url) {
		throw new Error('Either q (search query) or url (image URL) must be provided');
	}

	if (location && uule) {
		throw new Error('location and uule cannot be used at the same time');
	}

	const useProxy = !apiKey;
	const searchParams = new URLSearchParams();

	const normalizedParams = {
		engine,
		q,
		url,
		location,
		uule,
		hl,
		gl,
		...(apiKey ? { api_key: apiKey } : {}),
		zero_retention: typeof zeroRetention === 'boolean' ? String(zeroRetention) : zeroRetention
	};

	Object.entries(normalizedParams).forEach(([key, value]) => {
		if (value === undefined || value === null || value === '') {
			return;
		}

		searchParams.append(key, value.toString());
	});

	const targetUrl = useProxy
		? `/api/google-ai-mode?${searchParams.toString()}`
		: `${GOOGLE_AI_MODE_ENDPOINT}?${searchParams.toString()}`;

	const sanitizedUrl = apiKey ? targetUrl.replace(apiKey, '***') : targetUrl;
	console.debug('Calling Google AI Mode API:', sanitizedUrl);

	const response = await fetch(targetUrl, {
		method: 'GET',
		headers: {
			Accept: 'application/json'
		},
		signal
	});

	if (!response.ok) {
		let details = await response.text();
		try {
			const parsed = JSON.parse(details);
			details = parsed?.error || parsed?.message || details;
		} catch {
			// noop – keep raw details
		}
		throw new Error(`Google AI Mode request failed (${response.status}): ${details}`);
	}

	const data = await response.json();
	console.debug('Google AI Mode raw response:', data);

	const formattedTextBlocks = formatGoogleAiModeTextBlocks(data?.text_blocks);
	console.debug('Google AI Mode processed text blocks:', formattedTextBlocks);

	return data;
}

