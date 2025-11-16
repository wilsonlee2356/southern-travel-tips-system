<script>
import { mobile, showSidebar, user, showArchivedChats, models } from '$lib/stores';
import { getContext, onMount } from 'svelte';
import { WEBUI_API_BASE_URL } from '$lib/constants';
import { goto } from '$app/navigation';
import { generateAIFlightAnalysisForAutoSearch } from '$lib/utils/flightPostHandler.js';
	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import SearchForm from './components/SearchForm.svelte';
	import SavedSearchesList from './components/SavedSearchesList.svelte';
	import SearchResults from './components/SearchResults.svelte';
	
	// List of saved search configurations
	let savedSearches = [];
	
	// Track which searches are currently loading
	let loadingSearches = new Set();
	
	// Track which search is currently selected for display
	let selectedSearchId = null;
	
	// Tooltip state for charts
	let hoveredBar = null;
	let tooltipPosition = { x: 0, y: 0 };
	
	// Track selected flights (multiple selection allowed)
	let selectedFlights = [];

	// Global auto-search refresh schedule (HH:MM, 24-hour)
	let autoSearchRefreshTime = '03:00';
	let isUpdatingSchedule = false;

	// Placeholder event handlers (page in development)
	const toggleFlight = () => {};
	const selectFlight = () => {};
	const toggleCompare = () => {};
	const updateHoveredBar = () => {};
	const deselectFlight = () => {};
	
// Model selection
let selectedModel = null;

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
	try {
		const response = await fetch(`${WEBUI_API_BASE_URL}/auto-flight-search/auto-search/schedule`, {
			method: 'GET',
			credentials: 'include'
		});
		if (!response.ok) {
			console.warn('Failed to load auto-search schedule', await response.text());
			return;
		}
		const data = await response.json();
		if (data?.time && typeof data.time === 'string') {
			autoSearchRefreshTime = data.time;
		}
	} catch (err) {
		console.warn('Error loading auto-search schedule', err);
	}
};

const updateAutoSearchSchedule = async () => {
	const trimmed = (autoSearchRefreshTime || '').trim();
	// Very basic HH:MM validation on the client side
	if (!/^\d{2}:\d{2}$/.test(trimmed)) {
		alert('Please enter a valid time in HH:MM format (e.g. 03:00 or 18:30).');
		return;
	}

	isUpdatingSchedule = true;
	try {
		const response = await fetch(`${WEBUI_API_BASE_URL}/auto-flight-search/auto-search/schedule`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ time: trimmed })
		});

		if (!response.ok) {
			const text = await response.text();
			console.error('Failed to update auto-search schedule', text);
			alert('Failed to update auto-search refresh time.');
			return;
		}

		const data = await response.json();
		if (data?.time) {
			autoSearchRefreshTime = data.time;
		}
	} catch (err) {
		console.error('Error updating auto-search schedule', err);
		alert('Error updating auto-search refresh time.');
	} finally {
		isUpdatingSchedule = false;
	}
};

const buildSavedSearchFromResponse = (data) => {
	const autoSearchId = data?.auto_search?.auto_search_id;
	const route = data?.route;

	if (!autoSearchId || !route) {
		return null;
	}

	const airlineModels = Array.isArray(data?.airlines) ? data.airlines : [];
	const airlineCodes = airlineModels
		.map((airline) => airline?.code)
		.filter((code) => typeof code === 'string' && code.trim().length > 0);
	const airlineNames = airlineModels.map(
		(airline) => airline?.name ?? airline?.code ?? airline?.airline_id ?? 'Unknown Airline'
	);

	return {
		id: autoSearchId,
		departure: route.from_place ?? '',
		departureDisplay: route.from_place ?? '',
		destination: route.to_place ?? '',
		destinationDisplay: route.to_place ?? '',
		travelClass: travelClassReverseMap[data?.travel_class] ?? 'ECONOMY',
		nonStop: Boolean(data?.direct_flight),
		enabled: true,
		airlines: airlineCodes,
		airlineNames,
		lastSearched: data?.auto_search?.updated_at ?? data?.auto_search?.created_at ?? null,
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
});

