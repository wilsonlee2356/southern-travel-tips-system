<script>
	import { getContext, createEventDispatcher } from 'svelte';
	import { filterCities, getLocationCode } from '$lib/utils/cityCodes';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let availableAirlines = [];
	export let airlinesLoading = false;
	export let airlinesError = '';

	const MAX_AIRLINES = 10;

let safeAirlines = [];
let codeToName = new Map();
	let newSearchForm = {
		departure: '',
		destination: '',
		travelClass: 'ECONOMY',
		nonStop: false,
		enabled: true
	};
	
	let returnTripDays = null;

	let isAddingSearch = false;
	let searchError = '';

	let departureInput = '';
	let destinationInput = '';
	let filteredDepartures = [];
	let filteredDestinations = [];
	let showDepartureDropdown = false;
	let showDestinationDropdown = false;

	let selectedAirlineCodes = [];
	let airlineSelectionError = '';
let airlinePanelOpen = false;

	$: safeAirlines = Array.isArray(availableAirlines) ? availableAirlines : [];
	$: codeToName = new Map(
		safeAirlines
			.filter((airline) => airline?.code)
			.map((airline) => [airline.code, airline.name ?? airline.code])
	);
$: selectedAirlineSummary = selectedAirlineCodes.map((code) => codeToName.get(code) ?? code);

	const handleDepartureInput = (e) => {
		departureInput = e.target.value;
		newSearchForm.departure = departureInput;
		filteredDepartures = filterCities(departureInput);
		showDepartureDropdown = true;
	};

	const handleDestinationInput = (e) => {
		destinationInput = e.target.value;
		newSearchForm.destination = destinationInput;
		filteredDestinations = filterCities(destinationInput);
		showDestinationDropdown = true;
	};

	const selectDeparture = (city) => {
		departureInput = city.display;
		newSearchForm.departure = city.code;
		showDepartureDropdown = false;
	};

	const selectDestination = (city) => {
		destinationInput = city.display;
		newSearchForm.destination = city.code;
		showDestinationDropdown = false;
	};

	const handleClickOutside = (e) => {
		if (!e.target.closest('.autocomplete-container')) {
			showDepartureDropdown = false;
			showDestinationDropdown = false;
		}
	};

	const toggleAirlineSelection = (code) => {
		if (!code) return;
		if (selectedAirlineCodes.includes(code)) {
			selectedAirlineCodes = selectedAirlineCodes.filter((c) => c !== code);
			airlineSelectionError = '';
			return;
		}

		if (selectedAirlineCodes.length >= MAX_AIRLINES) {
			airlineSelectionError = `You can select up to ${MAX_AIRLINES} airlines.`;
			return;
		}

		selectedAirlineCodes = [...selectedAirlineCodes, code];
		airlineSelectionError = '';
	};

	const resetForm = () => {
		newSearchForm = {
			departure: '',
			destination: '',
			travelClass: 'ECONOMY',
			nonStop: false,
			enabled: true
		};
		departureInput = '';
		destinationInput = '';
		selectedAirlineCodes = [];
		airlineSelectionError = '';
		returnTripDays = null;
	};

	const handleAddSearch = async () => {
		// Prevent double submission
		if (isAddingSearch) {
			return;
		}
		
		searchError = '';
		airlineSelectionError = '';
		isAddingSearch = true;

		try {
			let originCode = newSearchForm.departure;
			if (!/^[A-Z]{3}$/i.test(originCode)) {
				originCode = getLocationCode(newSearchForm.departure);
			}

			if (!originCode) {
				searchError = 'Please enter a valid departure location';
				return;
			}

			let destinationCode = newSearchForm.destination;
			if (!destinationCode) {
				searchError = 'Please enter a destination';
				return;
			}
			if (!/^[A-Z]{3}$/i.test(destinationCode)) {
				destinationCode = getLocationCode(newSearchForm.destination);
			}
			if (!destinationCode) {
				searchError = 'Please enter a valid destination location';
				return;
			}

			if (selectedAirlineCodes.length < 1) {
				searchError = `Select at least one airline (up to ${MAX_AIRLINES}).`;
				return;
			}
			if (selectedAirlineCodes.length > MAX_AIRLINES) {
				searchError = `Select no more than ${MAX_AIRLINES} airlines.`;
				return;
			}

			// Validate return trip days
			if (!returnTripDays || returnTripDays < 1 || returnTripDays > 365) {
				searchError = 'Please enter a valid return trip duration (1-365 days).';
				return;
			}

			const airlineNames = selectedAirlineCodes.map(
				(code) => codeToName.get(code) ?? code
			);

			const newSearch = {
				id: Date.now(),
				departure: originCode,
				departureDisplay: departureInput || originCode,
				destination: destinationCode,
				destinationDisplay: destinationInput || destinationCode,
				travelClass: newSearchForm.travelClass || 'ECONOMY',
				nonStop: newSearchForm.nonStop,
				enabled: newSearchForm.enabled,
				airlines: [...selectedAirlineCodes],
				airlineNames,
				lastSearched: null,
				results: null,
				priceGrid: null,
				chartData: []
			};

			dispatch('addSearch', {
				search: newSearch,
				returnTripDays: returnTripDays
			});
			resetForm();
		} catch (error) {
			console.error('Error adding search:', error);
			searchError = error.message || 'Failed to add search';
		} finally {
			isAddingSearch = false;
		}
	};
