/**
 * Flight Post Handler
 * Handles posting selected flights to the Post review page with AI analysis
 */

import { OllamaAIClient, FlightAIHelper } from './ollamaAI.js';
import { generateScenicImage, extractDestination } from '$lib/apis/pollinations/index.js';

/**
 * Formats flight data for posting to the blog
 * @param {Array} selectedFlights - Array of selected flight objects
 * @returns {Object} Formatted data for the Post page
 */
export function formatFlightDataForPost(selectedFlights) {
	if (!selectedFlights || selectedFlights.length === 0) {
		return null;
	}

	// If multiple flights selected, create a comprehensive post
	if (selectedFlights.length > 1) {
		return formatMultipleFlightsPost(selectedFlights);
	}

	// Single flight post
	return formatSingleFlightPost(selectedFlights[0]);
}

/**
 * Formats data for a single flight post
 * @param {Object} flight - Single flight object
 * @returns {Object} Formatted post data
 */
function formatSingleFlightPost(flight) {
	const departureTime = generateFlightTime();
	const returnPrice = flight.cost;
	const luggageInfo = generateLuggageInfo(flight.seatClass);

	return {
		airline: flight.airline,
		returnPrice: returnPrice,
		departureDate: flight.departureDate,
		flightTime: departureTime,
		luggageInfo: luggageInfo,
		startingPlace: flight.startingPlace,
		destination: flight.destination,
		seatClass: flight.seatClass,
		ticketValidDate: flight.ticketValidDate
	};
}

/**
 * Formats data for multiple flights post
 * @param {Array} flights - Array of flight objects
 * @returns {Object} Formatted post data
 */
function formatMultipleFlightsPost(flights) {
	const totalPrice = flights.reduce((sum, flight) => sum + flight.cost, 0);
	const airlines = [...new Set(flights.map(flight => flight.airline))];
	const routes = flights.map(flight => `${flight.startingPlace} → ${flight.destination}`).join(', ');
	
	// Use the earliest departure date
	const earliestDate = flights.reduce((earliest, flight) => 
		new Date(flight.departureDate) < new Date(earliest) ? flight.departureDate : earliest, 
		flights[0].departureDate
	);

	const departureTime = generateFlightTime();
	const luggageInfo = generateLuggageInfo('Mixed'); // Mixed for multiple flights

	return {
		airline: airlines.join(', '),
		returnPrice: totalPrice,
		departureDate: earliestDate,
		flightTime: departureTime,
		luggageInfo: luggageInfo,
		startingPlace: flights[0].startingPlace, // First flight's starting place
		destination: flights[flights.length - 1].destination, // Last flight's destination
		seatClass: 'Mixed',
		ticketValidDate: flights[0].ticketValidDate,
		multipleFlights: true,
		flightCount: flights.length,
		allRoutes: routes
	};
}

/**
 * Generates a realistic flight time
 * @returns {string} Formatted flight time
 */
function generateFlightTime() {
	const hours = Math.floor(Math.random() * 12) + 2; // 2-14 hours
	const minutes = Math.random() < 0.5 ? '00' : '30';
	return `${hours}:${minutes}`;
}

/**
 * Generates luggage information based on seat class
 * @param {string} seatClass - Seat class (Economy, Business, Mixed)
 * @returns {string} Luggage information
 */
function generateLuggageInfo(seatClass) {
	const luggageOptions = {
		'Economy': '1x 23kg checked bag, 1x 7kg carry-on',
		'Business': '2x 32kg checked bags, 1x 10kg carry-on, Priority boarding',
		'Mixed': 'Varies by airline and class - check individual bookings'
	};
	
	return luggageOptions[seatClass] || luggageOptions['Economy'];
}

/**
 * Generates AI analysis for flight data using two-stage pipeline
 * @param {Object} flightData - Formatted flight data object
 * @param {Object} modelToUse - The AI model to use for analysis
 * @returns {Promise<Object>} AI analysis with header, content, and summary
 */
