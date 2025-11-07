<script>
	import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
	import { getContext, onMount } from 'svelte';
	import { writable } from 'svelte/store';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import { navigateToPostWithFlightData } from '$lib/utils/flightPostHandler.js';
	import { goto } from '$app/navigation';
	import googleFlightsApi from '$lib/services/googleApi.js';
	import { cityList, locationCodeMap, getLocationCode, filterCities } from '$lib/utils/cityCodes';
import SearchBox from './components/search-box.svelte';
import ResultBox from './components/result-box.svelte';
import CalendarGridModal from './components/calendar-grid-modal.svelte';
	// No longer need adapter merging imports since we only use pre-existing merged models

	// Form state
	let searchForm = {
		startingPlace: '',
		destination: '',
		cost: '',
		tripType: 'round-trip',
		adults: 1,
		children: 0,
		seatClass: 'economy',
		stops: 'any',
		airlines: [],
		maxPrice: 200000,
		maxDuration: 12,
		departureDate: '',
		returnDate: ''
	};

	// Search results state
	let searchResults = [];
let allSearchResults = [];
	let isSearching = false;
	let hasSearched = false;
	let selectedFlights = new Set();
	let selectedFlightObjects = []; // Store actual flight objects for display
	let isPosting = false;
	let aiStage = ''; // Track which AI stage is running
	let searchError = ''; // Track search errors
	let searchCounter = 0; // Counter to create unique IDs across searches
let calendarData = null;
let otherFlightResults = [];
const showCalendarModal = writable(false);

const openCalendarModal = () => {
	console.log('openCalendarModal invoked', calendarData);
	if (!calendarData) {
		console.warn('Price calendar data not available yet. Displaying placeholder modal.');
	}
	showCalendarModal.set(true);
};

const closeCalendarModal = () => {
	showCalendarModal.set(false);
};
	
	// Autocomplete state
	let startingPlaceInput = '';
	let destinationInput = '';
	let filteredStartingPlaces = [];
	let filteredDestinations = [];
	let showStartingPlaceDropdown = false;
	let showDestinationDropdown = false;
	
	// Model selection state
	let selectedRAGModel = null;
	let selectedBaseModel = null;
	let selectedAdapter = null;
	let selectedModel = null; // For any model (including external APIs)

	// Initialize with all flights on page load
	$: if (typeof window !== 'undefined') {
		if (searchResults.length === 0 && !hasSearched) {
			searchResults = [];
			allSearchResults = [];
	searchResults = [];
	allSearchResults = [];
		}
	}

	// Location code mapping and city list are now imported from shared module
	// See: import { cityList, locationCodeMap, getLocationCode, filterCities } from '$lib/utils/cityCodes';

	// Handle starting place input
	const handleStartingPlaceInput = (e) => {
		startingPlaceInput = e.target.value;
	updateSearchForm({ startingPlace: startingPlaceInput });
		filteredStartingPlaces = filterCities(startingPlaceInput);
		showStartingPlaceDropdown = true;
	};

const updateSearchForm = (updates) => {
	searchForm = {
		...searchForm,
		...updates
	};
	};

	// Handle destination input
	const handleDestinationInput = (e) => {
		destinationInput = e.target.value;
	updateSearchForm({ destination: destinationInput });
		filteredDestinations = filterCities(destinationInput);
		showDestinationDropdown = true;
	};

$: if (searchForm.tripType === 'one-way' && searchForm.returnDate) {
	updateSearchForm({ returnDate: '' });
}

const handleStartingPlaceFocus = () => {
	filteredStartingPlaces = filterCities(startingPlaceInput);
	showStartingPlaceDropdown = true;
};

const handleDestinationFocus = () => {
		filteredDestinations = filterCities(destinationInput);
		showDestinationDropdown = true;
	};

	// Select starting place from dropdown
	const selectStartingPlace = (city) => {
		startingPlaceInput = city.display;
	updateSearchForm({ startingPlace: city.code });
		showStartingPlaceDropdown = false;
	};

	// Select destination from dropdown
	const selectDestination = (city) => {
		destinationInput = city.display;
	updateSearchForm({ destination: city.code });
		showDestinationDropdown = false;
	};

	// Close dropdowns when clicking outside
	const handleClickOutside = (e) => {
		if (!e.target.closest('.autocomplete-container')) {
			showStartingPlaceDropdown = false;
			showDestinationDropdown = false;
		}
	};

	// const sampleFlights = [...]; // commented out demo data per request