</script>

<svelte:window on:click={handleClickOutside} />

<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
	<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
		Add New Auto Search
	</h2>

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
			<div class="autocomplete-container relative">
				<label for="departure" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Departure')} <span class="text-red-500">*</span>
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

			<div class="autocomplete-container relative">
				<label for="destination" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Destination')} <span class="text-red-500">*</span>
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
					required
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

			<div>
				<label for="travel-class" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					Travel Class
				</label>
				<select
					id="travel-class"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
					bind:value={newSearchForm.travelClass}
				>
					<option value="ECONOMY">Economy</option>
					<option value="PREMIUM_ECONOMY">Premium Economy</option>
					<option value="BUSINESS">Business</option>
					<option value="FIRST">First</option>
				</select>
			</div>
		</div>

		<div class="md:col-span-2 lg:col-span-3 space-y-2">
			<div class="flex items-center justify-between gap-3">
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Airlines (select up to {MAX_AIRLINES}) <span class="text-red-500">*</span>
					</label>
					<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
						{#if selectedAirlineSummary.length}
							Selected: {selectedAirlineSummary.slice(0, 3).join(', ')}{selectedAirlineSummary.length > 3 ? ` +${selectedAirlineSummary.length - 3} more` : ''}
						{:else}
							No airlines selected yet.
						{/if}
					</p>
				</div>
				<button
					type="button"
					class="px-3 py-2 text-sm font-medium border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
					on:click={() => (airlinePanelOpen = !airlinePanelOpen)}
					aria-expanded={airlinePanelOpen}
				>
					{airlinePanelOpen ? 'Hide airlines' : 'Select airlines'} ({selectedAirlineCodes.length}/{MAX_AIRLINES})
				</button>
			</div>

			{#if airlineSelectionError}
				<div class="text-sm text-red-600 dark:text-red-400">
					{airlineSelectionError}
				</div>
			{/if}

			{#if airlinePanelOpen}
				<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-gray-50 dark:bg-gray-900/30">
					{#if airlinesLoading}
						<div class="text-sm text-gray-500 dark:text-gray-400 py-2">
							Loading airlines...
						</div>
					{:else if airlinesError}
						<div class="text-sm text-red-600 dark:text-red-400 py-2">
							{airlinesError}
						</div>
					{:else}
						<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 max-h-64 overflow-y-auto">
							{#each safeAirlines as airline (airline.airline_id ?? `${airline.code}-${airline.name}`)}
								<label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200 cursor-pointer">
									<input
										type="checkbox"
										class="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
										checked={selectedAirlineCodes.includes(airline.code)}
										on:change={() => toggleAirlineSelection(airline.code)}
									/>
									<span>{airline.code} — {airline.name}</span>
								</label>
							{/each}
							{#if !safeAirlines.length}
								<div class="col-span-full text-sm text-gray-500 dark:text-gray-400">
									No airlines available.
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div>
				<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					Flight Options
				</div>
				<div class="flex items-center gap-4">
					<label class="flex items-center cursor-pointer">
						<div class="relative">
							<input
								type="checkbox"
								class="w-6 h-6 bg-white dark:bg-gray-800 rounded outline-none focus:outline-none focus-visible:outline-none focus:ring-0 focus-visible:ring-0 checked:bg-black dark:checked:bg-white appearance-none cursor-pointer transition-all"
								bind:checked={newSearchForm.nonStop}
							/>
							{#if newSearchForm.nonStop}
								<svg class="absolute left-0.5 top-0.5 w-5 h-5 pointer-events-none fill-white dark:fill-black" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
								</svg>
							{/if}
						</div>
						<span class="ml-3 text-sm font-medium text-gray-900 dark:text-gray-100">Direct flights only</span>
					</label>
				</div>
			</div>
			
			<div>
				<label for="return-trip-days" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					Return Trip Days <span class="text-red-500">*</span>
				</label>
				<input
					id="return-trip-days"
					type="number"
					min="1"
					max="365"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
					placeholder="e.g., 7"
					bind:value={returnTripDays}
					required
				/>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					Number of days for return trip (1-365 days)
				</p>
			</div>
		</div>

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