export async function generateAIFlightAnalysis(flightData, modelToUse = null) {
	try {
		// Determine which model to use
		let modelName = 'qwen2.5:14b'; // Default fallback
		
		if (modelToUse) {
			if (modelToUse.ollama_model_name) {
				modelName = modelToUse.ollama_model_name;
			} else if (modelToUse.rag_model_name) {
				modelName = modelToUse.rag_model_name;
			} else if (modelToUse.merged_model_name) {
				modelName = modelToUse.merged_model_name;
			} else if (modelToUse.base_model) {
				modelName = modelToUse.base_model;
			}
		}
		
		console.log('🔍 Final model name selected:', modelName);
		
		const client = new OllamaAIClient({ model: modelName });
		const flightHelper = new FlightAIHelper(client);
		
		console.log('Starting two-stage AI analysis for flight data:', flightData);
		
		// Use the two-stage analysis pipeline
		const analysis = await flightHelper.twoStageFlightAnalysis(flightData);
		console.log('Final analysis result:', analysis);
		
		return {
			header: analysis.header || `Flight Deal: ${flightData.airline}`,
			content: analysis.short_comment || `Great flight deal found! ${flightData.airline} from ${flightData.startingPlace} to ${flightData.destination}`,
			summary: analysis.summary || `Excellent flight deal with ${flightData.airline}! Price: $${flightData.returnPrice} for ${flightData.startingPlace} → ${flightData.destination}`
		};
	} catch (error) {
		console.error('Error generating two-stage AI analysis:', error);
		
		// Fallback to default values if AI fails
		return {
			header: `Flight Deal: ${flightData.airline}`,
			content: `Great flight deal found! ${flightData.airline} from ${flightData.startingPlace} to ${flightData.destination}`,
			summary: `Excellent flight deal with ${flightData.airline}! Price: $${flightData.returnPrice} for ${flightData.startingPlace} → ${flightData.destination}`
		};
	}
}

/**
 * Navigates to the Post page with flight data and AI analysis
 * @param {Array} selectedFlights - Array of selected flight objects
 * @param {Function} goto - SvelteKit navigation function
 * @param {Function} onStageUpdate - Optional callback for stage updates
 * @param {Object} modelToUse - The AI model to use for analysis
 */