const splitDateTime = (value) => {
	if (!value) return { date: '', time: '' };
	if (typeof value === 'string') {
		const normalized = value.replace('Z', '');
		if (normalized.includes('T')) {
			const [date, timePart] = normalized.split('T');
			const time = timePart ? timePart.slice(0, 5) : '';
			return { date, time };
		}
		const parts = normalized.split(' ');
		if (parts.length >= 2) {
			return { date: parts[0], time: parts[1] };
		}
		return { date: normalized, time: '' };
	}
	if (typeof value === 'object') {
		return {
			date: value.date ?? '',
			time: value.time ?? ''
		};
	}
	return { date: '', time: '' };
};

const parsePriceInfo = (priceInfo) => {
	let amount = null;
	let currency = '';
	let formatted = '';

	if (priceInfo == null) {
		return { amount, currency, formatted };
	}

	if (typeof priceInfo === 'number') {
		amount = priceInfo;
	} else if (typeof priceInfo === 'string') {
		formatted = priceInfo.trim();
		const numeric = formatted.replace(/[^\d.,]/g, '').replace(/,/g, '');
		const parsed = parseFloat(numeric);
		amount = Number.isFinite(parsed) ? parsed : null;
		const currencyMatch = formatted.replace(/[\d.,\s]/g, '').trim();
		if (currencyMatch) currency = currencyMatch;
	} else if (typeof priceInfo === 'object') {
		const maybeAmount = priceInfo.amount ?? priceInfo.price ?? priceInfo.value;
		if (maybeAmount != null) {
			const parsed = parseFloat(maybeAmount);
			amount = Number.isFinite(parsed) ? parsed : null;
		}
		currency =
			priceInfo.currency ??
			priceInfo.currency_code ??
			priceInfo.currencyCode ??
			priceInfo.currency_symbol ??
			priceInfo.currencySymbol ??
			currency;
		formatted =
			priceInfo.display_price ??
			priceInfo.display ??
			priceInfo.formatted ??
			priceInfo.price_string ??
			priceInfo.price_display ??
			formatted;
	}

	if (!formatted && amount != null) {
		formatted = currency ? `${currency} ${amount}` : `$${amount}`;
	}

	return { amount, currency, formatted };
};

const parseDurationMinutes = (duration) => {
	if (!duration) return null;

	if (typeof duration === 'number') return duration;

	if (typeof duration === 'string') {
		let total = 0;
		const hourMatch = duration.match(/(\d+)\s*(?:h|hour)/i);
		const minuteMatch = duration.match(/(\d+)\s*(?:m|min)/i);
		if (hourMatch) total += parseInt(hourMatch[1], 10) * 60;
		if (minuteMatch) total += parseInt(minuteMatch[1], 10);
		if (total > 0) return total;

		const numeric = parseFloat(duration);
		if (Number.isFinite(numeric)) {
			// assume hours if contains colon? otherwise fallback to hours * 60
			return numeric > 12 ? numeric : numeric * 60;
		}
	}

	return null;
};

const formatDurationLabel = (minutes, fallback) => {
	if (!minutes || !Number.isFinite(minutes)) {
		return fallback ?? 'N/A';
	}
	const hrs = Math.floor(minutes / 60);
	const mins = minutes % 60;
	if (hrs && mins) return `${hrs}h ${mins}m`;
	if (hrs) return `${hrs}h`;
	return `${mins}m`;
};

const collectSegments = (flight) => {
	if (!flight) return [];
	if (Array.isArray(flight.flights)) return flight.flights;
	if (Array.isArray(flight.legs)) return flight.legs;
	if (Array.isArray(flight.segments)) return flight.segments;
	if (Array.isArray(flight.outbound_flights)) return flight.outbound_flights;
	if (Array.isArray(flight.outbound)) return flight.outbound;
	return [];
};

const normalizeDateValue = (primary, secondary) => {
	const normalize = (value) => {
		if (typeof value === 'string') {
			const trimmed = value.trim();
			return trimmed.length ? trimmed : null;
		}
		return null;
	};
	return normalize(primary) ?? normalize(secondary) ?? null;
};

const normalizeTimeValue = (value) => {
	if (typeof value === 'string') {
		const trimmed = value.trim();
		return trimmed.length ? trimmed : null;
	}
	return null;
};

