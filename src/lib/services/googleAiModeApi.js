/**
 * Google AI Mode API Service (SearchAPI.io)
 * Documentation: https://www.searchapi.io/docs/google-ai-mode-api
 */

const GOOGLE_AI_MODE_ENDPOINT = 'https://www.searchapi.io/api/v1/search';

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

	return response.json();
}

