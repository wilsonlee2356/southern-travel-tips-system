<script>
	import { mobile, showSidebar, user, showArchivedChats, models } from '$lib/stores';
	import { getContext, onMount } from 'svelte';
	import googleFlightsApi from '$lib/services/googleApi.js';

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

	// Placeholder event handlers (page in development)
	const toggleFlight = () => {};
	const selectFlight = () => {};
	const toggleCompare = () => {};
	const updateHoveredBar = () => {};
	const deselectFlight = () => {};
	
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

	// Handle adding a new search from the SearchForm component
	const handleAddSearch = async (event) => {
		const newSearch = event.detail;
		
		try {
			// Add to saved searches
			savedSearches = [...savedSearches, newSearch];
			
			// Select the new search
			selectedSearchId = newSearch.id;
			
			// Save to localStorage
			localStorage.setItem('autoFlightSearches', JSON.stringify(savedSearches));
			
			// Run the search immediately
			await runSearch(newSearch.id);
			
		} catch (error) {
			console.error('Error adding search:', error);
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
			// Build search parameters - only include parameters that have values
			const searchParams = {
				originLocationCode: search.departure,
			};

			// Add destination if provided
			if (search.destination && typeof search.destination === 'string' && search.destination.trim() !== '') {
				searchParams.destinationLocationCode = search.destination;
			}
			
			// Add departure date if provided
			if (search.departureDate && typeof search.departureDate === 'string' && search.departureDate.trim() !== '') {
				searchParams.departureDate = search.departureDate;
			}
			
			// Add oneWay only if explicitly set to true
			if (search.oneWay === true) {
				searchParams.oneWay = true;
			}
			
			// Add duration if provided and valid (stored as number or string)
			if (search.duration !== null && search.duration !== undefined && search.duration !== '') {
				const durationNum = typeof search.duration === 'number' ? search.duration : parseInt(search.duration);
				if (!isNaN(durationNum) && durationNum > 0 && durationNum <= 15) {
					searchParams.duration = durationNum;
				}
			}
			
			// Add nonStop only if explicitly set to true
			if (search.nonStop === true) {
				searchParams.nonStop = true;
			}
			
			// Add viewBy if provided (default is 'DATE', so always include it)
			if (search.viewBy && typeof search.viewBy === 'string' && search.viewBy.trim() !== '') {
				searchParams.viewBy = search.viewBy;
			}
			
			// Add maxPrice if provided and valid (stored as number or string)
			if (search.maxPrice !== null && search.maxPrice !== undefined && search.maxPrice !== '') {
				const priceNum = typeof search.maxPrice === 'number' ? search.maxPrice : parseFloat(search.maxPrice);
				if (!isNaN(priceNum) && priceNum > 0) {
					searchParams.maxPrice = priceNum;
				}
			}
			
			console.log(`Running search ${searchId}:`, searchParams);

            // Use dates directly from search (YYYY-MM-DD format)
            const departureDate = search.departureDate;
            const returnDate = search.oneWay ? null : (search.returnDate || null);

            // Call Google Flights API (SerpApi)
            // Ensure required params: departure_id, arrival_id, outbound_date
            if (!searchParams.originLocationCode) {
                throw new Error('Departure airport/city code is required');
            }
            if (!searchParams.destinationLocationCode) {
                throw new Error('Arrival airport/city code is required');
            }
            if (!departureDate) {
                throw new Error('Departure date is required');
            }

            const googleFlightsParams = {
                departure_id: searchParams.originLocationCode,
                arrival_id: searchParams.destinationLocationCode,
                outbound_date: departureDate,
                adults: search.adults && Number(search.adults) > 0 ? Number(search.adults) : 1,
                currency: 'HKD' // Set currency to HKD
            };

            if (returnDate && !search.oneWay) {
                googleFlightsParams.return_date = returnDate;
            }

            // Make API call to Google Flights API
            const response = await googleFlightsApi.searchFlights(googleFlightsParams);
            console.log('Google Flights API raw response:', response);
            
            const transformed = googleFlightsApi.transformFlightData(response);
            console.log('Google Flights transformed results:', transformed);
            
            // Group results by airline for display
            const priceGrid = null;
            const chartData = [];
			
			// Update the search with results
			savedSearches[searchIndex] = {
				...search,
                results: transformed,
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
				<div class="mb-8">
					<SearchForm on:addSearch={handleAddSearch} />
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
								{loadingSearches}
								on:toggleSearch={(e) => toggleSearch(e.detail)}
								on:toggleFlight={(e) => toggleFlight(e.detail)}
								on:selectFlight={(e) => selectFlight(e.detail)}
								on:toggleCompare={(e) => toggleCompare(e.detail)}
								on:updateModel={(e) => (selectedModel = e.detail)}
								on:updateHoveredBar={(e) => updateHoveredBar(e.detail)}
								on:deselectFlight={(e) => deselectFlight(e.detail)}
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

