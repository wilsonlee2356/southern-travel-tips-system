/**
 * Flight Post Handler
 * Handles posting selected flights to the Post review page
 */

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
 * Navigates to the Post page with flight data
 * @param {Array} selectedFlights - Array of selected flight objects
 * @param {Function} goto - SvelteKit navigation function
 */
export function navigateToPostWithFlightData(selectedFlights, goto) {
	const postData = formatFlightDataForPost(selectedFlights);
	
	if (!postData) {
		console.error('No flight data to post');
		return;
	}

	// Store the flight data in sessionStorage for the Post page to retrieve
	sessionStorage.setItem('flightPostData', JSON.stringify(postData));
	
	// Navigate to the Post page
	goto('/post');
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
