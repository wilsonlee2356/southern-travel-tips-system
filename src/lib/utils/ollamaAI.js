/**
 * Ollama AI Integration for OpenWebUI
 * Handles communication with Ollama AI models through OpenWebUI API
 */

// Configuration
const OLLAMA_CONFIG = {
	baseUrl: 'http://localhost:11434', // Default Ollama API URL
	openWebUIUrl: 'http://localhost:8080', // OpenWebUI URL (adjust as needed)
	model: 'humblemat/hon9kon9ize_CantoneseLLMChat-v1.0-7B-F16.gguf:latest', // Default model name (change to your pulled model)
	largeModel: 'qwen2.5:32b', // Larger model for initial analysis (adjust to your available model)
	timeout: 30000, // 30 seconds timeout
	knowledgeUUID: '9028d569-f4e6-47d2-bc11-14f130548a23', // Knowledge base UUID for context
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
			knowledge: this.config.knowledgeUUID,
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
			knowledge: this.config.knowledgeUUID,
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

			let done = false;
			while (!done) {
				const result = await reader.read();
				done = result.done;
				if (done) break;
				const value = result.value;

				const chunk = decoder.decode(value);
				const lines = chunk.split('\n');

				for (const line of lines) {
					if (line.trim()) {
						try {
							const data = JSON.parse(line);
							if (data.response) {
								onChunk(data.response);
							}
						} catch {
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

	/**
	 * Set knowledge UUID for context
	 * @param {string} knowledgeUUID - Knowledge base UUID
	 */
	setKnowledge(knowledgeUUID) {
		this.config.knowledgeUUID = knowledgeUUID;
	}

	/**
	 * Get current knowledge UUID
	 * @returns {string} Current knowledge UUID
	 */
	getKnowledge() {
		return this.config.knowledgeUUID;
	}

	/**
	 * Clear knowledge context
	 */
	clearKnowledge() {
		this.config.knowledgeUUID = null;
	}

	/**
	 * Generate response using the larger model for initial analysis
	 * @param {string} prompt - The prompt to send to the AI
	 * @param {Object} options - Additional options
	 * @returns {Promise<string>} AI response from larger model
	 */
	async generateResponseWithLargeModel(prompt, options = {}) {
		const requestOptions = {
			model: options.model || this.config.largeModel,
			prompt: prompt,
			stream: false,
			knowledge: this.config.knowledgeUUID,
			options: {
				temperature: options.temperature || 0.7,
				top_p: options.top_p || 0.9,
				max_tokens: options.max_tokens || 1500, // Larger token limit for comprehensive analysis
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
			console.error('Error generating response with large model:', error);
			throw error;
		}
	}
}

/**
 * Utility function to clean JSON responses from markdown formatting and explanatory text
 * @param {string} response - Raw AI response
 * @returns {string} Cleaned JSON string
 */
function cleanJsonResponse(response) {
	// Remove markdown formatting
	let cleaned = response.replace(/^```json\s*/, '').replace(/\s*```$/, '');
	
	// Remove any text before the first { (opening brace)
	const jsonStartIndex = cleaned.indexOf('{');
	if (jsonStartIndex > 0) {
		cleaned = cleaned.substring(jsonStartIndex);
	}
	
	// Find the last } (closing brace) and remove everything after it
	const jsonEndIndex = cleaned.lastIndexOf('}');
	if (jsonEndIndex > 0 && jsonEndIndex < cleaned.length - 1) {
		cleaned = cleaned.substring(0, jsonEndIndex + 1);
	}
	
	// Fix JSON by removing newlines and control characters from string values
	cleaned = fixJsonStringValues(cleaned);
	
	return cleaned;
}

/**
 * Recursively clean string values in objects
 * @param {any} obj - Object to clean
 * @returns {any} Cleaned object
 */
function cleanObject(obj) {
	if (typeof obj === 'string') {
		// Remove newlines, carriage returns, and other control characters
		return obj.replace(/[\r\n\t\f\v]/g, ' ').replace(/\s+/g, ' ').trim();
	} else if (Array.isArray(obj)) {
		return obj.map(cleanObject);
	} else if (obj && typeof obj === 'object') {
		const cleaned = {};
		for (const [key, value] of Object.entries(obj)) {
			cleaned[key] = cleanObject(value);
		}
		return cleaned;
	}
	return obj;
}

/**
 * Fix JSON string values by removing newlines and control characters
 * @param {string} jsonString - JSON string that may contain invalid characters
 * @returns {string} Fixed JSON string
 */
function fixJsonStringValues(jsonString) {
	try {
		// Parse and re-stringify to fix control characters
		const parsed = JSON.parse(jsonString);
		
		// Recursively clean string values
		const cleaned = cleanObject(parsed);
		return JSON.stringify(cleaned);
	} catch (error) {
		// If parsing fails, try to manually fix common issues
		console.warn('JSON parsing failed, attempting manual fix:', error);
		
		// Remove newlines and control characters from string values
		let fixed = jsonString
			.replace(/\\n/g, ' ')  // Replace literal \n
			.replace(/\\r/g, ' ')  // Replace literal \r
			.replace(/\\t/g, ' ')  // Replace literal \t
			.replace(/\n/g, ' ')   // Replace actual newlines
			.replace(/\r/g, ' ')   // Replace actual carriage returns
			.replace(/\t/g, ' ')   // Replace actual tabs
			.replace(/\s+/g, ' '); // Replace multiple spaces with single space
		
		return fixed;
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
		const prompt = `根據已選機票資料和航空促銷文件指引的格式,並根據促銷文本指引分別生成標題,評論和總結,重要!評論只能在三十字以內,而總結能夠長約一百字.這些都必須是繁體中文.你的輸出必須只能有Json,絕對不能有任何文字,符號或回應在前後.Json格式內只能有"header","short_comment"和"summary".Json內不能有任何換行,以下是Json例子
						{
							"header": "【美國】創疫後直航新低價！多平飛日子選擇！國泰航空來回洛杉磯/三藩市，連稅$5,328起！2026年6月30日或之前出發",
							"short_comment": "好多平飛！去美國嘅人真係少咗？",
							"summary": "國泰直航一減再減，不斷創疫後新低價，直迫轉機價！直航慳時間就算貴幾厝，都值得俾啦！優惠仲可以 open jaw，可以唔走回頭路玩晒加州兩大城市，連復活節都有平，正呀～"
						}
						已選機票資料:
						[
						航空公司：${flightData.airline}
						出發地點：${flightData.startingPlace}
						目的地：${flightData.destination}
						來回價錢：$${flightData.returnPrice}
						艙等：${flightData.seatClass}
						出發日期：${flightData.departureDate}
						出發時間：${flightData.flightTime}
						行李資訊：${flightData.luggageInfo}]`;

		return await this.client.generateResponse(prompt, {
			temperature: 0.2, // Lower temperature for more factual responses
			max_tokens: 3000
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
		const prompt = `Provide comprehensive travel tips for ${destination} based on your knowledge base:

Include:
1. Best time to visit
2. Must-see attractions
3. Local cuisine recommendations
4. Cultural etiquette
5. Transportation options
6. Budget tips
7. Safety considerations
8. Packing suggestions

Use your knowledge base to provide accurate and up-to-date information. Format as a helpful travel guide with practical advice.`;

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

		const prompt = `Compare these flight options and recommend the best one based on your knowledge base:

${flightsText}

Consider:
1. Value for money
2. Airline reputation
3. Route convenience
4. Class benefits
5. Overall recommendation

Use your knowledge base to provide accurate airline information and route insights. Provide a clear recommendation with reasoning.`;

		return await this.client.generateResponse(prompt, {
			temperature: 0.3,
			max_tokens: 600
		});
	}

	/**
	 * Stage 1: Generate initial flight analysis using larger model
	 * @param {Object} flightData - Flight data object
	 * @returns {Promise<string>} Initial AI analysis JSON
	 */
	async generateInitialFlightAnalysis(flightData) {
		const prompt = `Analyze this flight deal comprehensively and create promotional content:

Flight Details:
- Airline: ${flightData.airline}
- Route: ${flightData.startingPlace} → ${flightData.destination}
- Price: $${flightData.returnPrice}
- Class: ${flightData.seatClass}
- Departure: ${flightData.departureDate}
- Flight Time: ${flightData.flightTime}
- Luggage: ${flightData.luggageInfo}

Please analyze this flight deal and create promotional content. Consider:
1. Market price comparison
2. Route popularity and demand
3. Airline reputation and service quality
4. Seasonal factors and timing
5. Value proposition for travelers

Generate a comprehensive analysis and create engaging promotional content. Return the result as a JSON object with the following structure:
{
  "header": "Compelling promotional headline",
  "content": "Engaging promotional content/comment",
  "summary": "Concise summary of the deal's value proposition"
}

Make the content engaging, informative, and persuasive for potential travelers.`;

		return await this.client.generateResponseWithLargeModel(prompt, {
			temperature: 0.4, // Balanced creativity and accuracy
			max_tokens: 1200
		});
	}

	/**
	 * Stage 2: Refine content using current model
	 * @param {Object} initialContent - Initial content from large model
	 * @param {Object} flightData - Flight data object for context
	 * @returns {Promise<string>} Refined content JSON
	 */
	async refineFlightContent(initialContent, flightData) {
		const prompt = `以下是機票資料:
[
航空公司：${flightData.airline}
出發地點：${flightData.startingPlace}
目的地：${flightData.destination}
來回價錢：$${flightData.returnPrice}
艙等：${flightData.seatClass}
出發日期：${flightData.departureDate}
出發時間：${flightData.flightTime}
行李資訊：${flightData.luggageInfo}]

以下是初步分析結果:
{
  "header": "${initialContent.header}",
  "short_comment": "${initialContent.short_comment}",
  "summary": "${initialContent.summary}"
}

請根據機票資料和促銷文件指引的格式，優化並改進以上內容至廣東話口語。
請保持JSON格式，但可以修改header、short_comment和summary的文字內容，使其更符合香港/廣東話的口語。
"header"對應為標題,"short_comment"對應為評論和"summary"對應為總結。
修改的header、short_comment和summary的文字內容絕對不能有任何換行、空格、制表符或其他控制字符。所有文字必須在同一行內。
請根據機票資料生成優化後的JSON內容。
重要：你的回應必須只包含JSON格式，不能有任何其他文字、說明、解釋或回應。直接輸出JSON，不要有任何前綴或後綴文字。不要使用對答模式，不要解釋你的回應。
以下是JSON格式例子:
{
  "header": "【美國】創疫後直航新低價！多平飛日子選擇！國泰航空來回洛杉磯/三藩市，連稅$5,328起！2026年6月30日或之前出發",
  "short_comment": "好多平飛！去美國嘅人真係少咗？",
  "summary": "國泰直航一減再減，不斷創疫後新低價，直迫轉機價！直航慳時間就算貴幾厝，都值得俾啦！優惠仲可以 open jaw，可以唔走回頭路玩晒加州兩大城市，連復活節都有平，正呀～"
}`;

		return await this.client.generateResponse(prompt, {
			temperature: 0.6, // Slightly higher for creative refinement
			max_tokens: 800
		});
	}

	/**
	 * Two-stage flight analysis: Large model + Current model refinement
	 * @param {Object} flightData - Flight data object
	 * @param {Function} onStageUpdate - Optional callback for stage updates
	 * @returns {Promise<Object>} Final refined analysis
	 */
	async twoStageFlightAnalysis(flightData, onStageUpdate = null) {
		try {
			console.log('Stage 1: Generating initial analysis with large model...');
			if (onStageUpdate) onStageUpdate('stage1');
			
			// Stage 1: Generate initial content with larger model
			const initialResponse = await this.generateInitialFlightAnalysis(flightData);
			console.log('Initial response:', initialResponse);
			
			// Remove markdown formatting if present
			const cleanedResponse = cleanJsonResponse(initialResponse);
			const initialContent = JSON.parse(cleanedResponse);
			
			console.log('Stage 2: Refining content with current model...');
			if (onStageUpdate) onStageUpdate('stage2');
			
			// Stage 2: Refine with current model
			const refinedResponse = await this.refineFlightContent(initialContent, flightData);
			console.log('Refined response:', refinedResponse);
			
			// Remove markdown formatting if present
			const cleanedRefinedResponse = cleanJsonResponse(refinedResponse);
			const refinedContent = JSON.parse(cleanedRefinedResponse);
			
			return refinedContent;
		} catch (error) {
			console.error('Error in two-stage analysis:', error);
			
			// Fallback to single-stage analysis
			console.log('Falling back to single-stage analysis...');
			const fallbackResponse = await this.analyzeFlightDeal(flightData);
			// Remove markdown formatting if present
			const cleanedFallbackResponse = cleanJsonResponse(fallbackResponse);
			return JSON.parse(cleanedFallbackResponse);
		}
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
	},

	/**
	 * Create client with specific knowledge UUID
	 * @param {string} knowledgeUUID - Knowledge base UUID
	 * @param {Object} config - Additional configuration
	 * @returns {OllamaAIClient} Configured client with knowledge
	 */
	createClientWithKnowledge(knowledgeUUID, config = {}) {
		return new OllamaAIClient({
			...config,
			knowledgeUUID: knowledgeUUID
		});
	}
};

// Default export
export default OllamaAIClient;
