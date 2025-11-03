/**
 * Amadeus API Configuration
 * This file handles configuration for the Amadeus Flight API integration
 */

// Default configuration values
const DEFAULT_CONFIG = {
	// API Base URLs
	BASE_URL: 'https://api.amadeus.com',
	
	// API Credentials (will be overridden by environment variables)
	API_KEY: '',
	API_SECRET: '',
	
	// API Settings
	TOKEN_EXPIRY_BUFFER: 300, // 5 minutes buffer before token expiry
	DEFAULT_MAX_RESULTS: 20,
	DEFAULT_ADULTS: 1,
	DEFAULT_TRAVEL_CLASS: 'ECONOMY',
	
	// Request timeouts
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
		BASE_URL: env.VITE_AMADEUS_BASE_URL || env.AMADEUS_BASE_URL || DEFAULT_CONFIG.BASE_URL,
		API_KEY: env.VITE_AMADEUS_API_KEY || env.AMADEUS_API_KEY || DEFAULT_CONFIG.API_KEY,
		API_SECRET: env.VITE_AMADEUS_API_SECRET || env.AMADEUS_API_SECRET || DEFAULT_CONFIG.API_SECRET,
		TOKEN_EXPIRY_BUFFER: parseInt(env.VITE_AMADEUS_TOKEN_EXPIRY_BUFFER || env.AMADEUS_TOKEN_EXPIRY_BUFFER || DEFAULT_CONFIG.TOKEN_EXPIRY_BUFFER),
		DEFAULT_MAX_RESULTS: parseInt(env.VITE_AMADEUS_MAX_RESULTS || env.AMADEUS_MAX_RESULTS || DEFAULT_CONFIG.DEFAULT_MAX_RESULTS),
		DEFAULT_ADULTS: parseInt(env.VITE_AMADEUS_DEFAULT_ADULTS || env.AMADEUS_DEFAULT_ADULTS || DEFAULT_CONFIG.DEFAULT_ADULTS),
		DEFAULT_TRAVEL_CLASS: env.VITE_AMADEUS_DEFAULT_TRAVEL_CLASS || env.AMADEUS_DEFAULT_TRAVEL_CLASS || DEFAULT_CONFIG.DEFAULT_TRAVEL_CLASS,
		REQUEST_TIMEOUT: parseInt(env.VITE_AMADEUS_REQUEST_TIMEOUT || env.AMADEUS_REQUEST_TIMEOUT || DEFAULT_CONFIG.REQUEST_TIMEOUT),
		MAX_RETRIES: parseInt(env.VITE_AMADEUS_MAX_RETRIES || env.AMADEUS_MAX_RETRIES || DEFAULT_CONFIG.MAX_RETRIES),
		RETRY_DELAY: parseInt(env.VITE_AMADEUS_RETRY_DELAY || env.AMADEUS_RETRY_DELAY || DEFAULT_CONFIG.RETRY_DELAY),
	};
}

/**
 * Validate configuration
 */
function validateConfig(config) {
	const errors = [];
	
	if (!config.API_KEY) {
		errors.push('AMADEUS_API_KEY is required');
	}
	
	if (!config.API_SECRET) {
		errors.push('AMADEUS_API_SECRET is required');
	}
	
	if (!config.BASE_URL) {
		errors.push('AMADEUS_BASE_URL is required');
	}
	
	if (errors.length > 0) {
		throw new Error(`Configuration validation failed: ${errors.join(', ')}`);
	}
	
	return true;
}

/**
 * Get validated configuration
 */
export function getAmadeusConfig() {
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
		return !!(config.API_KEY && config.API_SECRET && config.BASE_URL);
	} catch (error) {
		return false;
	}
}

/**
 * Get configuration for development (with fallback values)
 */
export function getDevConfig() {
	const config = getConfig();
	
	// For development, provide fallback values if not configured
	if (!config.API_KEY) {
		console.warn('AMADEUS_API_KEY not found in environment variables. Using fallback for development.');
		config.API_KEY = 'Jqw7LkuKMaxLSTFLCJAvKfl4JwhWrDWu'; // Fallback for development
	}
	
	if (!config.API_SECRET) {
		console.warn('AMADEUS_API_SECRET not found in environment variables. Using fallback for development.');
		config.API_SECRET = 'GZGmwJsBDKRKr6Fg'; // Fallback for development
	}
	
	return config;
}

export default {
	getAmadeusConfig,
	isConfigAvailable,
	getDevConfig
};