const mapBestFlightsToResults = (bestFlights, counter, airportsMetaList = []) => {
	return bestFlights.map((flight, index) => {
		const priceInfo =
			parsePriceInfo(flight.price) ||
			parsePriceInfo(flight.price_per_ticket) ||
			parsePriceInfo(flight.purchase_links?.[0]?.price);

		const segments = collectSegments(flight);
		const firstSegment = segments[0] ?? {};
		const lastSegment = segments[segments.length - 1] ?? firstSegment;

		const outboundDeparture =
			firstSegment.departure_airport ??
			firstSegment.departure ??
			firstSegment.from ??
			firstSegment.origin ??
			{};
		const outboundArrival =
			lastSegment.arrival_airport ??
			lastSegment.arrival ??
			lastSegment.to ??
			lastSegment.destination ??
			{};

		const departureTimeInfo =
			outboundDeparture.time ??
			firstSegment.departure_time ??
			firstSegment.departureDateTime ??
			firstSegment.departure_time_utc;
		const arrivalTimeInfo =
			outboundArrival.time ??
			lastSegment.arrival_time ??
			lastSegment.arrivalDateTime ??
			lastSegment.arrival_time_utc;

		const departureDate = outboundDeparture.date ?? firstSegment.departure_date ?? flight.departure_date;
		const arrivalDate = outboundArrival.date ?? lastSegment.arrival_date ?? firstSegment.arrival_date ?? flight.arrival_date;

		const departure = splitDateTime(
			departureTimeInfo ??
				(departureDate ? `${departureDate}T${outboundDeparture.time ?? firstSegment.departure_time ?? ''}` : '')
		);
		const arrival = splitDateTime(arrivalTimeInfo);

		const airlineNames = new Set();
		const airlineCodes = new Set();
		const collectCarrier = (segment) => {
			const name =
				segment.airline ||
				segment.airline_name ||
				segment.marketing_airline ||
				segment.carrier ||
				segment.display_airline;
			if (name) airlineNames.add(name);
			const code =
				segment.airline_code ||
				segment.carrier_code ||
				segment.marketing_airline_code ||
				segment.flight_number?.slice(0, 2);
			if (code) airlineCodes.add(code.toUpperCase());
			if (segment.operating_airline_code) airlineCodes.add(segment.operating_airline_code.toUpperCase());
		};
		segments.forEach(collectCarrier);
		if (Array.isArray(flight.airlines)) {
			flight.airlines.forEach((item) => {
				if (typeof item === 'string') airlineNames.add(item);
				if (item?.name) airlineNames.add(item.name);
				const code = item?.code ?? item?.iata;
				if (code) airlineCodes.add(code.toUpperCase());
			});
		}

		const airlineName =
			flight.airline ||
			flight.display_airline ||
			Array.from(airlineNames).join(', ') ||
			firstSegment.airline ||
			firstSegment.operating_airline ||
			'Unknown airline';

		const seatClassRaw =
			flight.cabin_class ??
			flight.cabin ??
			flight.travel_class ??
			firstSegment.cabin ??
			firstSegment.travel_class ??
			firstSegment.seat_class ??
			firstSegment.cabin_class;
		const seatClassLabel = seatClassRaw ? seatClassRaw.toString() : '—';

		const totalDurationMinutes =
			parseDurationMinutes(flight.total_duration) ??
			parseDurationMinutes(flight.duration) ??
			parseDurationMinutes(firstSegment.duration);
		const totalDurationLabel = formatDurationLabel(totalDurationMinutes, flight.total_duration ?? flight.duration);

		const normalizedDepartureDate = normalizeDateValue(departureDate, departure.date);
		const normalizedArrivalDate = normalizeDateValue(arrivalDate, arrival.date);
		const normalizedDepartureTime = normalizeTimeValue(
			outboundDeparture.time ?? firstSegment.departure_time ?? departure.time
		);
		const normalizedArrivalTime = normalizeTimeValue(
			outboundArrival.time ?? lastSegment.arrival_time ?? arrival.time
		);
		const departureDateTimeLabel = [normalizedDepartureTime, normalizedDepartureDate]
			.filter(Boolean)
			.join(' ');
		const arrivalDateTimeLabel = [normalizedArrivalTime, normalizedArrivalDate]
			.filter(Boolean)
			.join(' ');

		const flightAirports = Array.isArray(flight.airports) && flight.airports.length ? flight.airports : airportsMetaList;
		const departureCity =
			getCityFromAirportsMeta(flightAirports, 'departure',
				firstSegment.departure_airport?.id ||
				firstSegment.departure_airport?.code ||
				outboundDeparture.code ||
				outboundDeparture.airport_code ||
				outboundDeparture.iata ||
				outboundDeparture.id
			) ??
			outboundDeparture.city ??
			flight.origin?.city ??
			null;
		const arrivalCity =
			getCityFromAirportsMeta(flightAirports, 'arrival',
				lastSegment.arrival_airport?.id ||
				lastSegment.arrival_airport?.code ||
				outboundArrival.code ||
				outboundArrival.airport_code ||
				outboundArrival.iata ||
				outboundArrival.id
			) ??
			outboundArrival.city ??
			flight.destination?.city ??
			null;

		const rawData = { ...flight };
		if (!rawData.airports && Array.isArray(flightAirports) && flightAirports.length) {
			rawData.airports = flightAirports;
		}

		return {
			id: `${counter}_${index + 1}`,
			airline: airlineName,
			airlineCode: flight.airline_code || Array.from(airlineCodes)[0] || '',
			airlineLogo: flight.airline_logo || firstSegment.airline_logo || null,
			startingPlace:
				departureCity ||
				outboundDeparture.name ||
				outboundDeparture.city ||
				outboundDeparture.code ||
				outboundDeparture.airport ||
				'—',
			startingPlaceCode:
				outboundDeparture.code ||
				outboundDeparture.airport_code ||
				outboundDeparture.iata ||
				outboundDeparture.id ||
				'',
			startingCity: departureCity,
			startingPlaceCity: departureCity,
			destination:
				arrivalCity ||
				outboundArrival.name ||
				outboundArrival.city ||
				outboundArrival.code ||
				outboundArrival.airport ||
				'—',
			destinationCode:
				outboundArrival.code ||
				outboundArrival.airport_code ||
				outboundArrival.iata ||
				outboundArrival.id ||
				'',
			destinationCity: arrivalCity,
			destinationPlaceCity: arrivalCity,
			cost: priceInfo.amount,
			currency: priceInfo.currency,
			displayPrice: priceInfo.formatted,
			seatClass: seatClassLabel,
			departureDate: normalizedDepartureDate,
			departureLocalDate: normalizedDepartureDate,
			departureTime: normalizedDepartureTime,
			departureDateTimeLabel: departureDateTimeLabel,
			departureAirportName:
				outboundDeparture.name ||
				outboundDeparture.airport ||
				outboundDeparture.city ||
				outboundDeparture.code ||
				'',
			arrivalDate: normalizedArrivalDate,
			arrivalLocalDate: normalizedArrivalDate,
			arrivalTime: normalizedArrivalTime,
			arrivalDateTimeLabel: arrivalDateTimeLabel,
			duration: formatDurationLabel(totalDurationMinutes, flight.total_duration ?? flight.duration),
			durationMinutes: totalDurationMinutes,
			totalDurationLabel,
			arrivalAirportName:
				outboundArrival.name ||
				outboundArrival.airport ||
				outboundArrival.city ||
				outboundArrival.code ||
				'',
			segments: segments.length || flight.connections?.length || 1,
			airlines: Array.from(airlineCodes),
			flightNumber: firstSegment.flight_number || flight.flight_number || null,
			rawData
		};
	});
};

