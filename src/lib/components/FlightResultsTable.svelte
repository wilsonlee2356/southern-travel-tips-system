<script>
	import { getContext } from 'svelte';
	import { models } from '$lib/stores';
	
	const i18n = getContext('i18n');
	
	// Props
	export let flights = [];
	export let selectedFlights = new Set();
	export let selectedFlightObjects = []; // Actual flight objects for display
	export let onToggleFlight = () => {};
	export let onToggleSelectAll = () => {};
	export let onPost = () => {};
	export let isPosting = false;
	export let aiStage = '';
	
	// Binding props for model selection
	export let selectedAdapter = null;
	export let selectedMergedModel = null;
	export let selectedRAGModel = null;
	export let selectedBaseModel = null;
	export let selectedModel = null; // For any model (including external APIs)
	
const sanitizeString = (value) => (typeof value === 'string' ? value.trim() : null);

const formatDateDisplay = (value) => {
	const sanitized = sanitizeString(value);
	if (!sanitized) return null;
	const date = new Date(sanitized);
	if (!Number.isNaN(date.getTime())) {
		return date.toLocaleDateString();
	}
	return sanitized;
};

const formatTimeDisplay = (value) => {
	const sanitized = sanitizeString(value);
	if (!sanitized) return '—';
	return sanitized;
};

const formatDateTimeInline = (label, dateValue, timeValue) => {
	const sanitizedLabel = sanitizeString(label);
	if (sanitizedLabel) return sanitizedLabel;
	const timePart = formatTimeDisplay(timeValue);
	const datePart = formatDateDisplay(dateValue);
	const pieces = [];
	if (timePart && timePart !== '—') pieces.push(timePart);
	if (datePart) pieces.push(datePart);
	return pieces.length ? pieces.join(' ') : '—';
};

	// Handle AI model selection change
	function handleAIModelChange(event) {
		const selectedValue = event.target.value;
		
		// Reset all selections first
		selectedAdapter = null;
		selectedMergedModel = null;
		selectedRAGModel = null;
		selectedBaseModel = null;
		selectedModel = null;
		
		if (!selectedValue) return;
		
		// Select the model from the models store
		const fullModelId = selectedValue.substring(6); // Remove 'model:' prefix
		selectedModel = ($models || []).find(m => m.id === fullModelId) || null;
		console.log('Selected model:', selectedModel);
	}
	
	// Allowed model patterns (exact matches or starts with)
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

	// AI model options - only show allowed models
	$: aiModelOptions = (() => {
		console.log('=== MODEL FILTERING DEBUG (Flight Search) ===');
		console.log('Total models available:', ($models || []).length);
		
		// Log all available models
		($models || []).forEach(model => {
			console.log(`Model: ID="${model.id}", Name="${model.name}", Owner="${model.owned_by}"`);
		});
		
		// Filter and log results
		const filtered = ($models || []).filter(model => {
			const isAllowed = isAllowedModel(model);
			console.log(`Checking "${model.id}" / "${model.name}": ${isAllowed ? '✅ ALLOWED' : '❌ FILTERED'}`);
			return isAllowed;
		});
		
		console.log('Filtered models count:', filtered.length);
		console.log('=== END DEBUG ===');
		
		return filtered.map(model => ({
			value: `model:${model.id}`,
			label: `${model.name || model.id}${model.owned_by && model.owned_by !== 'ollama' ? ` (${model.owned_by})` : ''}`,
			type: 'all_models',
			modelId: model.id,
			ownedBy: model.owned_by
		}));
	})();
	
	// Get current selected value for the dropdown
	$: currentSelectedValue = selectedModel ? `model:${selectedModel.id}` : '';

	// Table state
	let currentPage = 1;
	let itemsPerPage = 10;
	let sortColumn = 'cost';
	let sortDirection = 'asc';
	let filters = {
		airline: '',
		priceRange: { min: '', max: '' },
		duration: '',
		stops: 'all'
	};

let expandedRows = new Set();

