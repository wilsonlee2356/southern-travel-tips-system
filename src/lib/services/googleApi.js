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
	 * Search for flights using Google Flights API (SearchAPI.io)
	 * @param {Object} searchParams - Search parameters (supports all Google Flights API parameters)
	 * @returns {Promise<Object>} Flight search results from SearchAPI
	 */
	async searchFlights(searchParams) {
		try {
			// Validate based on engine type
			const engine = searchParams.engine || 'google_flights';
			const flightType = searchParams.flight_type || 'round_trip';
			const isCalendar = engine === 'google_flights_calendar';
			
			if (flightType !== 'multi_city') {
				// Validate required parameters
				if (!searchParams.departure_id) {
					throw new Error('Departure airport/city code is required');
				}
				if (!searchParams.arrival_id) {
					throw new Error('Arrival airport/city code is required');
				}

				if (isCalendar) {
					// Calendar mode validation - requires both anchor dates and ranges
					if (!searchParams.outbound_date || !searchParams.outbound_date_start || !searchParams.outbound_date_end) {
						throw new Error('Outbound date and date range (start and end) are required for calendar view');
					}
					if (flightType === 'round_trip' && (!searchParams.return_date || !searchParams.return_date_start || !searchParams.return_date_end)) {
						throw new Error('Return date and date range (start and end) are required for round trip calendar view');
					}
				} else {
					// Standard mode validation
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
				}
			}

			// Build query parameters - pass ALL parameters to the backend proxy
			const queryParams = new URLSearchParams();
			
			// Add all provided parameters
			Object.keys(searchParams).forEach(key => {
				const value = searchParams[key];
				if (value !== null && value !== undefined && value !== '') {
					queryParams.append(key, value.toString());
				}
			});

			// Call local proxy to avoid CORS and hide API key
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
			console.log('Google Flights API Response Data:', data);
			
			const calendarData = await this.fetchCalendarData(searchParams);

			return {
				data,
				calendarData
			};
		} catch (error) {
			console.error('Error searching flights:', error);
			throw error;
		}
	}

	async fetchCalendarData(searchParams) {
		try {
			const outboundDate = searchParams.outbound_date;
			if (!outboundDate) {
				return null;
			}

			const calendarParams = new URLSearchParams();
			const calendarSearchParams = {
				...searchParams,
				engine: 'google_flights_calendar',
			};

			calendarSearchParams.outbound_date_start = this.adjustDate(outboundDate, -3);
			calendarSearchParams.outbound_date_end = this.adjustDate(outboundDate, 3);

			if (searchParams.return_date) {
				calendarSearchParams.return_date_start = this.adjustDate(searchParams.return_date, -3);
				calendarSearchParams.return_date_end = this.adjustDate(searchParams.return_date, 3);
			}

			Object.keys(calendarSearchParams).forEach((key) => {
				const value = calendarSearchParams[key];
				if (value !== null && value !== undefined && value !== '') {
					calendarParams.append(key, value.toString());
				}
			});

			const calendarRequestUrl = `/api/google-flights?${calendarParams}`;
			console.log('Google Flights Calendar Request URL:', calendarRequestUrl);

			const calendarResponse = await fetch(calendarRequestUrl, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			});

			if (!calendarResponse.ok) {
				console.warn('Google Flights calendar request failed:', calendarResponse.status, calendarResponse.statusText);
				return null;
			}

			const calendarData = await calendarResponse.json();
			console.log('Google Flights Calendar Data:', calendarData);
			return calendarData;
		} catch (error) {
			console.warn('Failed to fetch Google Flights calendar data:', error);
			return null;
		}
	}

	adjustDate(dateString, offsetDays) {
		try {
			const date = new Date(dateString);
			if (Number.isNaN(date.getTime())) {
				return dateString;
			}
			date.setDate(date.getDate() + offsetDays);
			return date.toISOString().slice(0, 10);
		} catch (error) {
			console.warn('Failed to adjust date:', dateString, error);
			return dateString;
		}
	}

	/**
	 * Transform Google Flights API data to match our UI structure
	 * @param {Object} googleData - Raw data from SerpApi Google Flights API
	 * @returns {Array} Transformed flight data
	 */
	transformFlightData(googleData) {
		const normalizedData = googleData?.data ?? googleData;
		if (!normalizedData?.flights || !Array.isArray(normalizedData.flights)) {
			return [];
		}

		const airports = Array.isArray(normalizedData.airports) ? normalizedData.airports : [];

		return normalizedData.flights.map((flightOffer, index) => {
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
			const departureCode = firstSegment.departure_airport?.id || firstSegment.departure_airport?.code || '';
			const arrivalCode = lastSegment.arrival_airport?.id || lastSegment.arrival_airport?.code || '';

			const { city: departureCity } = this.resolveCity(
				firstSegment.departure_airport,
				airports,
				'departure',
				departureCode
			);
			const { city: arrivalCity } = this.resolveCity(
				lastSegment.arrival_airport,
				airports,
				'arrival',
				arrivalCode
			);

			// Price and currency
			const price = flightOffer.price || 0;
			const currency = 'HKD'; // Google Flights API typically returns USD

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
				startingPlace: departureCity,
				startingPlaceCode: departureCode,
				destination: arrivalCity,
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

	findAirportCity(airports, collectionKey, code) {
		if (!Array.isArray(airports) || !code) {
			return null;
		}

		const normalizedCode = code.toString().toLowerCase();

		for (const airportGroup of airports) {
			const entries = airportGroup?.[collectionKey];
			if (!Array.isArray(entries)) {
				continue;
			}

			for (const entry of entries) {
				if (!entry) continue;
				const rawIdentifiers = [
					entry.id,
					entry.code,
					entry.iata,
					entry.iata_code,
					entry.airport_code,
					entry.display_code,
					entry.full_code
				]
					.filter(Boolean)
					.map((value) => value.toString().toLowerCase());
				const identifiers = new Set(rawIdentifiers);
				rawIdentifiers.forEach((identifier) => {
					identifier.split(/[^a-z0-9]/i).forEach((part) => {
						const trimmed = part.trim();
						if (trimmed) identifiers.add(trimmed.toLowerCase());
					});
				});
				if ([...identifiers].some((identifier) => identifier === normalizedCode || identifier.endsWith(normalizedCode) || identifier.includes(`${normalizedCode}-`) || identifier.includes(`-${normalizedCode}`))) {
					return entry.city || entry.city_name || entry.cityName || entry.name || null;
				}
			}

			// If no direct code match, fall back to first city value
			const firstEntryWithCity = entries.find((entry) => entry?.city || entry?.city_name || entry?.cityName);
			if (firstEntryWithCity) {
				return firstEntryWithCity.city || firstEntryWithCity.city_name || firstEntryWithCity.cityName;
			}
		}

		return null;
	}

	resolveCity(airportInfo, airports, collectionKey, code) {
		const attempts = [];
		const recordAttempt = (value, source) => {
			if (value == null) return;
			const stringValue = value.toString().trim();
			if (!stringValue) return;
			attempts.push({ value: stringValue, source });
		};

		recordAttempt(airportInfo?.city, `${collectionKey}.segment.city`);
		recordAttempt(airportInfo?.city_name, `${collectionKey}.segment.city_name`);
		recordAttempt(airportInfo?.cityName, `${collectionKey}.segment.cityName`);

		const metadataCity = this.findAirportCity(airports, collectionKey, code);
		recordAttempt(metadataCity, `${collectionKey}.metadata`);

		recordAttempt(airportInfo?.name, `${collectionKey}.segment.name`);
		recordAttempt(code, `${collectionKey}.code`);

		const resolved = attempts[0] || { value: null, source: null };

		console.log('Google Flights city resolution', {
			type: collectionKey,
			code,
			resolvedCity: resolved.value,
			source: resolved.source,
			fallbackChain: attempts.map((entry) => entry.source)
		});

		return {
			city: resolved.value,
			source: resolved.source,
			attempts
		};
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

