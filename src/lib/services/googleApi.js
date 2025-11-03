/**
 * Google Flights API Service (via SerpApi)
 * Handles flight search requests using SerpApi's Google Flights API
 * Documentation: https://serpapi.com/google-flights-api
 */

import { getGoogleFlightsConfig, getDevConfig } from '$lib/config/googleFlights.js';

class GoogleFlightsApiService {
	constructor() {
		this.config = null;
		this.initializeConfig();
	}

	/**
	 * Initialize configuration
	 */
	initializeConfig() {
		try {
			// Try to get production config first
			this.config = getGoogleFlightsConfig();
		} catch (error) {
			// Fall back to development config with warnings
			console.warn('Using development configuration for Google Flights API:', error.message);
			this.config = getDevConfig();
		}
	}

	/**
	 * Search for flights using Google Flights API (SerpApi)
	 * @param {Object} searchParams - Search parameters
	 * @param {string} searchParams.departure_id - Departure airport/city IATA code (e.g., "LAX", "HKG")
	 * @param {string} searchParams.arrival_id - Arrival airport/city IATA code (e.g., "AUS", "ICN")
	 * @param {string} searchParams.outbound_date - Departure date in YYYY-MM-DD format (required)
	 * @param {string} searchParams.return_date - Return date in YYYY-MM-DD format (optional, for round trips)
	 * @param {number} searchParams.adults - Number of adult passengers (default: 1)
	 * @param {string} searchParams.currency - Currency code (default: "USD")
	 * @returns {Promise<Object>} Flight search results from SerpApi
	 */
	async searchFlights(searchParams) {
		try {
			// Validate required parameters
			if (!searchParams.departure_id) {
				throw new Error('Departure airport/city code is required');
			}
			if (!searchParams.arrival_id) {
				throw new Error('Arrival airport/city code is required');
			}
			if (!searchParams.outbound_date) {
				throw new Error('Departure date (outbound_date) is required');
			}

			// Validate date format
			const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
			if (!dateRegex.test(searchParams.outbound_date)) {
				throw new Error('Invalid departure date format. Use YYYY-MM-DD');
			}
			if (searchParams.return_date && !dateRegex.test(searchParams.return_date)) {
				throw new Error('Invalid return date format. Use YYYY-MM-DD');
			}

			// Validate return date is after departure date
			if (searchParams.return_date) {
				const departureDate = new Date(searchParams.outbound_date);
				const returnDate = new Date(searchParams.return_date);
				if (returnDate <= departureDate) {
					throw new Error('Return date must be after departure date');
				}
			}

			// Build query parameters for proxy endpoint (no api_key on client)
			const queryParams = new URLSearchParams({
				departure_id: searchParams.departure_id,
				arrival_id: searchParams.arrival_id,
				outbound_date: searchParams.outbound_date,
			});

			// Add optional parameters
			if (searchParams.return_date) {
				queryParams.append('return_date', searchParams.return_date);
			}

			if (searchParams.adults && Number(searchParams.adults) > 0) {
				queryParams.append('adults', searchParams.adults.toString());
			}

			if (searchParams.currency) {
				queryParams.append('currency', searchParams.currency);
			}

			// Call local proxy to avoid CORS and hide key
			const requestUrl = `/api/google-flights?${queryParams}`;
			console.log('Google Flights Proxy Request URL:', requestUrl);

			const response = await fetch(requestUrl, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			});

			console.log('Google Flights API Response Status:', response.status, response.statusText);

			if (!response.ok) {
				let errorMessage = `Flight search failed: ${response.status} ${response.statusText}`;
				try {
					const errorData = await response.json();
					if (errorData.error) {
						errorMessage = errorData.error;
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
			const resultCount = data?.flights?.length || 0;
			console.log(`Google Flights API Response: ${resultCount} flight offers returned`);
			console.log('Google Flights API Response Data:', data);
			
			return data;
		} catch (error) {
			console.error('Error searching flights:', error);
			throw error;
		}
	}

	/**
	 * Transform Google Flights API data to match our UI structure
	 * @param {Object} googleData - Raw data from SerpApi Google Flights API
	 * @returns {Array} Transformed flight data
	 */
	transformFlightData(googleData) {
		if (!googleData.flights || !Array.isArray(googleData.flights)) {
			return [];
		}

		return googleData.flights.map((flightOffer, index) => {
			// Extract flight segments
			const segments = flightOffer.flights || [];
			if (segments.length === 0) {
				return null;
			}

			const firstSegment = segments[0];
			const lastSegment = segments[segments.length - 1];

			// Extract dates and times
			const departureDateTime = firstSegment.departure_airport?.time || '';
			const arrivalDateTime = lastSegment.arrival_airport?.time || '';
			
			const departureDate = departureDateTime.split(' ')[0];
			const departureTime = departureDateTime.split(' ')[1] || '';
			const arrivalDate = arrivalDateTime.split(' ')[0];
			const arrivalTime = arrivalDateTime.split(' ')[1] || '';

			// Get airline information
			const airlineName = firstSegment.airline || 'Unknown';
			const airlineLogo = firstSegment.airline_logo || '';
			const flightNumber = firstSegment.flight_number || '';

			// Get airport codes
			const departureCode = firstSegment.departure_airport?.id || '';
			const arrivalCode = lastSegment.arrival_airport?.id || '';

			// Price and currency
			const price = flightOffer.price || 0;
			const currency = 'USD'; // Google Flights API typically returns USD

			// Duration
			const duration = flightOffer.total_duration || 0; // in minutes

			// Travel class
			const travelClass = firstSegment.travel_class || 'Economy';

			// Carbon emissions
			const carbonEmissions = flightOffer.carbon_emissions?.this_flight || null;

			// Return date (for round trips)
			let returnDate = null;
			if (flightOffer.type === 'Round trip' && segments.length > 1) {
				// For round trips, the return date would be in the return segment
				// This is a simplified extraction - may need adjustment based on actual API response
				returnDate = arrivalDate;
			}

			return {
				id: `google_flights_${index}`,
				airline: airlineName,
				airlineCode: flightNumber.split(' ')[0] || '', // Extract airline code from flight number
				startingPlace: departureCode,
				startingPlaceCode: departureCode,
				destination: arrivalCode,
				destinationCode: arrivalCode,
				cost: Math.ceil(price),
				currency: currency,
				seatClass: travelClass,
				departureDate: departureDate,
				departureTime: departureTime,
				arrivalDate: arrivalDate,
				arrivalTime: arrivalTime,
				returnDate: returnDate,
				ticketValidDate: arrivalDate,
				duration: this.formatDuration(duration),
				segments: segments.length,
				luggageInfo: '20kg', // Default, may need to extract from API response
				carbonEmissions: carbonEmissions,
				airlineLogo: airlineLogo,
				// Store original Google Flights data for reference
				googleFlightsData: flightOffer
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
			if (!this.config.API_KEY) {
				throw new Error('API key not configured');
			}
			console.log('Google Flights API connection test successful');
			return true;
		} catch (error) {
			console.error('Google Flights API connection test failed:', error);
			return false;
		}
	}
}

// Export singleton instance
const googleFlightsApi = new GoogleFlightsApiService();
export default googleFlightsApi;