export async function navigateToPostWithFlightData(selectedFlights, goto, onStageUpdate = null, modelToUse = null) {
	if (!selectedFlights || selectedFlights.length === 0) {
		console.error('No flight data to post');
		return;
	}

	// Generate AI analysis with stage tracking - pass original array of flights
	// console.log('Passing flights to AI analysis:', selectedFlights.length, 'flight(s)');
	const aiAnalysis = await generateAIFlightAnalysisWithStages(selectedFlights, onStageUpdate, modelToUse);
	
	// Log the complete AI analysis to see all fields
	console.log('🔍 Complete AI Analysis Object:', aiAnalysis);
	console.log('🔍 AI Analysis tourist_spot:', aiAnalysis?.tourist_spot);
	
	// Format the flight data for display after AI analysis
	const postData = formatFlightDataForPost(selectedFlights);
	
	// Temporary mock data for testing images without AI token usage
	// Uncomment the line above and comment out the lines below to use AI
	// const aiAnalysis = {
	// 	header: "Test Header - AI Generation Disabled",
	// 	content: "This is test content. AI generation is currently commented out to save tokens during image testing. Destination: 首爾",
	// 	summary: "Test summary for image testing"
	// };
	
	// Generate scenic image for destination
	let scenicImageUrl = null;
	let imageResponse = null;
	if (onStageUpdate) onStageUpdate('generating_scenic_image');
	
	try {
		// Extract destination and tourist_spot from flight data or AI analysis
		let destination = '';
		let touristSpot = '';
		
		if (postData.destination) {
			destination = postData.destination;
		} else if (aiAnalysis && aiAnalysis.content) {
			destination = extractDestination(aiAnalysis.content) || '';
		}
		
		// Extract tourist_spot from AI analysis if available
		if (aiAnalysis && aiAnalysis.tourist_spot) {
			touristSpot = aiAnalysis.tourist_spot;
			console.log('Tourist spot extracted from AI:', touristSpot);
		}
		
		if (destination) {
			console.log('Generating scenic image for destination:', destination, 'Tourist spot:', touristSpot);
			const token = localStorage.getItem('token') || '';
			
			// Prepare flight data to send to backend
			let flightDataForBackend;
			
			if (selectedFlights.length === 1) {
				// Single flight - send as single object
				const flight = selectedFlights[0];
				flightDataForBackend = {
					airline: flight.airline,
					startingPlace: flight.startingPlace,
					destination: flight.destination,
					departureDate: flight.departureDate,
					returnDate: flight.returnDate || flight.departureDate,
					departureTime: flight.departureTime || "09:30",
					arrivalTime: flight.arrivalTime || "12:50",
					returnDepartureTime: flight.returnDepartureTime || "15:30",
					returnArrivalTime: flight.returnArrivalTime || "19:45",
					cost: flight.cost || 3500,
					seatClass: flight.seatClass
				};
			} else {
				// Multiple flights - send as array
				flightDataForBackend = {
					flights: selectedFlights.map(flight => ({
						airline: flight.airline,
						startingPlace: flight.startingPlace,
						destination: flight.destination,
						departureDate: flight.departureDate,
						returnDate: flight.returnDate || flight.departureDate,
						departureTime: flight.departureTime || "09:30",
						arrivalTime: flight.arrivalTime || "12:50",
						returnDepartureTime: flight.returnDepartureTime || "15:30",
						returnArrivalTime: flight.returnArrivalTime || "19:45",
						cost: flight.cost || 3500,
						seatClass: flight.seatClass
					}))
				};
			}
			
		console.log('About to call generateScenicImage with:', {
			destination: destination,
			tourist_spot: touristSpot,
			style: 'realistic',
			width: 1024,
			height: 1024,
			flight_data: flightDataForBackend,
			ai_analysis: aiAnalysis
		});
		imageResponse = await generateScenicImage(token, {
			destination: destination,
			tourist_spot: touristSpot,
			style: 'realistic',
			width: 1024,
			height: 1024,
			flight_data: flightDataForBackend,
			ai_analysis: aiAnalysis
		});
		console.log('Raw imageResponse received:', imageResponse);
		
		if (imageResponse.success) {
			// Use the edited base64 image if available, otherwise fall back to URL
			scenicImageUrl = imageResponse.image_base64 || imageResponse.image_url;
			console.log('Scenic image generated successfully:', {
				edited: imageResponse.edited,
				hasBase64: !!imageResponse.image_base64,
				hasUrl: !!imageResponse.image_url,
				usingBase64: !!imageResponse.image_base64,
				hasFlightInfoImage: !!imageResponse.flight_info_image_base64,
				response: imageResponse
			});
		}
		}
	} catch (imageError) {
		console.error('Error generating scenic image:', imageError);
		// Continue without image - don't block the flow
	}
	
	// Combine flight data with AI analysis and scenic image
	const completePostData = {
		...postData,
		aiAnalysis: aiAnalysis,
		scenicImage: scenicImageUrl,
		flightInfoImage: imageResponse?.flight_info_image_base64 || null,
		modelInfo: modelToUse // Include model information
	};

	// Store the complete data in sessionStorage for the Post page to retrieve
	sessionStorage.setItem('flightPostData', JSON.stringify(completePostData));
	
	// Navigate to the Post page
	goto('/post');
}

/**
 * Generates AI analysis with stage tracking
 * @param {Object|Array} flightData - Formatted flight data object or array of flight objects
 * @param {Function} onStageUpdate - Optional callback for stage updates
 * @param {Object} modelToUse - The AI model to use for analysis
 * @returns {Promise<Object>} AI analysis with header, content, and summary
 */
