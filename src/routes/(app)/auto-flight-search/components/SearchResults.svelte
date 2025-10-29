<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let selectedSearch = null;
	export let selectedFlights = [];
	export let selectedFlightKeys = new Set();
	export let hoveredBar = null;
	export let filteredModels = [];
	export let selectedModel = null;
	export let loadingSearches = new Set();

	// Format date for grid display
	const formatGridDate = (dateString) => {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	};

	// Format date for tooltip
	const formatTooltipDate = (dateString) => {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	};

	const toggleSearch = () => {
		dispatch('toggleSearch', selectedSearch.id);
	};

	const handleCellClick = (depDate, retDate, cell) => {
		dispatch('cellClick', { depDate, retDate, cell });
	};

	const handleBarHover = (event, data, index) => {
		dispatch('barHover', { event, data, index });
	};

	const handleBarLeave = () => {
		dispatch('barLeave');
	};

	const removeSelectedFlight = (flightKey) => {
		dispatch('removeSelectedFlight', flightKey);
	};

	const handlePost = () => {
		dispatch('post', { flights: selectedFlights, model: selectedModel });
	};
</script>

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
			<!-- iOS-style Toggle Switch with Label -->
			<div class="flex items-center gap-2">
				<span class="text-sm text-gray-700 dark:text-gray-300">Enable</span>
				<button
					on:click={toggleSearch}
					class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none {
						selectedSearch.enabled 
							? 'bg-green-500' 
							: 'bg-gray-300 dark:bg-gray-600'
					}"
					role="switch"
					aria-checked={selectedSearch.enabled}
					title={selectedSearch.enabled ? 'Disable auto search' : 'Enable auto search'}
				>
					<span
						class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {
							selectedSearch.enabled ? 'translate-x-6' : 'translate-x-1'
						}"
					/>
				</button>
			</div>
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
						on:click={handlePost}
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

