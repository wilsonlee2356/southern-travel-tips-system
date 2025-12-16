<script>
import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
import { getContext, onMount } from 'svelte';
import { WEBUI_API_BASE_URL } from '$lib/constants';
import { goto } from '$app/navigation';
import { generateScenicImage } from '$lib/apis/pollinations/index.js';
import { cityList } from '$lib/utils/cityCodes';
import { generateAIFlightAnalysisForAutoSearch } from '$lib/utils/flightPostHandler.js';
// import { runGrokConnectivityTest } from '$lib/services/grokTest.js';
	const i18n = getContext('i18n');

const grokFlightPrompt = `Search ONLY on skyscanner.com.hk using DIRECT URL method with the exact syntax shown below (do NOT modify the date format or add extra slashes).

Reference example URL (must follow this pattern exactly):
https://www.skyscanner.com.hk/transport/flights/hkg/nrt/251126/251203/?adultsv2=1&childrenv2=&cabinclass=economy&rtn=1&outboundaltsenabled=false&inboundaltsenabled=false&airlines=235&preferdirects=false

Rules:
- Dates MUST be in YYMMDD format (e.g., 251126 = 26 Nov 2025, 260101 = 1 Jan 2026)
- CX-only filter = &airlines=235 (strictly Cathay Pacific operated only, no codeshares)
- Route: hkg/nrt/ or hkg/hnd/ (use nrt first, fall back to hnd if needed)
- Earliest outbound = tomorrow in YYMMDD
- Latest return = exactly 6 months after tomorrow in YYMMDD

Construct and scan multiple direct URLs covering the cheapest date combinations from tomorrow through the next 6 months (Dec 2025 – May 2026).

Only include flights 100% operated by Cathay Pacific (CX metal, flight numbers CX4xx/CX5xx).

Take the 10 absolute cheapest unique round-trip options (deduplicate by outbound+return YYMMDD pair), sorted by price ascending.

Output ONLY pure valid JSON — no extra text, no placeholders, no comments, all 10 entries fully listed.

{
  "search_parameters": {
    "departure": "HKG",
    "destination": "TYO",
    "airline": "Cathay Pacific (CX-operated only, no codeshares)",
    "cabin": "Economy",
    "trip_type": "Round-trip",
    "date_range_start": "tomorrow (YYMMDD)",
    "date_range_end": "6 months after tomorrow (YYMMDD)",
    "sites": ["skyscanner.com.hk"],
    "retrieved_at": "2025-11-24 HH:mm (HKT)",
    "url_template_example": "https://www.skyscanner.com.hk/transport/flights/hkg/nrt/251126/251203/?adultsv2=1&childrenv2=&cabinclass=economy&rtn=1&outboundaltsenabled=false&inboundaltsenabled=false&airlines=235&departure-times=480-840&preferdirects=false"
  },
  "flights": [
    {
      "outbound_date": "251201",
      "return_date": "251208",
      "price_hkd": 1680,
      "original_price_hkd": 2180,
      "outbound_flight": "CX506 HKG 08:15 → HND 13:55",
      "return_flight": "CX505 HND 15:25 → HKG 20:05",
      "duration_nights": 7,
      "stops": "Direct",
      "source_site": "https://www.skyscanner.com.hk/transport/flights/hkg/nrt/251201/251208/?adultsv2=1&childrenv2=&cabinclass=economy&rtn=1&outboundaltsenabled=false&inboundaltsenabled=false&airlines=235&preferdirects=false"
    }
  ],
  "total_options_aggregated": 10,
  "price_range_hkd": { "lowest": 0, "highest": 0 },
  "note": "10 cheapest unique CX-operated round-trips using exact Skyscanner YYMMDD direct URLs (example syntax enforced)."
}`;

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import SearchForm from './components/SearchForm.svelte';
	import SavedSearchesList from './components/SavedSearchesList.svelte';
	
	// List of saved search configurations
	let savedSearches = [];
	
	// Track which searches are currently loading
	let loadingSearches = new Set();
	
	// Track which search is currently selected for display
	let selectedSearchId = null;
	
	// Store flight search results for each auto search
	let flightSearchResults = new Map(); // Map<autoSearchId, results>
	let loadingFlightResults = new Set(); // Set<autoSearchId>
	let selectedAirlineTab = null; // Currently selected airline tab
	

	// Global auto-search refresh schedule (HH:MM, 24-hour)
	let autoSearchRefreshTime = '03:00';
	let isUpdatingSchedule = false;

	// Airline metadata
let availableAirlines = [];
let airlinesError = '';
let airlinesLoading = false;
let airlineCodeToName = new Map();

const travelClassMap = {
	ECONOMY: 0,
	PREMIUM_ECONOMY: 1,
	BUSINESS: 2,
	FIRST: 3
};
const MAX_AIRLINES = 10;

const travelClassReverseMap = {
	0: 'ECONOMY',
	1: 'PREMIUM_ECONOMY',
	2: 'BUSINESS',
	3: 'FIRST'
};

const formatDateForApi = (value) => {
	if (!value) return null;
	const date =
		value instanceof Date
			? value
			: typeof value === 'string'
				? new Date(value)
				: new Date(Number(value));
	if (Number.isNaN(date.getTime())) {
		return null;
	}
	const year = date.getFullYear();
	const month = `${date.getMonth() + 1}`.padStart(2, '0');
	const day = `${date.getDate()}`.padStart(2, '0');
	return `${year}-${month}-${day}`;
};

const getNextDateString = (isoDate, offsetDays = 1) => {
	if (!isoDate) return null;
	const date = new Date(isoDate);
	if (Number.isNaN(date.getTime())) return null;
	date.setDate(date.getDate() + offsetDays);
	return formatDateForApi(date);
};

const translateDestinationToChinese = (destination) => {
	if (!destination || typeof destination !== 'string') return destination;
	const normalized = destination.trim().toLowerCase();
	const match = cityList.find(
		(city) =>
			city.name.toLowerCase() === normalized ||
			city.chinese.toLowerCase() === normalized ||
			city.code.toLowerCase() === normalized
	);
	return match?.chinese || destination;
};

const persistSavedSearches = () => {
	try {
		if (typeof localStorage === 'undefined') {
			return;
		}
		localStorage.setItem('autoFlightSearches', JSON.stringify(savedSearches));
	} catch (error) {
		console.warn('Failed to persist auto flight searches to localStorage:', error);
	}
};

// --- Auto-search refresh schedule API helpers ---

const loadAutoSearchSchedule = async () => {
	// Schedule endpoint has been removed - using default schedule time
	// This function is kept for compatibility but does nothing
	return;
};

const updateAutoSearchSchedule = async () => {
	const trimmed = (autoSearchRefreshTime || '').trim();
	// Very basic HH:MM validation on the client side
	if (!/^\d{2}:\d{2}$/.test(trimmed)) {
		alert('Please enter a valid time in HH:MM format (e.g. 03:00 or 18:30).');
		return;
	}

	// Schedule endpoint has been removed - just update local state
	isUpdatingSchedule = true;
	try {
		autoSearchRefreshTime = trimmed;
		// Note: Schedule functionality has been removed, this only updates local UI state
	} finally {
		isUpdatingSchedule = false;
	}
};

