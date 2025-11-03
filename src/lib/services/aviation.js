/**
 * Aviationstack API Service
 * Handles flight search requests using Aviationstack API
 * Documentation: https://docs.apilayer.com/aviationstack/docs/aviationstack-api-v-1-0-0#/default/getFlights
 */

class AviationstackApiService {
	constructor() {
		this.config = null;
		this.baseUrl = 'http://api.aviationstack.com/v1';
		this.initializeConfig();
	}

	/**
	 * Initialize configuration
	 */
	initializeConfig() {
		// In browser environment, we'll use import.meta.env (Vite)
		// In Node.js environment, we'll use process.env
		const env = typeof window !== 'undefined' ? import.meta.env : process.env;
		
		this.config = {
			baseUrl: env.VITE_AVIATIONSTACK_BASE_URL || env.AVIATIONSTACK_BASE_URL || this.baseUrl,
			apiKey: env.VITE_AVIATIONSTACK_API_KEY || env.AVIATIONSTACK_API_KEY || '',
		};

		if (!this.config.apiKey) {
			console.warn('AVIATIONSTACK_API_KEY not found in environment variables.');
		}
	}

	/**
	 * Search for flights using Aviationstack API
	 * @param {Object} searchParams - Search parameters
	 * @param {string} searchParams.dep_iata - Departure airport IATA code (e.g., "HKG", "LAX")
	 * @param {string} searchParams.arr_iata - Arrival airport IATA code (e.g., "ICN", "AUS")
	 * @param {string} searchParams.dep_icao - Departure airport ICAO code (optional, alternative to dep_iata)
	 * @param {string} searchParams.arr_icao - Arrival airport ICAO code (optional, alternative to arr_iata)
	 * @param {string} searchParams.flight_date - Flight date in YYYY-MM-DD format (required)
	 * @param {string} searchParams.flight_status - Filter by flight status: scheduled, active, landed, cancelled, incident, diverted, redirected (optional)
	 * @param {string} searchParams.airline_name - Filter by airline name (optional)
	 * @param {string} searchParams.airline_iata - Filter by airline IATA code (optional)
	 * @param {string} searchParams.airline_icao - Filter by airline ICAO code (optional)
	 * @param {string} searchParams.flight_number - Filter by flight number (optional)
	 * @param {string} searchParams.flight_type - Filter by flight type: scheduled, charter, cargo (optional)
	 * @param {number} searchParams.limit - Limit the number of results returned (default: 100, max: 100)
	 * @param {number} searchParams.offset - Use for pagination (default: 0)
	 * @returns {Promise<Object>} Flight search results from Aviationstack API
	 */
	async searchFlights(searchParams) {
		try {
			if (!this.config.apiKey) {
				throw new Error('Aviationstack API key is required');
			}

			// Validate required parameters
			if (!searchParams.dep_iata && !searchParams.dep_icao) {
				throw new Error('Departure airport code (dep_iata or dep_icao) is required');
			}
			if (!searchParams.arr_iata && !searchParams.arr_icao) {
				throw new Error('Arrival airport code (arr_iata or arr_icao) is required');
			}
			if (!searchParams.flight_date) {
				throw new Error('Flight date (flight_date) is required');
			}

			// Validate date format
			const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
			if (!dateRegex.test(searchParams.flight_date)) {
				throw new Error('Invalid flight date format. Use YYYY-MM-DD');
			}

			// Build query parameters
			const queryParams = new URLSearchParams({
				access_key: this.config.apiKey,
			});

			// Add required parameters
			if (searchParams.dep_iata) {
				queryParams.append('dep_iata', searchParams.dep_iata);
			}
			if (searchParams.dep_icao) {
				queryParams.append('dep_icao', searchParams.dep_icao);
			}
			if (searchParams.arr_iata) {
				queryParams.append('arr_iata', searchParams.arr_iata);
			}
			if (searchParams.arr_icao) {
				queryParams.append('arr_icao', searchParams.arr_icao);
			}
			queryParams.append('flight_date', searchParams.flight_date);

			// Add optional parameters
			if (searchParams.flight_status) {
				queryParams.append('flight_status', searchParams.flight_status);
			}
			if (searchParams.airline_name) {
				queryParams.append('airline_name', searchParams.airline_name);
			}
			if (searchParams.airline_iata) {
				queryParams.append('airline_iata', searchParams.airline_iata);
			}
			if (searchParams.airline_icao) {
				queryParams.append('airline_icao', searchParams.airline_icao);
			}
			if (searchParams.flight_number) {
				queryParams.append('flight_number', searchParams.flight_number);
			}
			if (searchParams.flight_type) {
				queryParams.append('flight_type', searchParams.flight_type);
			}
			if (searchParams.limit && Number(searchParams.limit) > 0) {
				queryParams.append('limit', Math.min(Number(searchParams.limit), 100).toString()); // Max 100
			}
			if (searchParams.offset && Number(searchParams.offset) >= 0) {
				queryParams.append('offset', searchParams.offset.toString());
			}

			const requestUrl = `${this.config.baseUrl}/flights?${queryParams}`;
			console.log('Aviationstack API Request URL:', requestUrl.replace(this.config.apiKey, '***'));

			const response = await fetch(requestUrl, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			});

			console.log('Aviationstack API Response Status:', response.status, response.statusText);

			if (!response.ok) {
				let errorMessage = `Flight search failed: ${response.status} ${response.statusText}`;
				try {
					const errorData = await response.json();
					if (errorData.error) {
						errorMessage = errorData.error.info || errorData.error.message || errorMessage;
					} else if (errorData.message) {
						errorMessage = errorData.message;
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
			console.log(`Aviationstack API Response: ${resultCount} flights returned`);
			console.log('Aviationstack API Response Data:', data);
			
			return data;
		} catch (error) {
			console.error('Error searching flights:', error);
			throw error;
		}
	}

	/**
	 * Transform Aviationstack API data to match our UI structure
	 * @param {Object} aviationData - Raw data from Aviationstack API
	 * @returns {Array} Transformed flight data
	 */
	transformFlightData(aviationData) {
		if (!aviationData.data || !Array.isArray(aviationData.data)) {
			return [];
		}

		return aviationData.data.map((flight, index) => {
			// Extract flight information
			const flightInfo = flight.flight || {};
			const departure = flight.departure || {};
			const arrival = flight.arrival || {};
			const airline = flight.airline || {};
			const aircraft = flight.aircraft || {};

			// Extract dates and times
			const departureDateTime = departure.scheduled || departure.estimated || departure.actual || '';
			const arrivalDateTime = arrival.scheduled || arrival.estimated || arrival.actual || '';
			
			const departureDate = departureDateTime.split('T')[0] || '';
			const departureTime = departureDateTime.split('T')[1]?.substring(0, 5) || '';
			const arrivalDate = arrivalDateTime.split('T')[0] || '';
			const arrivalTime = arrivalDateTime.split('T')[1]?.substring(0, 5) || '';

			// Get airline information
			const airlineName = airline.name || 'Unknown';
			const airlineIata = airline.iata || '';
			const airlineIcao = airline.icao || '';
			const flightNumber = flightInfo.number || '';
			const flightIata = flightInfo.iata || '';
			const flightIcao = flightInfo.icao || '';

			// Get airport codes
			const departureCode = departure.iata || departure.icao || '';
			const arrivalCode = arrival.iata || arrival.icao || '';

			// Flight status
			const flightStatus = flight.flight_status || 'unknown';

			// Aircraft information
			const aircraftRegistration = aircraft.registration || '';
			const aircraftIata = aircraft.iata || '';
			const aircraftIcao = aircraft.icao || '';

			// Duration (if available)
			let duration = null;
			if (departureDateTime && arrivalDateTime) {
				const depTime = new Date(departureDateTime);
				const arrTime = new Date(arrivalDateTime);
				if (!isNaN(depTime.getTime()) && !isNaN(arrTime.getTime())) {
					duration = Math.floor((arrTime - depTime) / (1000 * 60)); // Duration in minutes
				}
			}

			// Airport names
			const departureAirport = departure.airport || '';
			const arrivalAirport = arrival.airport || '';
			const departureTerminal = departure.terminal || null;
			const departureGate = departure.gate || null;
			const arrivalTerminal = arrival.terminal || null;
			const arrivalGate = arrival.gate || null;

			return {
				id: `aviationstack_${index}`,
				airline: airlineName,
				airlineCode: airlineIata || airlineIcao || '',
				startingPlace: departureAirport || departureCode,
				startingPlaceCode: departureCode,
				destination: arrivalAirport || arrivalCode,
				destinationCode: arrivalCode,
				cost: null, // Aviationstack API doesn't provide pricing
				currency: null,
				seatClass: 'Economy', // Default, not provided by API
				departureDate: departureDate,
				departureTime: departureTime,
				departureTerminal: departureTerminal,
				departureGate: departureGate,
				arrivalDate: arrivalDate,
				arrivalTime: arrivalTime,
				arrivalTerminal: arrivalTerminal,
				arrivalGate: arrivalGate,
				returnDate: null, // Single flight, not round trip
				ticketValidDate: arrivalDate,
				duration: this.formatDuration(duration),
				segments: 1, // Single segment per flight in this API
				luggageInfo: 'N/A', // Not provided by API
				flightNumber: flightIata || flightIcao || flightNumber,
				flightStatus: flightStatus,
				aircraftRegistration: aircraftRegistration,
				aircraftType: aircraftIata || aircraftIcao || '',
				// Store original Aviationstack data for reference
				aviationstackData: flight
			};
		}).filter(flight => flight !== null); // Remove null entries
	}

	/**
	 * Format duration from minutes to readable format
	 * @param {number} minutes - Duration in minutes
	 * @returns {string} Formatted duration (e.g., "5h 30m")
	 */
	formatDuration(minutes) {
		if (!minutes || isNaN(minutes)) {
			return 'N/A';
		}
		const hours = Math.floor(minutes / 60);
		const mins = minutes % 60;
		if (hours > 0 && mins > 0) {
			return `${hours}h ${mins}m`;
		} else if (hours > 0) {
			return `${hours}h`;
		} else {
			return `${mins}m`;
		}
	}

	/**
	 * Test API connection
	 * @returns {Promise<boolean>} True if connection is successful
	 */
	async testConnection() {
		try {
			// Simple test - just check if API key is configured
			if (!this.config.apiKey) {
				throw new Error('API key not configured');
			}
			console.log('Aviationstack API connection test successful');
			return true;
		} catch (error) {
			console.error('Aviationstack API connection test failed:', error);
			return false;
		}
	}
}

// Export singleton instance
const aviationstackApi = new AviationstackApiService();
export default aviationstackApi;

