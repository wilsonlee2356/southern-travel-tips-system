<script>
	import { mobile, showSidebar, user, showArchivedChats, models } from '$lib/stores';
	import { getContext } from 'svelte';
	import { amadeusApi } from '$lib/services/amadeusApi.js';
	import { cityList, getLocationCode, filterCities } from '$lib/utils/cityCodes';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	// Form state for adding new searches
	let newSearchForm = {
		departure: '',
		destination: '',
		autoSearchTime: '09:00', // Default 9 AM
		enabled: true
	};

	// UI state
	let isAddingSearch = false;
	let searchError = '';
	
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
	
	// Model selection
	let selectedModel = null;
	
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
		let modelId = (model.id || '').toLowerCase().trim();
		let modelName = (model.name || '').toLowerCase().trim();
		
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
	$: filteredModels = ($models || []).filter(model => isAllowedModel(model));

	// Autocomplete state
	let departureInput = '';
	let destinationInput = '';
	let filteredDepartures = [];
	let filteredDestinations = [];
	let showDepartureDropdown = false;
	let showDestinationDropdown = false;

	// Handle departure input
	const handleDepartureInput = (e) => {
		departureInput = e.target.value;
		newSearchForm.departure = departureInput;
		filteredDepartures = filterCities(departureInput);
		showDepartureDropdown = true;
	};

	// Handle destination input
	const handleDestinationInput = (e) => {
		destinationInput = e.target.value;
		newSearchForm.destination = destinationInput;
		filteredDestinations = filterCities(destinationInput);
		showDestinationDropdown = true;
	};

	// Select departure from dropdown
	const selectDeparture = (city) => {
		departureInput = city.display;
		newSearchForm.departure = city.code;
		showDepartureDropdown = false;
	};

	// Select destination from dropdown
	const selectDestination = (city) => {
		destinationInput = city.display;
		newSearchForm.destination = city.code;
		showDestinationDropdown = false;
	};

	// Close dropdowns when clicking outside
	const handleClickOutside = (e) => {
		if (!e.target.closest('.autocomplete-container')) {
			showDepartureDropdown = false;
			showDestinationDropdown = false;
		}
	};

	// Add new search configuration
	const handleAddSearch = async () => {
		searchError = '';
		
		try {
			// Validate inputs
			let originCode = newSearchForm.departure;
			if (!/^[A-Z]{3}$/i.test(originCode)) {
				originCode = getLocationCode(newSearchForm.departure);
			}
			
			if (!originCode) {
				searchError = 'Please enter a valid departure location';
				return;
			}
			
			let destinationCode = null;
			if (newSearchForm.destination) {
				destinationCode = newSearchForm.destination;
				if (!/^[A-Z]{3}$/i.test(destinationCode)) {
					destinationCode = getLocationCode(newSearchForm.destination);
				}
			}
			
			// Create new search entry
			const newSearch = {
				id: Date.now(),
				departure: originCode,
				departureDisplay: departureInput,
				destination: destinationCode,
				destinationDisplay: destinationInput,
				autoSearchTime: newSearchForm.autoSearchTime,
				enabled: newSearchForm.enabled,
				lastSearched: null,
				results: null,
				priceGrid: null,
				chartData: []
			};
			
			// Add to saved searches
			savedSearches = [...savedSearches, newSearch];
			
			// Select the new search
			selectedSearchId = newSearch.id;
			
			// Save to localStorage
			localStorage.setItem('autoFlightSearches', JSON.stringify(savedSearches));
			
			// Run the search immediately
			await runSearch(newSearch.id);
			
			// Reset form
			newSearchForm = {
				departure: '',
				destination: '',
				autoSearchTime: '09:00',
				enabled: true
			};
			departureInput = '';
			destinationInput = '';
			
		} catch (error) {
			console.error('Error adding search:', error);
			searchError = error.message || 'Failed to add search';
		}
	};

	// Run search for a specific saved search
	const runSearch = async (searchId) => {
		const searchIndex = savedSearches.findIndex(s => s.id === searchId);
		if (searchIndex === -1) return;
		
		const search = savedSearches[searchIndex];
		loadingSearches.add(searchId);
		loadingSearches = loadingSearches; // Trigger reactivity
		
		try {
			// Build search parameters
			const searchParams = {
				originLocationCode: search.departure,
			};

			if (search.destination) {
				searchParams.destinationLocationCode = search.destination;
			}
			
			console.log(`Running search ${searchId}:`, searchParams);

			// Call the cheapest date search API
			const amadeusResponse = await amadeusApi.searchCheapestDates(searchParams);
			
			// Transform the results
			const transformedResults = amadeusApi.transformCheapestDateData(amadeusResponse);
			
			// Build price grid and chart data
			const priceGrid = buildPriceGrid(transformedResults);
			const chartData = buildChartData(transformedResults);
			
			// Update the search with results
			savedSearches[searchIndex] = {
				...search,
				results: transformedResults,
				priceGrid: priceGrid,
				chartData: chartData,
				lastSearched: new Date().toISOString()
			};
			
			// Save to localStorage
			localStorage.setItem('autoFlightSearches', JSON.stringify(savedSearches));
			
		} catch (error) {
			console.error(`Error searching ${searchId}:`, error);
			// Update search with error
			savedSearches[searchIndex] = {
				...search,
				error: error.message
			};
		} finally {
			loadingSearches.delete(searchId);
			loadingSearches = loadingSearches; // Trigger reactivity
		}
	};

	// Delete a saved search
	const deleteSearch = (searchId) => {
		savedSearches = savedSearches.filter(s => s.id !== searchId);
		localStorage.setItem('autoFlightSearches', JSON.stringify(savedSearches));
	};

	// Toggle search enabled/disabled
	const toggleSearch = (searchId) => {
		const searchIndex = savedSearches.findIndex(s => s.id === searchId);
		if (searchIndex !== -1) {
			savedSearches[searchIndex].enabled = !savedSearches[searchIndex].enabled;
			savedSearches = savedSearches;
			localStorage.setItem('autoFlightSearches', JSON.stringify(savedSearches));
		}
	};

	// Load saved searches from localStorage on mount
	import { onMount } from 'svelte';
	
	onMount(() => {
		const saved = localStorage.getItem('autoFlightSearches');
		if (saved) {
			try {
				savedSearches = JSON.parse(saved);
				// Auto-select first search
				if (savedSearches.length > 0) {
					selectedSearchId = savedSearches[0].id;
				}
			} catch (error) {
				console.error('Error loading saved searches:', error);
			}
		}
	});

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
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
					Add New Auto Search
				</h2>

				<!-- Error Display -->
				{#if searchError}
					<div class="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
						<div class="flex">
							<svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
								<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
							</svg>
							<div class="ml-3">
								<h3 class="text-sm font-medium text-red-800 dark:text-red-200">
									Error
								</h3>
								<div class="mt-2 text-sm text-red-700 dark:text-red-300">
									{searchError}
								</div>
							</div>
						</div>
					</div>
				{/if}
				
				<form on:submit|preventDefault={handleAddSearch} class="space-y-6">
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
						<!-- Departure -->
						<div class="autocomplete-container relative">
							<label for="departure" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Departure')}
							</label>
							<input
								id="departure"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								placeholder="e.g., Hong Kong, 香港, HKG..."
								value={departureInput}
								on:input={handleDepartureInput}
								on:focus={() => {
									filteredDepartures = filterCities(departureInput);
									showDepartureDropdown = true;
								}}
								autocomplete="off"
								required
							/>
							{#if showDepartureDropdown && filteredDepartures.length > 0}
								<div class="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
									{#each filteredDepartures as city}
										<button
											type="button"
											class="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-sm text-gray-900 dark:text-gray-100"
											on:click={() => selectDeparture(city)}
										>
											{city.display}
										</button>
									{/each}
								</div>
							{/if}
						</div>

						<!-- Destination -->
						<div class="autocomplete-container relative">
							<label for="destination" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Destination')}
							</label>
							<input
								id="destination"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								placeholder="e.g., Seoul, Tokyo, 首爾..."
								value={destinationInput}
								on:input={handleDestinationInput}
								on:focus={() => {
									filteredDestinations = filterCities(destinationInput);
									showDestinationDropdown = true;
								}}
								autocomplete="off"
							/>
							{#if showDestinationDropdown && filteredDestinations.length > 0}
								<div class="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
									{#each filteredDestinations as city}
										<button
											type="button"
											class="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-sm text-gray-900 dark:text-gray-100"
											on:click={() => selectDestination(city)}
										>
											{city.display}
										</button>
									{/each}
								</div>
							{/if}
						</div>

						<!-- Auto Search Time -->
						<div>
							<label for="auto-search-time" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Daily Search Time
							</label>
							<input
								id="auto-search-time"
								type="time"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								bind:value={newSearchForm.autoSearchTime}
								required
							/>
							<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
								Search will run automatically every day at this time
							</p>
						</div>
					</div>

					<!-- Action Button -->
					<div class="flex gap-4 pt-4">
						<button
							type="submit"
							class="flex-1 bg-black hover:bg-gray-800 text-white font-medium py-3 px-6 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
							disabled={isAddingSearch}
						>
							{#if isAddingSearch}
								<div class="flex items-center justify-center">
									<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									Adding...
								</div>
							{:else}
								<svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
								</svg>
								Add Auto Search
							{/if}
						</button>
					</div>
				</form>
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
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
								Saved Searches
							</h3>
							<div class="space-y-2">
								{#each savedSearches as search (search.id)}
									<div 
										class="p-3 rounded-lg border cursor-pointer transition-all {
											selectedSearchId === search.id 
												? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
												: 'border-gray-300 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700'
										}"
										role="button"
										tabindex="0"
										on:click={() => selectSearch(search.id)}
										on:keydown={(e) => e.key === 'Enter' && selectSearch(search.id)}
									>
										<!-- Route -->
										<div class="font-medium text-gray-900 dark:text-gray-100 text-sm mb-2">
											{search.departureDisplay} → {search.destinationDisplay}
										</div>
										
										<!-- Time -->
										<div class="text-xs text-gray-600 dark:text-gray-400 mb-2">
											🕐 Daily at {search.autoSearchTime}
										</div>
										
										<!-- Status -->
										<div class="flex items-center justify-between">
											<span class="text-xs {
												search.enabled ? 'text-green-600 dark:text-green-400' : 'text-gray-500'
											}">
												{search.enabled ? '✓ Enabled' : '✗ Disabled'}
											</span>
											
											<div class="flex gap-1">
												<!-- Refresh Mini Button -->
												<button
													on:click|stopPropagation={() => runSearch(search.id)}
													disabled={loadingSearches.has(search.id)}
													class="px-2 py-1 bg-black hover:bg-gray-800 text-white rounded text-xs transition disabled:opacity-50"
													title="Refresh"
												>
													{#if loadingSearches.has(search.id)}
														<svg class="animate-spin h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
															<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
														</svg>
													{:else}
														<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
														</svg>
													{/if}
												</button>
												<!-- Delete Mini Button -->
												<button
													on:click|stopPropagation={() => deleteSearch(search.id)}
													class="px-2 py-1 bg-black hover:bg-gray-800 text-white rounded text-xs transition"
													title="Delete"
												>
													<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
													</svg>
												</button>
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					</div>
					
					<!-- Right Column: Results Display (2/3 width) -->
					<div class="lg:col-span-2">
						{#if selectedSearchId}
							{@const selectedSearch = savedSearches.find(s => s.id === selectedSearchId)}
							{#if selectedSearch}
								<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
									<!-- Results Header -->
									<div class="flex items-center justify-between mb-6 pb-4 border-b border-gray-200 dark:border-gray-700">
										<div>
											<h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
												{selectedSearch.departureDisplay} → {selectedSearch.destinationDisplay}
											</h3>
											<div class="flex gap-4 mt-2 text-sm text-gray-600 dark:text-gray-400">
												<span>🕐 Daily at {selectedSearch.autoSearchTime}</span>
												{#if selectedSearch.lastSearched}
													<span>Last updated: {new Date(selectedSearch.lastSearched).toLocaleString()}</span>
												{/if}
											</div>
										</div>
										<button
											on:click={() => toggleSearch(selectedSearch.id)}
											class="px-4 py-2 rounded-md text-sm font-medium transition {
												selectedSearch.enabled 
													? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400' 
													: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400'
											}"
										>
											{selectedSearch.enabled ? 'Enabled' : 'Disabled'}
										</button>
									</div>

									<!-- Search Results -->
									{#if selectedSearch.results && selectedSearch.results.length > 0}
										<!-- Grid and Chart Container (Vertical Layout) -->
										<div class="space-y-6 mb-4">
											<!-- Price Grid Calendar -->
											{#if selectedSearch.priceGrid}
										<div class="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-4">
											<h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
												Price Calendar
											</h4>
											<div class="overflow-x-auto">
												<table class="border-collapse w-full text-xs">
																<thead>
																	<tr>
																		<th class="border border-gray-300 dark:border-gray-600 px-2 py-1 bg-gray-50 dark:bg-gray-700 text-xs"></th>
																		{#each selectedSearch.priceGrid.departureDates as depDate}
																			<th class="border border-gray-300 dark:border-gray-600 px-2 py-1 bg-gray-50 dark:bg-gray-700 text-xs text-center">
																				{new Date(depDate).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' })}
																			</th>
																		{/each}
																	</tr>
																</thead>
																<tbody>
																	{#each selectedSearch.priceGrid.returnDates as retDate}
																		<tr>
																			<td class="border border-gray-300 dark:border-gray-600 px-2 py-1 bg-gray-50 dark:bg-gray-700 text-xs text-center">
																				{new Date(retDate).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' })}
																			</td>
																			{#each selectedSearch.priceGrid.departureDates as depDate}
																				{@const key = `${depDate}_${retDate}`}
																				{@const cell = selectedSearch.priceGrid.cells[key]}
																				{@const isCheapest = cell && cell.price === selectedSearch.priceGrid.cheapestPrice}
																				{@const isHighPrice = cell && cell.price > selectedSearch.priceGrid.cheapestPrice * 2}
																				
																				<td 
																					class="border border-gray-300 dark:border-gray-600 px-2 py-1 text-center cursor-pointer transition-colors text-xs
																						{selectedFlightKeys.has(key) ? 'bg-blue-200 dark:bg-blue-800' : 
																						 isCheapest ? 'bg-green-50 dark:bg-green-900/20' :
																						 'bg-white dark:bg-gray-800 hover:bg-blue-100 dark:hover:bg-blue-900/20'}"
																					on:click={() => handleCellClick(depDate, retDate, cell)}
																				>
																					{#if cell}
																						<span class="font-semibold {
																							selectedFlightKeys.has(key) ? 'text-blue-900 dark:text-blue-100' :
																							isCheapest ? 'text-green-600 dark:text-green-400' :
																							isHighPrice ? 'text-red-600 dark:text-red-400' :
																							'text-green-600 dark:text-green-400'
																						}">
																							${cell.price}
																						</span>
																					{:else}
																						<span class="text-gray-400 dark:text-gray-500">—</span>
																					{/if}
																				</td>
																			{/each}
																		</tr>
																	{/each}
																</tbody>
															</table>
														</div>
													</div>
												{/if}
												
												<!-- Price Bar Chart -->
												{#if selectedSearch.chartData && selectedSearch.chartData.length > 0}
													{@const maxPrice = Math.max(...selectedSearch.chartData.map(d => d.price))}
													{@const minPrice = Math.min(...selectedSearch.chartData.map(d => d.price))}
													{@const priceRange = maxPrice - minPrice}
													{@const chartHeight = 250}
													{@const barWidth = 8}
													{@const barGap = 2}
													{@const chartWidth = selectedSearch.chartData.length * (barWidth + barGap)}
													
													<div class="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-4">
														<h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
															Price Graph ({selectedSearch.chartData.length} days)
														</h4>
														
														<div class="relative overflow-x-auto bg-blue-50 dark:bg-gray-900 p-4 rounded-lg">
															<svg 
																width="100%" 
																height={chartHeight + 60}
																viewBox="0 0 {chartWidth + 60} {chartHeight + 60}"
																class="w-full"
																style="min-width: {chartWidth + 60}px;"
															>
																<!-- Y-axis labels -->
																<text x="5" y="20" class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="start">
																	${Math.ceil(maxPrice)}
																</text>
																<text x="5" y={chartHeight / 2} class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="start">
																	${Math.ceil(maxPrice / 2)}
																</text>
																<text x="5" y={chartHeight - 10} class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="start">
																	$0
																</text>
																
																<!-- Grid lines -->
																<line x1="50" y1="0" x2={chartWidth + 50} y2="0" stroke="#e5e7eb" stroke-width="1" />
																<line x1="50" y1={chartHeight / 2} x2={chartWidth + 50} y2={chartHeight / 2} stroke="#e5e7eb" stroke-width="1" stroke-dasharray="4" />
																<line x1="50" y1={chartHeight} x2={chartWidth + 50} y2={chartHeight} stroke="#e5e7eb" stroke-width="1" />
																
																<!-- Bars -->
																{#each selectedSearch.chartData as data, i}
																	{@const barHeight = ((data.price - minPrice) / priceRange) * chartHeight}
																	{@const x = 50 + i * (barWidth + barGap)}
																	{@const y = chartHeight - barHeight}
																	{@const isHovered = hoveredBar === i}
																	
																	<rect
																		x={x}
																		y={y}
																		width={barWidth}
																		height={barHeight}
																		fill={isHovered ? '#3b82f6' : '#93c5fd'}
																		class="cursor-pointer transition-colors"
																		role="button"
																		tabindex="0"
																		on:mouseenter={(e) => handleBarHover(e, data, i)}
																		on:mouseleave={handleBarLeave}
																	/>
																	
																	<!-- Date labels at intervals -->
																	{#if i % 7 === 0}
																		{@const date = new Date(data.date)}
																		<text 
																			x={x - 10} 
																			y={chartHeight + 20} 
																			class="text-xs fill-gray-600 dark:fill-gray-400"
																			text-anchor="start"
																		>
																			{date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
																		</text>
																	{/if}
																{/each}
																
																<!-- Month labels -->
																{#if selectedSearch.chartData.length > 0}
																	{@const firstDate = new Date(selectedSearch.chartData[0].date)}
																	{@const lastDate = new Date(selectedSearch.chartData[selectedSearch.chartData.length - 1].date)}
																	<text x={50 + chartWidth / 4} y={chartHeight + 45} class="text-sm fill-gray-700 dark:fill-gray-300 font-medium">
																		{firstDate.toLocaleDateString('en-US', { month: 'long' })}
																	</text>
																	{#if firstDate.getMonth() !== lastDate.getMonth()}
																		<text x={50 + chartWidth * 3 / 4} y={chartHeight + 45} class="text-sm fill-gray-700 dark:fill-gray-300 font-medium">
																			{lastDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
																		</text>
																	{/if}
																{/if}
															</svg>
														</div>
													</div>
												{/if}
											</div>
											
											<!-- Selected Flights List -->
											{#if selectedFlights.length > 0}
												<div class="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-4">
													<h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
														Selected Flights ({selectedFlights.length})
													</h4>
													
													<div class="space-y-2">
														{#each selectedFlights as flight}
															<div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-300 dark:border-gray-600">
																<div class="flex items-center justify-between">
																	<div class="flex-1">
																		<div class="flex items-center gap-3 mb-2">
																			<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
																				{flight.originName} ({flight.origin}) → {flight.destinationName} ({flight.destination})
																			</span>
																			<span class="text-lg font-bold text-blue-600 dark:text-blue-400">
																				${flight.price}
																			</span>
																		</div>
																		<div class="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400">
																			<span>
																				📅 Departure: {formatGridDate(flight.departureDate)}
																			</span>
																			<span>
																				📅 Return: {formatGridDate(flight.returnDate)}
																			</span>
																			<span>
																				💶 €{flight.priceEuro}
																			</span>
																		</div>
																	</div>
																	<button
																		on:click={() => removeSelectedFlight(flight.key)}
																		class="ml-3 px-2 py-1 bg-transparent hover:bg-gray-200 dark:hover:bg-gray-700 text-red-600 dark:text-red-500 rounded text-xs transition"
																		title="Remove"
																	>
																		<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
																		</svg>
																	</button>
																</div>
															</div>
														{/each}
													</div>
												</div>
											{/if}
											
										<!-- Model Selection and Post Button -->
										<div class="mt-6 flex items-center justify-between gap-4">
											<!-- Model Dropdown -->
											<div class="flex-1 max-w-xs">
												<label for="model-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
													AI Model
												</label>
												<select
													id="model-select"
													bind:value={selectedModel}
													class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
												>
													<option value={null}>Select a model...</option>
													{#each filteredModels as model}
														<option value={model.id}>
															{model.name || model.id}
														</option>
													{/each}
												</select>
											</div>
											
											<!-- Post Button -->
											<div class="flex-shrink-0 mt-6">
												<button
													class="px-6 py-2 bg-black hover:bg-gray-800 text-white font-medium rounded-lg transition disabled:opacity-50"
													disabled={!selectedModel || selectedFlights.length === 0}
													on:click={() => console.log('Post flight deals:', selectedFlights, 'with model', selectedModel)}
												>
													Post {selectedFlights.length > 0 ? `(${selectedFlights.length})` : ''}
												</button>
											</div>
										</div>
									{:else}
										<div class="text-center py-12 text-gray-500 dark:text-gray-400">
											{#if loadingSearches.has(selectedSearch.id)}
												<svg class="animate-spin mx-auto h-8 w-8 text-blue-500" fill="none" viewBox="0 0 24 24">
													<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
													<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
												</svg>
												<p class="mt-2">Searching for flights...</p>
											{:else if selectedSearch.error}
												<p class="text-red-600">Error: {selectedSearch.error}</p>
											{:else}
												<p>No results yet. Click refresh button to search.</p>
											{/if}
										</div>
									{/if}
								</div>
							{/if}
						{:else}
							<!-- No search selected -->
							<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
								<svg class="mx-auto h-16 w-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"></path>
								</svg>
								<h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
									Select a Search
								</h3>
								<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
									Click on a saved search from the left to view its results
								</p>
							</div>
						{/if}
					</div>
				</div>
			{/if}
			
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
</div>