const toggleRowExpansion = (flightId) => {
	const next = new Set(expandedRows);
	if (next.has(flightId)) {
		next.delete(flightId);
	} else {
		next.add(flightId);
	}
	expandedRows = next;
};
	
	// Track previous flights to detect new searches
	let previousFlightsLength = 0;
	let previousFlightsHash = '';
	let isRefreshing = false;

	// Computed values
	$: filteredFlights = flights.filter(flight => {
		// Case-insensitive airline filter
		const airlineFilter = filters.airline.toLowerCase().trim();
		const matchesAirline = !airlineFilter || 
			(flight.airline && flight.airline.toLowerCase().includes(airlineFilter)) ||
			(flight.airlineCode && flight.airlineCode.toLowerCase().includes(airlineFilter));
		
		// Price range filter
		const minPrice = filters.priceRange.min && filters.priceRange.min.trim() ? parseFloat(filters.priceRange.min) : null;
		const maxPrice = filters.priceRange.max && filters.priceRange.max.trim() ? parseFloat(filters.priceRange.max) : null;
		const matchesPrice = (!minPrice || (flight.cost && flight.cost >= minPrice)) &&
			(!maxPrice || (flight.cost && flight.cost <= maxPrice));
		
		// Stops filter
		const matchesStops = filters.stops === 'all' || 
			(filters.stops === 'direct' && flight.segments === 1) ||
			(filters.stops === '1stop' && flight.segments === 2) ||
			(filters.stops === '2plus' && flight.segments > 2);
		
		return matchesAirline && matchesPrice && matchesStops;
	});

	$: sortedFlights = [...filteredFlights].sort((a, b) => {
		let aVal = a[sortColumn];
		let bVal = b[sortColumn];
		
		// Handle special cases
		if (sortColumn === 'cost') {
			aVal = parseFloat(aVal);
			bVal = parseFloat(bVal);
		} else if (sortColumn === 'departureDate') {
			aVal = new Date(aVal);
			bVal = new Date(bVal);
		} else if (sortColumn === 'duration') {
			// Extract numeric value from duration for sorting
			const aMatch = aVal.match(/(\d+)小時/);
			const bMatch = bVal.match(/(\d+)小時/);
			aVal = aMatch ? parseInt(aMatch[1]) : 0;
			bVal = bMatch ? parseInt(bMatch[1]) : 0;
		}
		
		if (sortDirection === 'asc') {
			return aVal > bVal ? 1 : -1;
		} else {
			return aVal < bVal ? 1 : -1;
		}
	});

	$: totalPages = Math.ceil(sortedFlights.length / itemsPerPage);
	$: paginatedFlights = sortedFlights.slice(
		(currentPage - 1) * itemsPerPage,
		currentPage * itemsPerPage
	);

	// Functions
	const handleSort = (column) => {
		if (sortColumn === column) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortColumn = column;
			sortDirection = 'asc';
		}
		currentPage = 1; // Reset to first page when sorting
	};

	const handlePageChange = (page) => {
		currentPage = page;
	};

	const handleItemsPerPageChange = (event) => {
		itemsPerPage = parseInt(event.target.value);
		currentPage = 1; // Reset to first page
	};

	const clearFilters = () => {
		filters = {
			airline: '',
			priceRange: { min: '', max: '' },
			duration: '',
			stops: 'all'
		};
		currentPage = 1;
	};

	const getSortIcon = (column) => {
		if (sortColumn !== column) return '↕️';
		return sortDirection === 'asc' ? '↑' : '↓';
	};

	// Reset table state when new search results arrive
	$: {
		// Create a simple hash of the flights data to detect changes
		const currentFlightsHash = flights.map(f => f.id).join(',');
		
		// Check if this is a new search (different data or different length)
		const isNewSearch = currentFlightsHash !== previousFlightsHash || 
			flights.length !== previousFlightsLength;
		
		if (isNewSearch && flights.length > 0) {
			// Show refreshing indicator
			isRefreshing = true;
			
			// Reset pagination to first page
			currentPage = 1;
			
			// Reset filters to show all results
			filters = {
				airline: '',
				priceRange: { min: '', max: '' },
				duration: '',
				stops: 'all'
			};
			
			// Reset sorting to default (price ascending)
			sortColumn = 'cost';
			sortDirection = 'asc';
			
			// Update tracking variables
			previousFlightsHash = currentFlightsHash;
			previousFlightsLength = flights.length;
			
			// Hide refreshing indicator after a short delay
			setTimeout(() => {
				isRefreshing = false;
			}, 500);
		}
	}
