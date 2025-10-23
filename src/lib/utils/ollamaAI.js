/**
 * Ollama AI Integration for OpenWebUI
 * Handles communication with Ollama AI models through OpenWebUI API
 */

// Configuration
const OLLAMA_CONFIG = {
	baseUrl: 'http://localhost:8080', // OpenWebUI API URL for RAG functionality
	openWebUIUrl: 'http://localhost:8080', // OpenWebUI URL
	model: 'humblemat/hon9kon9ize_CantoneseLLMChat-v1.0-7B-F16.gguf:latest', // Default model name
	largeModel: 'qwen2.5:32b', // Larger model for initial analysis
	timeout: 30000, // 30 seconds timeout
	knowledgeUUID: '9028d569-f4e6-47d2-bc11-14f130548a23', // Knowledge base UUID for RAG context
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
		const modelToUse = options.model || this.config.model;
		
		// Detect if this is an external model (non-Ollama)
		// External models like GPT-4, Gemini don't support the 'knowledge' parameter
		// They get RAG context injected directly into the prompt by the backend middleware
		const isExternalModel = modelToUse.startsWith('gpt-') || 
		                        modelToUse.startsWith('models/gemini-') || 
		                        modelToUse.includes('gemini-') ||
		                        modelToUse.startsWith('claude-') ||
		                        !modelToUse.includes(':'); // Ollama models usually have : like qwen2.5:14b
		
		const requestOptions = {
			model: modelToUse,
			messages: [
				{
					role: "user",
					content: prompt
				}
			],
			stream: false,
			temperature: options.temperature || 0.7,
			top_p: options.top_p || 0.9,
			max_tokens: options.max_tokens || 1000,
			...options.ollamaOptions
		};
		
		// Add knowledge UUID for ALL models (Ollama and external)
		// The backend middleware will use this to inject RAG context
		if (this.config.knowledgeUUID) {
			requestOptions.knowledge = this.config.knowledgeUUID;
			if (isExternalModel) {
				console.log('🌐 External model detected - sending knowledge UUID for backend RAG injection');
			} else {
				console.log('📚 Adding RAG knowledge UUID for Ollama model');
			}
		}

		// Add adapter information to metadata if provided
		if (options.adapterInfo) {
			requestOptions.metadata = {
				adapter_info: options.adapterInfo
			};
			console.log('🔧 Adding adapter info to metadata:', options.adapterInfo);
		}

		// ===== LOG THE COMPLETE PROMPT BEING SENT =====
		console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
		console.log('📝 COMPLETE PROMPT BEING SENT TO AI:');
		console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
		console.log(prompt);
		console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
		console.log('📋 RAG Knowledge UUID:', this.config.knowledgeUUID);
		console.log('🤖 Model:', modelToUse);
		console.log('🌡️ Temperature:', requestOptions.temperature);
		console.log('📊 Max Tokens:', requestOptions.max_tokens);
		console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

		// Enhanced logging for debugging
		console.log('🔍 OllamaAIClient.generateResponse() called:');
		console.log('  📍 Base URL:', this.config.baseUrl);
		console.log('  🤖 Model to use:', modelToUse);
		console.log('  🔧 Options passed:', options);
		console.log('  📋 Full request options:', requestOptions);
		console.log('  🌐 Full URL:', `${this.config.baseUrl}/api/v1/chat/completions`);
		console.log('  📦 Request body:', JSON.stringify(requestOptions, null, 2));

		// Test if the model exists first
		try {
			console.log('🔍 Testing model availability...');
			
			// Get authentication token for model check
			const token = localStorage.getItem('token');
			const modelHeaders = {
				'Content-Type': 'application/json',
			};
			
			if (token) {
				modelHeaders['Authorization'] = `Bearer ${token}`;
			}
			
			const modelsResponse = await fetch(`${this.config.baseUrl}/api/v1/models`, {
				headers: modelHeaders
			});
			if (modelsResponse.ok) {
				const modelsData = await modelsResponse.json();
				const availableModels = modelsData.data?.map(m => m.id) || [];
				console.log('  ✅ Available models:', availableModels);
				console.log('  ❓ Model exists?', availableModels.includes(modelToUse));
				if (!availableModels.includes(modelToUse)) {
					console.warn('⚠️ Model not found in available models list!');
				}
			} else {
				console.warn('⚠️ Could not fetch available models list');
			}
		} catch (modelsError) {
			console.warn('⚠️ Error checking available models:', modelsError);
		}

		try {
			console.log('🚀 Making request to OpenWebUI API...');
			
			// Get authentication token from localStorage
			const token = localStorage.getItem('token');
			const headers = {
				'Content-Type': 'application/json',
			};
			
			// Add authorization header if token exists
			if (token) {
				headers['Authorization'] = `Bearer ${token}`;
				console.log('  🔐 Using authentication token');
			} else {
				console.warn('  ⚠️ No authentication token found');
			}
			
			const response = await fetch(`${this.config.baseUrl}/api/v1/chat/completions`, {
				method: 'POST',
				headers: headers,
				body: JSON.stringify(requestOptions),
			});

			console.log('📡 Response received:');
			console.log('  📊 Status:', response.status);
			console.log('  📋 Status Text:', response.statusText);
			console.log('  🔗 URL:', response.url);

			if (!response.ok) {
				const errorText = await response.text();
				console.error('❌ HTTP Error Details:');
				console.error('  📊 Status:', response.status);
				console.error('  📋 Status Text:', response.statusText);
				console.error('  📄 Response Body:', errorText);
				throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
			}

			const data = await response.json();
			console.log('✅ Response parsed successfully');
			console.log('  📄 Response data:', data);
			// OpenWebUI returns response in data.choices[0].message.content
			return data.choices?.[0]?.message?.content || data.response || 'No response generated';
		} catch (error) {
			console.error('💥 Error in generateResponse:');
			console.error('  🔍 Error type:', error.constructor.name);
			console.error('  📝 Error message:', error.message);
			console.error('  📍 Stack trace:', error.stack);
			console.error('  🔧 Request options that failed:', requestOptions);
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
	
	// Try to parse the JSON directly first (handles pretty-printed JSON)
	try {
		const parsed = JSON.parse(cleaned);
		console.log('✅ Successfully parsed JSON, now cleaning object...');
		// Clean the object but preserve \n in promote_text
		const cleanedObj = cleanObject(parsed);
		const result = JSON.stringify(cleanedObj);
		console.log('✅ Successfully cleaned and stringified JSON');
		return result;
	} catch (parseError) {
		console.warn('⚠️ JSON processing failed (trying to fix):', parseError.message);
		
		// The JSON has actual newline characters inside string values
		// We need to escape them BEFORE parsing
		// Use a regex to find string values and replace actual newlines with \n
		let fixed = cleaned.replace(
			/"([^"]*?)"/g, 
			(match, content) => {
				// Replace actual newlines with escaped \n inside string values
				const escapedContent = content
					.replace(/\r\n/g, '\\n')
					.replace(/\n/g, '\\n')
					.replace(/\r/g, '\\n')
					.replace(/\t/g, '\\t');
				return `"${escapedContent}"`;
			}
		);
		
		console.log('🔧 Fixed newlines in string values');
		
		try {
			const parsed = JSON.parse(fixed);
			console.log('✅ Successfully parsed fixed JSON');
			// Clean the object but preserve \n in promote_text
			const cleanedObj = cleanObject(parsed);
			const result = JSON.stringify(cleanedObj);
			console.log('✅ Successfully cleaned and stringified fixed JSON');
			return result;
		} catch (fixError) {
			console.error('❌ Still failed to parse after fix:', fixError.message);
			console.log('Fixed JSON (first 300 chars):', fixed.substring(0, 300));
			throw new Error(`Unable to parse or fix JSON: ${parseError.message}`);
		}
	}
}