export async function generateAIFlightAnalysisWithStages(flightData, onStageUpdate = null, modelToUse = null) {
	try {
		// Determine which model to use and prepare adapter info
		let modelName = 'qwen2.5:14b'; // Default fallback
		let adapterInfo = null;
		
		if (modelToUse) {
			// Check for external model (like Gemini, GPT, etc.)
			if (modelToUse.is_external_model && modelToUse.id) {
				modelName = modelToUse.id;
				console.log('🌐 Using external model:', modelName, 'from provider:', modelToUse.owned_by);
			} else if (modelToUse.id && !modelToUse.ollama_model_name && !modelToUse.rag_model_name) {
				// Generic model ID (could be any model from the list)
				modelName = modelToUse.id;
				console.log('🤖 Using model:', modelName);
			} else if (modelToUse.ollama_model_name) {
				modelName = modelToUse.ollama_model_name;
			} else if (modelToUse.rag_model_name) {
				modelName = modelToUse.rag_model_name;
			} else if (modelToUse.merged_model_name) {
				modelName = modelToUse.merged_model_name;
			} else if (modelToUse.base_model) {
				modelName = modelToUse.base_model;
			}
			
			// Check if this is an adapter selection that needs interception
			if (modelToUse.is_adapter_rag && modelToUse.export_id) {
				// Use base model for RAG processing, but pass adapter info for interception
				modelName = 'qwen2.5:14b';
				adapterInfo = {
					export_id: modelToUse.export_id,
					adapter_name: modelToUse.adapter_name
				};
				console.log('🔄 Adapter interception mode: Using qwen2.5:14b with adapter info:', adapterInfo);
			}
		}
		
		console.log('🔍 Using AI model:', modelName, 'for flight analysis');
		console.log('🔍 Model details passed to function:', modelToUse);
		console.log('🔍 Model selection logic:');
		console.log('  - modelToUse.id:', modelToUse?.id);
		console.log('  - modelToUse.is_external_model:', modelToUse?.is_external_model);
		console.log('  - modelToUse.owned_by:', modelToUse?.owned_by);
		console.log('  - modelToUse.ollama_model_name:', modelToUse?.ollama_model_name);
		console.log('  - modelToUse.rag_model_name:', modelToUse?.rag_model_name);
		console.log('  - modelToUse.merged_model_name:', modelToUse?.merged_model_name);
		console.log('  - modelToUse.base_model:', modelToUse?.base_model);
		console.log('  - adapterInfo:', adapterInfo);
		
		const client = new OllamaAIClient({ model: modelName });
		const flightHelper = new FlightAIHelper(client, adapterInfo);
		
		console.log('Starting two-stage AI analysis for flight data:', flightData);
		
		if (onStageUpdate) onStageUpdate('stage1');
		
		// Use the two-stage analysis pipeline
		const analysis = await flightHelper.twoStageFlightAnalysis(flightData, onStageUpdate);
		console.log('Final analysis result:', analysis);
		
		// Combine destination and header if both exist, otherwise use fallback
		const combinedHeader = analysis.destination && analysis.header 
			? `【${analysis.destination}】${analysis.header}` 
			: (analysis.header || 'Flight Deal');
		
		// Get first flight for fallback values
		const firstFlight = Array.isArray(flightData) ? flightData[0] : flightData;
		
		return {
			header: combinedHeader,
			content: analysis.short_comment || `Great flight deal found! ${firstFlight.airline} from ${firstFlight.startingPlace} to ${firstFlight.destination}`,
			summary: analysis.summary || `Excellent flight deal with ${firstFlight.airline}! Price: $${firstFlight.cost} for ${firstFlight.startingPlace} → ${firstFlight.destination}`,
			destination: analysis.destination || firstFlight.destination,
			tourist_spot: analysis.tourist_spot || ''
		};
	} catch (error) {
		console.error('Error generating two-stage AI analysis:', error);
		
		// Get first flight for fallback values
		const firstFlight = Array.isArray(flightData) ? flightData[0] : flightData;
		
		// Fallback to default values if AI fails
		return {
			header: `Flight Deal: ${firstFlight.airline}`,
			content: `Great flight deal found! ${firstFlight.airline} from ${firstFlight.startingPlace} to ${firstFlight.destination}`,
			summary: `Excellent flight deal with ${firstFlight.airline}! Price: $${firstFlight.cost} for ${firstFlight.startingPlace} → ${firstFlight.destination}`,
			destination: firstFlight.destination,
			tourist_spot: ''
		};
	}
}

