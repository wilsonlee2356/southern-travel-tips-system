<script>
	import { getContext } from 'svelte';
	import { fetchAdapters, fetchMergedModels } from '$lib/utils/adapterApi.js';
	import { models } from '$lib/stores';
	
	const i18n = getContext('i18n');
	
	// Props
	export let flights = [];
	export let selectedFlights = new Set();
	export let onToggleFlight = () => {};
	export let onToggleSelectAll = () => {};
	export let onPost = () => {};
	export let isPosting = false;
	export let aiStage = '';
	
	// Binding props for adapter selection
	export let selectedAdapter = null;
	export let selectedMergedModel = null;
	export let selectedRAGModel = null;
	export let selectedBaseModel = null;
	
	// Adapter selection state
	let availableAdapters = [];
	let availableMergedModels = [];
	let availableRAGModels = [];
	let isLoadingAdapters = false;
	let adapterError = '';
	
	// Load adapters and merged models when models store is available
	$: if ($models && typeof window !== 'undefined') {
		loadAdapters();
	}
	
	async function loadAdapters() {
		isLoadingAdapters = true;
		adapterError = '';
		
		try {
			// Load adapters, merged models, and standard OpenWebUI models (which now include RAG models)
			const [adaptersResult, mergedModelsResult] = await Promise.all([
				fetchAdapters(),
				fetchMergedModels()
			]);
			
			if (adaptersResult.success) {
				availableAdapters = adaptersResult.adapters;
			} else {
				console.warn('Failed to load adapters:', adaptersResult.error);
			}
			
			if (mergedModelsResult.success) {
				availableMergedModels = mergedModelsResult.mergedModels;
			} else {
				console.warn('Failed to load merged models:', mergedModelsResult.error);
			}
			
			// Load RAG models from standard OpenWebUI models (filter for RAG models)
			// RAG models are now registered as base models in OpenWebUI
			console.log('Available OpenWebUI models:', $models);
			const ragModelsFromOpenWebUI = $models?.filter(model => 
				model.id.includes('rag') && model.id.includes('ollama')
			) || [];
			
			console.log('Filtered RAG models from OpenWebUI:', ragModelsFromOpenWebUI);
			
			// Convert OpenWebUI model format to RAG model format
			availableRAGModels = ragModelsFromOpenWebUI.map(model => ({
				rag_model_name: model.id.replace('_ollama:latest', ''),
				adapter_name: model.name,
				ollama_model_name: model.id,
				base_model: 'qwen2.5:14b', // Default base model
				created_at: new Date().toISOString(), // Use current time as fallback
				status: 'ready_for_rag'
			}));
			
			console.log('Final availableRAGModels:', availableRAGModels);
			
		} catch (error) {
			console.error('Error loading AI models:', error);
			adapterError = 'Failed to load AI models';
		} finally {
			isLoadingAdapters = false;
		}
	}
	
	// Handle combined AI model selection change
	function handleAIModelChange(event) {
		const selectedValue = event.target.value;
		
		// Reset all selections first
		selectedAdapter = null;
		selectedMergedModel = null;
		selectedRAGModel = null;
		selectedBaseModel = null;
		
		if (!selectedValue) return;
		
		// Parse the selection type and value
		const [type, value] = selectedValue.split(':');
		
		switch (type) {
			case 'base':
				selectedBaseModel = value;
				// Always apply RAG if available
				if (availableRAGModels.length > 0) {
					// Use the first available RAG model for base model
					selectedRAGModel = availableRAGModels[0];
				}
				break;
				
			case 'adapter':
				// Select an adapter
				selectedAdapter = availableAdapters.find(adapter => adapter.export_id === value) || null;
				break;
				
			case 'rag':
				// Select an already-merged RAG model
				selectedRAGModel = availableRAGModels.find(ragModel => ragModel.rag_model_name === value) || null;
				break;
		}
	}
	
	// Legacy handlers (kept for compatibility but not used in UI)
	function handleBaseModelChange(event) {
		// This function is kept for compatibility but not used
	}
	
	function handleAdapterChange(event) {
		// This function is kept for compatibility but not used
	}
	
	function handleMergedModelChange(event) {
		// This function is kept for compatibility but not used
	}
	
	function handleRAGModelChange(event) {
		// This function is kept for compatibility but not used
	}
	
	// Combined AI model options - include base models, adapters, and RAG models
	$: aiModelOptions = [
		// Base model with RAG (if available)
		{ 
			value: 'base:qwen2.5:14b', 
			label: 'Qwen2.5 14B + RAG', 
			type: 'base_with_rag',
			hasRAG: availableRAGModels.length > 0
		},
		
		// Show available adapters
		...availableAdapters.map(adapter => ({
			value: `adapter:${adapter.export_id}`,
			label: `${adapter.adapter_name} (Adapter)`,
			type: 'adapter',
			hasRAG: false
		})),
		
		// Show RAG models that are already created
		...availableRAGModels.map(ragModel => ({
			value: `rag:${ragModel.rag_model_name}`,
			label: `${ragModel.adapter_name} + RAG (${new Date(ragModel.created_at).toLocaleString()})`,
			type: 'rag_model',
			ragModel: ragModel
		}))
	];
	
	// Get current selected value for the dropdown
	$: currentSelectedValue = selectedBaseModel ? `base:${selectedBaseModel}` :
		selectedAdapter ? `adapter:${selectedAdapter.export_id}` :
		selectedRAGModel ? `rag:${selectedRAGModel.rag_model_name}` : '';

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
	<div class="p-6 border-b border-gray-200 dark:border-gray-700">
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
		
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
			<!-- Airline Filter -->
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

			<!-- Price Range Filter -->
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

			<!-- Stops Filter -->
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

			<!-- Items Per Page -->
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
							checked={selectedFlights.size === paginatedFlights.length && paginatedFlights.length > 0}
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
						on:click={() => handleSort('departureDate')}
					>
						<div class="flex items-center gap-1">
							{$i18n.t('Departure')}
							<span class="text-xs">{getSortIcon('departureDate')}</span>
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
							<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
								{flight.airline}
							</div>
							{#if flight.airlineCode}
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{flight.airlineCode}
								</div>
							{/if}
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
								{flight.currency || '$'}{flight.cost}
							</div>
						</td>
						<td class="px-4 py-4 whitespace-nowrap">
							<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {flight.seatClass.toLowerCase() === 'business' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'}">
								{flight.seatClass}
							</span>
						</td>
						<td class="px-4 py-4 whitespace-nowrap">
							<div class="text-sm text-gray-900 dark:text-gray-100">
								{new Date(flight.departureDate).toLocaleDateString()}
							</div>
							{#if flight.departureTime}
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{flight.departureTime}
								</div>
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
					</tr>
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

	<!-- Post Button -->
	{#if selectedFlights.size > 0}
		<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between gap-4">
				<!-- AI Model Selection -->
				<div class="flex items-center gap-4">
					<!-- Combined AI Model Dropdown -->
					<div class="flex flex-col">
						<label for="ai-model-select" class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							AI Model
						</label>
						<select
							id="ai-model-select"
							class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[300px]"
							on:change={handleAIModelChange}
							disabled={isLoadingAdapters || isPosting}
							value={currentSelectedValue}
						>
							<option value="">Select AI Model...</option>
							{#each aiModelOptions as option}
								<option value={option.value}>{option.label}</option>
							{/each}
						</select>
					</div>
					
					<!-- Selected Model Info -->
					{#if currentSelectedValue}
						<div class="flex flex-col">
							<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Selected Model
							</div>
							<div class="px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm">
								{#if selectedBaseModel}
									<span class="text-gray-600 dark:text-gray-300">Base Model: <strong>{selectedBaseModel}</strong></span>
									{#if selectedRAGModel}
										<br><span class="text-blue-600 dark:text-blue-400">+ RAG: <strong>{selectedRAGModel.rag_model_name}</strong></span>
									{/if}
								{:else if selectedAdapter}
									<span class="text-purple-600 dark:text-purple-400">Adapter: <strong>{selectedAdapter.adapter_name}</strong></span>
									<br><span class="text-gray-500 dark:text-gray-400">Export ID: {selectedAdapter.export_id}</span>
								{:else if selectedRAGModel}
									<span class="text-green-600 dark:text-green-400">RAG Model: <strong>{selectedRAGModel.rag_model_name}</strong></span>
									<br><span class="text-blue-600 dark:text-blue-400">Base: {selectedRAGModel.base_model}</span>
								{/if}
							</div>
						</div>
					{/if}
					
					<!-- Loading indicator -->
					{#if isLoadingAdapters}
						<div class="flex items-center text-sm text-gray-500 dark:text-gray-400">
							<svg class="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							{$i18n.t('Loading models...')}
						</div>
					{/if}
					
					<!-- Error message -->
					{#if adapterError}
						<div class="text-sm text-red-600 dark:text-red-400">
							{adapterError}
						</div>
					{/if}
				</div>
				
				<!-- Post Button -->
				<button
					class="bg-black hover:bg-gray-800 text-white font-medium py-3 px-6 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={isPosting || (!selectedRAGModel && !selectedBaseModel && !selectedAdapter)}
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
			{#if selectedRAGModel || selectedBaseModel}
				<div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
					{#if selectedRAGModel}
						Using RAG model: <span class="font-medium">{selectedRAGModel.adapter_name} + RAG</span>
					{:else if selectedBaseModel}
						Using base model: <span class="font-medium">{selectedBaseModel}</span> with RAG
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>
