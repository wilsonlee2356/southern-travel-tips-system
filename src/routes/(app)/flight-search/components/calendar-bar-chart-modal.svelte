<script>
	import { createEventDispatcher, onDestroy, onMount } from 'svelte';

	export let open = false;
	export let calendarData = null;
	export let tripLengthDays = null;

	const dispatch = createEventDispatcher();

	const portal = (node) => {
		if (typeof document === 'undefined') return;
		const target = document.body;
		if (!target) return;
		target.appendChild(node);
		return {
			destroy() {
				if (node.parentNode === target) {
					target.removeChild(node);
				}
			}
		};
	};

	const close = () => {
		dispatch('close');
	};

	const handleKeydown = (event) => {
		if (event.key === 'Escape') {
			close();
		}
	};

	onMount(() => {
		window.addEventListener('keydown', handleKeydown);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', handleKeydown);
	});

	const parseDate = (value) => {
		if (!value) return null;
		const parsed = new Date(value);
		if (Number.isNaN(parsed.getTime())) {
			return null;
		}
		parsed.setHours(0, 0, 0, 0);
		return parsed;
	};

	const formatISODate = (date) => {
		const year = date.getFullYear();
		const month = `${date.getMonth() + 1}`.padStart(2, '0');
		const day = `${date.getDate()}`.padStart(2, '0');
		return `${year}-${month}-${day}`;
	};

	const addDays = (date, days) => {
		const result = new Date(date);
		result.setDate(result.getDate() + days);
		return result;
	};

	const extractDepartureDate = (value) =>
		value?.departure ||
		value?.departure_date ||
		value?.outbound_date ||
		value?.outboundDate ||
		value?.departureDate ||
		value?.date ||
		null;

	const extractReturnDate = (value) =>
		value?.return ||
		value?.return_date ||
		value?.inbound_date ||
		value?.returnDate ||
		value?.inboundDate ||
		null;

	const extractPrice = (value) => {
		const rawPrice =
			value?.price ??
			value?.price_raw ??
			value?.lowest_price ??
			value?.amount ??
			value?.currency_price ??
			value?.price_value ??
			value?.priceValue;

		if (typeof rawPrice === 'number') {
			return Number.isFinite(rawPrice) ? rawPrice : null;
		}

		if (typeof rawPrice === 'string') {
			const parsed = parseFloat(rawPrice.replace(/[^\d.-]+/g, ''));
			return Number.isFinite(parsed) ? parsed : null;
		}

		return null;
	};

	const formatCurrency = (value) => {
		if (value == null || Number.isNaN(value)) {
			return '—';
		}
		const currency = calendarData?.search_parameters?.currency ?? 'HKD';
		try {
			return new Intl.NumberFormat('en-US', {
				style: 'currency',
				currency,
				maximumFractionDigits: value >= 1000 ? 0 : 2
			}).format(value);
		} catch (error) {
			console.warn('Failed to format currency', error);
			return `${currency} ${value}`;
		}
	};

	const formatRangeLabel = (departure, ret) => {
		const departureDate = parseDate(departure);
		const returnDate = parseDate(ret);
		if (!departureDate || !returnDate) {
			return `${departure} → ${ret}`;
		}
		try {
			const departureLabel = new Intl.DateTimeFormat('en-GB', {
				month: 'short',
				day: 'numeric'
			}).format(departureDate);
			const returnLabel = new Intl.DateTimeFormat('en-GB', {
				month: 'short',
				day: 'numeric'
			}).format(returnDate);
			return `${departureLabel} → ${returnLabel}`;
		} catch (error) {
			console.warn('Failed to format range label', error);
			return `${departure} → ${ret}`;
		}
	};

	// Detect if this is a one-way trip
	$: isOneWay = (() => {
		if (!calendarData) return false;
		// Check if tripLengthDays is null/undefined (one-way trips don't have trip length)
		if (tripLengthDays == null) return true;
		// Check if calendar data has entries without return dates
		if (Array.isArray(calendarData?.calendar)) {
			return calendarData.calendar.every(item => !extractReturnDate(item));
		}
		return false;
	})();

	const buildOneWayBarData = (data) => {
		if (!data || !Array.isArray(data?.calendar)) {
			return [];
		}

		const entryMap = new Map();

		for (const item of data.calendar) {
			const departure = extractDepartureDate(item);
			const price = extractPrice(item);

			if (!departure || price == null) continue;

			const departureKey = formatISODate(parseDate(departure));
			if (!departureKey) continue;

			// For one-way, use departure date as key
			if (!entryMap.has(departureKey) || price < entryMap.get(departureKey).price) {
				entryMap.set(departureKey, { price, raw: item });
			}
		}

		const bars = Array.from(entryMap.entries())
			.map(([departureKey, entry]) => {
				const departureDate = parseDate(departureKey);
				if (!departureDate) return null;
				return {
					departure: departureKey,
					return: null,
					price: entry.price,
					raw: entry.raw,
					label: formatShortDate(departureKey)
				};
			})
			.filter(Boolean)
			.sort((a, b) => {
				const dateA = parseDate(a.departure);
				const dateB = parseDate(b.departure);
				if (!dateA || !dateB) return 0;
				return dateA.getTime() - dateB.getTime();
			});

		return bars;
	};

	const buildBarData = (data, tripLength) => {
		// If one-way trip, use one-way builder
		if (isOneWay) {
			return buildOneWayBarData(data);
		}

		if (!data || !Array.isArray(data?.calendar) || !Number.isFinite(tripLength) || tripLength <= 0) {
			return [];
		}

		const entryMap = new Map();
		const departures = new Set();

		for (const item of data.calendar) {
			const departure = extractDepartureDate(item);
			const ret = extractReturnDate(item);
			const price = extractPrice(item);

			if (!departure || !ret || price == null) continue;

			const key = `${departure}|${ret}`;
			if (!entryMap.has(key) || price < entryMap.get(key).price) {
				entryMap.set(key, { price, raw: item });
			}

			departures.add(departure);
		}

		const sortedDepartures = Array.from(departures)
			.map((value) => parseDate(value))
			.filter(Boolean)
			.sort((a, b) => a.getTime() - b.getTime());

		const usedReturns = new Set();
		const bars = [];

		for (const departureDate of sortedDepartures) {
			const returnDate = addDays(departureDate, tripLength);
			const returnKey = formatISODate(returnDate);
			const departureKey = formatISODate(departureDate);
			const entry = entryMap.get(`${departureKey}|${returnKey}`);

			if (!entry) continue;
			if (usedReturns.has(returnKey)) continue;

			usedReturns.add(returnKey);
			bars.push({
				departure: departureKey,
				return: returnKey,
				price: entry.price,
				raw: entry.raw,
				label: formatRangeLabel(departureKey, returnKey)
			});
		}

		return bars;
	};

	let bars = [];
	let maxPrice = 0;
	let minPrice = 0;
