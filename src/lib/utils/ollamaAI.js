/**
 * Ollama AI Integration for OpenWebUI
 * Handles communication with Ollama AI models through OpenWebUI API
 */

// Configuration
const OLLAMA_CONFIG = {
	baseUrl: 'http://localhost:11434', // Default Ollama API URL
	openWebUIUrl: 'http://localhost:8080', // OpenWebUI URL (adjust as needed)
	model: 'humblemat/hon9kon9ize_CantoneseLLMChat-v1.0-7B-F16.gguf:latest', // Default model name (change to your pulled model)
	timeout: 30000, // 30 seconds timeout
};

/**
 * Ollama AI Client Class
 */
export class OllamaAIClient {
	constructor(config = {}) {
		this.config = { ...OLLAMA_CONFIG, ...config };
		this.isConnected = false;
	}

	/**
	 * Test connection to Ollama
	 * @returns {Promise<boolean>} Connection status
	 */
	async testConnection() {
		try {
			const response = await fetch(`${this.config.baseUrl}/api/tags`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			});

			if (response.ok) {
				const data = await response.json();
				this.isConnected = true;
				console.log('Available models:', data.models?.map(m => m.name) || []);
				return true;
			}
		} catch (error) {
			console.error('Connection test failed:', error);
			this.isConnected = false;
		}
		return false;
	}

	/**
	 * Get list of available models
	 * @returns {Promise<Array>} List of available models
	 */
	async getAvailableModels() {
		try {
			const response = await fetch(`${this.config.baseUrl}/api/tags`);
			if (response.ok) {
				const data = await response.json();
				return data.models || [];
			}
		} catch (error) {
			console.error('Failed to get models:', error);
		}
		return [];
	}

	/**
	 * Generate response from Ollama AI
	 * @param {string} prompt - The prompt to send to the AI
	 * @param {Object} options - Additional options
	 * @returns {Promise<string>} AI response
	 */
	async generateResponse(prompt, options = {}) {
		const requestOptions = {
			model: options.model || this.config.model,
			prompt: prompt,
			stream: false,
			options: {
				temperature: options.temperature || 0.7,
				top_p: options.top_p || 0.9,
				max_tokens: options.max_tokens || 1000,
				...options.ollamaOptions
			}
		};

		try {
			const response = await fetch(`${this.config.baseUrl}/api/generate`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(requestOptions),
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const data = await response.json();
			return data.response || 'No response generated';
		} catch (error) {
			console.error('Error generating response:', error);
			throw error;
		}
	}

	/**
	 * Stream response from Ollama AI (for real-time responses)
	 * @param {string} prompt - The prompt to send to the AI
	 * @param {Function} onChunk - Callback function for each chunk
	 * @param {Object} options - Additional options
	 * @returns {Promise<void>}
	 */
	async streamResponse(prompt, onChunk, options = {}) {
		const requestOptions = {
			model: options.model || this.config.model,
			prompt: prompt,
			stream: true,
			options: {
				temperature: options.temperature || 0.7,
				top_p: options.top_p || 0.9,
				...options.ollamaOptions
			}
		};

		try {
			const response = await fetch(`${this.config.baseUrl}/api/generate`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(requestOptions),
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const reader = response.body.getReader();
			const decoder = new TextDecoder();

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const chunk = decoder.decode(value);
				const lines = chunk.split('\n');

				for (const line of lines) {
					if (line.trim()) {
						try {
							const data = JSON.parse(line);
							if (data.response) {
								onChunk(data.response);
							}
						} catch (e) {
							// Skip invalid JSON lines
						}
					}
				}
			}
		} catch (error) {
			console.error('Error streaming response:', error);
			throw error;
		}
	}

	/**
	 * Chat with context (conversation history)
	 * @param {Array} messages - Array of message objects with 'role' and 'content'
	 * @param {Object} options - Additional options
	 * @returns {Promise<string>} AI response
	 */
	async chat(messages, options = {}) {
		// Convert messages to a single prompt
		const prompt = messages.map(msg => {
			const role = msg.role === 'user' ? 'Human' : 'Assistant';
			return `${role}: ${msg.content}`;
		}).join('\n\n') + '\n\nAssistant:';

		return await this.generateResponse(prompt, options);
	}
}

/**
 * Flight-specific AI prompts and utilities
 */
export class FlightAIHelper {
	constructor(ollamaClient) {
		this.client = ollamaClient;
	}