/**
 * Recursively clean string values in objects
 * @param {any} obj - Object to clean
 * @param {string} key - Current key being processed (to preserve \n in promote_text)
 * @returns {any} Cleaned object
 */
function cleanObject(obj, key = null) {
	if (typeof obj === 'string') {
		// For promote_text field, preserve newline characters (\n) but clean up formatting
		if (key === 'promote_text') {
			// Split by \n, trim each line, then rejoin with \n
			// This removes extra spaces from pretty-printed JSON formatting
			return obj.split('\n').map(line => line.trim()).join('\n');
		}
		// For other fields, remove newlines, carriage returns, and other control characters
		return obj.replace(/[\r\n\t\f\v]/g, ' ').replace(/\s+/g, ' ').trim();
	} else if (Array.isArray(obj)) {
		return obj.map(item => cleanObject(item, key));
	} else if (obj && typeof obj === 'object') {
		const cleaned = {};
		for (const [k, value] of Object.entries(obj)) {
			cleaned[k] = cleanObject(value, k);
		}
		return cleaned;
	}
	return obj;
}

/**
 * Flight-specific AI prompts and utilities
 */
export class FlightAIHelper {
	constructor(ollamaClient, adapterInfo = null) {
		this.client = ollamaClient;
		this.adapterInfo = adapterInfo;
	}