let chartTicks = [];
let chartMaxValue = 0;
const CHART_HEIGHT = 280;
const AXIS_GAP = 72;
const TOP_GAP = 40;
const MIN_BAR_HEIGHT = 4;
let sortedTicks = [];

	const computeTickValues = (maxValue) => {
		if (!maxValue || !Number.isFinite(maxValue) || maxValue <= 0) {
			return [0, 1000, 2000, 3000];
		}

		const baseStep = Math.max(1000, Math.ceil(maxValue / 3 / 1000) * 1000);
		let topValue = baseStep * 3;

		while (topValue <= maxValue) {
			topValue += baseStep;
		}

		return [0, baseStep, baseStep * 2, topValue];
	};

	$: {
		if (open) {
			bars = buildBarData(calendarData, tripLengthDays);
			maxPrice = bars.reduce((max, bar) => (bar.price != null && bar.price > max ? bar.price : max), 0);
			minPrice = bars.reduce(
				(min, bar) => (bar.price != null && bar.price < min ? bar.price : min),
				Number.POSITIVE_INFINITY
			);
			if (!Number.isFinite(minPrice)) {
				minPrice = 0;
			}
			chartTicks = computeTickValues(maxPrice);
			// monthMarkers = computeMonthMarkers(bars);

			const searchParams = calendarData?.search_parameters ?? {};
			const searchDeparture = normalizeDateKey(extractSearchDeparture(searchParams));
			const searchReturn = normalizeDateKey(extractSearchReturn(searchParams));
			const searchKey = isOneWay 
				? searchDeparture 
				: (searchDeparture && searchReturn ? `${searchDeparture}|${searchReturn}` : null);

			if (searchKey !== lastSearchKey) {
				initialSelectionApplied = false;
				lastSearchKey = searchKey;
			}

			if (!initialSelectionApplied && searchKey) {
				const matchingBar = bars.find((bar) => getBarKey(bar) === searchKey);
				if (matchingBar) {
					selectedBarKey = searchKey;
					// Update tooltip position for initial selection
					setTimeout(() => {
						if (scrollContainer) {
							const barElement = scrollContainer.querySelector(`[data-bar-key="${searchKey}"]`);
							if (barElement) {
								updateSelectedTooltipPosition(matchingBar, barElement);
								selectedTooltipBar = matchingBar;
							}
						}
					}, 100);
				}
				initialSelectionApplied = true;
			} else if (selectedBarKey && !bars.some((bar) => getBarKey(bar) === selectedBarKey)) {
				selectedBarKey = null;
				selectedTooltipPosition.visible = false;
				selectedTooltipBar = null;
			}

			if (hoveredBarKey && !bars.some((bar) => getBarKey(bar) === hoveredBarKey)) {
				hoveredBarKey = null;
			}
		} else {
			bars = [];
			maxPrice = 0;
			minPrice = 0;
			chartTicks = [];
			selectedBarKey = null;
			hoveredBarKey = null;
			initialSelectionApplied = false;
			lastSearchKey = null;
			// monthMarkers = [];
		}
	}

