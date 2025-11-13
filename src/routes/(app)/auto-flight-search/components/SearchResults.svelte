<script>
import { createEventDispatcher } from 'svelte';
import PriceLineChart from './PriceLineChart.svelte';

	const dispatch = createEventDispatcher();

	export let selectedSearch = null;
	export let selectedFlights = [];
	export let selectedFlightKeys = new Set();
	export let hoveredBar = null;
	export let filteredModels = [];
	export let selectedModel = null;
	export let loadingSearches = new Set();

// Airline tabs (group results by airline)
let selectedAirline = null;
$: airlineGroups = selectedSearch && selectedSearch.results
    ? selectedSearch.results.reduce((acc, f) => {
        const key = f.airline || f.airlineCode || 'Unknown';
        (acc[key] ||= []).push(f);
        return acc;
      }, {})
    : {};
$: airlineList = Object.keys(airlineGroups);
$: airlineListWithAll = ['All', ...airlineList];
$: selectedAirline = selectedAirline || (airlineListWithAll[0] || null);
	
	// Filter flights by selected airline
$: currentFlights = selectedAirline && selectedAirline !== 'All' ? (airlineGroups[selectedAirline] || []) : [];
	
	// Build price grid from flights (cheapest for each departure/return date pair)
	function buildPriceGrid(flights) {
		if (!flights || flights.length === 0) return null;
		const depSet = new Set();
		const retSet = new Set();
		const cells = {};
		let cheapest = Infinity;
		
		for (const f of flights) {
			const dep = f.departureDate;
			const ret = f.returnDate || f.arrivalDate;
			if (!dep || !ret) continue;
			depSet.add(dep);
			retSet.add(ret);
			const key = `${dep}_${ret}`;
			const price = Number(f.cost || f.price || 0);
			if (!cells[key] || price < cells[key].price) {
				cells[key] = { price, flight: f };
			}
			if (price > 0 && price < cheapest) cheapest = price;
		}
		
		const departureDates = Array.from(depSet).sort();
		const returnDates = Array.from(retSet).sort();
		return {
			departureDates,
			returnDates,
			cells,
			cheapestPrice: isFinite(cheapest) ? cheapest : null
		};
	}
	
	// Build chart data (cheapest per day)
	function buildChartData(flights) {
		if (!flights || flights.length === 0) return [];
		const byDay = new Map();
		for (const f of flights) {
			const day = f.departureDate;
			if (!day) continue;
			const price = Number(f.cost || f.price || 0);
			const prev = byDay.get(day);
			if (!prev || price < prev.price) {
				byDay.set(day, { date: day, price, flight: f });
			}
		}
		return Array.from(byDay.values()).sort((a, b) => a.date.localeCompare(b.date));
	}
	
	$: currentPriceGrid = buildPriceGrid(currentFlights);
	$: currentChartData = buildChartData(currentFlights);

// Aggregate series for "All" tab (cheapest per day per airline)
$: allAirlineSeries = Object.entries(airlineGroups).map(([airline, flights]) => ({
    airline,
    data: buildChartData(flights)
}));
$: allDates = Array.from(new Set(allAirlineSeries.flatMap(s => s.data.map(d => d.date)))).sort();

function colorForIndex(index) {
    const palette = [
        '#2563eb', // blue-600
        '#16a34a', // green-600
        '#dc2626', // red-600
        '#7c3aed', // purple-600
        '#ca8a04', // yellow-600
        '#0891b2', // cyan-600
        '#ea580c', // orange-600
        '#0ea5e9', // sky-500
        '#f43f5e', // rose-500
        '#10b981'  // emerald-500
    ];
    return palette[index % palette.length];
}

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

// Price series controls
let selectedPriceAirlineCode = null;
let selectedPriceLeg = 'departure';
$: priceSeries =
	selectedSearch?.autoSearchResponse?.prices && Array.isArray(selectedSearch.autoSearchResponse.prices)
		? selectedSearch.autoSearchResponse.prices
		: [];