const applyResultFilters = (results) => {
	let filtered = Array.isArray(results) ? [...results] : [];

	if (searchForm.airlines?.length) {
		filtered = filtered.filter((flight) => {
			if (!flight.airlines?.length) return false;
			return flight.airlines.some((code) => searchForm.airlines.includes(code));
		});
	}

	if (searchForm.stops && searchForm.stops !== 'any') {
		filtered = filtered.filter((flight) => {
			const segments = flight.segments ?? 1;
			if (searchForm.stops === 'direct') return segments <= 1;
			if (searchForm.stops === 'one-or-less') return segments <= 2;
			if (searchForm.stops === 'two-or-less') return segments <= 3;
			return true;
		});
	}

	const maxPriceFilters = [searchForm.maxPrice, searchForm.cost]
		.filter((value) => value != null && value !== '')
		.map((value) => parseFloat(value))
		.filter((num) => Number.isFinite(num) && num > 0);
	if (maxPriceFilters.length) {
		const effectiveMaxPrice = Math.min(...maxPriceFilters);
		filtered = filtered.filter((flight) => {
			if (flight.cost == null) return true;
			return flight.cost <= effectiveMaxPrice;
		});
	}

	if (searchForm.maxDuration) {
		const maxDurationMinutes = Number(searchForm.maxDuration) * 60;
		if (Number.isFinite(maxDurationMinutes) && maxDurationMinutes > 0) {
			filtered = filtered.filter((flight) => {
				if (!flight.durationMinutes) return true;
				return flight.durationMinutes <= maxDurationMinutes;
			});
		}
	}

	return filtered;
};