$: chartMaxValue = chartTicks.length ? chartTicks[chartTicks.length - 1] : maxPrice;
$: sortedTicks = [...chartTicks].sort((a, b) => a - b);

const getBarHeight = (price) => {
	if (!sortedTicks.length || !chartMaxValue) return MIN_BAR_HEIGHT;
	const base = sortedTicks[0];
	const range = chartMaxValue - base;
	if (!Number.isFinite(price) || range <= 0) return MIN_BAR_HEIGHT;
	const normalized = (price - base) / range;
	if (normalized <= 0) {
		return 0;
	}
	const height = normalized * CHART_HEIGHT;
	return Math.min(CHART_HEIGHT, Math.max(height, MIN_BAR_HEIGHT));
};

const getTickPercent = (tick) => {
	if (!sortedTicks.length || !chartMaxValue) return 0;
	return ((tick - sortedTicks[0]) / (chartMaxValue - sortedTicks[0] || 1)) * 100;
};

const formatShortDate = (date) => {
	const parsed = parseDate(date);
	if (!parsed) return date;
	const month = parsed.getMonth() + 1;
	const day = parsed.getDate();
	const weekday = parsed.toLocaleDateString('zh-Hant', { weekday: 'short' });
	return `${month}月${day}日（${weekday}）`;
};

const formatMonthLabel = (date) => {
	const parsed = parseDate(date);
	return parsed ? `${parsed.getMonth() + 1}月` : '';
};

// const computeMonthMarkers = (barsData) => {
// 	if (!Array.isArray(barsData)) return [];
// 	const markers = [];
// 	const seenMonths = new Set();
//
// 	for (let index = 0; index < barsData.length; index += 1) {
// 		const bar = barsData[index];
// 		const parsed = parseDate(bar?.departure);
// 		if (!parsed) continue;
//
// 		const monthKey = `${parsed.getFullYear()}-${parsed.getMonth()}`;
// 		if (seenMonths.has(monthKey)) continue;
//
// 		seenMonths.add(monthKey);
// 		const label = `${parsed.getMonth() + 1}月`;
// 		markers.push({ label, index });
// 	}
//
// 	return markers;
// };

const formatShortDateRange = (start, end) => {
	const startDate = parseDate(start);
	const endDate = parseDate(end);
	if (!startDate || !endDate) return `${start} → ${end}`;
	return `${formatShortDate(start)} → ${formatShortDate(end)}`;
};

	const chartTooltip = (bar) => {
		const durationLabel = tripLengthDays === 1 ? '1 day' : `${tripLengthDays} days`;
		return `${durationLabel}\n${formatRangeLabel(bar.departure, bar.return)}\n${formatCurrency(bar.price)}`;
	};

const getBarKey = (bar) => {
	if (isOneWay) {
		return bar?.departure || '';
	}
	return `${bar?.departure}|${bar?.return}`;
};

let selectedBarKey = null;
let hoveredBarKey = null;
let initialSelectionApplied = false;
let lastSearchKey = null;
let selectedTooltipPosition = { x: 0, y: 0, visible: false };
let selectedTooltipBar = null;
let hoveredTooltipPosition = { x: 0, y: 0, visible: false };
let hoveredTooltipBar = null;
// let monthMarkers = [];