$: airlineCodeToName = new Map(
	availableAirlines
		.filter((airline) => airline?.code)
		.map((airline) => [airline.code, airline.name ?? airline.code])
);
	
	// Allowed model patterns (same as flight search page)
	const allowedModelPatterns = [
		/^gpt-4$/i,
		/^gpt-?4o$/i,
		/^gpt-?4\.1$/i,
		/^gpt-?4\.1-?mini$/i,
		/^gpt-?5$/i,
		/^gemini-?2\.5-?flash$/i,
		/^gemini-?2\.0-?flash$/i,
		/^gemini-?2\.0-?flash-?live$/i
	];

	// Function to check if a model is allowed
	const isAllowedModel = (model) => {
		// Always allow Ollama models
		if (model?.owned_by === 'ollama') {
			return true;
		}
		// Fallback: if owned_by is missing/undefined, check for Ollama-specific properties
		// Ollama models typically have: details, ollama property, or model property without external flag
		if (!model?.owned_by) {
			const hasOllamaProperties = model?.details || model?.ollama || (model?.model && model?.external === false);
			if (hasOllamaProperties) {
				return true;
			}
		}
		
		let modelId = (model?.id || '').toLowerCase().trim();
		let modelName = (model?.name || '').toLowerCase().trim();
		
		// Strip 'models/' prefix if present
		if (modelId.startsWith('models/')) {
			modelId = modelId.substring(7);
		}
		if (modelName.startsWith('models/')) {
			modelName = modelName.substring(7);
		}
		
		// Check if model ID or name matches any of the allowed patterns
		return allowedModelPatterns.some(pattern => {
			return pattern.test(modelId) || pattern.test(modelName);
		});
	};

	// Filtered models for dropdown
	$: filteredModels = (() => {
		const allModels = $models || [];
		console.log('=== AUTO FLIGHT SEARCH MODEL FILTERING ===');
		console.log('Total models:', allModels.length);
		
		const filtered = allModels.filter(model => {
			const isAllowed = isAllowedModel(model);
			if (model?.owned_by === 'ollama') {
				console.log(`Ollama model: "${model?.id}" / "${model?.name}" - ${isAllowed ? '✅ ALLOWED' : '❌ FILTERED'}`);
			}
			return isAllowed;
		});
		
		console.log('Filtered models count:', filtered.length);
		console.log('Ollama models in filtered:', filtered.filter(m => m?.owned_by === 'ollama').length);
		console.log('=== END FILTERING DEBUG ===');
		
		return filtered;
	})();

	// Handle adding a new search from the SearchForm component
	const callAutoSearchApi = async (search) => {
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
			direct_flight: Boolean(search.nonStop)
		};

		const response = await fetch(`${WEBUI_API_BASE_URL}/auto-flight-search/auto-search`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload),
			credentials: 'include'
		});

		if (!response.ok) {
			const errorText = await response.text();
			throw new Error(errorText || `Auto search failed (${response.status})`);
		}

		return await response.json();
	};

	const handleAddSearch = async (event) => {
		const newSearch = event.detail;
		let backendId = null;

		// Add a loading state for this new search so the right-side panel shows the same
		// loading cover as when the user presses the refresh button on a saved search.
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
			const data = await callAutoSearchApi(newSearch);

			console.debug('Auto search response (add):', data);

			backendId = data?.auto_search?.auto_search_id ?? newSearch.id;
			const backendAirlineModels = Array.isArray(data?.airlines) ? data.airlines : [];
			const backendAirlineCodes = backendAirlineModels
				.map((airline) => airline?.code)
				.filter((code) => typeof code === 'string' && code.trim().length > 0);
			const backendAirlineNames = backendAirlineModels.map(
				(airline) => airline?.name ?? airline?.code ?? airline?.airline_id ?? 'Unknown Airline'
			);

			savedSearches[searchIndex] = {
				...newSearch,
				id: backendId,
				lastSearched: new Date().toISOString(),
				travelClass:
					travelClassReverseMap[data?.travel_class] ?? newSearch.travelClass ?? 'ECONOMY',
				nonStop: Boolean(data?.direct_flight),
				airlines: backendAirlineCodes.length ? backendAirlineCodes : newSearch.airlines,
				airlineNames: backendAirlineNames.length ? backendAirlineNames : newSearch.airlineNames,
				autoSearchResponse: data,
				error: undefined
			};

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
		if (!search?.autoSearchResponse?.auto_search?.auto_search_id) {
			console.error('Cannot refresh search: missing auto_search_id', search);
			return;
		}

		const autoSearchId = search.autoSearchResponse.auto_search.auto_search_id;

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
			console.debug('Auto search response (refresh):', data);

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
				nonStop: Boolean(data?.direct_flight),
				airlines: backendAirlineCodes.length ? backendAirlineCodes : search.airlines,
				airlineNames: backendAirlineNames.length ? backendAirlineNames : search.airlineNames,
				autoSearchResponse: data,
				error: undefined
			};
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
		const autoSearchId = search?.autoSearchResponse?.auto_search?.auto_search_id;

		const loadingCopy = new Set(loadingSearches);
		loadingCopy.add(searchId);
		loadingSearches = loadingCopy;

		try {
			if (autoSearchId) {
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

				const data = await response.json();
				console.debug('Auto search response (delete):', data);
			} else {
				console.warn('Deleting search without backend auto_search_id:', search);
			}

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
		selectedFlights = [];
		hoveredBar = null;
	};

	// Handle bar hover
	const handleBarHover = (event, data, index) => {
		hoveredBar = index;
		const rect = event.target.getBoundingClientRect();
		tooltipPosition = {
			x: rect.left + rect.width / 2,
			y: rect.top
		};
	};

	// Handle bar leave
	const handleBarLeave = () => {
		hoveredBar = null;
	};

	// Handle cell click in grid - toggle flight selection
	const handleCellClick = (depDate, retDate, cell) => {
		if (!cell) return;
		
		const flightKey = `${depDate}_${retDate}`;
		const existingIndex = selectedFlights.findIndex(f => f.key === flightKey);
		
		console.log('Cell clicked:', { depDate, retDate, flightKey, existingIndex });
		
		if (existingIndex >= 0) {
			// Deselect - remove from array
			console.log('Deselecting flight');
			selectedFlights = selectedFlights.filter((_, i) => i !== existingIndex);
		} else {
			// Select - add to array
			console.log('Selecting flight');
			selectedFlights = [...selectedFlights, {
				key: flightKey,
				...cell
			}];
		}
		
		console.log('Selected flights after click:', selectedFlights);
	};
	
	// Reactive set of selected flight keys for faster lookup
	$: selectedFlightKeys = new Set(selectedFlights.map(f => f.key));
	
	// Debug reactive statement
	$: {
		console.log('selectedFlightKeys updated:', Array.from(selectedFlightKeys));
	}
	
	// Check if a flight is selected
	const isFlightSelected = (depDate, retDate) => {
		const flightKey = `${depDate}_${retDate}`;
		const isSelected = selectedFlightKeys.has(flightKey);
		return isSelected;
	};
	
	// Remove a flight from selection
	const removeSelectedFlight = (flightKey) => {
		selectedFlights = selectedFlights.filter(f => f.key !== flightKey);
	};

	// Posting state for auto-search post button
	let isPostingAuto = false;

	// Handle post from CheapestPricesList
	const handleAutoSearchPost = async (event) => {
		const { selectedDates, model, airlineCode, airlineName } = event.detail;
		const selectedSearch = savedSearches.find(s => s.id === selectedSearchId);
		
		if (!selectedSearch || !selectedSearch.autoSearchResponse) {
			alert('Please select a search first');
			return;
		}

		if (!selectedDates || selectedDates.length === 0) {
			alert('Please select at least one date to post');
			return;
		}

		if (!model) {
			alert('Please select an AI model to use for content generation');
			return;
		}

		try {
			isPostingAuto = true;
			// Get route information from the selected search
			const route = selectedSearch.autoSearchResponse?.route;
			const departurePlace = route?.from_place || '';
			const returnPlace = route?.to_place || '';

			// Filter selectedDates to only include dates from the current airline
			// Since combinedCalendarData in PriceLineChart is already filtered to the current airline
			// when viewing a specific airline (not "Overall"), the selectedDates should already
			// be filtered. But we add an extra check here to ensure we only use the current airline's data.
			let filteredSelectedDates = selectedDates;
			
			// If airlineCode is provided, filter to only include dates from that airline
			if (airlineCode && selectedDates.length > 0) {
				filteredSelectedDates = selectedDates.filter(d => {
					// Check if the date's airline_code matches the current airline
					// If airline_code is not available in the date object, we trust that
					// combinedCalendarData was already filtered correctly
					return !d.airline_code || d.airline_code === airlineCode;
				});
			}
			
			// Find the lowest price from filtered selected dates
			const lowestPrice = Math.min(...filteredSelectedDates.map(d => d.price));

			// Separate departure and return dates (using filtered dates)
			const departureDates = filteredSelectedDates
				.filter(d => d.direction === 'departure')
				.map(d => d.formattedDate);
			const returnDates = filteredSelectedDates
				.filter(d => d.direction === 'return')
				.map(d => d.formattedDate);

			// Format flight data for auto-search
			const flightData = {
				departurePlace,
				returnPlace,
				lowestPrice,
				departureDates,
				returnDates
			};

			// Generate AI analysis with modified prompt
			const aiAnalysis = await generateAIFlightAnalysisForAutoSearch(flightData, model);

			// Format post data
			const postData = {
				airline: airlineName || airlineCode || 'Multiple Airlines',
				returnPrice: lowestPrice,
				departureDate: departureDates.join(', '),
				returnDate: returnDates.join(', '),
				startingPlace: departurePlace,
				destination: returnPlace,
				seatClass: travelClassReverseMap[selectedSearch.autoSearchResponse?.travel_class] || 'ECONOMY',
				departureDates: departureDates,
				returnDates: returnDates
			};

			// Combine with AI analysis
			const completePostData = {
				...postData,
				aiAnalysis: aiAnalysis,
				modelInfo: model
			};

			// Store in sessionStorage and navigate to post page
			sessionStorage.setItem('flightPostData', JSON.stringify(completePostData));
			goto('/post');
		} catch (error) {
			console.error('Error posting auto-search:', error);
			alert('Failed to generate post. Please try again.');
		} finally {
			// In practice, navigation to /post will unmount this page; this is just a safety.
			isPostingAuto = false;
		}
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
					<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
						<!-- Left Column: Saved Searches List (1/3 width) -->
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
						
						<!-- Right Column: Results Display (2/3 width) -->
						<div class="lg:col-span-2">
							<SearchResults
								selectedSearch={savedSearches.find(s => s.id === selectedSearchId)}
								{selectedFlights}
								{selectedFlightKeys}
								{hoveredBar}
								{filteredModels}
								{selectedModel}
								isPosting={isPostingAuto}
								{loadingSearches}
								on:toggleSearch={(e) => toggleSearch(e.detail)}
								on:toggleFlight={(e) => toggleFlight(e.detail)}
								on:selectFlight={(e) => selectFlight(e.detail)}
								on:toggleCompare={(e) => toggleCompare(e.detail)}
								on:updateModel={(e) => (selectedModel = e.detail)}
								on:updateHoveredBar={(e) => updateHoveredBar(e.detail)}
								on:deselectFlight={(e) => deselectFlight(e.detail)}
								on:post={handleAutoSearchPost}
							/>
						</div>
					</div>
				{/if}
			</div>

			<!-- Hover Tooltip -->
			{#if hoveredBar !== null && selectedSearchId}
				{@const selectedSearch = savedSearches.find(s => s.id === selectedSearchId)}
				{#if selectedSearch && selectedSearch.chartData && selectedSearch.chartData[hoveredBar]}
					{@const data = selectedSearch.chartData[hoveredBar]}
					<div 
						class="fixed z-50 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-xl p-3 pointer-events-none text-xs"
						style="left: {tooltipPosition.x}px; top: {tooltipPosition.y - 80}px; transform: translateX(-50%);"
					>
						<div class="absolute bottom-[-6px] left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-6 border-r-6 border-t-6 border-l-transparent border-r-transparent border-t-white dark:border-t-gray-800"></div>
						
						<div class="space-y-1 min-w-[150px]">
							<div class="font-semibold text-gray-700 dark:text-gray-300">
								{data.duration}-day trip
							</div>
							<div class="text-gray-900 dark:text-gray-100">
								{formatTooltipDate(data.departureDate)} - {formatTooltipDate(data.returnDate)}
							</div>
							<div class="font-bold text-blue-600 dark:text-blue-400">
								From ${data.price}
							</div>
						</div>
					</div>
				{/if}
			{/if}
	</div>
</div>