	/**
	 * Generate flight deal analysis
	 * @param {Object} flightData - Flight data object
	 * @returns {Promise<string>} AI analysis
	 */
	async analyzeFlightDeal(flightData) {
		const prompt = `根據已選機票資料和指引的格式,並根據指引分別生成目的地,標題,評論和總結,任何日期必須以中文形式年月日.重要!評論只能在三十字以內,而總結能夠長約一百字.這些都必須是繁體中文廣東話語氣.你的輸出必須只能有Json,絕對不能有任何文字,符號或回應在前後.Json格式內只能有"destination","header","short_comment"和"summary".Json內不能有任何換行,以下是Json例子
						{
							"destination": "美國",
							"header": "創疫後直航新低價！多平飛日子選擇！國泰航空來回洛杉磯/三藩市，連稅$5,328起！2026年6月30日或之前出發",
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

		return await this.client.generateResponseWithLargeModel(prompt, {
			temperature: 0.4, // Balanced creativity and accuracy
			max_tokens: 800
		});
		// const prompt = `根據已選機票資料和航空促銷文件指引的格式,並根據促銷文本指引分別生成目的地,標題,評論和總結,重要!評論只能在三十字以內,而總結能夠長約一百字.這些都必須是繁體中文.你的輸出必須只能有Json,絕對不能有任何文字,符號或回應在前後.Json格式內只能有"destination","header","short_comment"和"summary".Json內不能有任何換行,以下是Json例子
		// 				{
		// 					"destination": "美國",
		// 					"header": "創疫後直航新低價！多平飛日子選擇！國泰航空來回洛杉磯/三藩市，連稅$5,328起！2026年6月30日或之前出發",
		// 					"short_comment": "好多平飛！去美國嘅人真係少咗？",
		// 					"summary": "國泰直航一減再減，不斷創疫後新低價，直迫轉機價！直航慳時間就算貴幾厝，都值得俾啦！優惠仲可以 open jaw，可以唔走回頭路玩晒加州兩大城市，連復活節都有平，正呀～"
		// 				}
		// 				已選機票資料:
		// 				[
		// 				航空公司：${flightData.airline}
		// 				出發地點：${flightData.startingPlace}
		// 				目的地：${flightData.destination}
		// 				來回價錢：$${flightData.returnPrice}
		// 				艙等：${flightData.seatClass}
		// 				出發日期：${flightData.departureDate}
		// 				出發時間：${flightData.flightTime}
		// 				行李資訊：${flightData.luggageInfo}]`;

		// return await this.client.generateResponse(prompt, {
		// 	temperature: 0.2, // Lower temperature for more factual responses
		// 	max_tokens: 3000
		// });
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
	 * Stage 1: Generate initial flight analysis using selected model
	 * @param {Object|Array} flightData - Flight data object or array of flight objects
	 * @returns {Promise<string>} Initial AI analysis JSON
	 */
	async generateInitialFlightAnalysis(flightData) {
		// Handle both single flight and multiple flights
		const flights = Array.isArray(flightData) ? flightData : [flightData];
		
		// Remove duplicates based on unique combination of airline, route, date, and time
		const uniqueFlights = [];
		const seen = new Set();
		
		flights.forEach(flight => {
			// Create a unique key based on flight details
			const uniqueKey = `${flight.airline}|${flight.startingPlace}|${flight.destination}|${flight.departureDate}|${flight.departureTime || flight.flightTime || ''}|${flight.cost || flight.returnPrice}`;
			
			if (!seen.has(uniqueKey)) {
				seen.add(uniqueKey);
				uniqueFlights.push(flight);
			} else {
				console.log('🎯 Duplicate flight detected and removed:', uniqueKey);
			}
		});
		
		console.log(`🎯 Deduplicated: ${flights.length} flights -> ${uniqueFlights.length} unique flights`);
		
		// Group flights by route (starting place → destination)
		const routeGroups = {};
		
		uniqueFlights.forEach(flight => {
			const routeKey = `${flight.startingPlace}->${flight.destination}`;
			
			if (!routeGroups[routeKey]) {
				routeGroups[routeKey] = {
					airlines: [],
					startingPlace: flight.startingPlace,
					destination: flight.destination,
					prices: [],
					seatClasses: [],
					departureDates: [],
					departureTimes: [],
					luggageInfos: []
				};
			}
			
			// Collect data from each flight in this route
			routeGroups[routeKey].airlines.push(flight.airline);
			routeGroups[routeKey].prices.push(flight.cost || flight.returnPrice);
			routeGroups[routeKey].seatClasses.push(flight.seatClass);
			routeGroups[routeKey].departureDates.push(flight.departureDate);
			routeGroups[routeKey].departureTimes.push(flight.departureTime || flight.flightTime || '待定');
			routeGroups[routeKey].luggageInfos.push(flight.luggageInfo || '20kg');
		});
		
		// Build flight data string with each route group separated by comma
		const flightDataString = Object.values(routeGroups).map(group => {
			// Combine airlines with comma
			const airlines = [...new Set(group.airlines)].join(', ');
			
			// Calculate total price or use first price if only one
			const totalPrice = group.prices.reduce((sum, p) => sum + p, 0);
			
			// Use first values for other fields, or "Mixed" if multiple different values
			const seatClass = new Set(group.seatClasses).size > 1 ? 'Mixed' : group.seatClasses[0];
			const departureDate = group.departureDates[0]; // Use earliest date
			const departureTime = group.departureTimes[0]; // Use first time
			const luggage = new Set(group.luggageInfos).size > 1 ? 'Varies by airline and class - check individual bookings' : group.luggageInfos[0];
			
			return `[航空公司：${airlines} 出發地點：${group.startingPlace} 目的地：${group.destination} 來回價錢：$${totalPrice} 艙等：${seatClass} 出發日期：${departureDate} 出發時間：${departureTime} 行李資訊：${luggage}]`;
		}).join(', ');
		
		const prompt = `仿又飛啦廣東俚語，輸JSON，每來回一對象，選最平價，含destination、header、short_comment、summary、tourist_spot、promote_text。destination取非香港地。header首句約十字，含超前部署、平、抵、減之一，推銷機票，後接航司、價、期，勿含destination。short_comment一至二句，限二十字，多變語氣，述地或價優（如直航減到咁平，心動！）。summary約八十字，句以逗點斷，每句宜長，約二三十字，述價、地景、促行，依資料，勿增詞。destination、header、short_comment、summary、promote_text用繁體廣東話，promote_text短句分行，限二行，述價、航優或地景，可含行李。tourist_spot用英文，隨選目的地名勝。價港幣，出發地香港，假設連稅、2025/2026。

## 例
### 東京
{"destination":"東京","header":"超前部署！人氣日本目的地！ANA來回連稅$2,323起！2025年9月出發","short_comment":"想嚟日本旅行？呢個又幾抵玩！","summary":"二千五唔使飛東京真係好抵玩，航班時間都好多選擇，早/凌晨去晚返都得，日子選擇都唔少，東京最快10月下旬就開始有紅葉，想去睇可以plan一plan佢啦～","tourist_spot":"Shibuya Crossing","promote_text":"直航抵飛！\n加埋寄艙行李都唔使二千四！"}
### 福岡
{"destination":"福岡","header":"難得減到咁平！德威航空來回連稅$1,885起！2025年10月出發","short_comment":"正！福岡難得減到咁平！","summary":"減到千四有找包埋行李，平時要二千樓上㗎！真係勁抵買呀！航班時間中去黃昏返都幾唔錯，想去福岡玩就要快啲睇睇啦～","tourist_spot":"Canal City","promote_text":"激抵！平飛福岡！\n包15kg行李真平！"}
### 曼谷
{"destination":"曼谷","header":"減到千五有找！泰航來回連稅$1,500起！2026年1月出發","short_comment":"嘩！平到唔信～","summary":"搭國泰呢口價，一日有多達七班機揀，可以早去晚返，連暑假都照有平，好值得入手！去曼谷食玩買返幾日叉叉電啦～","tourist_spot":"Grand Palace","promote_text":"抵價飛泰國！\n千五有找！"}

## 資料：${flightDataString}`;

		// ===== LOG THE CONSTRUCTED PROMPT BEFORE SENDING =====
		console.log('🎯 ═══════════════════════════════════════════════════════════');
		console.log('🎯 FLIGHT ANALYSIS PROMPT (with flight data filled in):');
		console.log('🎯 Original flights received:', flights.length);
		console.log('🎯 After deduplication:', uniqueFlights.length);
		console.log('🎯 UNIQUE FLIGHT OBJECTS:');
		uniqueFlights.forEach((flight, idx) => {
			console.log(`🎯 Flight ${idx + 1}:`, {
				id: flight.id,
				airline: flight.airline,
				startingPlace: flight.startingPlace,
				destination: flight.destination,
				cost: flight.cost,
				departureDate: flight.departureDate,
				departureTime: flight.departureTime
			});
		});
		console.log('🎯 Number of route groups:', Object.keys(routeGroups).length);
		console.log('🎯 Route groups:', routeGroups);
		console.log('🎯 ═══════════════════════════════════════════════════════════');
		console.log('🎯 FINAL PROMPT:');
		console.log(prompt);
		console.log('🎯 ═══════════════════════════════════════════════════════════');

		return await this.client.generateResponse(prompt, {
			temperature: 0.4, // Balanced creativity and accuracy
			max_tokens: 800,
			adapterInfo: this.adapterInfo // Pass adapter info for interception
		});
	}

	/**
	 * Stage 2: Refine content using current model
	 * @param {Object} initialContent - Initial content from large model
	 * @param {Object} flightData - Flight data object for context
	 * @returns {Promise<string>} Refined content JSON
	 */
	async refineFlightContent(initialContent, flightData, model = null) {
		console.log('refineFlightContent called with model:', model);
		console.log('client.config.model:', this.client.config.model);
		const actualModel = model || this.client.config.model;
		console.log('Using model for refinement:', actualModel);
		
		const prompt = `
以下是初步分析結果:
{
  "destination": "${initialContent.destination}",
  "header": "${initialContent.header}",
  "short_comment": "${initialContent.short_comment}",
  "summary": "${initialContent.summary}"
}

請根據廣東話翻譯指引的格式，由書面語翻譯以上內容至廣東話語氣同標點符號。
請保持JSON格式，但係修改header、short_comment和summary的文字內容，令到佢更符合香港/廣東話的語氣。
"header"對應為標題,"short_comment"對應為評論和"summary"對應為總結。
修改的header、short_comment和summary的文字內容絕對唔可以有任何換行、空格、制表符或其他控制字符。所有文字必須在同一行裏面。
重要：你的回應必須只包含JSON格式，唔可以有JSON之外的任何其他文字、說明、解釋或回應。直接輸出JSON，不要有任何前綴或後綴文字。不要使用對答模式，不要解釋你的回應。
以下是JSON格式例子:
{
  "destination": "美國",
  "header": "創疫後直航新低價！多平飛日子選擇！國泰航空來回洛杉磯/三藩市，連稅$5,328起！2026年6月30日或之前出發",
  "short_comment": "好多平飛！去美國嘅人真係少咗？",
  "summary": "國泰直航一減再減，不斷創疫後新低價，直迫轉機價！直航慳時間就算貴幾厝，都值得俾啦！優惠仲可以 open jaw，可以唔走回頭路玩晒加州兩大城市，連復活節都有平，正呀～"
}`;

		return await this.client.generateResponseWithLargeModel(prompt, {
			temperature: 0.8, // Slightly higher for creative refinement
			max_tokens: 800
		});
	}

	/**
	 * Two-stage flight analysis: Large model + Current model refinement
	 * @param {Object|Array} flightData - Flight data object or array of flight objects
	 * @param {Function} onStageUpdate - Optional callback for stage updates
	 * @returns {Promise<Object>} Final refined analysis
	 */
	async twoStageFlightAnalysis(flightData, onStageUpdate = null) {
		try {
			const flights = Array.isArray(flightData) ? flightData : [flightData];
			console.log(`Stage 1: Generating initial analysis for ${flights.length} flight(s) with large model...`);
			if (onStageUpdate) onStageUpdate('stage1');
			
		// Stage 1: Generate initial content with larger model
		const initialResponse = await this.generateInitialFlightAnalysis(flightData);
		console.log('🎯 RAW AI RESPONSE:', initialResponse);
		
		// Remove markdown formatting if present
		const cleanedResponse = cleanJsonResponse(initialResponse);
		console.log('🎯 CLEANED JSON RESPONSE (ready for parsing):', cleanedResponse);
		console.log('🎯 First 200 chars:', cleanedResponse.substring(0, 200));
		
		const initialContent = JSON.parse(cleanedResponse);
		console.log('🎯 PARSED AI CONTENT:', initialContent);
		console.log('🎯 Has tourist_spot?', 'tourist_spot' in initialContent, '| Value:', initialContent.tourist_spot);
		console.log('🎯 Has promote_text?', 'promote_text' in initialContent, '| Value:', initialContent.promote_text);
			
		// TODO: Uncomment Stage 2 later
		// console.log('Stage 2: Refining content with current model...');
		// console.log('Stage 2 using model:', this.client.config.model);
		// if (onStageUpdate) onStageUpdate('stage2');
		
		// Stage 2: Refine with current model (use the same model as Stage 1)
		// const refinedResponse = await this.refineFlightContent(initialContent, flightData, this.client.config.model);
		// console.log('Refined response:', refinedResponse);
		
		// Remove markdown formatting if present
		// const cleanedRefinedResponse = cleanJsonResponse(refinedResponse);
		// const refinedContent = JSON.parse(cleanedRefinedResponse);
		
		// For now, return the initial content without refinement
		console.log('Skipping Stage 2 refinement, returning initial content');
		return initialContent;
		} catch (error) {
			console.error('Error in two-stage analysis:', error);
			
			// Fallback to single-stage analysis
			console.log('Falling back to single-stage analysis...');
			// Use first flight for fallback if array
			const singleFlight = Array.isArray(flightData) ? flightData[0] : flightData;
			const fallbackResponse = await this.analyzeFlightDeal(singleFlight);
			// Remove markdown formatting if present
			const cleanedFallbackResponse = cleanJsonResponse(fallbackResponse);
			const fallbackContent = JSON.parse(cleanedFallbackResponse);
			console.log('🎯 FALLBACK PARSED CONTENT:', fallbackContent);
			console.log('🎯 Fallback has promote_text?', 'promote_text' in fallbackContent, '| Value:', fallbackContent.promote_text);
			return fallbackContent;
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