$: if (!isSearching && allSearchResults.length > 0) {
	const filtered = applyResultFilters(allSearchResults);
	const sameLength = filtered.length === searchResults.length;
	const sameOrder = sameLength && filtered.every((flight, index) => flight.id === searchResults[index]?.id);
	if (!sameOrder) {
		searchResults = filtered;
	}
}

	// Search function
	const handleSearch = async () => {
		isSearching = true;
		hasSearched = true;
		searchError = '';
		calendarData = null;
		showCalendarModal.set(false);
		otherFlightResults = [];
		
		// Keep selected flights when starting new search (don't clear)
		// Increment search counter to create unique IDs
		searchCounter++;

		try {
				console.log('Looking up origin code for:', searchForm.startingPlace);
				const originCode = getLocationCode(searchForm.startingPlace);
				console.log('Origin code result:', originCode);
				
				console.log('Looking up destination code for:', searchForm.destination);
				const destinationCode = getLocationCode(searchForm.destination);
				console.log('Destination code result:', destinationCode);

				if (!originCode || !destinationCode) {
					const missingFields = [];
					if (!originCode) missingFields.push('origin');
					if (!destinationCode) missingFields.push('destination');
					throw new Error(`Please enter valid ${missingFields.join(' and ')} cities. Use specific city names or airport codes (e.g., "Tokyo", "NRT", "Osaka", "KIX").`);
				}

				if (!searchForm.departureDate) {
					throw new Error('Please select a departure date');
				}

			if (searchForm.tripType !== 'one-way' && searchForm.returnDate) {
					const departureDate = new Date(searchForm.departureDate);
					const returnDate = new Date(searchForm.returnDate);
					if (returnDate <= departureDate) {
						throw new Error('Return date must be after departure date');
					}
			}

			const flightTypeMap = {
				'round-trip': 'round_trip',
				'one-way': 'one_way',
				'multi-city': 'multi_city'
			};

				const travelClassMap = {
				'economy': 'economy',
				'premium economy': 'premium_economy',
				'business': 'business',
				'first class': 'first'
				};

			const normalizedSeatClass = (searchForm.seatClass || 'economy').toLowerCase();
			const adultsCount = Math.max(1, Number(searchForm.adults) || 1);
			const childrenCount = Math.max(0, Number(searchForm.children) || 0);

				const searchParams = {
				engine: 'google_flights',
				flight_type: flightTypeMap[searchForm.tripType] || 'round_trip',
				departure_id: originCode,
				arrival_id: destinationCode,
				outbound_date: searchForm.departureDate,
				travel_class: travelClassMap[normalizedSeatClass] || 'economy',
				adults: adultsCount,
				hl: 'zh-TW',
				currency: 'HKD'
			};

			if (childrenCount > 0) {
				searchParams.children = childrenCount;
			}

			if (searchForm.tripType !== 'one-way' && searchForm.returnDate) {
				searchParams.return_date = searchForm.returnDate;
				}

			console.log('Google Flights API Search Parameters:', searchParams);

			const { data: googleFlightsResponse, calendarData: googleFlightsCalendarData } =
				await googleFlightsApi.searchFlights(searchParams);
			console.log('Google Flights API raw response:', googleFlightsResponse);
			calendarData = googleFlightsCalendarData;

			const bestFlights = Array.isArray(googleFlightsResponse?.best_flights)
				? googleFlightsResponse.best_flights
				: [];
			const otherFlightsRaw = Array.isArray(googleFlightsResponse?.other_flights)
				? googleFlightsResponse.other_flights
				: [];

		const airportsMetaList = Array.isArray(googleFlightsResponse?.airports)
			? googleFlightsResponse.airports
			: [];
		const mappedResults = mapBestFlightsToResults(bestFlights, searchCounter, airportsMetaList);
		const mappedOtherFlights = mapBestFlightsToResults(otherFlightsRaw, `${searchCounter}_other`, airportsMetaList);
			otherFlightResults = mappedOtherFlights;

		allSearchResults = [...mappedResults, ...otherFlightResults];
		const filteredResults = applyResultFilters(allSearchResults);

			if (!mappedResults.length) {
				searchError = 'No flights found for your search. Please adjust the dates or search parameters.';
			} else if (!filteredResults.length) {
				searchError = 'No flights match the selected filters. Try adjusting the filters to see more results.';
			} else {
				searchError = '';
			}

			selectedFlights = new Set();
			selectedFlightObjects = [];
			searchResults = filteredResults.length ? filteredResults : [];
		} catch (error) {
			console.error('Search error:', error);
			searchError = error.message || 'An error occurred while searching for flights';
			searchResults = [];
			allSearchResults = [];
			calendarData = null;
			otherFlightResults = [];
		} finally {
			isSearching = false;
		}
	};

	// Reset search
	const resetSearch = () => {
	updateSearchForm({
			startingPlace: '',
			destination: '',
			cost: '',
		tripType: 'round-trip',
		adults: 1,
		children: 0,
			seatClass: 'economy',
		stops: 'any',
		airlines: [],
		maxPrice: 200000,
		maxDuration: 12,
			departureDate: '',
			returnDate: ''
	});
		startingPlaceInput = '';
		destinationInput = '';
		filteredStartingPlaces = [];
		filteredDestinations = [];
		showStartingPlaceDropdown = false;
		showDestinationDropdown = false;
		searchCounter = 0;
		searchResults = [];
		allSearchResults = [];
		hasSearched = false;
		selectedFlights.clear();
		selectedFlightObjects = [];
		searchError = '';
		calendarData = null;
		otherFlightResults = [];
		showCalendarModal.set(false);
	};

	// Handle checkbox selection
	const toggleFlightSelection = (flightId) => {
		if (selectedFlights.has(flightId)) {
			selectedFlights.delete(flightId);
			// Remove from selected flight objects
			selectedFlightObjects = selectedFlightObjects.filter(f => f.id !== flightId);
		} else {
			selectedFlights.add(flightId);
			// Add to selected flight objects
			let flight = searchResults.find(f => f.id === flightId);
			if (!flight) {
				flight = otherFlightResults.find(f => f.id === flightId);
			}
			if (flight && !selectedFlightObjects.find(f => f.id === flightId)) {
				selectedFlightObjects = [...selectedFlightObjects, flight];
			}
		}
		selectedFlights = selectedFlights; // Trigger reactivity
	};

	// Handle select all checkbox
	const toggleSelectAll = (flightsList = searchResults) => {
		const list = Array.isArray(flightsList) && flightsList.length ? flightsList : searchResults;
		// Check if all current flights are selected
		const allCurrentSelected = list.every(flight => selectedFlights.has(flight.id));
		
		if (allCurrentSelected) {
			// Deselect all current flights (but keep others)
			list.forEach(flight => selectedFlights.delete(flight.id));
			// Remove from selected flight objects
			selectedFlightObjects = selectedFlightObjects.filter(
				f => !list.find(sr => sr.id === f.id)
			);
		} else {
			// Select all current flights (add to existing selections)
			list.forEach(flight => {
				selectedFlights.add(flight.id);
				// Add to selected flight objects if not already there
				if (!selectedFlightObjects.find(f => f.id === flight.id)) {
					selectedFlightObjects = [...selectedFlightObjects, flight];
				}
			});
		}
		selectedFlights = selectedFlights; // Trigger reactivity
	};

	// Handle post action
	const handlePost = async () => {
		if (selectedFlights.size === 0) {
			alert('Please select at least one flight to post');
			return;
		}
		
		if (!selectedRAGModel && !selectedBaseModel && !selectedAdapter && !selectedModel) {
			alert('Please select an AI model to use for content generation');
			return;
		}
		
		isPosting = true;
		aiStage = 'initializing';
		
		try {
			// Use selectedFlightObjects instead of filtering searchResults
			const selectedFlightData = selectedFlightObjects.map((flight) => {
				const startingCity = getFlightCity(flight, 'departure');
				const destinationCity = getFlightCity(flight, 'arrival');
				return {
					...flight,
					startingCity,
					destinationCity,
					startingPlace: startingCity ?? flight.startingPlace,
					destination: destinationCity ?? flight.destination
				};
			});
			
			// Handle model selection
			let modelToUse = null;
			
			if (selectedModel) {
				// Use any selected model (including external APIs like Gemini)
				modelToUse = {
					id: selectedModel.id,
					name: selectedModel.name || selectedModel.id,
					owned_by: selectedModel.owned_by,
					is_external_model: selectedModel.owned_by && selectedModel.owned_by !== 'ollama'
				};
				aiStage = 'stage1';
				console.log('Using selected model:', modelToUse);
			} else if (selectedBaseModel) {
				// Use base model with RAG (if available)
				modelToUse = {
					ollama_model_name: selectedBaseModel,
					base_model: selectedBaseModel,
					adapter_name: null,
					is_base_model_only: true,
					rag_model: selectedRAGModel
				};
				aiStage = 'stage1';
			} else if (selectedAdapter) {
				// Use adapter - create a model reference for the RAG model that should exist
				aiStage = 'stage1';
				console.log('Using adapter:', selectedAdapter);
				
				// Create the expected RAG model name based on the adapter export ID
				const expectedRAGModelName = `${selectedAdapter.export_id}_rag_ollama:latest`;
				console.log('Expected RAG model name:', expectedRAGModelName);
				
				modelToUse = {
					rag_model_name: `${selectedAdapter.export_id}_rag`,
					ollama_model_name: expectedRAGModelName,
					adapter_name: selectedAdapter.adapter_name,
					base_model: 'qwen2.5:14b',
					export_id: selectedAdapter.export_id,
					is_adapter_rag: true
				};
			} else if (selectedRAGModel) {
				// Use already-merged RAG model
				aiStage = 'stage1';
				console.log('Using existing RAG model:', selectedRAGModel);
				
				modelToUse = {
					rag_model_name: selectedRAGModel.rag_model_name,
					ollama_model_name: selectedRAGModel.ollama_model_name,
					adapter_name: selectedRAGModel.adapter_name,
					base_model: selectedRAGModel.base_model,
					rag_model: selectedRAGModel
				};
			}
			
			// Use the flight post handler to navigate to Post page with data and AI analysis
			await navigateToPostWithFlightData(selectedFlightData, goto, (stage) => {
				aiStage = stage;
			}, modelToUse);
		} catch (error) {
			console.error('Error posting flight data:', error);
			alert(`Error generating AI analysis: ${error.message}`);
		} finally {
			isPosting = false;
			aiStage = '';
		}
	};

	const getFlightCity = (flight, type) => {
		const raw = flight?.rawData;
		const airportsMetaList = Array.isArray(raw?.airports) ? raw.airports : [];
		const codeCandidates = type === 'departure'
			? [
				flight?.startingPlaceCode,
				raw?.origin?.code,
				raw?.origin?.airport_code,
				raw?.origin?.iata,
				raw?.origin?.id
			]
			: [
				flight?.destinationCode,
				raw?.destination?.code,
				raw?.destination?.airport_code,
				raw?.destination?.iata,
				raw?.destination?.id
			];
		const lookupCode = codeCandidates
			.map((value) => (value != null ? value.toString().trim() : ''))
			.find((value) => value.length);
		const metaCity = getCityFromAirportsMeta(airportsMetaList, type, lookupCode);
		if (metaCity) return metaCity;
		if (type === 'departure') {
			return (
				flight?.startingCity ??
				flight?.startingPlaceCity ??
				raw?.origin?.city ??
				flight?.startingPlace
			);
		}
		if (type === 'arrival') {
			return (
				flight?.destinationCity ??
				flight?.destinationPlaceCity ??
				raw?.destination?.city ??
				flight?.destination
			);
		}
		return null;
	};

	const getCityFromAirportsMeta = (airportGroups, type, code) => {
		if (!Array.isArray(airportGroups) || airportGroups.length === 0) {
			return null;
		}

	const normalizedCode = typeof code === 'string' ? code.trim().toLowerCase() : null;
	const keys = type === 'departure'
		? ['departure', 'departures', 'departure_airports', 'departureAirports']
		: ['arrival', 'arrivals', 'arrival_airports', 'arrivalAirports'];

		for (const group of airportGroups) {
			if (!group) continue;
			for (const key of keys) {
				const value = group?.[key];
				if (Array.isArray(value)) {
					for (const entry of value) {
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
						.map((identifier) => identifier.toString().toLowerCase());
					const identifiers = new Set(rawIdentifiers);
					rawIdentifiers.forEach((identifier) => {
						identifier.split(/[^a-z0-9]/i).forEach((part) => {
							const trimmed = part.trim();
							if (trimmed) identifiers.add(trimmed.toLowerCase());
						});
					});
					if (
						!normalizedCode ||
						[...identifiers].some((identifier) =>
							identifier === normalizedCode ||
							identifier.endsWith(normalizedCode) ||
							identifier.includes(`${normalizedCode}-`) ||
							identifier.includes(`-${normalizedCode}`)
						)
					) {
						const city = entry.city || entry.city_name || entry.cityName || entry.name;
							if (city) return city;
						}
					}
				} else if (value) {
				const rawIdentifiers = [
					value.id,
					value.code,
					value.iata,
					value.iata_code,
					value.airport_code,
					value.display_code,
					value.full_code
				]
					.filter(Boolean)
					.map((identifier) => identifier.toString().toLowerCase());
				const identifiers = new Set(rawIdentifiers);
				rawIdentifiers.forEach((identifier) => {
					identifier.split(/[^a-z0-9]/i).forEach((part) => {
						const trimmed = part.trim();
						if (trimmed) identifiers.add(trimmed.toLowerCase());
					});
				});
				if (
					!normalizedCode ||
					[...identifiers].some((identifier) =>
						identifier === normalizedCode ||
						identifier.endsWith(normalizedCode) ||
						identifier.includes(`${normalizedCode}-`) ||
						identifier.includes(`-${normalizedCode}`)
					)
				) {
					const city = value.city || value.city_name || value.cityName || value.name;
						if (city) return city;
					}
				}
			}

		// Fallback: return first city value if available
		for (const key of keys) {
			const value = group?.[key];
			if (Array.isArray(value)) {
				const entry = value.find((item) => item?.city || item?.city_name || item?.cityName);
				if (entry) return entry.city || entry.city_name || entry.cityName;
			} else if (value?.city || value?.city_name || value?.cityName) {
				return value.city || value.city_name || value.cityName;
			}
		}
		}

		return null;
	};
