/**
 * Amadeus Flight Offers Search API Service
 * Handles authentication and flight search requests
 */

import { getAmadeusConfig, getDevConfig } from '$lib/config/amadeus.js';

class AmadeusApiService {
	constructor() {
		this.accessToken = null;
		this.tokenExpiry = null;
		this.config = null;
		this.initializeConfig();
	}

	/**
	 * Initialize configuration
	 */
	initializeConfig() {
		try {
			// Try to get production config first
			this.config = getAmadeusConfig();
		} catch (error) {
			// Fall back to development config with warnings
			console.warn('Using development configuration for Amadeus API:', error.message);
			this.config = getDevConfig();
		}
	}

	/**
	 * Get access token from Amadeus API
	 */
	async getAccessToken() {
		// Check if we have a valid token
		if (this.accessToken && this.tokenExpiry && Date.now() < this.tokenExpiry) {
			return this.accessToken;
		}

		try {
			console.log('Requesting Amadeus access token...');
			const response = await fetch(`${this.config.BASE_URL}/v1/security/oauth2/token`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded',
				},
				body: new URLSearchParams({
					grant_type: 'client_credentials',
					client_id: this.config.API_KEY,
					client_secret: this.config.API_SECRET,
				}),
			});

			console.log('Amadeus authentication response status:', response.status);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				console.error('Amadeus authentication error:', errorData);
				throw new Error(`Authentication failed: ${response.status} ${response.statusText}. ${errorData.error_description || errorData.error || ''}`);
			}

			const data = await response.json();
			this.accessToken = data.access_token;
			// Set expiry time (subtract buffer time for safety)
			this.tokenExpiry = Date.now() + (data.expires_in - this.config.TOKEN_EXPIRY_BUFFER) * 1000;

			console.log('Amadeus access token obtained successfully');
			return this.accessToken;
		} catch (error) {
			console.error('Error getting Amadeus access token:', error);
			throw new Error(`Failed to authenticate with Amadeus API: ${error.message}`);
		}
	}

	/**
	 * Test API credentials and connection
	 */
	async testConnection() {
		try {
			console.log('Testing Amadeus API connection...');
			await this.getAccessToken();
			console.log('Amadeus API connection test successful');
			return true;
		} catch (error) {
			console.error('Amadeus API connection test failed:', error);
			return false;
		}
	}

	/**
	 * Search for flight offers
	 * @param {Object} searchParams - Search parameters
	 * @param {string} searchParams.originLocationCode - Origin airport/city code
	 * @param {string} searchParams.destinationLocationCode - Destination airport/city code
	 * @param {string} searchParams.departureDate - Departure date (YYYY-MM-DD)
	 * @param {string} searchParams.returnDate - Return date (YYYY-MM-DD, optional)
	 * @param {number} searchParams.adults - Number of adult passengers
	 * @param {string} searchParams.travelClass - Travel class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
	 * @param {number} searchParams.max - Maximum number of results
	 */
	async searchFlightOffers(searchParams) {
		try {
			// Validate required parameters
			if (!searchParams.originLocationCode) {
				throw new Error('Origin location code is required');
			}
			if (!searchParams.destinationLocationCode) {
				throw new Error('Destination location code is required');
			}
			if (!searchParams.departureDate) {
				throw new Error('Departure date is required');
			}

			// Validate date format
			const departureDate = new Date(searchParams.departureDate);
			if (isNaN(departureDate.getTime())) {
				throw new Error('Invalid departure date format. Use YYYY-MM-DD');
			}

			// Check if departure date is not in the past
			const today = new Date();
			today.setHours(0, 0, 0, 0);
			if (departureDate < today) {
				throw new Error('Departure date cannot be in the past');
			}

			// Validate return date if provided
			if (searchParams.returnDate) {
				const returnDate = new Date(searchParams.returnDate);
				if (isNaN(returnDate.getTime())) {
					throw new Error('Invalid return date format. Use YYYY-MM-DD');
				}
				if (returnDate <= departureDate) {
					throw new Error('Return date must be after departure date');
				}
			}

			const token = await this.getAccessToken();

			// For flexible dates, use POST body with originDestinations and dateWindow (±3 days)
			// Ref: https://developers.amadeus.com/self-service/category/flights/api-doc/flight-offers-search/api-reference
			const originDestinations = [];
			const outbound = {
				id: '1',
				originLocationCode: searchParams.originLocationCode,
				destinationLocationCode: searchParams.destinationLocationCode,
				departureDateTimeRange: {
					date: searchParams.departureDate,
					dateWindow: 'P3D'
				}
			};
			originDestinations.push(outbound);
			if (searchParams.returnDate) {
				originDestinations.push({
					id: '2',
					originLocationCode: searchParams.destinationLocationCode,
					destinationLocationCode: searchParams.originLocationCode,
					departureDateTimeRange: {
						date: searchParams.returnDate,
						dateWindow: 'P3D'
					}
				});
			}

			const travelers = [
				{ id: '1', travelerType: 'ADULT' }
			];

			const maxFlightOffers = searchParams.max || this.config.DEFAULT_MAX_RESULTS;
			console.log(`Setting maxFlightOffers: ${maxFlightOffers} (searchParams.max=${searchParams.max}, config.DEFAULT_MAX_RESULTS=${this.config.DEFAULT_MAX_RESULTS})`);
			
			const searchCriteria = {
				maxFlightOffers: maxFlightOffers
			};

			// Map travelClass if provided
			if (searchParams.travelClass) {
				searchCriteria.flightFilters = {
					cabinRestrictions: [
						{
							cabin: (searchParams.travelClass || 'ECONOMY'),
							coverage: 'MOST_SEGMENTS',
							originDestinationIds: originDestinations.map(od => od.id)
						}
					]
				};
			}

			const body = {
				currencyCode: 'HKD',
				originDestinations,
				travelers,
				sources: ['GDS'],
				searchCriteria
			};

			const requestUrl = `${this.config.BASE_URL}/v2/shopping/flight-offers`;
			console.log('Amadeus API Request URL (POST flex):', requestUrl, body);

			const response = await fetch(requestUrl, {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${token}`,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(body)
			});

			console.log('Amadeus API Response Status:', response.status, response.statusText);

			if (!response.ok) {
				let errorMessage = `Flight search failed: ${response.status} ${response.statusText}`;
				try {
					const errorData = await response.json();
					console.error('Amadeus API Error Details:', errorData);
					
					// Handle specific Amadeus error codes
					if (errorData.errors && Array.isArray(errorData.errors)) {
						const errorMessages = errorData.errors.map(err => err.detail || err.title || 'Unknown error');
						errorMessage += `. ${errorMessages.join(', ')}`;
					} else if (errorData.detail) {
						errorMessage += `. ${errorData.detail}`;
					}
				} catch (parseError) {
					console.error('Failed to parse error response:', parseError);
				}
				throw new Error(errorMessage);
			}

			const data = await response.json();
			const resultCount = data?.data?.length || 0;
			console.log(`Amadeus API Response: ${resultCount} flight offers returned (requested maxFlightOffers: ${maxFlightOffers})`);
			if (data?.data) {
				console.log('Amadeus API Response Data:', data);
			}
			return data;
		} catch (error) {
			console.error('Error searching flights:', error);
			throw error;
		}
	}

	/**
	 * Search for cheapest flight dates (Amadeus Flight Cheapest Date Search API)
	 * https://developers.amadeus.com/self-service/category/flights/api-doc/flight-cheapest-date-search/api-reference
	 * @param {Object} searchParams - Search parameters
	 * @param {string} searchParams.originLocationCode - Origin airport code (IATA, required)
	 * @param {string} searchParams.destinationLocationCode - Destination airport code (IATA, required)
	 * @param {string} searchParams.departureDate - Departure date in YYYY-MM-DD format (required)
	 * @param {boolean} searchParams.oneWay - One-way trip (default: false for round trip)
	 * @param {number} searchParams.duration - Trip duration in days (1-15, optional)
	 * @param {boolean} searchParams.nonStop - Direct flights only (default: false)
	 * @param {string} searchParams.viewBy - View results by DATE, DESTINATION, DURATION, WEEK, COUNTRY (default: DATE)
	 * @param {number} searchParams.maxPrice - Maximum price (optional)
	 */
	async searchCheapestDates(searchParams) {
		try {
			// Validate required parameters
			if (!searchParams.originLocationCode) {
				throw new Error('Origin location code is required');
			}

			// Validate origin code format (3-letter IATA code)
			if (!/^[A-Z]{3}$/i.test(searchParams.originLocationCode)) {
				throw new Error('Origin must be a valid 3-letter IATA airport code (e.g., HKG, NRT)');
			}

			// Validate destination if provided
			if (searchParams.destinationLocationCode && !/^[A-Z]{3}$/i.test(searchParams.destinationLocationCode)) {
				throw new Error('Destination must be a valid 3-letter IATA airport code (e.g., NRT, LAX)');
			}

			// Validate departure date (YYYY-MM-DD format required by API)
			if (searchParams.departureDate) {
				// Check if it's YYYY-MM-DD format
				if (!/^\d{4}-\d{2}-\d{2}$/.test(searchParams.departureDate)) {
					throw new Error('Invalid departure date format. Use YYYY-MM-DD (e.g., 2025-10-29)');
				}

				// Validate the date is not in the past
				const departureDate = new Date(searchParams.departureDate);
				if (isNaN(departureDate.getTime())) {
					throw new Error('Invalid departure date');
				}
				
				const today = new Date();
				today.setHours(0, 0, 0, 0);
				if (departureDate < today) {
					throw new Error('Departure date cannot be in the past');
				}
			}

			// Validate duration if provided
			if (searchParams.duration !== undefined) {
				const duration = parseInt(searchParams.duration);
				if (isNaN(duration) || duration < 1 || duration > 15) {
					throw new Error('Duration must be between 1 and 15 days');
				}
			}

			// Validate viewBy if provided
			const validViewBy = ['DATE', 'DESTINATION', 'DURATION', 'WEEK', 'COUNTRY'];
			if (searchParams.viewBy && !validViewBy.includes(searchParams.viewBy.toUpperCase())) {
				throw new Error(`viewBy must be one of: ${validViewBy.join(', ')}`);
			}

			const token = await this.getAccessToken();

			// Build query parameters - API uses 'origin' and 'destination', not 'originLocationCode'
			const queryParams = new URLSearchParams({
				origin: searchParams.originLocationCode.toUpperCase(),
			});

			// Add optional parameters
			if (searchParams.destinationLocationCode) {
				queryParams.append('destination', searchParams.destinationLocationCode.toUpperCase());
			}
			if (searchParams.departureDate) {
				queryParams.append('departureDate', searchParams.departureDate);
			}
			if (searchParams.oneWay !== undefined) {
				queryParams.append('oneWay', searchParams.oneWay.toString());
			}
			if (searchParams.duration) {
				queryParams.append('duration', searchParams.duration.toString());
			}
			if (searchParams.nonStop !== undefined) {
				queryParams.append('nonStop', searchParams.nonStop.toString());
			}
			if (searchParams.viewBy) {
				queryParams.append('viewBy', searchParams.viewBy.toUpperCase());
			}
			if (searchParams.maxPrice) {
				queryParams.append('maxPrice', searchParams.maxPrice.toString());
			}

			console.log('Calling Amadeus Flight Cheapest Date Search API...');
			console.log('Environment: PRODUCTION (api.amadeus.com)');
			console.log('Endpoint:', `${this.config.BASE_URL}/v1/shopping/flight-dates`);
			console.log('Query params:', queryParams.toString());

			const response = await fetch(
				`${this.config.BASE_URL}/v1/shopping/flight-dates?${queryParams}`,
				{
					method: 'GET',
					headers: {
						'Authorization': `Bearer ${token}`,
					},
				}
			);

			console.log('Amadeus Cheapest Date Search response status:', response.status);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				console.error('Amadeus API error response:', errorData);
				
				// Check if it's a "no results" response (valid, just no flights found)
				if (response.status === 404 && errorData.errors?.[0]?.detail === 'No response found for this query') {
					console.log('No flights found for this search criteria');
					console.log('Note: This route/date combination may not have data available in the API.');
					return { data: [], meta: { count: 0 } }; // Return empty results
				}
				
				// Provide helpful error messages for actual errors
				if (response.status === 400) {
					const errorMsg = errorData.errors?.[0]?.detail || 'Invalid search parameters';
					throw new Error(`Search error: ${errorMsg}`);
				} else if (response.status === 401) {
					throw new Error('Authentication failed. Please check API credentials.');
				} else if (response.status === 404) {
					const errorMsg = errorData.errors?.[0]?.detail || 'Resource not found';
					throw new Error(`API error: ${errorMsg}`);
				} else if (response.status === 500) {
					throw new Error('Amadeus API service error. Please try again later.');
				}
				
				throw new Error(`API request failed: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			console.log('Amadeus Cheapest Date Search results:', data);
			
			// Return the raw data - the calling code can transform it as needed
			return data;
		} catch (error) {
			console.error('Error searching cheapest dates:', error);
			throw error;
		}
	}

	/**
	 * Transform Amadeus cheapest date search data to match our UI structure
	 * @param {Object} amadeusData - Raw data from Amadeus Flight Inspiration Search API
	 */
	transformCheapestDateData(amadeusData) {
		if (!amadeusData.data || !Array.isArray(amadeusData.data)) {
			return [];
		}

		return amadeusData.data.map((dateOffer, index) => {
			// Extract basic information
			const departureDate = dateOffer.departureDate;
			const returnDate = dateOffer.returnDate;
			const rawTotal = parseFloat(dateOffer.price?.total || 0);
			const apiCurrency = (dateOffer.price?.currency || '').toUpperCase();
			const EUR_TO_HKD = 9.02;
			let price = Math.ceil(rawTotal);
			let currency = apiCurrency || 'EUR';
			if (apiCurrency === 'EUR') {
				price = Math.ceil(rawTotal * EUR_TO_HKD);
				currency = 'HKD';
			}

			// Get origin and destination from the response
			const origin = dateOffer.origin;
			const destination = dateOffer.destination;
			
			// Get city names in Chinese
			const originChinese = this.getCityName(origin) || origin;
			const destinationChinese = this.getCityName(destination) || destination;

			console.log(`Cheapest date ${index + 1} transformation:`, {
				departureDate,
				returnDate,
				origin,
				originChinese,
				destination,
				destinationChinese,
				apiCurrency,
				price
			});

			return {
				id: index + 1,
				departureDate: departureDate,
				returnDate: returnDate,
				origin: origin,
				originName: originChinese,
				destination: destination,
				destinationName: destinationChinese,
				price: price,
				currency: currency,
				// Additional fields from the response
				links: dateOffer.links || null
			};
		});
	}

	/**
	 * Get airport/city suggestions for location search
	 * @param {string} keyword - Search keyword
	 * @param {string} subType - Type of location (AIRPORT, CITY, ANY)
	 */
	async getLocationSuggestions(keyword, subType = 'ANY') {
		try {
			const token = await this.getAccessToken();

			const queryParams = new URLSearchParams({
				keyword: keyword,
				subType: subType,
			});

			const response = await fetch(`${this.config.BASE_URL}/v1/reference-data/locations?${queryParams}`, {
				method: 'GET',
				headers: {
					'Authorization': `Bearer ${token}`,
					'Content-Type': 'application/json',
				},
			});

			if (!response.ok) {
				throw new Error(`Location search failed: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			return data;
		} catch (error) {
			console.error('Error getting location suggestions:', error);
			throw error;
		}
	}

	/**
	 * Transform Amadeus flight offer data to match our UI structure
	 * @param {Object} amadeusData - Raw data from Amadeus API
	 */
	transformFlightData(amadeusData) {
		if (!amadeusData.data || !Array.isArray(amadeusData.data)) {
			return [];
		}

		return amadeusData.data.map((offer, index) => {
			const itinerary = offer.itineraries[0];
			const segments = itinerary.segments;
			const firstSegment = segments[0];
			const lastSegment = segments[segments.length - 1];

			// Derive return date if round-trip itinerary exists
			let returnDate = null;
			if (offer.itineraries && offer.itineraries.length > 1) {
				const returnItinerary = offer.itineraries[1];
				if (returnItinerary && returnItinerary.segments && returnItinerary.segments.length > 0) {
					const returnFirstSegment = returnItinerary.segments[0];
					if (returnFirstSegment && returnFirstSegment.departure && returnFirstSegment.departure.at) {
						returnDate = returnFirstSegment.departure.at.split('T')[0];
					}
				}
			}

			// Get airline information
			const airlineCode = firstSegment.carrierCode;
			const airlineName = this.getAirlineName(airlineCode);

			// Calculate total price and apply conversion only if needed
			const rawTotal = parseFloat(offer.price.total);
			const apiCurrency = (offer.price.currency || '').toUpperCase();
			const EUR_TO_HKD = 9.02; // Exchange rate
			let cost = Math.ceil(rawTotal);
			let currency = apiCurrency || 'EUR';
			if (apiCurrency === 'EUR') {
				cost = Math.ceil(rawTotal * EUR_TO_HKD);
				currency = 'HKD';
			}

			// Get travel class
			const travelClass = this.mapTravelClass(offer.travelerPricings[0].fareOption);

			// Get city names in Chinese
			const startingPlaceCode = firstSegment.departure.iataCode;
			const destinationCode = lastSegment.arrival.iataCode;
			const startingPlaceChinese = this.getCityName(startingPlaceCode);
			const destinationChinese = this.getCityName(destinationCode);

			// Removed verbose per-flight transformation logging

			return {
				id: `amadeus_${index}`,
				airline: airlineName,
				airlineCode: airlineCode,
				startingPlace: startingPlaceChinese,
				startingPlaceCode: startingPlaceCode,
				destination: destinationChinese,
				destinationCode: destinationCode,
				cost: cost,
				currency: currency,
				seatClass: travelClass,
				departureDate: firstSegment.departure.at.split('T')[0],
				departureTime: firstSegment.departure.at.split('T')[1].substring(0, 5),
				arrivalDate: lastSegment.arrival.at.split('T')[0],
				arrivalTime: lastSegment.arrival.at.split('T')[1].substring(0, 5),
				returnDate: returnDate,
				ticketValidDate: lastSegment.arrival.at.split('T')[0],
				duration: this.formatDuration(itinerary.duration),
				segments: segments.length,
				luggageInfo: '20kg',
				// Store original Amadeus data for reference
				amadeusData: offer
			};
		});
	}

	/**
	 * Map Amadeus travel class to our UI format
	 */
	mapTravelClass(fareOption) {
		const classMap = {
			'STANDARD': '經濟艙',
			'INCLUSIVE': '經濟艙',
			'BUSINESS': '商務艙',
			'FIRST': '頭等艙'
		};
		return classMap[fareOption] || '經濟艙';
	}

	/**
	 * Get airline name from IATA code
	 */
	getAirlineName(iataCode) {
		const airlineMap = {
		// Major Asian Airlines
		'CX': '國泰航空',
		'KA': '國泰港龍航空',
		'HX': '香港航空',
		'UO': '香港快運航空',
		'BR': '長榮航空',
		'CI': '中華航空',
		'IT': '台灣虎航',
		'AE': '華信航空',
		'B7': '立榮航空',
		'GE': '復興航空',
		'GK': '捷星日本航空',
		'MM': '樂桃航空',
		'BC': '天馬航空',
		'JW': '香草航空',
		'NH': '全日空航空公司',
		'JL': '日本航空',
		'HD': 'Air Do航空',
		'KE': '大韓航空',
		'OZ': '韓亞航空',
		'SQ': '新加坡航空',
		'TR': '酷航',
		'3K': '捷星亞洲航空',
		'MI': '勝安航空',
		'TG': '泰國航空',
		'WE': '泰國微笑航空',
		'PG': '曼谷航空',
		'MH': '馬來西亞航空',
		'OD': '馬印航空',
		'GA': '印尼鷹航',
		'JT': '獅子航空',
		'ID': '巴澤航空',
		'PR': '菲律賓航空',
		'5J': '宿霧太平洋航空',
		'DG': '宿霧太平洋航空',
		'VJ': '越捷航空',
		'VN': '越南航空',
		'BL': '越南捷星太平洋航空',
		'VU': '越南航空',
		'FD': '泰國亞洲航空',
		'AK': '馬來西亞亞洲航空',
		'D7': '馬來西亞亞洲航空X',
		'I5': '印度亞洲航空',
		'QZ': '印尼亞洲航空',
		'Z2': '菲律賓亞洲航空',
		'SL': '泰國獅子航空',
		'XJ': '泰國亞洲航空',
		'QH': '竹子航空',
		'BI': '汶萊皇家航空',
		'KB': '柬埔寨JC國際航空',
		'PZ': '緬甸國際航空',
		'8M': '緬甸國家航空',
		'K6': '柬埔寨吳哥航空',
		'QV': '老撾航空',
		'RL': '老撾皇家航空',
			
		// Chinese Airlines
		'CZ': '中國南方航空',
		'CA': '中國國際航空',
		'MF': '廈門航空',
		'MU': '中國東方航空',
		'3U': '四川航空',
		'9C': '春秋航空',
		'HO': '吉祥航空',
		'JD': '首都航空',
		'GS': '天津航空',
		'PN': '西部航空',
		'8L': '祥鵬航空',
		'G5': '華夏航空',
		'KY': '昆明航空',
		'TV': '西藏航空',
		'UQ': '烏魯木齊航空',
		'9H': '長安航空',
		'DR': '瑞麗航空',
		'GJ': '長龍航空',
		'NS': '河北航空',
		'EU': '成都航空',
		'BK': '奧凱航空',
		'FU': '福州航空',
		'GT': '桂林航空',
		'LT': '龍江航空',
		'RY': '江西航空',
		'QW': '青島航空',
		'SC': '山東航空',
		'ZH': '深圳航空',
		'FM': '上海航空',
		'KN': '聯合航空',
			
		// Korean Low Cost Carriers
		'7C': '濟州航空',
		'TW': '德威航空',
		'H1': '韓亞航空',
		'BX': '釜山航空',
		'ZE': '易斯達航空',
		'LJ': '真航空',
		'4V': '濟州航空',
		'RS': '首爾航空',
		'YP': '空中首爾航空',
			
		// Middle East Airlines
		'EK': '阿聯酋航空',
		'EY': '阿提哈德航空',
		'QR': '卡塔爾航空',
		'SV': '沙特阿拉伯航空',
		'MS': '埃及航空',
		'RJ': '約旦皇家航空',
		'KU': '科威特航空',
		'GF': '海灣航空',
		'WY': '阿曼航空',
		'FZ': '杜拜航空',
		'G9': '阿拉伯航空',
		'XY': '沙迦航空',
		'J2': '阿塞拜疆航空',
		'J9': '賈茲拉航空',
		'ME': '中東航空',
		'OV': '沙烏地航空',
		
		// Indian Airlines
		'IX': '印度航空',
		'AI': '印度航空',
		'6E': '印度靛藍航空',
		'9W': '印度捷特航空',
		'SG': '香料航空',
		'G8': '印度航空',
		'UK': '維斯塔拉航空',
		'QP': '印度航空',
		'9I': '印度航空',
		'2T': '印度航空',
			
		// European Airlines
		'BA': '英國航空',
		'VS': '維珍航空',
		'EI': '愛爾蘭航空',
		'BE': 'Flybe航空',
		'LH': '漢莎航空',
		'EN': '德國之翼航空',
		'EW': '歐洲之翼航空',
		'4U': '日耳曼之翼航空',
		'AF': '法國航空',
		'TO': '越洋航空',
		'XK': '法國Corsair航空',
		'KL': '荷蘭皇家航空',
		'HV': '荷蘭泛航航空',
		'LX': '瑞士航空',
		'OS': '奧地利航空',
		'SN': '布魯塞爾航空',
		'TP': '葡萄牙航空',
		'IB': '西班牙航空',
		'VY': '伏林航空',
		'UX': '歐洲航空',
		'I2': '伊比利亞航空',
		'NT': '英特捷特航空',
		'AY': '芬蘭航空',
		'SK': '北歐航空',
		'DY': '挪威航空',
		'D8': '挪威航空',
		'LO': '波蘭航空',
		'OK': '捷克航空',
		'RO': '羅馬尼亞航空',
		'A3': '愛琴海航空',
		'TK': '土耳其航空',
		'PC': '飛馬航空',
		'XQ': '太陽快運航空',
		'SU': '俄羅斯航空',
		'U6': '烏拉爾航空',
		'FV': '俄羅斯勝利航空',
		'S7': '西伯利亞航空',
		'NN': '俄羅斯VIM航空',
		'FR': '瑞安航空',
		'U2': '易捷航空',
		'W6': '維茲航空',
		'W4': '維茲航空匈牙利',
		'LS': '捷特2航空',
		'AZ': '意大利航空',
		'AP': '阿爾巴星航空',
			
		// North American Airlines
		'AA': '美國航空',
		'DL': '達美航空',
		'UA': '聯合航空',
		'WN': '西南航空',
		'B6': '捷藍航空',
		'NK': '精神航空',
		'F9': '邊疆航空',
		'G4': '忠實航空',
		'SY': '太陽城航空',
		'AS': '阿拉斯加航空',
		'HA': '夏威夷航空',
		'VX': '維珍美國航空',
		'AC': '加拿大航空',
		'WS': '西捷航空',
		'PD': '波特航空',
		'TS': '越洋航空',
		'WG': '太陽之翼航空',
		'Y9': '加拿大北方航空',
		'5T': '加拿大航空',
		'AM': '墨西哥航空',
		'Y4': '沃拉里斯航空',
		'VB': '維瓦航空墨西哥',
		
		// Australian Airlines
		'QF': '澳洲航空',
		'VA': '維珍澳洲航空',
		'JQ': '捷星航空',
		'TT': '澳洲虎航',
		'DJ': '維珍澳洲航空',
		'QQ': '聯盟航空',
		'NZ': '紐西蘭航空',
		
		// South American Airlines
		'LA': '智利南美航空',
		'JJ': '巴西天馬航空',
		'G3': '巴西高爾航空',
		'AD': '巴西天馬航空',
		'AR': '阿根廷航空',
		'CM': '巴拿馬航空',
		'AV': '哥倫比亞航空',
		
		// African Airlines
		'ET': '衣索比亞航空',
		'SA': '南非航空',
		'KQ': '肯尼亞航空',
		'WB': '盧旺達航空',
		'AT': '摩洛哥皇家航空',
		'UL': '斯里蘭卡航空',
		'PK': '巴基斯坦國際航空',
		'BG': '孟加拉航空',
		
		// Other Airlines
		'HY': '烏茲別克航空',
		'KC': '阿斯塔納航空',
		'LY': '以色列航空',
		'IZ': '伊朗航空',
		'IR': '伊朗航空'
		};
		
		// Return Chinese name if found, otherwise return the IATA code with a generic label
		const chineseName = airlineMap[iataCode];
		if (chineseName) {
			return chineseName;
		} else {
			// For unknown airlines, return the code with a generic label
			console.warn(`Unknown airline code: ${iataCode}`);
			return `${iataCode}航空`;
		}
	}

	/**
	 * Convert ISO 8601 duration (PT14H55M) to human-readable format
	 */
	formatDuration(isoDuration) {
		if (!isoDuration) return 'N/A';
		
		// Parse PT14H55M format
		const match = isoDuration.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
		if (!match) return isoDuration;
		
		const hours = parseInt(match[1] || '0');
		const minutes = parseInt(match[2] || '0');
		
		if (hours === 0 && minutes === 0) return 'N/A';
		
		const parts = [];
		if (hours > 0) {
			parts.push(`${hours}小時`);
		}
		if (minutes > 0) {
			parts.push(`${minutes}分鐘`);
		}
		
		return parts.join(' ');
	}

	/**
	 * Get city name from airport code
	 */
	getCityName(airportCode) {
		const cityMap = {
		// Major Asian cities
		'HKG': '香港',
		'ICN': '首爾',
		'PUS': '釜山',
		'CJU': '濟州',
		'NRT': '東京',
		'HND': '東京',
		'KIX': '大阪',
		'NGO': '名古屋',
		'FUK': '福岡',
		'CTS': '札幌',
		'OKA': '沖繩',
		'TPE': '台北',
		'KHH': '高雄',
		'RMQ': '台中',
		'SIN': '新加坡',
		'BKK': '曼谷',
		'HKT': '布吉',
		'CNX': '清邁',
		'UTP': '芭堤雅',
		'KBV': '喀比',
		'KUL': '吉隆坡',
		'PEN': '檳城',
		'BKI': '亞庇',
		'LGK': '浮羅交怡',
		'CGK': '雅加達',
		'MNL': '馬尼拉',
		'CEB': '宿霧',
		'MPH': '長灘島',
		'DPS': '峇里',
		'SGN': '胡志明市',
		'HAN': '河內',
		'DAD': '峴港',
		'CXR': '芽莊',
		'PNH': '金邊',
		'REP': '暹粒',
			'PVG': '上海',
			'PEK': '北京',
			'CAN': '廣州',
			'SZX': '深圳',
			'CTU': '成都',
			'XIY': '西安',
			'NKG': '南京',
			'TAO': '青島',
			'TSN': '天津',
			'CKG': '重慶',
			'URC': '烏魯木齊',
			'HRB': '哈爾濱',
			'DLC': '大連',
			'SJW': '石家莊',
			'TYN': '太原',
			'INC': '銀川',
			'LHW': '蘭州',
			'XNN': '西寧',
			'KMG': '昆明',
			'LXA': '拉薩',
			'HAK': '海口',
			'FOC': '福州',
			'XMN': '廈門',
			'CSX': '長沙',
			'WUH': '武漢',
			'CGO': '鄭州',
			'JIN': '濟南',
			'YNT': '煙台',
			'WEH': '威海',
			'LYG': '連雲港',
			'NTG': '南通',
			'WNZ': '溫州',
			'NGB': '寧波',
			'HGH': '杭州',
			
			// Major international cities
			'SYD': '雪梨',
			'MEL': '墨爾本',
			'BNE': '布里斯班',
			'PER': '珀斯',
			'ADL': '阿德萊德',
			'CBR': '坎培拉',
			'HOB': '荷巴特',
			'DRW': '達爾文',
			'CNS': '凱恩斯',
			'TSV': '湯斯維爾',
			'OOL': '黃金海岸',
			'MCY': '陽光海岸',
			'ROK': '羅克漢普頓',
			
		// Middle East
		'DXB': '杜拜',
		'AUH': '阿布達比',
		'DOH': '多哈',
		'KWI': '科威特',
		'BAH': '巴林',
		'JED': '吉達',
		'RUH': '利雅得',
		
		// South Asia & India
		'DEL': '德里',
		'BOM': '孟買',
		'BLR': '班加羅爾',
		'CMB': '可倫坡',
		'MLE': '馬爾代夫',
		
		// North America
		'LAX': '洛杉磯',
		'JFK': '紐約',
		'SFO': '三藩市',
		'ORD': '芝加哥',
		'SEA': '西雅圖',
		'YVR': '溫哥華',
		'YYZ': '多倫多',
		
		// Europe
		'LHR': '倫敦',
		'CDG': '巴黎',
		'FRA': '法蘭克福',
		'AMS': '阿姆斯特丹',
		'FCO': '羅馬',
		'MAD': '馬德里',
		'BCN': '巴塞隆拿',
		'ZRH': '蘇黎世',
		'VIE': '維也納',
		'CPH': '哥本哈根',
		'ARN': '斯德哥爾摩',
		'OSL': '奧斯陸',
		'HEL': '赫爾辛基',
		'WAW': '華沙',
		'PRG': '布拉格',
		'BUD': '布達佩斯',
		'ATH': '雅典',
		'IST': '伊斯坦堡',
		
		// Africa
		'CAI': '開羅',
		'JNB': '約翰尼斯堡',
		'CPT': '開普敦',
		'LOS': '拉各斯',
		'NBO': '內羅畢',
		'ADD': '亞的斯亞貝巴',
		'KRT': '喀土穆',
		'KGL': '基加利',
		
		// Australia & New Zealand
		'AKL': '奧克蘭',
		'CHC': '基督城',
			'DAR': '達累斯薩拉姆',
			'LUN': '盧薩卡',
			'GBE': '哈博羅內',
			'WDH': '溫得和克',
			'MPM': '馬普托',
			'BJM': '布瓊布拉'
		};
		
		return cityMap[airportCode] || airportCode;
	}
}

// Create and export a singleton instance
export const amadeusApi = new AmadeusApiService();