$: priceAirlineList = (() => {
	const map = new Map();
	if (selectedSearch?.autoSearchResponse?.airlines) {
		for (const airline of selectedSearch.autoSearchResponse.airlines) {
			const code = airline?.code ?? airline?.airline_id ?? 'UNKNOWN';
			const name = airline?.name ?? airline?.code ?? 'Unknown Airline';
			if (!map.has(code)) {
				map.set(code, {
					code,
					name,
					departure: null,
					return: null,
					extra: [],
				});
			}
		}
	}
	for (const series of priceSeries) {
		const code = series.airline_code ?? series.airline_name ?? series.airline_id ?? 'UNKNOWN';
		let group = map.get(code);
		if (!group) {
			group = {
				code,
				name: series.airline_name ?? series.airline_code ?? 'Unknown Airline',
				departure: null,
				return: null,
				extra: [],
			};
			map.set(code, group);
		}
		const direction =
			series.direction === 'return'
				? 'return'
				: series.direction === 'departure'
				? 'departure'
				: null;
		if (direction === 'return') {
			group.return = group.return ?? series;
		} else if (direction === 'departure') {
			group.departure = group.departure ?? series;
		} else if (!group.departure) {
			group.departure = series;
		} else if (!group.return) {
			group.return = series;
		} else {
			group.extra.push(series);
		}
	}
	return Array.from(map.values());
})();
$: {
	if (!selectedSearch || priceAirlineList.length === 0) {
		selectedPriceAirlineCode = null;
		selectedPriceLeg = 'departure';
	} else {
		const codes = priceAirlineList.map((item) => item.code);
		if (!selectedPriceAirlineCode || !codes.includes(selectedPriceAirlineCode)) {
			selectedPriceAirlineCode = codes[0];
		}
	}
}
$: selectedAirlineGroup =
	priceAirlineList.find((group) => group.code === selectedPriceAirlineCode) ?? null;