	/**
	 * Generate flight deal analysis
	 * @param {Object} flightData - Flight data object
	 * @returns {Promise<string>} AI analysis
	 */
	async analyzeFlightDeal(flightData) {
		const prompt = `Analyze this flight deal and provide insights:

Airline: ${flightData.airline}
Route: ${flightData.startingPlace} → ${flightData.destination}
Price: $${flightData.returnPrice}
Class: ${flightData.seatClass}
Departure: ${flightData.departureDate}
Flight Time: ${flightData.flightTime}
Luggage: ${flightData.luggageInfo}

Please provide:
1. Price analysis (good deal, average, expensive)
2. Route insights
3. Airline reputation
4. Travel tips for this route
5. Best booking timing advice

Format your response in a clear, structured way.`;

		return await this.client.generateResponse(prompt, {
			temperature: 0.3, // Lower temperature for more factual responses
			max_tokens: 800
		});
	}

	/**
	 * Generate social media post content
	 * @param {Object} flightData - Flight data object
	 * @param {string} platform - Social media platform (instagram, facebook, twitter)
	 * @returns {Promise<string>} Generated post content
	 */
	async generateSocialMediaPost(flightData, platform = 'instagram') {
		const platformStyles = {
			instagram: 'engaging, visual, use emojis, hashtags',
			facebook: 'informative, detailed, community-focused',
			twitter: 'concise, trending, use hashtags'
		};

		const prompt = `Create a ${platform} post about this flight deal:

Airline: ${flightData.airline}
Route: ${flightData.startingPlace} → ${flightData.destination}
Price: $${flightData.returnPrice}
Class: ${flightData.seatClass}

Style: ${platformStyles[platform]}
Length: ${platform === 'twitter' ? 'under 280 characters' : 'engaging and detailed'}
Include: relevant hashtags, call-to-action, travel excitement

Make it sound authentic and exciting for travelers.`;

		return await this.client.generateResponse(prompt, {
			temperature: 0.8, // Higher temperature for creative content
			max_tokens: 300
		});
	}

	/**
	 * Generate travel tips for destination
	 * @param {string} destination - Destination city/country
	 * @returns {Promise<string>} Travel tips
	 */
	async generateTravelTips(destination) {
		const prompt = `Provide comprehensive travel tips for ${destination}:

Include:
1. Best time to visit
2. Must-see attractions
3. Local cuisine recommendations
4. Cultural etiquette
5. Transportation options
6. Budget tips
7. Safety considerations
8. Packing suggestions

Format as a helpful travel guide with practical advice.`;

		return await this.client.generateResponse(prompt, {
			temperature: 0.4,
			max_tokens: 1000
		});
	}

	/**
	 * Compare multiple flight options
	 * @param {Array} flights - Array of flight objects
	 * @returns {Promise<string>} Comparison analysis
	 */
	async compareFlights(flights) {
		const flightsText = flights.map((flight, index) => 
			`Option ${index + 1}:
- Airline: ${flight.airline}
- Price: $${flight.cost}
- Class: ${flight.seatClass}
- Route: ${flight.startingPlace} → ${flight.destination}`
		).join('\n\n');

		const prompt = `Compare these flight options and recommend the best one:

${flightsText}

Consider:
1. Value for money
2. Airline reputation
3. Route convenience
4. Class benefits
5. Overall recommendation

Provide a clear recommendation with reasoning.`;

		return await this.client.generateResponse(prompt, {
			temperature: 0.3,
			max_tokens: 600
		});
	}
}

/**
 * Utility functions for common AI operations
 */
export const AIUtils = {
	/**
	 * Initialize Ollama client with custom configuration
	 * @param {Object} config - Configuration object
	 * @returns {OllamaAIClient} Configured client
	 */
	createClient(config = {}) {
		return new OllamaAIClient(config);
	},

	/**
	 * Quick prompt function for simple AI interactions
	 * @param {string} prompt - The prompt
	 * @param {string} model - Model name (optional)
	 * @returns {Promise<string>} AI response
	 */
	async quickPrompt(prompt, model = 'llama2') {
		const client = new OllamaAIClient({ model });
		return await client.generateResponse(prompt);
	},

	/**
	 * Check if Ollama is running and accessible
	 * @returns {Promise<boolean>} Connection status
	 */
	async checkOllamaStatus() {
		const client = new OllamaAIClient();
		return await client.testConnection();
	}
};

// Default export
export default OllamaAIClient;
