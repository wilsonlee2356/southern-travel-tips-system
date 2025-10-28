<script>
	import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
	import { getContext } from 'svelte';
	import { amadeusApi } from '$lib/services/amadeusApi.js';
	import { cityList, getLocationCode, filterCities } from '$lib/utils/cityCodes';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	// Form state
	let searchForm = {
		departure: '',
		destination: '',
		duration: '',
		seatClass: 'economy'
	};

	// UI state
	let isSearching = false;
	let searchError = '';
	let searchResults = null;
	let chartData = [];
	let hoveredBar = null;
	let tooltipPosition = { x: 0, y: 0 };
	let priceGrid = null;
	let selectedCell = null;

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
		searchForm.departure = departureInput;
		filteredDepartures = filterCities(departureInput);
		showDepartureDropdown = true;
	};

	// Handle destination input
	const handleDestinationInput = (e) => {
		destinationInput = e.target.value;
		searchForm.destination = destinationInput;
		filteredDestinations = filterCities(destinationInput);
		showDestinationDropdown = true;
	};

	// Select departure from dropdown
	const selectDeparture = (city) => {
		departureInput = city.display;
		searchForm.departure = city.code;
		showDepartureDropdown = false;
	};

	// Select destination from dropdown
	const selectDestination = (city) => {
		destinationInput = city.display;
		searchForm.destination = city.code;
		showDestinationDropdown = false;
	};

	// Close dropdowns when clicking outside
	const handleClickOutside = (e) => {
		if (!e.target.closest('.autocomplete-container')) {
			showDepartureDropdown = false;
			showDestinationDropdown = false;
		}
	};

	// Handle form submission
	const handleSearch = async () => {
		console.log('Auto flight search triggered:', searchForm);
		isSearching = true;
		searchError = '';
		searchResults = null;
		
		try {
			// Get location codes
			// If user selected from dropdown, searchForm already has the code
			// Otherwise, try to convert the input to a code
			let originCode = searchForm.departure;
			if (!/^[A-Z]{3}$/i.test(originCode)) {
				originCode = getLocationCode(searchForm.departure);
			}
			
			let destinationCode = null;
			if (searchForm.destination) {
				destinationCode = searchForm.destination;
				if (!/^[A-Z]{3}$/i.test(destinationCode)) {
					destinationCode = getLocationCode(searchForm.destination);
				}
			}
			
			console.log('Origin code:', originCode);
			console.log('Destination code:', destinationCode);

			// Build search parameters for cheapest date search
			const searchParams = {
				originLocationCode: originCode,
			};

			// Add optional parameters
			if (destinationCode) {
				searchParams.destinationLocationCode = destinationCode;
			}
			// Don't send date - API will return cheapest dates across all dates
			// Add duration if provided
			if (searchForm.duration && searchForm.duration >= 1 && searchForm.duration <= 15) {
				searchParams.duration = parseInt(searchForm.duration);
			}
			// Note: cheapest date search doesn't use travelClass
			
			console.log('Calling Amadeus Cheapest Date Search with params:', searchParams);

			// Call the cheapest date search API
			const amadeusResponse = await amadeusApi.searchCheapestDates(searchParams);
			
			console.log('========================================');
			console.log('RAW AMADEUS RESPONSE:');
			console.log(JSON.stringify(amadeusResponse, null, 2));
			console.log('========================================');
			
			// Transform the results
			const transformedResults = amadeusApi.transformCheapestDateData(amadeusResponse);
			
			console.log('========================================');
			console.log('TRANSFORMED RESULTS:');
			console.log(JSON.stringify(transformedResults, null, 2));
			console.log('========================================');
			console.log('Number of results:', transformedResults.length);
			
			searchResults = transformedResults;
			
			// Build price grid for calendar view (7x7)
			priceGrid = buildPriceGrid(transformedResults);
			console.log('Price Grid:', priceGrid);
			
			// Build chart data for 60 days
			chartData = buildChartData(transformedResults);
			console.log('Chart Data:', chartData);
			
		} catch (error) {
			console.error('Error in auto flight search:', error);
			searchError = error.message || 'Failed to search flights';
		} finally {
			isSearching = false;
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

	// Handle grid cell click
	const handleCellClick = (depDate, retDate, cell) => {
		if (cell) {
			selectedCell = `${depDate}_${retDate}`;
			console.log('Selected flight:', cell);
		}
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

	// Reset search
	const resetSearch = () => {
		searchForm = {
			departure: '',
			destination: '',
			duration: '',
			seatClass: 'economy'
		};
		departureInput = '';
		destinationInput = '';
		filteredDepartures = [];
		filteredDestinations = [];
		showDepartureDropdown = false;
		showDestinationDropdown = false;
		searchError = '';
		searchResults = null;
		priceGrid = null;
		selectedCell = null;
		chartData = [];
		hoveredBar = null;
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

			<!-- Search Form -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
					{$i18n.t('Search Flights')}
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
									Search Error
								</h3>
								<div class="mt-2 text-sm text-red-700 dark:text-red-300">
									{searchError}
								</div>
							</div>
						</div>
					</div>
				{/if}
				
				<form on:submit|preventDefault={handleSearch} class="space-y-6">
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

						<!-- Duration (Days) -->
						<div>
							<label for="duration" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Trip Duration <span class="text-gray-400 text-xs">(Optional, 1-15 days)</span>
							</label>
							<input
								id="duration"
								type="number"
								min="1"
								max="15"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								placeholder="e.g., 7"
								bind:value={searchForm.duration}
							/>
						</div>

						<!-- Seat Class -->
						<div>
							<label for="seat-class" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Seat Class')}
							</label>
							<select
								id="seat-class"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								bind:value={searchForm.seatClass}
							>
								<option value="economy">{$i18n.t('Economy')}</option>
								<option value="business">{$i18n.t('Business')}</option>
								<option value="first">{$i18n.t('First Class')}</option>
							</select>
						</div>
					</div>

					<!-- Action Buttons -->
					<div class="flex flex-col sm:flex-row gap-4 pt-4">
						<button
							type="submit"
							class="flex-1 bg-black hover:bg-gray-800 text-white font-medium py-3 px-6 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
							disabled={isSearching}
						>
							{#if isSearching}
								<div class="flex items-center justify-center">
									<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									{$i18n.t('Searching...')}
								</div>
							{:else}
								<svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
								</svg>
								{$i18n.t('Start Auto Search')}
							{/if}
						</button>
						<button
							type="button"
							on:click={resetSearch}
							class="flex-1 sm:flex-none bg-gray-500 hover:bg-gray-600 text-white font-medium py-3 px-6 rounded-lg transition"
						>
							{$i18n.t('Reset')}
						</button>
					</div>
				</form>
			</div>

			<!-- Results Display - Price Grid Calendar -->
			{#if priceGrid}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
						Flight Price Calendar
					</h2>
					
					<div class="overflow-x-auto">
						<table class="border-collapse w-full">
							<thead>
								<tr>
									<!-- Empty corner cell -->
									<th class="border border-gray-300 dark:border-gray-600 px-3 py-2 bg-gray-50 dark:bg-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300">
										
									</th>
									<!-- Departure date headers -->
									{#each priceGrid.departureDates as depDate}
										<th class="border border-gray-300 dark:border-gray-600 px-3 py-2 bg-gray-50 dark:bg-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300 text-center whitespace-nowrap">
											{formatGridDate(depDate)}
										</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each priceGrid.returnDates as retDate}
									<tr>
										<!-- Return date header -->
										<td class="border border-gray-300 dark:border-gray-600 px-3 py-2 bg-gray-50 dark:bg-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300 text-center whitespace-nowrap">
											{formatGridDate(retDate)}
										</td>
										
										<!-- Price cells -->
										{#each priceGrid.departureDates as depDate}
											{@const key = `${depDate}_${retDate}`}
											{@const cell = priceGrid.cells[key]}
											{@const isSelected = selectedCell === key}
											{@const isCheapest = cell && cell.price === priceGrid.cheapestPrice}
											{@const isHighPrice = cell && cell.price > priceGrid.cheapestPrice * 2}
											
											<td 
												class="border border-gray-300 dark:border-gray-600 px-3 py-2 text-center cursor-pointer transition-colors
													{isSelected ? 'bg-blue-500' : 
													 isCheapest ? 'bg-green-50 dark:bg-green-900/20' :
													 'bg-white dark:bg-gray-800 hover:bg-blue-100 dark:hover:bg-blue-900/20'}"
												on:click={() => handleCellClick(depDate, retDate, cell)}
											>
												{#if cell}
													<div class="flex items-center justify-center gap-1">
														{#if isCheapest}
															<svg class="w-3 h-3 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
																<path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
															</svg>
														{/if}
														<span class="text-sm font-semibold {
															isSelected ? 'text-white' :
															isCheapest ? 'text-green-600 dark:text-green-400' :
															isHighPrice ? 'text-red-600 dark:text-red-400' :
															'text-green-600 dark:text-green-400'
														}">
															${cell.price}
														</span>
													</div>
												{:else}
													<span class="text-xs text-gray-400 dark:text-gray-500">no flights</span>
												{/if}
											</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
					
					<!-- Legend -->
					<div class="mt-4 flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
						<div class="flex items-center gap-2">
							<svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
								<path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
							</svg>
							<span>Cheapest Price</span>
						</div>
						<div class="flex items-center gap-2">
							<div class="w-4 h-4 bg-blue-500 border border-gray-300 rounded"></div>
							<span>Selected</span>
						</div>
						<div class="flex items-center gap-2">
							<span class="text-red-600 font-semibold">Red</span>
							<span>High Price (2x+ cheapest)</span>
						</div>
						<div class="flex items-center gap-2">
							<span class="text-green-600 font-semibold">Green</span>
							<span>Standard Price</span>
						</div>
					</div>
				</div>
			{/if}
			
			<!-- Results Display - Price Chart -->
			{#if chartData && chartData.length > 0}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
						Price Graph ({chartData.length} days)
					</h2>
					
					{#if chartData.length > 0}
						{@const maxPrice = Math.max(...chartData.map(d => d.price))}
						{@const minPrice = Math.min(...chartData.map(d => d.price))}
						{@const priceRange = maxPrice - minPrice}
						{@const chartHeight = 300}
						{@const barWidth = 8}
						{@const barGap = 2}
						{@const chartWidth = chartData.length * (barWidth + barGap)}
						
						<div class="relative overflow-x-auto bg-blue-50 dark:bg-gray-900 p-4 rounded-lg">
							<!-- Bar Chart SVG -->
						<svg 
							width="100%" 
							height={chartHeight + 60}
							viewBox="0 0 {chartWidth + 60} {chartHeight + 60}"
							class="w-full"
							style="min-width: {chartWidth + 60}px; padding-left: 50px;"
						>
							<!-- Y-axis labels (moved further left) -->
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
							{#each chartData as data, i}
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
							{#if chartData.length > 0}
								{@const firstDate = new Date(chartData[0].date)}
								{@const lastDate = new Date(chartData[chartData.length - 1].date)}
								<text x={50 + chartWidth / 4} y={chartHeight + 40} class="text-sm fill-gray-700 dark:fill-gray-300 font-medium">
									{firstDate.toLocaleDateString('en-US', { month: 'long' })}
								</text>
								{#if firstDate.getMonth() !== lastDate.getMonth()}
									<text x={50 + chartWidth * 3 / 4} y={chartHeight + 40} class="text-sm fill-gray-700 dark:fill-gray-300 font-medium">
										{lastDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
									</text>
								{/if}
							{/if}
						</svg>
						</div>
					{/if}
				</div>
			{:else if searchResults && searchResults.length === 0}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
					<div class="text-center py-12">
						<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
						</svg>
						<h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
							No Flights Found
						</h3>
						<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
							No cheapest flight dates were found for this route. Try searching for a different destination or date.
						</p>
					</div>
				</div>
			{/if}
			
			<!-- Hover Tooltip (outside main if/else) -->
			{#if hoveredBar !== null && chartData[hoveredBar]}
				{@const data = chartData[hoveredBar]}
				<div 
					class="fixed z-50 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-xl p-4 pointer-events-none"
					style="left: {tooltipPosition.x}px; top: {tooltipPosition.y - 100}px; transform: translateX(-50%);"
				>
					<!-- Tooltip arrow -->
					<div class="absolute bottom-[-8px] left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent border-t-white dark:border-t-gray-800"></div>
					
					<div class="space-y-2 min-w-[200px]">
						<!-- Trip duration -->
						<div class="text-sm font-semibold text-gray-700 dark:text-gray-300">
							{data.duration}-day trip
						</div>
						
						<!-- Date range -->
						<div class="text-sm text-gray-900 dark:text-gray-100 font-medium">
							{formatTooltipDate(data.departureDate)} - {formatTooltipDate(data.returnDate)}
						</div>
						
						<!-- Price -->
						<div class="text-lg font-bold text-blue-600 dark:text-blue-400">
							From ${data.price}
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>