$: availableLegs = (() => {
	if (!selectedAirlineGroup) return [];
	const legs = [];
	if (selectedAirlineGroup.departure) legs.push('departure');
	if (selectedAirlineGroup.return) legs.push('return');
	if (legs.length === 0 && selectedAirlineGroup.extra.length > 0) legs.push('departure');
	return legs;
})();
$: {
	if (!availableLegs.includes(selectedPriceLeg)) {
		selectedPriceLeg = availableLegs[0] ?? 'departure';
	}
}
$: selectedSeries = (() => {
	if (!selectedAirlineGroup) return null;
	if (selectedPriceLeg === 'return') {
		return selectedAirlineGroup.return ?? selectedAirlineGroup.departure ?? selectedAirlineGroup.extra[0] ?? null;
	}
	return selectedAirlineGroup.departure ?? selectedAirlineGroup.return ?? selectedAirlineGroup.extra[0] ?? null;
})();
$: selectedSeriesLabel = selectedSeries
	? `${selectedSeries.airline_name ?? selectedSeries.airline_code ?? 'Unknown Airline'}${
			selectedSeries.route_from && selectedSeries.route_to
				? ` • ${selectedSeries.route_from} → ${selectedSeries.route_to}`
				: ''
	  }`
	: null;

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
		{#if selectedSearch && loadingSearches.has(selectedSearch.id)}
			<!-- Loading Screen (only covers the results box) -->
			<div class="text-center py-12">
				<svg class="animate-spin mx-auto h-12 w-12 text-blue-500 mb-4" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<p class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
					Searching flights...
				</p>
			</div>
		{:else if selectedSearch && selectedSearch.results && selectedSearch.results.length > 0}
			<!-- Airline Tabs -->
			{#if airlineListWithAll && airlineListWithAll.length > 0}
				<div class="mb-4 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
					<div class="flex gap-2 w-max">
						{#each airlineListWithAll as airline}
							<button
								class="px-5 py-3 text-sm rounded-t-md border-b-2 transition-colors min-w-[140px] whitespace-nowrap {selectedAirline === airline ? 'border-black text-black dark:border-white dark:text-white' : 'border-transparent text-gray-600 hover:text-black dark:text-gray-300 dark:hover:text-white'}"
								on:click={() => selectedAirline = airline}
							>
								{airline}
							</button>
						{/each}
                    </div>
                </div>
            {/if}
			<!-- Grid and Chart Container (Vertical Layout) -->
			{#if selectedAirline === 'All'}
				<!-- Multi-line chart for all airlines -->
				{#if allAirlineSeries && allAirlineSeries.length > 0 && allDates.length > 0}
					{@const allMaxPrice = Math.max(...allAirlineSeries.flatMap(s => s.data.map(d => Number(d.price) || 0)))}
					{@const allMinPrice = Math.min(...allAirlineSeries.flatMap(s => s.data.map(d => Number(d.price) || 0)))}
					{@const yMaxAll = Math.max(Math.ceil(allMaxPrice * 1.4), 1)}
					{@const chartHeight = 250}
                    {@const stepX = 40}
					{@const chartWidth = allDates.length * stepX}
					{@const labelHeight = 80}

					<div class="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-4 mb-4">
						<h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">All Airlines — {allDates.length} days</h4>
                    <div class="relative overflow-x-auto bg-blue-50 dark:bg-gray-900 p-4 rounded-lg">
							<svg
								width="100%"
								height={chartHeight + labelHeight}
								viewBox={`0 0 ${chartWidth + 60} ${chartHeight + labelHeight}`}
                            class="w-full"
                            style={`min-width: ${chartWidth + 60}px;`}
                        >
								<!-- Axes grid -->
								<line x1="50" y1="0" x2={chartWidth + 50} y2="0" stroke="#e5e7eb" stroke-width="1" />
								<line x1="50" y1={chartHeight / 2} x2={chartWidth + 50} y2={chartHeight / 2} stroke="#e5e7eb" stroke-width="1" stroke-dasharray="4" />
								<line x1="50" y1={chartHeight} x2={chartWidth + 50} y2={chartHeight} stroke="#e5e7eb" stroke-width="1" />

								<!-- Y labels -->
								<text x="5" y="20" class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="start">${yMaxAll}</text>
								<text x="5" y={chartHeight / 2} class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="start">${Math.ceil(yMaxAll / 2)}</text>
								<text x="5" y={chartHeight - 10} class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="start">$0</text>

								<!-- X labels (dates) -->
								{#each allDates as dateStr, idx}
									{@const x = 50 + idx * stepX}
									{@const date = new Date(dateStr)}
									<text x={x} y={chartHeight + 20} class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="middle" transform={`rotate(-45 ${x} ${chartHeight + 20})`}>
										{date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
									</text>
								{/each}

								<!-- Lines per airline -->
								{#each allAirlineSeries as series, si}
									{@const color = colorForIndex(si)}
									{@const points = series.data
										.sort((a,b) => a.date.localeCompare(b.date))
										.map(d => {
											const idx = allDates.indexOf(d.date);
											const x = 50 + idx * stepX;
											const price = Number(d.price) || 0;
									const hRaw = (price / yMaxAll) * chartHeight;
											const h = isNaN(hRaw) || hRaw < 0 ? 0 : hRaw;
											const y = chartHeight - h;
											return `${x},${y}`;
										}).join(' ')}
									<polyline points={points} fill="none" stroke={color} stroke-width="2" />
								{/each}
							</svg>
						</div>

						<!-- Legend -->
						<div class="mt-3 flex flex-wrap gap-3">
							{#each allAirlineSeries as series, si}
								<div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300">
									<span class="inline-block w-3 h-3 rounded-sm" style={`background-color: ${colorForIndex(si)}`}></span>
									{series.airline}
								</div>
							{/each}
						</div>
					</div>
				{/if}
			{:else}
				<div class="space-y-6 mb-4">
				<!-- Price Grid Calendar -->
				{#if currentPriceGrid}
					<div class="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-4">
						<h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
							Price Calendar — {selectedAirline}
						</h4>
						<div class="overflow-x-auto">
							<table class="border-collapse w-full text-xs">
								<thead>
									<tr>
										<th class="border border-gray-300 dark:border-gray-600 px-2 py-1 bg-gray-50 dark:bg-gray-700 text-xs"></th>
										{#each currentPriceGrid.departureDates as depDate}
											<th class="border border-gray-300 dark:border-gray-600 px-2 py-1 bg-gray-50 dark:bg-gray-700 text-xs text-center">
												{new Date(depDate).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' })}
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each currentPriceGrid.returnDates as retDate}
										<tr>
											<td class="border border-gray-300 dark:border-gray-600 px-2 py-1 bg-gray-50 dark:bg-gray-700 text-xs text-center">
												{new Date(retDate).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' })}
											</td>
											{#each currentPriceGrid.departureDates as depDate}
												{@const key = `${depDate}_${retDate}`}
												{@const cell = currentPriceGrid.cells[key]}
												{@const isCheapest = cell && currentPriceGrid.cheapestPrice && (cell.price === currentPriceGrid.cheapestPrice)}
												{@const isHighPrice = cell && currentPriceGrid.cheapestPrice && (cell.price > currentPriceGrid.cheapestPrice * 2)}
												
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
				{#if currentChartData && currentChartData.length > 0}
				{@const maxPrice = Math.max(...currentChartData.map(d => Number(d.price) || 0))}
				{@const yMax = Math.max(Math.ceil(maxPrice * 1.4), 1)}
					{@const chartHeight = 250}
					{@const barWidth = 8}
					{@const barGap = 20}
					{@const chartWidth = currentChartData.length * (barWidth + barGap)}
					{@const labelHeight = 80}
					
					<div class="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-4">
						<h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
							Price Graph — {selectedAirline} ({currentChartData.length} days)
						</h4>
						
						<div class="relative overflow-x-auto bg-blue-50 dark:bg-gray-900 p-4 rounded-lg">
							<svg 
								width="100%" 
								height={chartHeight + labelHeight}
								viewBox="0 0 {chartWidth + 60} {chartHeight + labelHeight}"
								class="w-full"
								style="min-width: {chartWidth + 60}px;"
							>
								<!-- Y-axis labels -->
					<text x="5" y="20" class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="start">${yMax}</text>
					<text x="5" y={chartHeight / 2} class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="start">${Math.ceil(yMax / 2)}</text>
								<text x="5" y={chartHeight - 10} class="text-xs fill-gray-600 dark:fill-gray-400" text-anchor="start">
									$0
								</text>
								
								<!-- Grid lines -->
								<line x1="50" y1="0" x2={chartWidth + 50} y2="0" stroke="#e5e7eb" stroke-width="1" />
								<line x1="50" y1={chartHeight / 2} x2={chartWidth + 50} y2={chartHeight / 2} stroke="#e5e7eb" stroke-width="1" stroke-dasharray="4" />
								<line x1="50" y1={chartHeight} x2={chartWidth + 50} y2={chartHeight} stroke="#e5e7eb" stroke-width="1" />
								
								<!-- Bars -->
								{#each currentChartData as data, i}
					{@const price = Number(data.price) || 0}
					{@const calculatedHeight = (price / yMax) * chartHeight}
									{@const barHeight = isNaN(calculatedHeight) || calculatedHeight < 0 ? 10 : Math.max(calculatedHeight, 10)}
									{@const x = 50 + i * (barWidth + barGap)}
									{@const y = isNaN(chartHeight - barHeight) ? chartHeight - 10 : Math.max(0, chartHeight - barHeight)}
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
									
									<!-- Date labels for each departure date -->
									{@const date = new Date(data.date)}
									{@const labelX = x + barWidth / 2}
									{@const labelY = chartHeight + 20}
									<text 
										x={labelX} 
										y={labelY} 
										class="text-xs fill-gray-600 dark:fill-gray-400"
										text-anchor="middle"
										transform={`rotate(-45 ${labelX} ${labelY})`}
									>
										{date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
									</text>
								{/each}
								
								<!-- Month labels (optional - dates are already shown) -->
							</svg>
						</div>
					</div>
				{/if}
			</div>
			{/if}
			
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
			{#if selectedSearch.autoSearchResponse}
				<div class="space-y-4">
					{#if priceSeries.length > 0}
						<div class="space-y-4">
							<div
								class="price-scroll flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 select-none cursor-grab active:cursor-grabbing scroller-hidden"
								on:mousedown={(event) => {
									const container = event.currentTarget;
									container.classList.add('dragging');
									let startX = event.pageX - container.offsetLeft;
									let scrollLeft = container.scrollLeft;
									let isDown = true;

									const handleMouseMove = (moveEvent) => {
										if (!isDown) return;
										moveEvent.preventDefault();
										const x = moveEvent.pageX - container.offsetLeft;
										const walk = (x - startX) * 1.2;
										container.scrollLeft = scrollLeft - walk;
									};

									const handleMouseUp = () => {
										isDown = false;
										container.classList.remove('dragging');
										window.removeEventListener('mousemove', handleMouseMove);
										window.removeEventListener('mouseup', handleMouseUp);
									};

									window.addEventListener('mousemove', handleMouseMove);
									window.addEventListener('mouseup', handleMouseUp);
								}}
							>
								<div style="height: 0; width: 0;" class="hidden"></div>
								{#each priceAirlineList as group (group.code)}
									<button
										type="button"
										class="px-4 py-2 rounded-full text-sm border transition-colors whitespace-nowrap {
											group.departure || group.return
												? selectedPriceAirlineCode === group.code
													? 'bg-black text-white border-black dark:bg-white dark:text-black'
													: 'bg-white text-gray-700 border-gray-300 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
												: 'bg-gray-200 text-gray-400 border-gray-300 dark:bg-gray-700 dark:text-gray-500 dark:border-gray-600 cursor-not-allowed'
										}"
										on:click={() => {
											if (group.departure || group.return) {
												selectedPriceAirlineCode = group.code;
											}
										}}
										disabled={!group.departure && !group.return}
									>
										<span>{group.name}</span>
										{#if group.departure?.route_from && group.departure?.route_to && !group.return}
											<span class="ml-1 text-xs text-gray-500 dark:text-gray-300">
												{group.departure.route_from} → {group.departure.route_to}
											</span>
										{:else if group.return?.route_from && group.return?.route_to && !group.departure}
											<span class="ml-1 text-xs text-gray-500 dark:text-gray-300">
												{group.return.route_from} → {group.return.route_to}
											</span>
										{/if}
									</button>
								{/each}
							</div>

							<div class="border-b border-gray-200 dark:border-gray-700 flex text-sm">
								{#each ['departure', 'return'] as leg}
									{@const legAvailable =
										leg === 'departure'
											? !!selectedAirlineGroup?.departure
											: !!selectedAirlineGroup?.return}
									<button
										type="button"
										class="w-1/2 pb-2 transition-colors border-b-2 -mb-px {
											selectedPriceLeg === leg && legAvailable
												? 'border-black text-black dark:border-white dark:text-white'
												: 'border-transparent text-gray-500 hover:text-black dark:text-gray-400 dark:hover:text-white'
										} {legAvailable ? '' : 'opacity-50 cursor-not-allowed'}"
										on:click={() => {
											if (legAvailable) selectedPriceLeg = leg;
										}}
										disabled={!legAvailable}
									>
										{leg === 'departure' ? 'Departure' : 'Return'}
									</button>
								{/each}
							</div>

							{#if selectedSeries}
								<PriceLineChart {selectedSeries} series={selectedSeries} leg={selectedPriceLeg} />
							{:else}
								<div class="min-h-[140px] flex items-center justify-center bg-gray-50 dark:bg-gray-800 rounded-lg border border-dashed border-gray-300 dark:border-gray-700 text-sm text-gray-500 dark:text-gray-300">
									Select an available leg to view data.
								</div>
							{/if}
						</div>
					{/if}
					<div class="text-sm text-gray-600 dark:text-gray-300">
						Backend logging is enabled. Price storage and visualisations will be added soon.
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
						<p>No results yet. Click refresh to trigger an auto search.</p>
				{/if}
			</div>
			{/if}
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

<style>
	.price-scroll {
		scrollbar-width: none;
		-ms-overflow-style: none;
	}

	.price-scroll::-webkit-scrollbar {
		display: none;
	}

	.price-scroll.dragging {
		cursor: grabbing;
	}
</style>

