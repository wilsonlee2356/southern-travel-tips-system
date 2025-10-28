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
			
		} catch (error) {
			console.error('Error in auto flight search:', error);
			searchError = error.message || 'Failed to search flights';
		} finally {
			isSearching = false;
		}
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

			<!-- Results Display -->
			{#if searchResults && searchResults.length > 0}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
						Cheapest Flight Dates ({searchResults.length} results)
					</h2>
					
					<div class="overflow-x-auto">
						<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
							<thead class="bg-gray-50 dark:bg-gray-700">
								<tr>
									<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
										Departure Date
									</th>
									<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
										Return Date
									</th>
									<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
										Route
									</th>
									<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
										Price (HKD)
									</th>
									<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
										Price (EUR)
									</th>
								</tr>
							</thead>
							<tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
								{#each searchResults as result}
									<tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
											{result.departureDate}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
											{result.returnDate || 'N/A'}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
											{result.originName} ({result.origin}) → {result.destinationName} ({result.destination})
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 dark:text-gray-100">
											${result.price}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
											€{result.priceEuro}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
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
		</div>
	</div>
</div>