/**
 * Retrieves flight data from sessionStorage (to be called on Post page)
 * @returns {Object|null} Flight data or null if not found
 */
export function getFlightDataFromStorage() {
	try {
		const data = sessionStorage.getItem('flightPostData');
		if (data) {
			const parsedData = JSON.parse(data);
			// Clear the data after retrieval
			sessionStorage.removeItem('flightPostData');
			return parsedData;
		}
	} catch (error) {
		console.error('Error retrieving flight data:', error);
	}
	return null;
}

/**
 * Populates Post page form fields with flight data
 * @param {Object} flightData - Flight data object
 * @param {Object} formRefs - Object containing form field references
 */
export function populatePostFormFields(flightData, formRefs) {
	if (!flightData) return;

	// Populate airline field
	if (formRefs.airlineInput) {
		formRefs.airlineInput.value = flightData.airline;
	}

	// Populate return price field
	if (formRefs.returnPriceInput) {
		formRefs.returnPriceInput.value = flightData.returnPrice;
	}

	// Populate departure date field
	if (formRefs.departureDateInput) {
		formRefs.departureDateInput.value = flightData.departureDate;
	}

	// Populate flight time field
	if (formRefs.flightTimeInput) {
		formRefs.flightTimeInput.value = flightData.flightTime;
	}

	// Populate luggage info field
	if (formRefs.luggageInfoInput) {
		formRefs.luggageInfoInput.value = flightData.luggageInfo;
	}

	// Additional fields if they exist
	if (formRefs.startingPlaceInput) {
		formRefs.startingPlaceInput.value = flightData.startingPlace;
	}

	if (formRefs.destinationInput) {
		formRefs.destinationInput.value = flightData.destination;
	}

	if (formRefs.seatClassInput) {
		formRefs.seatClassInput.value = flightData.seatClass;
	}
}

/**
 * Creates a formatted post content from flight data
 * @param {Object} flightData - Flight data object
 * @returns {string} Formatted post content
 */
export function createFlightPostContent(flightData) {
	if (!flightData) return '';

	const { multipleFlights, flightCount, allRoutes } = flightData;

	if (multipleFlights) {
		return `✈️ Flight Deal Alert! ${flightCount} flights found

${flightData.airline}
${allRoutes}

💰 Total Price: $${flightData.returnPrice}
📅 Departure: ${new Date(flightData.departureDate).toLocaleDateString()}
⏰ Flight Time: ${flightData.flightTime}
🎒 Luggage: ${flightData.luggageInfo}

#FlightDeals #Travel #${flightData.airline.replace(/\s+/g, '')} #TravelTips`;
	} else {
		return `✈️ Great Flight Deal Found!

${flightData.airline}
${flightData.startingPlace} → ${flightData.destination}

💰 Price: $${flightData.returnPrice}
📅 Departure: ${new Date(flightData.departureDate).toLocaleDateString()}
⏰ Flight Time: ${flightData.flightTime}
🎒 Luggage: ${flightData.luggageInfo}
💺 Class: ${flightData.seatClass}

#FlightDeals #Travel #${flightData.airline.replace(/\s+/g, '')} #TravelTips`;
	}
}
