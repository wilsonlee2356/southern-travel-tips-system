<script>
import { createEventDispatcher, getContext, onDestroy, onMount } from 'svelte';
	import { get } from 'svelte/store';

	export let open = false;
	export let calendarData = null;

	const dispatch = createEventDispatcher();
	const i18nStore = getContext?.('i18n');
	let i18nValue = null;

	const portal = (node) => {
		if (typeof document === 'undefined') {
			return;
		}
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

	$: i18nValue = (() => {
		if (!i18nStore) return null;
		if (typeof i18nStore.subscribe === 'function') {
			try {
				return get(i18nStore);
			} catch (error) {
				console.warn('Failed to read i18n store value', error);
				return null;
			}
		}
		return i18nStore;
	})();

	const close = () => {
		dispatch('close');
	};

const handleKeydown = (event) => {
	if (event.key === 'Escape') {
		close();
	}
};

const handleOverlayInteraction = (event) => {
	if (event.type === 'click') {
		if (event.target === event.currentTarget) {
			close();
		}
	} else if (event.type === 'keydown') {
		const triggerKeys = ['Escape', 'Esc', 'Enter', ' '];
		if (triggerKeys.includes(event.key)) {
			event.preventDefault();
			close();
		}
	}
};

	onMount(() => {
		window.addEventListener('keydown', handleKeydown);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', handleKeydown);
	});

const extractCalendarEntries = (data, defaultCurrency) => {
	const entries = [];
	if (!data) {
		return entries;
	}

	const addEntry = (value = {}, rawSource) => {
		const departureDate =
			value.departure_date ||
			value.departure ||
			value.outbound_date ||
			value.departureDate ||
			value.outboundDate;
		const returnDate =
			value.return_date ||
			value.return ||
			value.inbound_date ||
			value.returnDate ||
			value.inboundDate;

		// Allow one-way trips (only departure date required)
		if (!departureDate) {
			return;
		}

		const rawPrice =
			value.price_raw ??
			value.price_value ??
			value.price ??
			value.lowest_price ??
			value.currency_price ??
			value.amount;
		const numericPrice =
			typeof rawPrice === 'number'
				? rawPrice
				: parseFloat(String(rawPrice ?? '').replace(/[^\d.-]+/g, ''));
		const displayPrice =
			value.price_display ??
			value.price_text ??
			value.price_string ??
			value.price_formatted ??
			value.price ??
			((Number.isFinite(numericPrice) && numericPrice > 0) ? numericPrice.toString() : null);
		const currency =
			value.currency ??
			value.currency_code ??
			value.currencyCode ??
			value.currency_symbol ??
			defaultCurrency ??
			null;

		entries.push({
			departureDate,
			returnDate,
			priceValue: Number.isFinite(numericPrice) ? numericPrice : null,
			priceDisplay: displayPrice,
			currency,
			raw: rawSource ?? value
		});
	};

	// Handle case where data.calendar is an array (Google format)
	if (Array.isArray(data.calendar)) {
		data.calendar.forEach((item) => addEntry(item, item));
	}
	// Handle case where data itself is an array (direct calendar array)
	else if (Array.isArray(data)) {
		data.forEach((item) => addEntry(item, item));
	}
	else {
		const visit = (value) => {
			if (Array.isArray(value)) {
				value.forEach(visit);
				return;
			}

			if (value && typeof value === 'object') {
				addEntry(value, value);
				Object.values(value).forEach(visit);
			}
		};

		if (!Array.isArray(data.calendar)) {
			visit(data);
		}
	}

	// Allow entries with only departure date (one-way trips)
	return entries.filter((entry) => entry.departureDate);
};

	const parseDate = (dateString) => {
		if (!dateString) return null;
		const timestamp = Date.parse(dateString);
		return Number.isFinite(timestamp) ? new Date(timestamp) : null;
	};

	const compareDates = (a, b) => {
		const dateA = parseDate(a);
		const dateB = parseDate(b);
		if (dateA && dateB) {
			return dateA.getTime() - dateB.getTime();
		}
		return String(a).localeCompare(String(b));
	};

	const formatDateLabel = (dateString) => {
		const date = parseDate(dateString);
		if (!date) {
			return dateString;
		}
		try {
			return new Intl.DateTimeFormat('en-GB', {
				month: 'short',
				day: 'numeric'
			}).format(date);
		} catch (error) {
			console.warn('Failed to format date label', error);
			return dateString;
		}
	};

	const formatPriceLabel = (entry, fallbackCurrency) => {
		if (!entry) {
			return '—';
		}

		const currency = entry.currency || fallbackCurrency;

		if (entry.priceDisplay && typeof entry.priceDisplay === 'string') {
			return entry.priceDisplay;
		}

		if (entry.priceValue != null) {
			try {
				if (currency) {
					return new Intl.NumberFormat('en-US', {
						style: 'currency',
						currency,
						minimumFractionDigits: 0,
						maximumFractionDigits: 0
					}).format(entry.priceValue);
				}
				return Math.round(entry.priceValue).toLocaleString();
			} catch (error) {
				console.warn('Failed to format price', error);
				return `${currency ?? ''} ${Math.round(entry.priceValue)}`.trim();
			}
		}

		return formatPriceValue(entry?.priceValue);
	};

	const defaultCurrency = () => calendarData?.search_parameters?.currency ?? null;

let outboundDates = [];
let returnDates = [];
let priceMatrix = new Map();
let priceRange = { min: null, max: null };
let hasCalendarMatrix = false;
let lowPriceThreshold = null;
let highPriceThreshold = null;

	$: {
		const fallbackCurrency = defaultCurrency();
		const rawEntries = extractCalendarEntries(calendarData, fallbackCurrency);
		const outboundSet = new Set();
		const returnSet = new Set();
		const matrix = new Map();
		let minPrice = null;
		let maxPrice = null;
		const priceValues = [];

		// Check if this is a one-way trip (no return dates)
		const isOneWay = rawEntries.every(entry => !entry.returnDate);
		
		for (const entry of rawEntries) {
			outboundSet.add(entry.departureDate);
			if (entry.returnDate) {
				returnSet.add(entry.returnDate);
			}

			if (isOneWay) {
				// For one-way trips, use a special key or just departure date
				const oneWayKey = 'ONE_WAY';
				if (!matrix.has(oneWayKey)) {
					matrix.set(oneWayKey, new Map());
				}
				const row = matrix.get(oneWayKey);
				const existing = row.get(entry.departureDate);
				if (!existing || ((entry.priceValue ?? Number.POSITIVE_INFINITY) < (existing.priceValue ?? Number.POSITIVE_INFINITY))) {
					row.set(entry.departureDate, entry);
				}
			} else {
				// For round trips, use return date as row key
				const returnKey = entry.returnDate || 'NO_RETURN';
				if (!matrix.has(returnKey)) {
					matrix.set(returnKey, new Map());
				}
				const row = matrix.get(returnKey);
				const existing = row.get(entry.departureDate);
				if (!existing || ((entry.priceValue ?? Number.POSITIVE_INFINITY) < (existing.priceValue ?? Number.POSITIVE_INFINITY))) {
					row.set(entry.departureDate, entry);
				}
			}

			if (entry.priceValue != null) {
				if (minPrice == null || entry.priceValue < minPrice) {
					minPrice = entry.priceValue;
				}
				if (maxPrice == null || entry.priceValue > maxPrice) {
					maxPrice = entry.priceValue;
				}
				priceValues.push(entry.priceValue);
			}
		}

		outboundDates = Array.from(outboundSet).sort(compareDates);
		// For one-way trips, ensure we show up to 10 dates (don't limit if less than 10)
		// The data should already be limited to 10 in limitCalendarDataset, but ensure we show all available
		returnDates = isOneWay ? ['ONE_WAY'] : Array.from(returnSet).sort(compareDates);
		priceMatrix = matrix;
		priceRange = { min: minPrice, max: maxPrice };

		if (priceValues.length) {
			priceValues.sort((a, b) => a - b);
			const lowIndex = Math.max(0, Math.ceil(priceValues.length * 0.1) - 1);
			const highIndex = Math.min(priceValues.length - 1, Math.floor(priceValues.length * 0.9));
			lowPriceThreshold = priceValues[lowIndex];
			highPriceThreshold = priceValues[highIndex];
		} else {
			lowPriceThreshold = null;
			highPriceThreshold = null;
		}
		// Allow one-way trips (only departure dates required)
		hasCalendarMatrix = outboundDates.length > 0;
	}

const formatPriceValue = (value) => {
	const currency = defaultCurrency();
	if (value == null || Number.isNaN(value)) {
		return '—';
	}
	try {
		if (currency) {
			return new Intl.NumberFormat('en-US', {
				style: 'currency',
				currency,
				maximumFractionDigits: value >= 1000 ? 0 : 2
			}).format(value);
		}
		return Number(value).toLocaleString();
	} catch (error) {
		console.warn('Failed to format price value:', error);
		return `${currency ?? ''} ${value}`.trim();
	}
};

const getPriceColorClasses = (entry) => {
	return '';
};

const getPriceTextClasses = (entry) => {
	if (!entry || entry.priceValue == null) {
		return 'text-gray-400 font-normal';
	}

	const value = entry.priceValue;

	if (lowPriceThreshold != null && value <= lowPriceThreshold) {
		return 'text-green-600 dark:text-green-300 font-semibold';
	}

	if (highPriceThreshold != null && value >= highPriceThreshold) {
		return 'text-red-500 dark:text-red-300 font-normal';
	}

	return 'text-gray-700 dark:text-gray-200 font-medium';
};

const isLowestPrice = (entry) => {
	if (!entry) return false;
	if (entry.raw?.is_lowest_price || entry.raw?.lowest_price) return true;
	if (entry.priceValue == null || priceRange.min == null) return false;
	return Math.abs(entry.priceValue - priceRange.min) < 0.01;
};

const getSelectedOutboundIndex = () => {
  const outboundDate = calendarData?.search_parameters?.outbound_date;
  if (!outboundDate) return -1;
  return outboundDates.indexOf(outboundDate);
};

const getSelectedReturnIndex = () => {
  const returnDate = calendarData?.search_parameters?.return_date;
  if (!returnDate) return -1;
  return returnDates.indexOf(returnDate);
};

const isSelectedOutbound = (outbound) => {
  const outboundIndex = outboundDates.indexOf(outbound);
  const selectedIndex = getSelectedOutboundIndex();
  return outboundIndex !== -1 && outboundIndex === selectedIndex;
};

const isSelectedReturn = (ret) => {
  const returnIndex = returnDates.indexOf(ret);
  const selectedIndex = getSelectedReturnIndex();
  return returnIndex !== -1 && returnIndex === selectedIndex;
};

const getCellHighlightClasses = (outbound, ret, entry) => {
  const outboundIndex = outboundDates.indexOf(outbound);
  const returnIndex = returnDates.indexOf(ret);
  const selectedOutboundIndex = getSelectedOutboundIndex();
  const selectedReturnIndex = getSelectedReturnIndex();

  const isIntersection =
    selectedOutboundIndex !== -1 &&
    selectedReturnIndex !== -1 &&
    outboundIndex === selectedOutboundIndex &&
    returnIndex === selectedReturnIndex;

  if (isIntersection) {
    return 'bg-gray-300 dark:bg-gray-700';
  }

  const inColumnPath =
    selectedOutboundIndex !== -1 &&
    outboundIndex === selectedOutboundIndex &&
    returnIndex !== -1 &&
    (selectedReturnIndex === -1 || returnIndex <= selectedReturnIndex);

  const inRowPath =
    selectedReturnIndex !== -1 &&
    returnIndex === selectedReturnIndex &&
    outboundIndex !== -1 &&
    (selectedOutboundIndex === -1 || outboundIndex >= selectedOutboundIndex);

  if (inColumnPath || inRowPath) {
    return 'bg-gray-100 dark:bg-gray-800';
  }

  if (isLowestPrice(entry)) {
    return 'bg-green-100 dark:bg-green-900/40';
  }

  return '';
};

const formatDurationMinutes = (minutes) => {
	if (!minutes || Number.isNaN(minutes)) return '';
	const hours = Math.floor(minutes / 60);
	const mins = Math.floor(minutes % 60);
	if (hours && mins) return `${hours}h ${mins}m`;
	if (hours) return `${hours}h`;
	return `${mins}m`;
};

const getEntryDurationLabel = (entry) => {
	if (!entry || !entry.raw) return '';
	const raw = entry.raw;
	const candidate =
		raw.total_duration ??
		raw.total_duration_minutes ??
		raw.duration_minutes ??
		raw.duration ??
		raw.flight_duration ??
		raw.travel_time ??
		raw.total_time;
	if (typeof candidate === 'number') {
		return formatDurationMinutes(candidate);
	}
	if (typeof candidate === 'string') {
		return candidate;
	}
	return '';
};

	const primaryLabel = (key, fallbackKey) => {
		return calendarData?.search_parameters?.[key] || calendarData?.search_parameters?.[fallbackKey] || '';
	};

	const translate = (key, fallback) => {
		const translator = i18nValue?.t ?? i18nValue;
		if (typeof translator === 'function') {
			try {
				return translator(key) ?? fallback;
			} catch (error) {
				console.warn('Translation failed for key:', key, error);
			}
		}
		return fallback;
	};
</script>

{#if open}
<div use:portal class="fixed inset-0 z-[1300] flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
<button
  type="button"
  class="absolute inset-0 z-[1320] w-full h-full bg-transparent cursor-default"
  aria-label={translate('Close price calendar', 'Close price calendar')}
  on:click={handleOverlayInteraction}
  on:keydown={handleOverlayInteraction}
  tabindex="0"
></button>
<div class="relative z-[1330] w-full max-w-4xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden" on:pointerdown|stopPropagation>
<header class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
<div>
<h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">
{translate('Price Calendar', 'Price Calendar')}
</h2>
<p class="mt-0.5 text-xs text-gray-600 dark:text-gray-400">
{#if calendarData?.search_parameters}
{translate('Route', 'Route')}: {primaryLabel('departure_id', 'departure')} → {primaryLabel('arrival_id', 'arrival')}
{:else}
{translate('Calendar preview of available fares', 'Calendar preview of available fares')}
{/if}
</p>
</div>
<button
  type="button"
  class="inline-flex items-center justify-center w-8 h-8 rounded-full text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500"
  on:click={close}
  aria-label={translate('Close', 'Close')}
>
  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
</button>
</header>

<section class="px-4 py-3 overflow-auto max-h-[75vh]">
{#if !hasCalendarMatrix}
<div class="py-16 text-center text-sm text-gray-500 dark:text-gray-400">
{translate('No calendar data available for this search yet.', 'No calendar data available for this search yet.')}
</div>
{:else}
<div class="space-y-2">
<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
{translate('Price Grid', 'Price Grid')}
</h3>
{#if priceRange.min != null && priceRange.max != null}
<div class="text-xs text-gray-600 dark:text-gray-400">
{translate('Price range', 'Price range')}: 
<span class="font-semibold text-green-600 dark:text-green-400">{formatPriceValue(priceRange.min)}</span>
<span class="mx-1">-</span>
<span class="font-semibold text-red-600 dark:text-red-400">{formatPriceValue(priceRange.max)}</span>
</div>
{/if}
</div>

<div class="flex flex-wrap gap-4 text-xs text-gray-600 dark:text-gray-400">
<div class="flex items-center gap-2">
<span class="inline-block w-4 h-4 rounded bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700"></span>
{translate('Lowest price', 'Lowest price')}
</div>
</div>

<div class="overflow-x-auto">
<table class="min-w-full border-collapse">
<thead>
<tr>
{#each outboundDates as outbound}
<th class={`px-1 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 text-center border border-gray-300 dark:border-gray-600 whitespace-nowrap ${isSelectedOutbound(outbound) ? 'bg-gray-100 dark:bg-gray-800' : ''}`}>
{formatDateLabel(outbound)}
</th>
{/each}
{#if !(returnDates.length === 1 && returnDates[0] === 'ONE_WAY')}
<th class="px-1 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 text-center border border-gray-300 dark:border-gray-600 w-20"></th>
{/if}
</tr>
</thead>
<tbody>
{#each returnDates as returnDate}
<tr class="border-b border-gray-200/70 dark:border-gray-700/60 last:border-0">
{#each outboundDates as outbound}
{@const entry = priceMatrix.get(returnDate)?.get(outbound)}
<td class={`px-1 py-1.5 text-[11px] text-center align-middle border border-gray-300 dark:border-gray-600 whitespace-nowrap ${getCellHighlightClasses(outbound, returnDate, entry)}`}>
{#if entry && (entry.priceValue != null || entry.priceDisplay)}
<div class={`text-[11px] ${getPriceTextClasses(entry)} whitespace-nowrap`}>
{formatPriceLabel(entry, defaultCurrency())}
</div>
{#if getEntryDurationLabel(entry)}
<div class="text-[10px] text-gray-600 dark:text-gray-300 mt-0.5 whitespace-nowrap">
{getEntryDurationLabel(entry)}
</div>
{/if}
{:else}
<span class="text-gray-400 text-[10px]">—</span>
{/if}
</td>
{/each}
{#if !(returnDates.length === 1 && returnDates[0] === 'ONE_WAY')}
<td class={`px-1 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 text-center align-middle border border-gray-300 dark:border-gray-600 w-20 whitespace-nowrap ${isSelectedReturn(returnDate) ? 'bg-gray-100 dark:bg-gray-800' : ''}`}>
{formatDateLabel(returnDate)}
</td>
{/if}
</tr>
{/each}
</tbody>
</table>
</div>

<p class="text-[10px] text-gray-500 dark:text-gray-400">
{translate('Tip: Adjust your dates to compare fare combinations. Prices reflect cached calendar data and may change when booking.', 'Tip: Adjust your dates to compare fare combinations. Prices reflect cached calendar data and may change when booking.')}
</p>
</div>
{/if}
</section>
</div>
</div>
{/if}