const extractSearchDeparture = (params) =>
	params?.departureDate ??
	params?.departure_date ??
	params?.outbound_date ??
	params?.outboundDate ??
	params?.departure ??
	null;

const extractSearchReturn = (params) =>
	params?.returnDate ??
	params?.return_date ??
	params?.inbound_date ??
	params?.inboundDate ??
	params?.return ??
	null;

const normalizeDateKey = (value) => {
	const parsed = parseDate(value);
	return parsed ? formatISODate(parsed) : null;
};

const isTooltipActive = (bar) => {
	const key = getBarKey(bar);
	return Boolean(key) && (key === selectedBarKey || key === hoveredBarKey);
};

const getTooltipZIndex = (bar) => {
	const key = getBarKey(bar);
	if (!key) return 100;
	if (hoveredBarKey === key) return 400;
	if (selectedBarKey === key) return 300;
	return 200;
};

const handleBarClick = (bar, event) => {
	const key = getBarKey(bar);
	if (!key) return;
	const wasSelected = selectedBarKey === key;
	selectedBarKey = wasSelected ? null : key;
	
	if (selectedBarKey && event?.currentTarget) {
		// Immediately update position when clicked
		updateSelectedTooltipPosition(bar, event.currentTarget);
		selectedTooltipBar = bar;
	} else {
		// Hide selected tooltip when deselected
		selectedTooltipPosition.visible = false;
		selectedTooltipBar = null;
	}
};

const updateSelectedTooltipPosition = (bar, element) => {
	if (!element) {
		selectedTooltipPosition.visible = false;
		return;
	}
	const rect = element.getBoundingClientRect();
	selectedTooltipPosition = {
		x: rect.left + rect.width / 2,
		y: rect.top - 24,
		visible: true
	};
	selectedTooltipBar = bar;
};

const updateHoveredTooltipPosition = (bar, element) => {
	if (!element) {
		hoveredTooltipPosition.visible = false;
		return;
	}
	const rect = element.getBoundingClientRect();
	hoveredTooltipPosition = {
		x: rect.left + rect.width / 2,
		y: rect.top - 24,
		visible: true
	};
	hoveredTooltipBar = bar;
};

const handleBarMouseEnter = (bar, event) => {
	hoveredBarKey = getBarKey(bar);
	if (event?.currentTarget) {
		updateHoveredTooltipPosition(bar, event.currentTarget);
		hoveredTooltipBar = bar;
	}
};

const handleBarMouseLeave = (bar) => {
	if (hoveredBarKey === getBarKey(bar)) {
		hoveredBarKey = null;
		hoveredTooltipPosition.visible = false;
		hoveredTooltipBar = null;
	}
};

const handleBarKeydown = (event, bar) => {
	if (event.key === 'Enter' || event.key === ' ') {
		event.preventDefault();
		handleBarClick(bar, event);
	}
};

// Update tooltip position on scroll
let scrollContainer = null;
const handleScroll = () => {
	// Update selected tooltip position
	if (selectedBarKey && scrollContainer && selectedTooltipBar) {
		const barElement = scrollContainer.querySelector(`[data-bar-key="${selectedBarKey}"]`);
		if (barElement) {
			updateSelectedTooltipPosition(selectedTooltipBar, barElement);
		}
	}
	// Update hovered tooltip position
	if (hoveredBarKey && scrollContainer && hoveredTooltipBar) {
		const barElement = scrollContainer.querySelector(`[data-bar-key="${hoveredBarKey}"]`);
		if (barElement) {
			updateHoveredTooltipPosition(hoveredTooltipBar, barElement);
		}
	}
};

// Update selected tooltip position when selectedBarKey changes
$: {
	if (selectedBarKey && scrollContainer && bars.length > 0) {
		// Use setTimeout to ensure DOM is updated
		setTimeout(() => {
			const barElement = scrollContainer?.querySelector(`[data-bar-key="${selectedBarKey}"]`);
			if (barElement) {
				const selectedBar = bars.find(bar => getBarKey(bar) === selectedBarKey);
				if (selectedBar) {
					updateSelectedTooltipPosition(selectedBar, barElement);
					selectedTooltipBar = selectedBar;
				}
			}
		}, 0);
	} else if (!selectedBarKey) {
		// Hide selected tooltip if no bar is selected
		selectedTooltipPosition.visible = false;
		selectedTooltipBar = null;
	}
}
</script>