</script>

<svelte:window on:click={handleClickOutside} />

<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
		<div class=" flex items-center">
			{#if $mobile}
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class=" self-center p-1.5">
								<Sidebar />
							</div>
						</button>
					</Tooltip>
				</div>
			{/if}

			<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
				<div class="">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium bg-transparent py-1 touch-auto pointer-events-auto"
					>
						<a class="min-w-fit transition flex items-center gap-2" href="/flight-search">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								class="size-5 text-gray-900 dark:text-gray-100"
							>
								<path
									d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linejoin="round"
									stroke-linecap="round"
								/>
							</svg>
							{$i18n.t('Flight Search')}
						</a>
					</div>
				</div>

				<div class=" self-center flex items-center gap-1">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[240px]"
							role={$user?.role}
							help={true}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<button
								class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								aria-label="User Menu"
							>
								<div class=" self-center">
									<img
										src={$user?.profile_image_url}
										class="size-6 object-cover rounded-full"
										alt="User profile"
										draggable="false"
									/>
								</div>
							</button>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</nav>

	<div class="pb-1 flex-1 max-h-full overflow-y-auto @container">
		<div class="max-w-7xl mx-auto p-6">
			<!-- Page Header -->
			<div class="mb-8">
				<h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
					{$i18n.t('Flight Search')}
				</h1>
				<p class="text-gray-600 dark:text-gray-400">
					{$i18n.t('Find the best flight deals for your next trip')}
				</p>
			</div>

			<!-- Search Form -->
			<SearchBox
									{searchError}
				{searchForm}
				{isSearching}
				{startingPlaceInput}
				{destinationInput}
				{filteredStartingPlaces}
				{filteredDestinations}
				{showStartingPlaceDropdown}
				{showDestinationDropdown}
				onSearch={handleSearch}
				onReset={resetSearch}
				onStartingPlaceInput={handleStartingPlaceInput}
				onDestinationInput={handleDestinationInput}
				onStartingPlaceFocus={handleStartingPlaceFocus}
				onDestinationFocus={handleDestinationFocus}
				onSelectStartingPlace={selectStartingPlace}
				onSelectDestination={selectDestination}
				on:passengerschange={(event) => {
					const { adults, children } = event.detail;
					updateSearchForm({ adults, children });
				}}
				on:filterschange={(event) => {
					updateSearchForm(event.detail);
				}}
			/>

			<!-- Search Results -->
			<ResultBox
				{searchResults}
				{selectedFlights}
				{selectedFlightObjects}
				onToggleFlight={toggleFlightSelection}
				onToggleSelectAll={toggleSelectAll}
				onPost={handlePost}
				{isPosting}
				{aiStage}
				bind:selectedRAGModel
				bind:selectedBaseModel
				bind:selectedAdapter
				bind:selectedModel
				showCalendarButton={Boolean(calendarData)}
				onOpenCalendar={openCalendarModal}
				otherFlights={otherFlightResults}
			/>

			<CalendarGridModal
				open={$showCalendarModal}
				calendarData={calendarData}
				on:close={closeCalendarModal}
			/>
		</div>
	</div>
</div>
