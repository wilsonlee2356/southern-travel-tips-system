<script>
	import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import { navigateToPostWithFlightData } from '$lib/utils/flightPostHandler.js';
	import { goto } from '$app/navigation';

	// Form state
	let searchForm = {
		startingPlace: '',
		destination: '',
		cost: '',
		seatClass: 'economy',
		departureDate: '',
		returnDate: ''
	};

	// Search results state
	let searchResults = [];
	let isSearching = false;
	let hasSearched = false;
	let selectedFlights = new Set();

	// Initialize with all flights on page load
	$: if (typeof window !== 'undefined') {
		if (searchResults.length === 0 && !hasSearched) {
			searchResults = [...sampleFlights];
		}
	}

	// Sample flight data for demonstration
	const sampleFlights = [
		{
			id: 1,
			airline: '國泰航空',
			startingPlace: '洛杉磯',
			destination: '紐約',
			cost: 2990,
			seatClass: '經濟艙',
			departureDate: '2024-02-15',
			ticketValidDate: '2024-02-20'
		},
		{
			id: 2,
			airline: '卡達航空',
			startingPlace: '舊金山',
			destination: '邁阿密',
			cost: 4900,
			seatClass: '商務艙',
			departureDate: '2024-02-16',
			ticketValidDate: '2024-02-22'
		},
		{
			id: 3,
			airline: '全日空航空公司',
			startingPlace: '香港',
			destination: '大阪',
			cost: 2900,
			seatClass: '經濟艙',
			departureDate: '2024-02-17',
			ticketValidDate: '2024-02-23'
		},
		{
			id: 4,
			airline: '阿聯酋航空',
			startingPlace: '香港',
			destination: '杜拜',
			cost: 2250,
			seatClass: '經濟艙',
			departureDate: '2024-02-18',
			ticketValidDate: '2024-02-24'
		},
		{
			id: 5,
			airline: '英國航空公司',
			startingPlace: '倫敦',
			destination: '香港',
			cost: 18000,
			seatClass: '商務艙',
			departureDate: '2024-02-19',
			ticketValidDate: '2024-02-25'
		}
	];

	// Search function
	const handleSearch = async () => {
		isSearching = true;
		hasSearched = true;

		// Simulate API call delay
		await new Promise(resolve => setTimeout(resolve, 1000));

		// Filter sample data based on search criteria
		let filteredResults = sampleFlights.filter(flight => {
			const matchesStartingPlace = !searchForm.startingPlace || 
				flight.startingPlace.toLowerCase().includes(searchForm.startingPlace.toLowerCase());
			const matchesDestination = !searchForm.destination || 
				flight.destination.toLowerCase().includes(searchForm.destination.toLowerCase());
			const matchesSeatClass = !searchForm.seatClass || 
				flight.seatClass.toLowerCase() === searchForm.seatClass.toLowerCase();
			const matchesCost = !searchForm.cost || 
				flight.cost <= parseInt(searchForm.cost);

			return matchesStartingPlace && matchesDestination && matchesSeatClass && matchesCost;
		});

		searchResults = filteredResults;
		isSearching = false;
	};

	// Reset search
	const resetSearch = () => {
		searchForm = {
			startingPlace: '',
			destination: '',
			cost: '',
			seatClass: 'economy',
			departureDate: '',
			returnDate: ''
		};
		searchResults = [...sampleFlights];
		hasSearched = false;
		selectedFlights.clear();
	};

	// Handle checkbox selection
	const toggleFlightSelection = (flightId) => {
		if (selectedFlights.has(flightId)) {
			selectedFlights.delete(flightId);
		} else {
			selectedFlights.add(flightId);
		}
		selectedFlights = selectedFlights; // Trigger reactivity
	};

	// Handle select all checkbox
	const toggleSelectAll = () => {
		if (selectedFlights.size === searchResults.length) {
			selectedFlights.clear();
		} else {
			selectedFlights = new Set(searchResults.map(flight => flight.id));
		}
		selectedFlights = selectedFlights; // Trigger reactivity
	};

	// Handle post action
	const handlePost = () => {
		if (selectedFlights.size === 0) {
			alert('Please select at least one flight to post');
			return;
		}
		
		const selectedFlightData = searchResults.filter(flight => selectedFlights.has(flight.id));
		
		// Use the flight post handler to navigate to Post page with data
		navigateToPostWithFlightData(selectedFlightData, goto);
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
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
					{$i18n.t('Search Flights')}
				</h2>
				
				<form on:submit|preventDefault={handleSearch} class="space-y-6">
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
						<!-- Starting Place -->
						<div>
							<label for="starting-place" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Starting Place')}
							</label>
							<input
								id="starting-place"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								placeholder="e.g., Los Angeles"
								bind:value={searchForm.startingPlace}
								required
							/>
						</div>

						<!-- Destination -->
						<div>
							<label for="destination" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Destination')}
							</label>
							<input
								id="destination"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								placeholder="e.g., New York"
								bind:value={searchForm.destination}
								required
							/>
						</div>

						<!-- Cost -->
						<div>
							<label for="cost" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Max Cost ($)')}
							</label>
							<input
								id="cost"
								type="number"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								placeholder="e.g., 500"
								bind:value={searchForm.cost}
								min="0"
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
							</select>
						</div>

						<!-- Departure Date -->
						<div>
							<label for="departure-date" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Departure Date')}
							</label>
							<input
								id="departure-date"
								type="date"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								bind:value={searchForm.departureDate}
							/>
						</div>

						<!-- Return Date -->
						<div>
							<label for="return-date" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Return Date')}
							</label>
							<input
								id="return-date"
								type="date"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								bind:value={searchForm.returnDate}
							/>
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
								{$i18n.t('Search Flights')}
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

			<!-- Search Results -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
				<div class="flex items-center justify-between mb-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
						{$i18n.t('Available Flights')}
					</h2>
					<span class="text-sm text-gray-600 dark:text-gray-400">
						{searchResults.length} {$i18n.t('flights found')}
					</span>
				</div>

					{#if searchResults.length > 0}
						<!-- Results Table -->
						<div class="overflow-x-auto">
							<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
								<thead class="bg-gray-50 dark:bg-gray-700">
									<tr>
										<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
											<input
												type="checkbox"
												class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
												checked={selectedFlights.size === searchResults.length && searchResults.length > 0}
												on:change={toggleSelectAll}
											/>
										</th>
										<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
											{$i18n.t('Airline')}
										</th>
										<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
											{$i18n.t('From')}
										</th>
										<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
											{$i18n.t('To')}
										</th>
										<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
											{$i18n.t('Cost')}
										</th>
										<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
											{$i18n.t('Class')}
										</th>
										<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
											{$i18n.t('Departure')}
										</th>
										<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
											{$i18n.t('Valid Until')}
										</th>
									</tr>
								</thead>
								<tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
									{#each searchResults as flight (flight.id)}
										<tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
											<td class="px-6 py-4 whitespace-nowrap">
												<input
													type="checkbox"
													class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
													checked={selectedFlights.has(flight.id)}
													on:change={() => toggleFlightSelection(flight.id)}
												/>
											</td>
											<td class="px-6 py-4 whitespace-nowrap">
												<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
													{flight.airline}
												</div>
											</td>
											<td class="px-6 py-4 whitespace-nowrap">
												<div class="text-sm text-gray-900 dark:text-gray-100">
													{flight.startingPlace}
												</div>
											</td>
											<td class="px-6 py-4 whitespace-nowrap">
												<div class="text-sm text-gray-900 dark:text-gray-100">
													{flight.destination}
												</div>
											</td>
											<td class="px-6 py-4 whitespace-nowrap">
												<div class="text-sm font-semibold text-green-600 dark:text-green-400">
													${flight.cost}
												</div>
											</td>
											<td class="px-6 py-4 whitespace-nowrap">
												<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {flight.seatClass.toLowerCase() === 'business' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'}">
													{flight.seatClass}
												</span>
											</td>
											<td class="px-6 py-4 whitespace-nowrap">
												<div class="text-sm text-gray-900 dark:text-gray-100">
													{new Date(flight.departureDate).toLocaleDateString()}
												</div>
											</td>
											<td class="px-6 py-4 whitespace-nowrap">
												<div class="text-sm text-gray-900 dark:text-gray-100">
													{new Date(flight.ticketValidDate).toLocaleDateString()}
												</div>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>

						<!-- Post Button -->
						<div class="mt-6 flex justify-end">
							<button
								class="bg-black hover:bg-gray-800 text-white font-medium py-3 px-6 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
								disabled={selectedFlights.size === 0}
								on:click={handlePost}
							>
								<svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h18v18h-18z M8 8h8v8h-8z M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0 M16 7a1 1 0 1 0 0-2a1 1 0 1 0 0 2"></path>
								</svg>
								{$i18n.t('Post')} ({selectedFlights.size})
							</button>
						</div>
				{:else}
					<!-- No Results -->
					<div class="text-center py-12">
						<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.29-1.009-5.824-2.709M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
						</svg>
						<h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
							{$i18n.t('No flights found')}
						</h3>
						<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
							{$i18n.t('Try adjusting your search criteria')}
						</p>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