{#if open}
	<div use:portal class="fixed inset-0 z-[1500] flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
		<button
			type="button"
			class="absolute inset-0 z-[1510] w-full h-full bg-transparent cursor-default"
			aria-label="Close price trend chart"
			on:click={close}
		></button>
		<div
			class="relative z-[1520] w-full max-w-4xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-visible"
			on:pointerdown|stopPropagation
		>
			<header class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						Flight Price Trend
					</h2>
					{#if isOneWay}
						<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
							One-way flights based on Google Flights calendar data
						</p>
					{:else if tripLengthDays != null}
						<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
							{tripLengthDays === 1 ? '1-day' : `${tripLengthDays}-day`} itineraries based on Google Flights calendar data
						</p>
					{/if}
				</div>
				<button
					type="button"
					class="inline-flex items-center justify-center w-9 h-9 rounded-full text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500"
					on:click={close}
					aria-label="Close"
				>
					<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<line x1="18" y1="6" x2="6" y2="18"></line>
						<line x1="6" y1="6" x2="18" y2="18"></line>
					</svg>
				</button>
			</header>

			<section class="px-6 py-4">
				{#if bars.length === 0}
					<div class="py-20 text-center text-sm text-gray-500 dark:text-gray-400">
						No matching itinerary combinations were found for this trip length.
					</div>
				{:else}
					<div class="flex flex-col gap-3">
						<div class="flex justify-between items-center">
							<div class="text-sm text-gray-600 dark:text-gray-400">
								Showing {bars.length} itineraries • Prices in {calendarData?.search_parameters?.currency ?? 'HKD'}
							</div>
							{#if maxPrice}
								<div class="text-sm text-gray-600 dark:text-gray-400">
									Highest price: <span class="font-semibold text-gray-900 dark:text-gray-200">{formatCurrency(maxPrice)}</span>
								</div>
							{/if}
						</div>

						<div class="space-y-4">
							<div class="flex gap-4 items-end">
								<div
									class="hidden sm:flex flex-col justify-between text-xs text-gray-500 dark:text-gray-400 pr-6 relative z-0"
									style={`height: ${CHART_HEIGHT + AXIS_GAP + TOP_GAP}px; padding: ${TOP_GAP}px 0 ${AXIS_GAP}px`}
								>
									{#each [...sortedTicks].reverse() as tick}
										<div class="flex items-center gap-3">
											<span class="w-16 text-right font-medium">{formatCurrency(tick)}</span>
											<div class="flex-1 h-px border-dashed border-gray-300 dark:border-gray-700"></div>
										</div>
									{/each}
								</div>
								<div
									class="flex sm:hidden flex-col relative z-0"
									style={`height: ${CHART_HEIGHT + AXIS_GAP + TOP_GAP}px; padding: ${TOP_GAP}px 0 ${AXIS_GAP}px`}
								>
									<div class="flex flex-col justify-between text-xs text-gray-500 dark:text-gray-400 h-full">
										{#each [...sortedTicks].reverse() as tick}
											<span class="font-medium">{formatCurrency(tick)}</span>
										{/each}
									</div>
								</div>
								<div
									bind:this={scrollContainer}
									class="relative z-10 flex-1 overflow-visible"
									style={`height: ${CHART_HEIGHT + AXIS_GAP + TOP_GAP}px; overflow-x: auto; overflow-y: visible;`}
									on:scroll={handleScroll}
								>
									<div
										class="pointer-events-none absolute inset-x-0"
										style={`top: ${TOP_GAP}px; bottom: ${AXIS_GAP}px`}
									>
										{#each sortedTicks as tick}
											<div
												class="absolute left-0 right-0 border-t ${tick === 0 ? 'border-gray-300 dark:border-gray-600' : 'border-dashed border-gray-200 dark:border-gray-700'}"
												style={`bottom: ${getTickPercent(tick)}%`}
											></div>
										{/each}
									</div>
									<div
										class="absolute inset-x-0 flex items-end gap-2"
										class:gap-1={isOneWay}
										class:gap-2={!isOneWay}
										style={`top: ${TOP_GAP}px; height: ${CHART_HEIGHT}px`}
									>
										{#each bars as bar (getBarKey(bar))}
											<div
												data-bar-key={getBarKey(bar)}
												class="flex flex-none flex-col items-center gap-2 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/70"
												style={`width: ${isOneWay ? '24px' : '28px'};`}
												on:mouseenter={(e) => handleBarMouseEnter(bar, e)}
												on:mouseleave={() => handleBarMouseLeave(bar)}
												on:click={(event) => {
													event.stopPropagation();
													handleBarClick(bar, event);
												}}
												on:keydown={(event) => handleBarKeydown(event, bar)}
												role="button"
												tabindex="0"
												aria-pressed={selectedBarKey === getBarKey(bar) ? 'true' : 'false'}
											>
												<div class="relative w-full h-full rounded-t-xl bg-gradient-to-b from-white via-gray-50 to-gray-100 dark:from-gray-900 dark:via-gray-850 dark:to-gray-800 shadow-inner flex items-end">
													<div
														class={`w-full rounded-t-lg transition-all duration-300 bg-blue-500 dark:bg-blue-400 ${
															selectedBarKey === getBarKey(bar) ? 'ring-2 ring-blue-500/70 ring-offset-2 ring-offset-transparent' : ''
														}`}
														style={`height: ${getBarHeight(bar.price)}px`}
													></div>
												</div>
											</div>
										{/each}
									</div>
									<div class="absolute inset-x-0 bottom-0" style={`height: ${AXIS_GAP}px`}></div>
								</div>
							</div>

							<div class="flex flex-wrap items-center gap-4 text-xs text-gray-500 dark:text-gray-400"></div>
						</div>
					</div>
				{/if}
			</section>
		</div>
	</div>
{/if}

<!-- Selected bar tooltip (fixed/persistent) -->
{#if selectedTooltipPosition.visible && selectedTooltipBar}
	<div
		class="pointer-events-none fixed flex flex-col items-center gap-1"
		style={`z-index: 10001; left: ${selectedTooltipPosition.x}px; top: ${selectedTooltipPosition.y}px; transform: translate(-50%, -100%);`}
	>
		<div class="rounded-lg bg-gray-900 px-3 py-2 text-xs text-white shadow-lg dark:bg-gray-700 flex flex-col gap-2 min-w-[180px] border-2 border-blue-500">
			{#if !isOneWay}
				<div class="flex items-center justify-between text-[11px] tracking-wide opacity-80">
					<span class="font-semibold">行程時長</span>
					<span>{tripLengthDays === 1 ? '1 天' : `${tripLengthDays} 天`}</span>
				</div>
			{/if}
			<div class="flex items-center justify-between gap-3">
				<div class="font-semibold whitespace-nowrap">{formatCurrency(selectedTooltipBar.price)} 起</div>
				<div class="opacity-80 whitespace-nowrap">
					{#if isOneWay}
						{formatShortDate(selectedTooltipBar.departure)}
					{:else}
						{formatShortDateRange(selectedTooltipBar.departure, selectedTooltipBar.return)}
					{/if}
				</div>
			</div>
		</div>
		<div class="h-2 w-2 rotate-45 bg-gray-900 dark:bg-gray-700"></div>
	</div>
{/if}

<!-- Hovered bar tooltip (temporary) -->
{#if hoveredTooltipPosition.visible && hoveredTooltipBar && hoveredBarKey !== selectedBarKey}
	<div
		class="pointer-events-none fixed flex flex-col items-center gap-1"
		style={`z-index: 10002; left: ${hoveredTooltipPosition.x}px; top: ${hoveredTooltipPosition.y}px; transform: translate(-50%, -100%);`}
	>
		<div class="rounded-lg bg-gray-900 px-3 py-2 text-xs text-white shadow-lg dark:bg-gray-700 flex flex-col gap-2 min-w-[180px]">
			{#if !isOneWay}
				<div class="flex items-center justify-between text-[11px] tracking-wide opacity-80">
					<span class="font-semibold">行程時長</span>
					<span>{tripLengthDays === 1 ? '1 天' : `${tripLengthDays} 天`}</span>
				</div>
			{/if}
			<div class="flex items-center justify-between gap-3">
				<div class="font-semibold whitespace-nowrap">{formatCurrency(hoveredTooltipBar.price)} 起</div>
				<div class="opacity-80 whitespace-nowrap">
					{#if isOneWay}
						{formatShortDate(hoveredTooltipBar.departure)}
					{:else}
						{formatShortDateRange(hoveredTooltipBar.departure, hoveredTooltipBar.return)}
					{/if}
				</div>
			</div>
		</div>
		<div class="h-2 w-2 rotate-45 bg-gray-900 dark:bg-gray-700"></div>
	</div>
{/if}