const buildSavedSearchFromResponse = (data) => {
	// Handle both old format (with auto_search nested) and new format (flat)
	const autoSearchId = data?.auto_search_id ?? data?.auto_search?.auto_search_id;
	
	if (!autoSearchId) {
		return null;
	}

	const airlineModels = Array.isArray(data?.airlines) ? data.airlines : [];
	const airlineCodes = airlineModels
		.map((airline) => airline?.code)
		.filter((code) => typeof code === 'string' && code.trim().length > 0);
	// Remove duplicate codes
	const uniqueAirlineCodes = [...new Set(airlineCodes)];
	const airlineNames = airlineModels
		.map((airline) => airline?.name ?? airline?.code ?? airline?.airline_id ?? 'Unknown Airline')
		.filter((name, index, self) => {
			// Remove duplicates by name
			return self.indexOf(name) === index;
		});

	return {
		id: autoSearchId,
		departure: data?.departure_id ?? '',
		departureDisplay: data?.departure_id ?? '',
		destination: data?.arrival_id ?? '',
		destinationDisplay: data?.arrival_id ?? '',
		travelClass: travelClassReverseMap[data?.travel_class] ?? 'ECONOMY',
		nonStop: Boolean(data?.is_direct),
		enabled: true,
		airlines: uniqueAirlineCodes,
		airlineNames,
		returnTripDays: data?.return_trip_duration ?? null,
		lastSearched: data?.updated_at ?? data?.created_at ?? null,
		autoSearchResponse: data,
		error: undefined,
		results: null,
		priceGrid: null,
		chartData: []
	};
};

	const loadSavedSearches = async () => {
		const previousSelectedId = selectedSearchId;
	try {
		const response = await fetch(`${WEBUI_API_BASE_URL}/auto-flight-search/auto-search`, {
			credentials: 'include'
		});

		if (!response.ok) {
			throw new Error(`Failed to fetch auto searches (${response.status})`);
		}

		const payload = await response.json();
		console.log('=== Auto Flight Searches (from backend database) ===');
		console.log('Total searches:', payload.length);
		console.log('Full payload:', payload);
		console.debug('Auto flight searches (initial load):', payload);
		
		const normalized = Array.isArray(payload)
			? payload
					.map((entry) => buildSavedSearchFromResponse(entry))
					.filter((entry) => entry !== null)
			: [];

		savedSearches = normalized;
		const preservedSelection =
			normalized.find((entry) => entry.id === previousSelectedId)?.id ??
			(normalized.length > 0 ? normalized[0].id : null);
		selectedSearchId = preservedSelection;
		
		// Load flight search results for each saved search
		for (const search of normalized) {
			if (search?.id) {
				await loadFlightSearchResults(search.id);
			}
		}
		
		persistSavedSearches();
	} catch (error) {
		console.error('Failed to load auto searches:', error);
		try {
			if (typeof localStorage === 'undefined') {
				return;
			}
			const cached = localStorage.getItem('autoFlightSearches');
			if (cached) {
				const parsed = JSON.parse(cached);
				if (Array.isArray(parsed)) {
					savedSearches = parsed;
					const preservedSelection =
						parsed.find((entry) => entry.id === previousSelectedId)?.id ??
						(parsed.length > 0 ? parsed[0].id : null);
					selectedSearchId = preservedSelection;
				}
			}
		} catch (cacheError) {
			console.warn('Failed to parse cached auto searches:', cacheError);
		}
	}
};

	// Load flight search results from database for a specific auto search
	const loadFlightSearchResults = async (autoSearchId) => {
		if (loadingFlightResults.has(autoSearchId)) {
			return; // Already loading
		}
		
		loadingFlightResults.add(autoSearchId);
		loadingFlightResults = loadingFlightResults; // Trigger reactivity
		
		try {
			const response = await fetch(
				`${WEBUI_API_BASE_URL}/auto-flight-search/auto-search/${autoSearchId}/results`,
				{
					credentials: 'include'
				}
			);

			if (!response.ok) {
				console.warn(`Failed to fetch flight search results for auto_search_id=${autoSearchId}: ${response.status}`);
				return;
			}

			const data = await response.json();
			console.log(`=== Flight Search Results for auto_search_id=${autoSearchId} ===`);
			console.log(`Total searches: ${data.total_searches}`);
			console.log(`Total flight options: ${data.total_flight_options}`);
			console.log('Full results data:', data);
			
			// Store the results
			flightSearchResults.set(autoSearchId, data);
			flightSearchResults = flightSearchResults; // Trigger reactivity
			
			// Log details for each search
			if (data.searches && Array.isArray(data.searches)) {
				data.searches.forEach((search, idx) => {
					console.log(`\n--- Search ${idx + 1} (search_id=${search.search_id}) ---`);
					console.log(`  Departure: ${search.departure_id} → Arrival: ${search.arrival_id}`);
					console.log(`  Outbound Date: ${search.outbound_date}, Return Date: ${search.return_date || 'N/A'}`);
					console.log(`  Flight Options: ${search.flight_options?.length || 0}`);
					
					if (search.flight_options && search.flight_options.length > 0) {
						search.flight_options.forEach((option, optIdx) => {
							console.log(`    Option ${optIdx + 1}: Price=$${option.price}, Best=${option.is_best_flight}, Segments=${option.segments?.length || 0}`);
						});
					}
					
					if (search.price_insight) {
						console.log(`  Price Insight: Lowest=$${search.price_insight.lowest_price}, Level=${search.price_insight.price_level}`);
					}
				});
			}
		} catch (error) {
			console.error(`Failed to load flight search results for auto_search_id=${autoSearchId}:`, error);
		} finally {
			loadingFlightResults.delete(autoSearchId);
			loadingFlightResults = loadingFlightResults; // Trigger reactivity
		}
	};
	
	// Function to aggregate flights by airline
	const aggregateFlightsByAirline = (results) => {
		if (!results || !results.searches || !Array.isArray(results.searches)) {
			return {};
		}
		
		const airlineMap = new Map();
		
		results.searches.forEach((search) => {
			// Check if flight_options is null, undefined, or empty
			if (!search || !search.flight_options || !Array.isArray(search.flight_options) || search.flight_options.length === 0) {
				return;
			}
			
			search.flight_options.forEach((option) => {
				// Skip if option is null or doesn't have required fields
				if (!option || option.price === null || option.price === undefined) {
					return;
				}
				
				// Get airline from first segment
				let airlineCode = 'Unknown';
				let airlineName = 'Unknown Airline';
				
				if (option.segments && option.segments.length > 0) {
					const firstSegment = option.segments[0];
					airlineCode = firstSegment.airline_id || firstSegment.airline || 'Unknown';
					airlineName = firstSegment.airline || airlineCode;
				}
				
				if (!airlineMap.has(airlineCode)) {
					airlineMap.set(airlineCode, {
						code: airlineCode,
						name: airlineName,
						bestFlights: [],
						otherFlights: []
					});
				}
				
				const airlineData = airlineMap.get(airlineCode);
				const flightData = {
					...option,
					search_id: search.search_id,
					outbound_date: search.outbound_date,
					return_date: search.return_date,
					departure_id: search.departure_id,
					arrival_id: search.arrival_id,
					// Get departure date from first segment
					departure_date: option.segments && option.segments.length > 0 
						? option.segments[0].departure_date 
						: search.outbound_date
				};
				
				if (option.is_best_flight) {
					airlineData.bestFlights.push(flightData);
				} else {
					airlineData.otherFlights.push(flightData);
				}
			});
		});
		
		// Sort flights by departure date
		airlineMap.forEach((airlineData) => {
			airlineData.bestFlights.sort((a, b) => {
				const dateA = new Date(a.departure_date || a.outbound_date || '');
				const dateB = new Date(b.departure_date || b.outbound_date || '');
				return dateA - dateB;
			});
			
			airlineData.otherFlights.sort((a, b) => {
				const dateA = new Date(a.departure_date || a.outbound_date || '');
				const dateB = new Date(b.departure_date || b.outbound_date || '');
				return dateA - dateB;
			});
		});
		
		return Object.fromEntries(airlineMap);
	};
	
	// Function to get aggregated flights for selected search
	$: selectedSearchFlights = selectedSearchId && flightSearchResults.has(selectedSearchId)
		? aggregateFlightsByAirline(flightSearchResults.get(selectedSearchId))
		: {};
	
	$: airlineTabs = Object.keys(selectedSearchFlights).sort();
	
	// Reset selected airline tab when search changes
	$: if (selectedSearchId) {
		if (airlineTabs.length > 0 && (!selectedAirlineTab || !airlineTabs.includes(selectedAirlineTab))) {
			selectedAirlineTab = airlineTabs[0];
		}
	}
	
	// Load flight results when a search is selected
	$: if (selectedSearchId && !flightSearchResults.has(selectedSearchId) && !loadingFlightResults.has(selectedSearchId)) {
		loadFlightSearchResults(selectedSearchId);
	}
	
	// Track expanded flight rows
	let expandedFlightRows = new Set();
	
	const toggleFlightRowExpansion = (flightId) => {
		const next = new Set(expandedFlightRows);
		if (next.has(flightId)) {
			next.delete(flightId);
		} else {
			next.add(flightId);
		}
		expandedFlightRows = next;
	};
	
	// Helper functions for formatting
	const formatTimeDisplay = (value) => {
		if (!value) return '—';
		const sanitized = String(value).trim();
		// If time includes seconds (HH:MM:SS), remove seconds
		if (sanitized.includes(':') && sanitized.split(':').length === 3) {
			return sanitized.substring(0, 5); // Return HH:MM
		}
		return sanitized;
	};
	
	const formatDateDisplay = (value) => {
		if (!value) return null;
		const date = new Date(value);
		if (!Number.isNaN(date.getTime())) {
			return date.toLocaleDateString();
		}
		return String(value).trim();
	};
	
	const formatDuration = (minutes) => {
		if (!minutes || isNaN(minutes)) return 'N/A';
		const hours = Math.floor(minutes / 60);
		const mins = minutes % 60;
		if (hours > 0 && mins > 0) {
			return `${hours}h ${mins}m`;
		} else if (hours > 0) {
			return `${hours}h`;
		} else {
			return `${mins}m`;
		}
	};
	
	// Generate unique flight ID for expansion tracking
	const getFlightId = (flight, index) => {
		return `flight-${selectedAirlineTab}-${index}-${flight.search_id}-${flight.option_id || index}`;
	};

