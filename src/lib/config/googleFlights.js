/**
 * Google Flights API (SerpApi) Configuration
 * This file handles configuration for the SerpApi Google Flights API integration
 */

// Default configuration values
const DEFAULT_CONFIG = {
	// API Base URL
	BASE_URL: 'https://serpapi.com',
	
	// API Key (will be overridden by environment variables)
	API_KEY: '',
	
	// API Settings
	REQUEST_TIMEOUT: 30000, // 30 seconds
	
	// Retry settings
	MAX_RETRIES: 3,
	RETRY_DELAY: 1000, // 1 second
};

/**
 * Get configuration values from environment variables or defaults
 */
function getConfig() {
	// In browser environment, we'll use import.meta.env (Vite)
	// In Node.js environment, we'll use process.env
	const env = typeof window !== 'undefined' ? import.meta.env : process.env;
	
	return {
		BASE_URL: env.VITE_GOOGLE_FLIGHTS_BASE_URL || env.GOOGLE_FLIGHTS_BASE_URL || DEFAULT_CONFIG.BASE_URL,
		API_KEY: env.VITE_GOOGLE_FLIGHTS_API_KEY || env.GOOGLE_FLIGHTS_API_KEY || DEFAULT_CONFIG.API_KEY,
		REQUEST_TIMEOUT: parseInt(env.VITE_GOOGLE_FLIGHTS_REQUEST_TIMEOUT || env.GOOGLE_FLIGHTS_REQUEST_TIMEOUT || DEFAULT_CONFIG.REQUEST_TIMEOUT),
		MAX_RETRIES: parseInt(env.VITE_GOOGLE_FLIGHTS_MAX_RETRIES || env.GOOGLE_FLIGHTS_MAX_RETRIES || DEFAULT_CONFIG.MAX_RETRIES),
		RETRY_DELAY: parseInt(env.VITE_GOOGLE_FLIGHTS_RETRY_DELAY || env.GOOGLE_FLIGHTS_RETRY_DELAY || DEFAULT_CONFIG.RETRY_DELAY),
	};
}

/**
 * Validate configuration
 */
function validateConfig(config) {
	const errors = [];
	
	if (!config.API_KEY) {
		errors.push('GOOGLE_FLIGHTS_API_KEY is required');
	}
	
	if (!config.BASE_URL) {
		errors.push('GOOGLE_FLIGHTS_BASE_URL is required');
	}
	
	if (errors.length > 0) {
		throw new Error(`Configuration validation failed: ${errors.join(', ')}`);
	}
	
	return true;
}

/**
 * Get validated configuration
 */
export function getGoogleFlightsConfig() {
	const config = getConfig();
	validateConfig(config);
	return config;
}

/**
 * Check if configuration is available
 */
export function isConfigAvailable() {
	try {
		const config = getConfig();
		return !!(config.API_KEY && config.BASE_URL);
	} catch (error) {
		return false;
	}
}

/**
 * Get configuration for development (with fallback values)
 * Note: API key is not needed on client side since API calls go through server proxy
 */
export function getDevConfig() {
	const config = getConfig();
	
	// API key is handled server-side, so no validation needed on client
	// Just return config with empty API key (not used on client anyway)
	config.API_KEY = '';
	
	return config;
}

export default {
	getGoogleFlightsConfig,
	isConfigAvailable,
	getDevConfig
};