</script>

<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg">
	<!-- Filters Section -->
	<!-- Filter section commented out per request -->
	<!--
	<div class="p-4 md:p-6 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
				{$i18n.t('Filters')}
			</h3>
			<button
				on:click={clearFilters}
				class="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
			>
				{$i18n.t('Clear All')}
			</button>
		</div>
		
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 md:mb-4 space-y-4 md:space-y-0">
			<div>
				<label for="airline-filter" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('Airline')}
				</label>
				<input
					id="airline-filter"
					type="text"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
					placeholder="e.g., Cathay, CX, 國泰..."
					bind:value={filters.airline}
				/>
			</div>

			<div>
				<label for="stops-filter" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('Stops')}
				</label>
				<select
					id="stops-filter"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
					bind:value={filters.stops}
				>
					<option value="all">{$i18n.t('All')}</option>
					<option value="direct">{$i18n.t('Direct')}</option>
					<option value="1stop">{$i18n.t('1 Stop')}</option>
					<option value="2plus">{$i18n.t('2+ Stops')}</option>
				</select>
			</div>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-4 space-y-4 md:space-y-0">
			<div>
				<fieldset>
					<legend class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('Price Range')}
					</legend>
					<div class="flex gap-2">
						<input
							id="price-min"
							type="number"
							class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
							placeholder="Min"
							bind:value={filters.priceRange.min}
						/>
						<input
							id="price-max"
							type="number"
							class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
							placeholder="Max"
							bind:value={filters.priceRange.max}
						/>
					</div>
				</fieldset>
			</div>

			<div>
				<label for="items-per-page" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('Per Page')}
				</label>
				<select
					id="items-per-page"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
					on:change={handleItemsPerPageChange}
				>
					<option value="5">5</option>
					<option value="10">10</option>
					<option value="20">20</option>
					<option value="50">50</option>
				</select>
			</div>
		</div>
	</div>
	-->

	<!-- Results Summary -->
	<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
				{#if isRefreshing}
					<svg class="animate-spin h-4 w-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					<span>Refreshing results...</span>
				{:else}
					<span>
						{$i18n.t('Showing')} {((currentPage - 1) * itemsPerPage) + 1}-{Math.min(currentPage * itemsPerPage, sortedFlights.length)} 
						{$i18n.t('of')} {sortedFlights.length} {$i18n.t('flights')}
					</span>
				{/if}
			</div>
			<div class="text-sm text-gray-600 dark:text-gray-400">
				{$i18n.t('Page')} {currentPage} {$i18n.t('of')} {totalPages}
			</div>
		</div>
	</div>

	<!-- Table -->
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
			<thead class="bg-gray-50 dark:bg-gray-700">
				<tr>
					<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
						<input
							type="checkbox"
							class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
							checked={paginatedFlights.length > 0 && paginatedFlights.every(flight => selectedFlights.has(flight.id))}
							on:change={onToggleSelectAll}
						/>
					</th>
					<th 
						class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
						on:click={() => handleSort('airline')}
					>
						<div class="flex items-center gap-1">
							{$i18n.t('Airline')}
							<span class="text-xs">{getSortIcon('airline')}</span>
						</div>
					</th>
					<th 
						class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
						on:click={() => handleSort('startingPlace')}
					>
						<div class="flex items-center gap-1">
							{$i18n.t('From')}
							<span class="text-xs">{getSortIcon('startingPlace')}</span>
						</div>
					</th>
					<th 
						class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
						on:click={() => handleSort('destination')}
					>
						<div class="flex items-center gap-1">
							{$i18n.t('To')}
							<span class="text-xs">{getSortIcon('destination')}</span>
						</div>
					</th>
					<th 
						class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
						on:click={() => handleSort('cost')}
					>
						<div class="flex items-center gap-1">
							{$i18n.t('Price')}
							<span class="text-xs">{getSortIcon('cost')}</span>
						</div>
					</th>
					<th 
						class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
						on:click={() => handleSort('seatClass')}
					>
						<div class="flex items-center gap-1">
							{$i18n.t('Class')}
							<span class="text-xs">{getSortIcon('seatClass')}</span>
						</div>
					</th>
					<th 
						class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
						on:click={() => handleSort('duration')}
					>
						<div class="flex items-center gap-1">
							{$i18n.t('Duration')}
							<span class="text-xs">{getSortIcon('duration')}</span>
						</div>
					</th>
					<th 
						class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
						on:click={() => handleSort('segments')}
					>
						<div class="flex items-center gap-1">
							{$i18n.t('Stops')}
							<span class="text-xs">{getSortIcon('segments')}</span>
						</div>
					</th>
				<th class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
					<span class="sr-only">{$i18n.t('Details')}</span>
				</th>
				</tr>
			</thead>
			<tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
				{#each paginatedFlights as flight (flight.id)}
					<tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
					<td class="px-4 py-4 whitespace-nowrap">
						<input
							type="checkbox"
							class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
							checked={selectedFlights.has(flight.id)}
							on:change={() => onToggleFlight(flight.id)}
						/>
					</td>
					<td class="px-4 py-4 whitespace-nowrap">
						<div class="flex items-center gap-3">
							{#if flight.airlineLogo}
								<img
									src={flight.airlineLogo}
									alt={`${flight.airline ?? 'Airline'} logo`}
									class="h-6 w-6 object-contain rounded-full border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900"
									loading="lazy"
								/>
							{/if}
							<div>
								<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
									{flight.airline}
								</div>
								{#if flight.airlineCode}
									<div class="text-xs text-gray-500 dark:text-gray-400">
										{flight.airlineCode}
									</div>
								{/if}
							</div>
						</div>
					</td>
						<td class="px-4 py-4 whitespace-nowrap">
							<div class="text-sm text-gray-900 dark:text-gray-100">
								{flight.startingPlace}
							</div>
							{#if flight.startingPlaceCode}
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{flight.startingPlaceCode}
								</div>
							{/if}
						</td>
						<td class="px-4 py-4 whitespace-nowrap">
							<div class="text-sm text-gray-900 dark:text-gray-100">
								{flight.destination}
							</div>
							{#if flight.destinationCode}
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{flight.destinationCode}
								</div>
							{/if}
						</td>
						<td class="px-4 py-4 whitespace-nowrap">
							<div class="text-sm font-semibold text-green-600 dark:text-green-400">
								{#if flight.displayPrice}
									{flight.displayPrice}
								{:else if flight.cost != null}
									{flight.currency || '$'}{flight.cost}
								{:else}
									—
								{/if}
							</div>
						</td>
						<td class="px-4 py-4 whitespace-nowrap">
							{#if flight.seatClass}
							<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {(flight.seatClass || '').toLowerCase() === 'business' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'}">
								{flight.seatClass}
							</span>
							{:else}
								<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
									{$i18n.t('N/A')}
								</span>
							{/if}
						</td>
						<td class="px-4 py-4 whitespace-nowrap">
							<div class="text-sm text-gray-900 dark:text-gray-100">
								{flight.duration || 'N/A'}
							</div>
						</td>
						<td class="px-4 py-4 whitespace-nowrap">
							<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {flight.segments > 1 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}">
								{flight.segments > 1 ? `${flight.segments - 1} stop${flight.segments > 2 ? 's' : ''}` : 'Direct'}
							</span>
						</td>
					<td class="px-4 py-4 whitespace-nowrap text-right">
						<button
							type="button"
							class="inline-flex items-center justify-center rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
							on:click={() => toggleRowExpansion(flight.id)}
							aria-expanded={expandedRows.has(flight.id)}
							aria-label={expandedRows.has(flight.id) ? $i18n.t('Hide details') : $i18n.t('Show details')}
						>
							<span class={`transform transition-transform ${expandedRows.has(flight.id) ? 'rotate-180' : ''}`}>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
								</svg>
							</span>
						</button>
					</td>
					</tr>
				{#if expandedRows.has(flight.id)}
					<tr class="bg-gray-50 dark:bg-gray-900/60">
					<td colspan="9" class="px-6 py-4">
					<div class="flex items-start justify-between gap-6">
						<div class="flex flex-col items-center justify-between text-gray-300 dark:text-gray-600 self-stretch ml-70">
							<span class="h-2 w-2 rounded-full bg-current transform translate-y-2"></span>
							<div class="w-px flex-1 border-l border-dashed border-current"></div>
							<span class="h-2 w-2 rounded-full bg-current transform -translate-y-2"></span>
						</div>
						<div class="flex flex-col items-start gap-6 flex-1">
								<div class="flex flex-col">
									<div class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
										{formatTimeDisplay(flight.departureTime)}
										{#if flight.departureAirportName}
											<span class="text-xs text-gray-500 dark:text-gray-400">{flight.departureAirportName}</span>
										{/if}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">
										{formatDateDisplay(flight.departureLocalDate) ?? '—'}
									</div>
								</div>
								<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
									路程時間：{flight.totalDurationLabel}
								</div>
								<div class="flex flex-col">
									<div class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
										{formatTimeDisplay(flight.arrivalTime)}
										{#if flight.arrivalAirportName}
											<span class="text-xs text-gray-500 dark:text-gray-400">{flight.arrivalAirportName}</span>
										{/if}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">
										{formatDateDisplay(flight.arrivalLocalDate) ?? '—'}
									</div>
								</div>
							</div>
						<div class="flex flex-col items-start text-sm text-gray-600 dark:text-gray-300 min-w-[200px]">
							<div class="flex flex-col gap-3">
								{#if flight.flightNumber}
									<div class="flex items-center gap-3">
										<div class="flex items-center justify-center w-6 h-6">
											<img src="/flight.png" alt="Flight number" class="w-6 h-6 object-contain" loading="lazy" />
										</div>
										<span>{flight.flightNumber}</span>
									</div>
								{/if}
								{#if flight.seatClass}
									<div class="flex items-center gap-3">
										<div class="flex items-center justify-center w-6 h-6">
											<img src="/seat.png" alt="Travel class" class="w-6 h-6 object-contain" loading="lazy" />
										</div>
										<span>{flight.seatClass}</span>
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

	<!-- Pagination -->
	{#if totalPages > 1}
		<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<button
						class="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
						disabled={currentPage === 1}
						on:click={() => handlePageChange(currentPage - 1)}
					>
						{$i18n.t('Previous')}
					</button>
					
					{#each Array.from({length: Math.min(5, totalPages)}, (_, i) => {
						const start = Math.max(1, currentPage - 2);
						return start + i;
					}).filter(page => page <= totalPages) as page}
						<button
							class="px-3 py-2 text-sm font-medium rounded-lg {page === currentPage ? 'bg-blue-600 text-white' : 'text-gray-500 bg-white border border-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700'}"
							on:click={() => handlePageChange(page)}
						>
							{page}
						</button>
					{/each}
					
					<button
						class="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
						disabled={currentPage === totalPages}
						on:click={() => handlePageChange(currentPage + 1)}
					>
						{$i18n.t('Next')}
					</button>
				</div>
				
				<div class="text-sm text-gray-600 dark:text-gray-400">
					{$i18n.t('Go to page')}:
					<input
						type="number"
						min="1"
						max={totalPages}
						class="ml-2 w-16 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
						bind:value={currentPage}
						on:change={() => handlePageChange(currentPage)}
					/>
				</div>
			</div>
		</div>
	{/if}

</div>

<!-- Selected Flights Section -->
{#if selectedFlights.size > 0}
	<div class="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
				{$i18n.t('Selected Flights')} ({selectedFlights.size})
			</h3>
		</div>
		
		<div class="p-6 space-y-4">
			{#each selectedFlightObjects as flight (flight.id)}
				<div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
					<div class="flex-1 grid grid-cols-1 md:grid-cols-5 gap-4">
						<div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Airline')}</div>
							<div class="font-medium text-gray-900 dark:text-gray-100">{flight.airline}</div>
							{#if flight.airlineCode}
								<div class="text-xs text-gray-500 dark:text-gray-400">{flight.airlineCode}</div>
							{/if}
						</div>
						<div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Route')}</div>
							<div class="text-sm text-gray-900 dark:text-gray-100">
								{flight.startingPlace} → {flight.destination}
							</div>
						</div>
						<div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Price')}</div>
							<div class="font-semibold text-green-600 dark:text-green-400">
								{#if flight.displayPrice}
									{flight.displayPrice}
								{:else if flight.cost != null}
									{flight.currency || '$'}{flight.cost}
								{:else}
									—
								{/if}
							</div>
						</div>
						<div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Departure')}</div>
					<div class="text-sm text-gray-900 dark:text-gray-100">
						{formatDateTimeInline(flight.departureDateTimeLabel, flight.departureLocalDate, flight.departureTime)}
					</div>
						</div>
						<div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Duration')}</div>
							<div class="text-sm text-gray-900 dark:text-gray-100">
								{flight.duration || 'N/A'}
							</div>
						</div>
					</div>
					<button
						class="ml-4 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
						on:click={() => onToggleFlight(flight.id)}
						aria-label="Remove flight"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				</div>
			{/each}
		</div>
		
		<!-- AI Model Selection and Post Button -->
		<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
			<div class="flex flex-col gap-4">
				<!-- AI Model Selection -->
				<div class="flex items-center gap-4 flex-wrap">
					<!-- Combined AI Model Dropdown -->
					<div class="flex flex-col flex-1 min-w-[250px]">
						<label for="ai-model-select" class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							AI Model
						</label>
						<select
							id="ai-model-select"
							class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
							on:change={handleAIModelChange}
							disabled={isPosting}
							value={currentSelectedValue}
						>
						<option value="">Select AI Model...</option>
						{#each aiModelOptions as option}
							<option value={option.value}>{option.label}</option>
						{/each}
						</select>
					</div>
					
					<!-- Selected Model Info -->
					{#if selectedModel}
						<div class="flex flex-col flex-1 min-w-[250px]">
							<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Selected Model
							</div>
							<div class="px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm">
								<span class="text-gray-600 dark:text-gray-300">Model: <strong>{selectedModel.name || selectedModel.id}</strong></span>
								{#if selectedModel.owned_by && selectedModel.owned_by !== 'ollama'}
									<br><span class="text-indigo-600 dark:text-indigo-400">Provider: <strong>{selectedModel.owned_by}</strong></span>
								{/if}
							</div>
						</div>
					{/if}
				</div>
				
				<!-- Post Button -->
				<div class="flex justify-end">
					<button
						class="bg-black hover:bg-gray-800 text-white font-medium py-3 px-8 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
						disabled={isPosting || !selectedModel}
						on:click={onPost}
					>
						{#if isPosting}
							<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							{#if aiStage === 'initializing'}
								Initializing AI Analysis...
							{:else if aiStage === 'stage1'}
								Stage 1: Large Model Analysis...
							{:else if aiStage === 'generating_scenic_image'}
								Generating Scenic Image...
							{:else}
								Stage 2: Content Refinement...
							{/if}
						{:else}
							<svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h18v18h-18z M8 8h8v8h-8z M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0 M16 7a1 1 0 1 0 0-2a1 1 0 1 0 0 2"></path>
							</svg>
							{$i18n.t('Post')} ({selectedFlights.size})
						{/if}
					</button>
				</div>
				
				<!-- Selection info -->
				{#if selectedModel}
					<div class="text-sm text-gray-600 dark:text-gray-400">
						Using model: <span class="font-medium">{selectedModel.name || selectedModel.id}</span>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