onMount(async () => {
	try {
		airlinesLoading = true;
		const response = await fetch(`${WEBUI_API_BASE_URL}/auto-flight-search/airlines`, {
			credentials: 'include'
		});
		if (!response.ok) {
			throw new Error(`Failed to fetch airlines (${response.status})`);
		}
		const data = await response.json();
		availableAirlines = Array.isArray(data) ? data : [];
	} catch (error) {
		console.error('Failed to load airlines:', error);
		airlinesError = error.message ?? 'Failed to load airlines';
	} finally {
		airlinesLoading = false;
	}

	await loadSavedSearches();
	await loadAutoSearchSchedule();

	// Lightweight Grok connectivity check so we detect issues as soon as the page loads.
	try {
		// const grokGreeting = await runGrokConnectivityTest(grokFlightPrompt);
		// console.info('Grok connectivity test succeeded:', grokGreeting);
	} catch (error) {
		console.warn('Grok connectivity test failed:', error);
	}
});

$: airlineCodeToName = new Map(
	availableAirlines
		.filter((airline) => airline?.code)
		.map((airline) => [airline.code, airline.name ?? airline.code])
);

	// Handle adding a new search from the SearchForm component
	const callAutoFlightSearch = async (search, returnTripDays) => {
		const airlineCodes = search.airlines ?? [];
		if (airlineCodes.length < 1) {
			throw new Error('Please select at least 1 airline before adding an auto search.');
		}
		if (airlineCodes.length > MAX_AIRLINES) {
			throw new Error(`Please select no more than ${MAX_AIRLINES} airlines.`);
		}

		const payload = {
			from_place: search.departure,
			to_place: search.destination,
			airlines: airlineCodes,
			travel_class: travelClassMap[search.travelClass] ?? 0,
			direct_flight: Boolean(search.nonStop),
			return_trip_duration: returnTripDays
		};

		const response = await fetch(`${WEBUI_API_BASE_URL}/auto-flight-search/auto-search`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload),
			credentials: 'include'
		});

		if (!response.ok) {
			const errorText = await response.text();
			throw new Error(errorText || `Auto flight search failed (${response.status})`);
		}

		return await response.json();
	};

	const handleAddSearch = async (event) => {
		const { search: newSearch, returnTripDays } = event.detail;
		let backendId = null;

		// Add a loading state for this new search
		{
			const loadingCopy = new Set(loadingSearches);
			loadingCopy.add(newSearch.id);
			loadingSearches = loadingCopy;
		}

		try {
			// Optimistically add the new search so it appears immediately in the list
			savedSearches = [...savedSearches, newSearch];
			selectedSearchId = newSearch.id;

			const searchIndex = savedSearches.findIndex((s) => s.id === newSearch.id);
			const data = await callAutoFlightSearch(newSearch, returnTripDays);

			console.log('=== Auto Flight Search Created ===');
			console.log('Full response:', data);
			console.debug('Auto flight search response (add):', data);

			backendId = data?.auto_search_id ?? data?.auto_search?.auto_search_id ?? newSearch.id;
			
			// Load flight search results after creation (wait for n8n to process)
			if (backendId) {
				setTimeout(async () => {
					await loadFlightSearchResults(backendId);
				}, 2000); // Wait 2 seconds for n8n to process
			}

			const builtSearch = buildSavedSearchFromResponse(data);
			if (builtSearch) {
				savedSearches[searchIndex] = builtSearch;
			} else {
				savedSearches[searchIndex] = {
					...newSearch,
					id: backendId,
					lastSearched: new Date().toISOString(),
					travelClass: newSearch.travelClass ?? 'ECONOMY',
					nonStop: newSearch.nonStop,
					airlines: newSearch.airlines,
					airlineNames: newSearch.airlineNames,
					autoSearchResponse: data,
					error: undefined
				};
			}

			savedSearches = [...savedSearches];
			selectedSearchId = backendId;
			persistSavedSearches();
		} catch (error) {
			console.error('Error adding search:', error);
			if (savedSearches.some((s) => s.id === newSearch.id)) {
				const searchIndex = savedSearches.findIndex((s) => s.id === newSearch.id);
				savedSearches[searchIndex] = {
					...newSearch,
					error: error.message || 'Failed to add auto search'
				};
				savedSearches = [...savedSearches];
				persistSavedSearches();
			}
		} finally {
			// Remove both the temporary ID and the backend ID (if set) from the loading set
			const loadingCopy = new Set(loadingSearches);
			loadingCopy.delete(newSearch.id);
			if (backendId) {
				loadingCopy.delete(backendId);
			}
			loadingSearches = loadingCopy;
		}
	};

	// Run search for a specific saved search
	const runSearch = async (searchId) => {
		const searchIndex = savedSearches.findIndex((s) => s.id === searchId);
		if (searchIndex === -1) return;

		const search = savedSearches[searchIndex];
		// Handle both formats: flat (auto_search_id) and nested (auto_search.auto_search_id)
		const autoSearchId = search?.id ?? 
			search?.autoSearchResponse?.auto_search_id ?? 
			search?.autoSearchResponse?.auto_search?.auto_search_id;
		
		if (!autoSearchId) {
			console.error('Cannot refresh search: missing auto_search_id', search);
			return;
		}

		const loadingCopy = new Set(loadingSearches);
		loadingCopy.add(searchId);
		loadingSearches = loadingCopy;

		try {
			const response = await fetch(
				`${WEBUI_API_BASE_URL}/auto-flight-search/auto-search/${autoSearchId}/refresh`,
				{
					method: 'POST',
					credentials: 'include'
				}
			);

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(errorText || `Auto search refresh failed (${response.status})`);
			}

			const data = await response.json();
			console.log('=== Auto Search Refresh Response ===');
			console.log('Full response:', data);
			console.debug('Auto search response (refresh):', data);
			
			// Load flight search results after refresh
			if (autoSearchId) {
				await loadFlightSearchResults(autoSearchId);
			}

			const builtSearch = buildSavedSearchFromResponse(data);
			if (builtSearch) {
				savedSearches[searchIndex] = {
					...builtSearch,
					...search,  // Preserve existing fields like lastSearched, etc.
					lastSearched: new Date().toISOString(),
					autoSearchResponse: data,
					error: undefined
				};
			} else {
				// Fallback if buildSavedSearchFromResponse returns null
				const backendAirlineModels = Array.isArray(data?.airlines) ? data.airlines : [];
				const backendAirlineCodes = backendAirlineModels
					.map((airline) => airline?.code)
					.filter((code) => typeof code === 'string' && code.trim().length > 0);
				const backendAirlineNames = backendAirlineModels.map(
					(airline) => airline?.name ?? airline?.code ?? airline?.airline_id ?? 'Unknown Airline'
				);

				savedSearches[searchIndex] = {
					...search,
					lastSearched: new Date().toISOString(),
					travelClass:
						travelClassReverseMap[data?.travel_class] ?? search.travelClass ?? 'ECONOMY',
					nonStop: Boolean(data?.is_direct ?? data?.direct_flight ?? search.nonStop),
					airlines: backendAirlineCodes.length ? backendAirlineCodes : search.airlines,
					airlineNames: backendAirlineNames.length ? backendAirlineNames : search.airlineNames,
					autoSearchResponse: data,
					error: undefined
				};
			}
			savedSearches = [...savedSearches];
			persistSavedSearches();
		} catch (error) {
			console.error('Error refreshing search:', error);
			savedSearches[searchIndex] = {
				...search,
				lastSearched: new Date().toISOString(),
				error: error.message || 'Failed to refresh auto search'
			};
			savedSearches = [...savedSearches];
			persistSavedSearches();
		} finally {
			const updatedLoading = new Set(loadingSearches);
			updatedLoading.delete(searchId);
			loadingSearches = updatedLoading;
		}
	};

	// Delete a saved search
	const deleteSearch = async (searchId) => {
		const searchIndex = savedSearches.findIndex((s) => s.id === searchId);
		if (searchIndex === -1) return;

		const search = savedSearches[searchIndex];
		// Try new format first, then fall back to old format
		const autoSearchId = search?.autoSearchResponse?.auto_search_id ?? 
		                      search?.autoSearchResponse?.auto_search?.auto_search_id ?? 
		                      searchId;

		const loadingCopy = new Set(loadingSearches);
		loadingCopy.add(searchId);
		loadingSearches = loadingCopy;

		try {
			const response = await fetch(
				`${WEBUI_API_BASE_URL}/auto-flight-search/auto-search/${autoSearchId}`,
				{
					method: 'DELETE',
					credentials: 'include'
				}
			);

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(errorText || `Auto search delete failed (${response.status})`);
			}

			// 204 No Content - no response body
			console.debug('Auto search deleted successfully:', autoSearchId);

			savedSearches = savedSearches.filter((s) => s.id !== searchId);
			if (selectedSearchId === searchId) {
				selectedSearchId = savedSearches.length > 0 ? savedSearches[0].id : null;
			}
			persistSavedSearches();
		} catch (error) {
			console.error('Error deleting search:', error);
			savedSearches[searchIndex] = {
				...search,
				error: error.message || 'Failed to delete auto search'
			};
			savedSearches = [...savedSearches];
			persistSavedSearches();
		} finally {
			const updatedLoading = new Set(loadingSearches);
			updatedLoading.delete(searchId);
			loadingSearches = updatedLoading;
		}
	};

	// Toggle search enabled/disabled
	const toggleSearch = (searchId) => {
		const searchIndex = savedSearches.findIndex(s => s.id === searchId);
		if (searchIndex !== -1) {
			savedSearches[searchIndex].enabled = !savedSearches[searchIndex].enabled;
			savedSearches = savedSearches;
			persistSavedSearches();
		}
	};

	// Build 7x7 price grid from search results
	const buildPriceGrid = (results) => {
		if (!results || results.length === 0) return null;

		// Extract unique departure and return dates
		const allDepartureDates = [...new Set(results.map(r => r.departureDate))].sort();
		const allReturnDates = [...new Set(results.map(r => r.returnDate).filter(d => d))].sort();

		if (allDepartureDates.length === 0 || allReturnDates.length === 0) return null;

		// Take first 7 dates for both axes
		const departureDates = allDepartureDates.slice(0, 7);
		const returnDates = allReturnDates.slice(0, 7);

		// Build a map for quick lookup
		const priceMap = {};
		results.forEach(result => {
			const key = `${result.departureDate}_${result.returnDate}`;
			priceMap[key] = result;
		});

		// Find cheapest price
		const cheapestPrice = Math.min(...results.map(r => r.price));

		// Build grid structure
		const grid = {
			departureDates,
			returnDates,
			cells: {},
			cheapestPrice
		};

		// Populate cells
		departureDates.forEach(depDate => {
			returnDates.forEach(retDate => {
				const key = `${depDate}_${retDate}`;
				grid.cells[key] = priceMap[key] || null;
			});
		});

		return grid;
	};

	// Build chart data from API results (60 days of data)
	const buildChartData = (results) => {
		if (!results || results.length === 0) return [];

		// Group by departure date
		const dateMap = {};
		results.forEach(result => {
			const depDate = result.departureDate;
			if (!dateMap[depDate]) {
				dateMap[depDate] = [];
			}
			dateMap[depDate].push(result);
		});

		// Get all dates and sort
		const dates = Object.keys(dateMap).sort();
		
		// Build chart data array
		const data = dates.map(date => {
			const flights = dateMap[date];
			// Find cheapest flight for this departure date
			const cheapest = flights.reduce((min, flight) => 
				flight.price < min.price ? flight : min
			);
			
			// Calculate trip duration
			const depDate = new Date(cheapest.departureDate);
			const retDate = new Date(cheapest.returnDate);
			const duration = Math.ceil((retDate - depDate) / (1000 * 60 * 60 * 24));

			return {
				date: date,
				price: cheapest.price,
				priceEuro: cheapest.priceEuro,
				departureDate: cheapest.departureDate,
				returnDate: cheapest.returnDate,
				duration: duration,
				origin: cheapest.origin,
				destination: cheapest.destination,
				originName: cheapest.originName,
				destinationName: cheapest.destinationName
			};
		});

		// If we have less than 60 days, return what we have
		// If we have more, take first 60
		return data.slice(0, 60);
	};

	// Format date for tooltip (e.g., "Thu, Nov 13")
	const formatTooltipDate = (dateStr) => {
		const date = new Date(dateStr);
		const options = { weekday: 'short', month: 'short', day: 'numeric' };
		return date.toLocaleDateString('en-US', options);
	};

	// Format date for grid header (e.g., "Mon Nov 10")
	const formatGridDate = (dateStr) => {
		const date = new Date(dateStr);
		const weekday = date.toLocaleDateString('en-US', { weekday: 'short' });
		const monthDay = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
		return `${weekday} ${monthDay}`;
	};

	// Select a search to display
	const selectSearch = (searchId) => {
		selectedSearchId = searchId;
	};
</script>

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
						<a class="min-w-fit transition flex items-center gap-2" href="/auto-flight-search">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								class="size-5 text-gray-900 dark:text-gray-100"
							>
								<path
									d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linejoin="round"
									stroke-linecap="round"
								/>
							</svg>
							{$i18n.t('Auto Flight Search')}
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
						{$i18n.t('Auto Flight Search')}
					</h1>
					<p class="text-gray-600 dark:text-gray-400">
						{$i18n.t('AI-powered automated flight search and deal monitoring')}
					</p>
				</div>

				<!-- Add New Search Form -->
				<div class="mb-8 space-y-6">
					<SearchForm
						on:addSearch={handleAddSearch}
						availableAirlines={availableAirlines}
						airlinesLoading={airlinesLoading}
						airlinesError={airlinesError}
					/>

					<!-- Auto-search daily refresh time configuration -->
					<!--
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
						<div>
							<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
								Auto-refresh time
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								Select a time of day to automatically refresh all saved auto searches.
							</div>
						</div>
						<div class="flex items-center gap-3">
							<input
								type="time"
								bind:value={autoSearchRefreshTime}
								class="border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
							/>
							<button
								class="inline-flex items-center justify-center px-3 py-1.5 rounded-md text-sm font-medium bg-black text-white dark:bg-white dark:text-black disabled:opacity-60"
								type="button"
								on:click={updateAutoSearchSchedule}
								disabled={isUpdatingSchedule}
							>
								{isUpdatingSchedule ? 'Updating…' : 'Update Timer'}
							</button>
						</div>
					</div>
					-->
				</div>

				<!-- 2-Column Layout: Searches List + Results -->
				{#if savedSearches.length === 0}
					<!-- Empty State -->
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
						<svg class="mx-auto h-16 w-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
						</svg>
						<h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
							No Auto Searches Yet
						</h3>
						<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
							Add your first auto search above to start monitoring flight prices automatically.
						</p>
					</div>
				{:else}
					<div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
						<!-- Left Column: Saved Searches List (1/5 width) -->
						<div class="lg:col-span-1">
							<SavedSearchesList 
								{savedSearches}
								{selectedSearchId}
								{loadingSearches}
								on:selectSearch={(e) => selectSearch(e.detail)}
								on:runSearch={(e) => runSearch(e.detail)}
								on:deleteSearch={(e) => deleteSearch(e.detail)}
							/>
						</div>
						
						<!-- Right Column: Search Details (4/5 width) -->
						<div class="lg:col-span-4">
							{#if selectedSearchId}
								{@const selectedSearch = savedSearches.find(s => s.id === selectedSearchId)}
								{#if selectedSearch}
									<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
										<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
											Search Details
										</h2>
										
										{#if selectedSearch.error}
											<div class="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
												<div class="text-red-700 dark:text-red-300">
													{selectedSearch.error}
												</div>
											</div>
										{:else if loadingFlightResults.has(selectedSearchId)}
											<div class="p-8 text-center">
												<svg class="animate-spin mx-auto h-8 w-8 text-blue-500 mb-4" fill="none" viewBox="0 0 24 24">
													<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
													<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
												</svg>
												<p class="text-gray-500 dark:text-gray-400">Loading flight data...</p>
											</div>
										{:else if airlineTabs.length > 0}
											<div class="space-y-4">
												<!-- Route Info -->
												<div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
													<div class="grid grid-cols-2 gap-4">
														<div>
															<div class="text-sm text-gray-600 dark:text-gray-400">Route</div>
															<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
																{selectedSearch.departure} → {selectedSearch.destination}
															</div>
														</div>
														<div>
															<div class="text-sm text-gray-600 dark:text-gray-400">Airlines</div>
															<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
																{selectedSearch.airlineNames?.join(', ') || selectedSearch.airlines?.join(', ') || 'N/A'}
															</div>
														</div>
													</div>
													
													{#if selectedSearch.lastSearched}
														<div class="mt-4 text-sm text-gray-500 dark:text-gray-400">
															Last searched: {new Date(selectedSearch.lastSearched).toLocaleString()}
														</div>
													{/if}
												</div>
												
												<!-- Airline Tabs -->
												<div class="border-b border-gray-200 dark:border-gray-700">
													<nav class="-mb-px flex space-x-8">
														{#each airlineTabs as airlineCode}
															{@const airlineData = selectedSearchFlights[airlineCode]}
															<button
																on:click={() => selectedAirlineTab = airlineCode}
																class="py-4 px-1 border-b-2 font-medium text-sm transition-colors {
																	selectedAirlineTab === airlineCode
																		? 'border-blue-500 text-blue-600 dark:text-blue-400'
																		: 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
																}"
															>
																{airlineData.name} ({airlineCode})
																<span class="ml-2 text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
																	{airlineData.bestFlights.length + airlineData.otherFlights.length}
																</span>
															</button>
														{/each}
													</nav>
												</div>
												
												<!-- Flight Lists for Selected Airline -->
												{#if selectedAirlineTab && selectedSearchFlights[selectedAirlineTab]}
													{@const airlineData = selectedSearchFlights[selectedAirlineTab]}
													
													<!-- Best Flights Table -->
													{#if airlineData.bestFlights && airlineData.bestFlights.length > 0}
														<div class="space-y-4">
															<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
																Best Flights ({airlineData.bestFlights.length})
															</h3>
															
															<!-- Mobile Layout -->
															<div class="block md:hidden space-y-3">
																{#each airlineData.bestFlights as flight, idx}
																	{@const flightId = getFlightId(flight, idx)}
																	{@const firstSegment = flight.segments && flight.segments.length > 0 ? flight.segments[0] : null}
																	{@const lastSegment = flight.segments && flight.segments.length > 0 ? flight.segments[flight.segments.length - 1] : null}
																	{@const stopsCount = flight.segments && flight.segments.length > 0 ? flight.segments.length - 1 : 0}
																	<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border border-gray-200 dark:border-gray-700">
																		<!-- Top Row: Departure → Arrival | Price -->
																		<div class="flex items-start justify-between mb-3">
																			<div class="flex items-center gap-2 flex-1 min-w-0">
																				<!-- Departure -->
																				<div class="flex flex-col items-start">
																					<div class="text-base font-semibold text-gray-900 dark:text-gray-100">
																						{formatTimeDisplay(firstSegment?.departure_time) || '—'}
																					</div>
																					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
																						{firstSegment?.departure_airport_iata || flight.departure_id || '—'}
																					</div>
																				</div>
																				
																				<!-- Arrow -->
																				<svg class="w-4 h-4 text-gray-400 flex-shrink-0 mt-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
																				</svg>
																				
																				<!-- Arrival -->
																				<div class="flex flex-col items-start">
																					<div class="text-base font-semibold text-gray-900 dark:text-gray-100">
																						{formatTimeDisplay(lastSegment?.arrival_time) || '—'}
																					</div>
																					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
																						{lastSegment?.arrival_airport_iata || flight.arrival_id || '—'}
																					</div>
																				</div>
																			</div>
																			
																			<!-- Price -->
																			<div class="ml-3 flex-shrink-0">
																				<div class="text-lg font-semibold text-green-600 dark:text-green-400">
																					${flight.price || 0}
																				</div>
																			</div>
																		</div>
																		
																		<!-- Bottom Row: Airline Icon with Duration and Airline Name -->
																		<div class="flex items-start gap-3 pt-3 border-t border-gray-200 dark:border-gray-700">
																			<!-- Airline Icon -->
																			<div class="flex-shrink-0">
																				{#if firstSegment && firstSegment.airline_logo}
																					<img src={firstSegment.airline_logo} alt="Airline logo" class="h-8 w-8 object-contain rounded-full border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900" loading="lazy" />
																				{:else}
																					<div class="h-8 w-8 rounded-full border border-gray-200 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
																						<span class="text-xs text-gray-500 dark:text-gray-400">{firstSegment?.airline_id || '—'}</span>
																					</div>
																				{/if}
																			</div>
																			
																			<!-- Duration, Stops, and Airline Name - aligned left with icon -->
																			<div class="flex flex-col items-start">
																				<div class="flex items-center gap-2 mb-1">
																					<span class="text-sm text-gray-600 dark:text-gray-400">
																						{formatDuration(flight.total_duration)}
																					</span>
																					<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {stopsCount > 0 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}">
																						{stopsCount > 0 ? `${stopsCount} stop${stopsCount > 1 ? 's' : ''}` : 'Direct'}
																					</span>
																				</div>
																				<div class="text-xs text-gray-500 dark:text-gray-400">
																					{firstSegment?.airline || airlineData.name || 'N/A'}
																				</div>
																			</div>
																		</div>
																	</div>
																{/each}
															</div>
															
															<!-- Desktop Table Layout -->
															<div class="hidden md:block bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
																<div class="overflow-x-auto">
																	<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
																		<thead class="bg-gray-50 dark:bg-gray-700">
																			<tr>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Airline</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">From</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">To</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Price</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Class</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Duration</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Stops</th>
																				<th class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Details</th>
																			</tr>
																		</thead>
																		<tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
																			{#each airlineData.bestFlights as flight, idx}
																				{@const flightId = getFlightId(flight, idx)}
																				{@const firstSegment = flight.segments && flight.segments.length > 0 ? flight.segments[0] : null}
																				{@const lastSegment = flight.segments && flight.segments.length > 0 ? flight.segments[flight.segments.length - 1] : null}
																				{@const stopsCount = flight.segments && flight.segments.length > 0 ? flight.segments.length - 1 : 0}
																				{@const travelClassMap = {0: 'Economy', 1: 'Premium Economy', 2: 'Business', 3: 'First'}}
																				{@const travelClass = firstSegment?.travel_class !== undefined ? (travelClassMap[firstSegment.travel_class] || 'Economy') : 'Economy'}
																				<tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="flex items-center gap-3">
																							{#if firstSegment && firstSegment.airline_logo}
																								<img src={firstSegment.airline_logo} alt="Airline logo" class="h-6 w-6 object-contain rounded-full border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900" loading="lazy" />
																							{/if}
																							<div>
																								<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
																									{firstSegment?.airline || airlineData.name || 'N/A'}
																								</div>
																								{#if firstSegment?.airline_id}
																									<div class="text-xs text-gray-500 dark:text-gray-400">
																										{firstSegment.airline_id}
																									</div>
																								{/if}
																							</div>
																						</div>
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="text-sm text-gray-900 dark:text-gray-100">
																							{firstSegment?.departure_airport_name || flight.departure_id || 'N/A'}
																						</div>
																						{#if firstSegment?.departure_airport_iata}
																							<div class="text-xs text-gray-500 dark:text-gray-400">
																								{firstSegment.departure_airport_iata}
																							</div>
																						{/if}
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="text-sm text-gray-900 dark:text-gray-100">
																							{lastSegment?.arrival_airport_name || flight.arrival_id || 'N/A'}
																						</div>
																						{#if lastSegment?.arrival_airport_iata}
																							<div class="text-xs text-gray-500 dark:text-gray-400">
																								{lastSegment.arrival_airport_iata}
																							</div>
																						{/if}
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="text-sm font-semibold text-green-600 dark:text-green-400">
																							${flight.price || 0}
																						</div>
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						{#if firstSegment?.travel_class !== undefined}
																							<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {travelClass.toLowerCase() === 'business' || travelClass.toLowerCase() === 'first' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'}">
																								{travelClass}
																							</span>
																						{:else}
																							<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">N/A</span>
																						{/if}
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="text-sm text-gray-900 dark:text-gray-100">
																							{formatDuration(flight.total_duration)}
																						</div>
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {stopsCount > 0 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}">
																							{stopsCount > 0 ? `${stopsCount} stop${stopsCount > 1 ? 's' : ''}` : 'Direct'}
																						</span>
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap text-right">
																						<button
																							type="button"
																							class="inline-flex items-center justify-center rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
																							on:click={() => toggleFlightRowExpansion(flightId)}
																							aria-expanded={expandedFlightRows.has(flightId)}
																						>
																							<span class={`transform transition-transform ${expandedFlightRows.has(flightId) ? 'rotate-180' : ''}`}>
																								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
																								</svg>
																							</span>
																						</button>
																					</td>
																				</tr>
																				{#if expandedFlightRows.has(flightId)}
																					<tr class="bg-gray-50 dark:bg-gray-900/60">
																						<td colspan="8" class="px-6 py-4">
																							<div class="flex items-start justify-between gap-6">
																								<div class="flex flex-col items-center justify-between text-gray-300 dark:text-gray-600 self-stretch ml-70">
																									<span class="h-2 w-2 rounded-full bg-current transform translate-y-2"></span>
																									<div class="w-px flex-1 border-l border-dashed border-current"></div>
																									<span class="h-2 w-2 rounded-full bg-current transform -translate-y-2"></span>
																								</div>
																								<div class="flex flex-col items-start gap-6 flex-1">
																									{#if firstSegment}
																										<div class="flex flex-col">
																											<div class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
																												{formatTimeDisplay(firstSegment.departure_time)}
																												{#if firstSegment.departure_airport_name}
																													<span class="text-xs text-gray-500 dark:text-gray-400">{firstSegment.departure_airport_name}</span>
																												{/if}
																											</div>
																											<div class="text-xs text-gray-500 dark:text-gray-400">
																												{formatDateDisplay(firstSegment.departure_date) ?? '—'}
																											</div>
																										</div>
																									{/if}
																									{#if flight.total_duration}
																										<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
																											路程時間：{formatDuration(flight.total_duration)}
																										</div>
																									{/if}
																									{#if lastSegment}
																										<div class="flex flex-col">
																											<div class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
																												{formatTimeDisplay(lastSegment.arrival_time)}
																												{#if lastSegment.arrival_airport_name}
																													<span class="text-xs text-gray-500 dark:text-gray-400">{lastSegment.arrival_airport_name}</span>
																												{/if}
																											</div>
																											<div class="text-xs text-gray-500 dark:text-gray-400">
																												{formatDateDisplay(lastSegment.arrival_date) ?? '—'}
																											</div>
																										</div>
																									{/if}
																								</div>
																								<div class="flex flex-col items-start text-sm text-gray-600 dark:text-gray-300 min-w-[200px]">
																									<div class="flex flex-col gap-3">
																										{#if firstSegment?.flight_number}
																											<div class="flex items-center gap-3">
																												<div class="flex items-center justify-center w-6 h-6">
																													<img src="/flight.png" alt="Flight number" class="w-6 h-6 object-contain" loading="lazy" />
																												</div>
																												<span>{firstSegment.flight_number}</span>
																											</div>
																										{/if}
																										{#if firstSegment?.travel_class !== undefined}
																											<div class="flex items-center gap-3">
																												<div class="flex items-center justify-center w-6 h-6">
																													<img src="/seat.png" alt="Travel class" class="w-6 h-6 object-contain" loading="lazy" />
																												</div>
																												<span>{travelClass}</span>
																											</div>
																										{/if}
																									</div>
																								</div>
																							</div>
																						</td>
																					</tr>
																				{/if}
																			{/each}
																		</tbody>
																	</table>
																</div>
															</div>
														</div>
													{/if}
													
													<!-- Other Flights Table -->
													{#if airlineData.otherFlights && airlineData.otherFlights.length > 0}
														<div class="space-y-4 mt-6">
															<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
																Other Flights ({airlineData.otherFlights.length})
															</h3>
															
															<!-- Mobile Layout -->
															<div class="block md:hidden space-y-3">
																{#each airlineData.otherFlights as flight, idx}
																	{@const flightId = getFlightId(flight, idx)}
																	{@const firstSegment = flight.segments && flight.segments.length > 0 ? flight.segments[0] : null}
																	{@const lastSegment = flight.segments && flight.segments.length > 0 ? flight.segments[flight.segments.length - 1] : null}
																	{@const stopsCount = flight.segments && flight.segments.length > 0 ? flight.segments.length - 1 : 0}
																	<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border border-gray-200 dark:border-gray-700">
																		<!-- Top Row: Departure → Arrival | Price -->
																		<div class="flex items-start justify-between mb-3">
																			<div class="flex items-center gap-2 flex-1 min-w-0">
																				<!-- Departure -->
																				<div class="flex flex-col items-start">
																					<div class="text-base font-semibold text-gray-900 dark:text-gray-100">
																						{formatTimeDisplay(firstSegment?.departure_time) || '—'}
																					</div>
																					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
																						{firstSegment?.departure_airport_iata || flight.departure_id || '—'}
																					</div>
																				</div>
																				
																				<!-- Arrow -->
																				<svg class="w-4 h-4 text-gray-400 flex-shrink-0 mt-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
																				</svg>
																				
																				<!-- Arrival -->
																				<div class="flex flex-col items-start">
																					<div class="text-base font-semibold text-gray-900 dark:text-gray-100">
																						{formatTimeDisplay(lastSegment?.arrival_time) || '—'}
																					</div>
																					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
																						{lastSegment?.arrival_airport_iata || flight.arrival_id || '—'}
																					</div>
																				</div>
																			</div>
																			
																			<!-- Price -->
																			<div class="ml-3 flex-shrink-0">
																				<div class="text-lg font-semibold text-green-600 dark:text-green-400">
																					${flight.price || 0}
																				</div>
																			</div>
																		</div>
																		
																		<!-- Bottom Row: Airline Icon with Duration and Airline Name -->
																		<div class="flex items-start gap-3 pt-3 border-t border-gray-200 dark:border-gray-700">
																			<!-- Airline Icon -->
																			<div class="flex-shrink-0">
																				{#if firstSegment && firstSegment.airline_logo}
																					<img src={firstSegment.airline_logo} alt="Airline logo" class="h-8 w-8 object-contain rounded-full border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900" loading="lazy" />
																				{:else}
																					<div class="h-8 w-8 rounded-full border border-gray-200 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
																						<span class="text-xs text-gray-500 dark:text-gray-400">{firstSegment?.airline_id || '—'}</span>
																					</div>
																				{/if}
																			</div>
																			
																			<!-- Duration, Stops, and Airline Name - aligned left with icon -->
																			<div class="flex flex-col items-start">
																				<div class="flex items-center gap-2 mb-1">
																					<span class="text-sm text-gray-600 dark:text-gray-400">
																						{formatDuration(flight.total_duration)}
																					</span>
																					<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {stopsCount > 0 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}">
																						{stopsCount > 0 ? `${stopsCount} stop${stopsCount > 1 ? 's' : ''}` : 'Direct'}
																					</span>
																				</div>
																				<div class="text-xs text-gray-500 dark:text-gray-400">
																					{firstSegment?.airline || airlineData.name || 'N/A'}
																				</div>
																			</div>
																		</div>
																	</div>
																{/each}
															</div>
															
															<!-- Desktop Table Layout -->
															<div class="hidden md:block bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
																<div class="overflow-x-auto">
																	<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
																		<thead class="bg-gray-50 dark:bg-gray-700">
																			<tr>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Airline</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">From</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">To</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Price</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Class</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Duration</th>
																				<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Stops</th>
																				<th class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Details</th>
																			</tr>
																		</thead>
																		<tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
																			{#each airlineData.otherFlights as flight, idx}
																				{@const flightId = getFlightId(flight, idx)}
																				{@const firstSegment = flight.segments && flight.segments.length > 0 ? flight.segments[0] : null}
																				{@const lastSegment = flight.segments && flight.segments.length > 0 ? flight.segments[flight.segments.length - 1] : null}
																				{@const stopsCount = flight.segments && flight.segments.length > 0 ? flight.segments.length - 1 : 0}
																				{@const travelClassMap = {0: 'Economy', 1: 'Premium Economy', 2: 'Business', 3: 'First'}}
																				{@const travelClass = firstSegment?.travel_class !== undefined ? (travelClassMap[firstSegment.travel_class] || 'Economy') : 'Economy'}
																				<tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="flex items-center gap-3">
																							{#if firstSegment && firstSegment.airline_logo}
																								<img src={firstSegment.airline_logo} alt="Airline logo" class="h-6 w-6 object-contain rounded-full border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900" loading="lazy" />
																							{/if}
																							<div>
																								<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
																									{firstSegment?.airline || airlineData.name || 'N/A'}
																								</div>
																								{#if firstSegment?.airline_id}
																									<div class="text-xs text-gray-500 dark:text-gray-400">
																										{firstSegment.airline_id}
																									</div>
																								{/if}
																							</div>
																						</div>
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="text-sm text-gray-900 dark:text-gray-100">
																							{firstSegment?.departure_airport_name || flight.departure_id || 'N/A'}
																						</div>
																						{#if firstSegment?.departure_airport_iata}
																							<div class="text-xs text-gray-500 dark:text-gray-400">
																								{firstSegment.departure_airport_iata}
																							</div>
																						{/if}
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="text-sm text-gray-900 dark:text-gray-100">
																							{lastSegment?.arrival_airport_name || flight.arrival_id || 'N/A'}
																						</div>
																						{#if lastSegment?.arrival_airport_iata}
																							<div class="text-xs text-gray-500 dark:text-gray-400">
																								{lastSegment.arrival_airport_iata}
																							</div>
																						{/if}
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
																							${flight.price || 0}
																						</div>
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						{#if firstSegment?.travel_class !== undefined}
																							<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {travelClass.toLowerCase() === 'business' || travelClass.toLowerCase() === 'first' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'}">
																								{travelClass}
																							</span>
																						{:else}
																							<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">N/A</span>
																						{/if}
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<div class="text-sm text-gray-900 dark:text-gray-100">
																							{formatDuration(flight.total_duration)}
																						</div>
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap">
																						<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {stopsCount > 0 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}">
																							{stopsCount > 0 ? `${stopsCount} stop${stopsCount > 1 ? 's' : ''}` : 'Direct'}
																						</span>
																					</td>
																					<td class="px-4 py-4 whitespace-nowrap text-right">
																						<button
																							type="button"
																							class="inline-flex items-center justify-center rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
																							on:click={() => toggleFlightRowExpansion(flightId)}
																							aria-expanded={expandedFlightRows.has(flightId)}
																						>
																							<span class={`transform transition-transform ${expandedFlightRows.has(flightId) ? 'rotate-180' : ''}`}>
																								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
																								</svg>
																							</span>
																						</button>
																					</td>
																				</tr>
																				{#if expandedFlightRows.has(flightId)}
																					<tr class="bg-gray-50 dark:bg-gray-900/60">
																						<td colspan="8" class="px-6 py-4">
																							<div class="flex items-start justify-between gap-6">
																								<div class="flex flex-col items-center justify-between text-gray-300 dark:text-gray-600 self-stretch ml-70">
																									<span class="h-2 w-2 rounded-full bg-current transform translate-y-2"></span>
																									<div class="w-px flex-1 border-l border-dashed border-current"></div>
																									<span class="h-2 w-2 rounded-full bg-current transform -translate-y-2"></span>
																								</div>
																								<div class="flex flex-col items-start gap-6 flex-1">
																									{#if firstSegment}
																										<div class="flex flex-col">
																											<div class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
																												{formatTimeDisplay(firstSegment.departure_time)}
																												{#if firstSegment.departure_airport_name}
																													<span class="text-xs text-gray-500 dark:text-gray-400">{firstSegment.departure_airport_name}</span>
																												{/if}
																											</div>
																											<div class="text-xs text-gray-500 dark:text-gray-400">
																												{formatDateDisplay(firstSegment.departure_date) ?? '—'}
																											</div>
																										</div>
																									{/if}
																									{#if flight.total_duration}
																										<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
																											路程時間：{formatDuration(flight.total_duration)}
																										</div>
																									{/if}
																									{#if lastSegment}
																										<div class="flex flex-col">
																											<div class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
																												{formatTimeDisplay(lastSegment.arrival_time)}
																												{#if lastSegment.arrival_airport_name}
																													<span class="text-xs text-gray-500 dark:text-gray-400">{lastSegment.arrival_airport_name}</span>
																												{/if}
																											</div>
																											<div class="text-xs text-gray-500 dark:text-gray-400">
																												{formatDateDisplay(lastSegment.arrival_date) ?? '—'}
																											</div>
																										</div>
																									{/if}
																								</div>
																								<div class="flex flex-col items-start text-sm text-gray-600 dark:text-gray-300 min-w-[200px]">
																									<div class="flex flex-col gap-3">
																										{#if firstSegment?.flight_number}
																											<div class="flex items-center gap-3">
																												<div class="flex items-center justify-center w-6 h-6">
																													<img src="/flight.png" alt="Flight number" class="w-6 h-6 object-contain" loading="lazy" />
																												</div>
																												<span>{firstSegment.flight_number}</span>
																											</div>
																										{/if}
																		{#if firstSegment?.travel_class !== undefined}
																			<div class="flex items-center gap-3">
																				<div class="flex items-center justify-center w-6 h-6">
																					<img src="/seat.png" alt="Travel class" class="w-6 h-6 object-contain" loading="lazy" />
																				</div>
																				<span>{travelClass}</span>
																			</div>
																		{/if}
																									</div>
																								</div>
																							</div>
																						</td>
																					</tr>
																				{/if}
																			{/each}
																		</tbody>
																	</table>
																</div>
															</div>
														</div>
													{/if}
													
													{#if (!airlineData.bestFlights || airlineData.bestFlights.length === 0) && (!airlineData.otherFlights || airlineData.otherFlights.length === 0)}
														<div class="p-8 text-center text-gray-500 dark:text-gray-400">
															No flight options available for this airline.
														</div>
													{/if}
												{/if}
											</div>
										{:else}
											<div class="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg text-center text-gray-500 dark:text-gray-400">
												No flight data available yet. Flight search results will appear here once data is loaded.
											</div>
										{/if}
									</div>
								{/if}
							{:else}
								<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
									<p class="text-gray-500 dark:text-gray-400">
										Select a search from the list to view details
									</p>
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>

	</div>
</div>


