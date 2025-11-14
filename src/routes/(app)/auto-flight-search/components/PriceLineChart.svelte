<script>
	import { createEventDispatcher } from 'svelte';
	import PriceCalendar from './PriceCalendar.svelte';
	import CheapestPricesList from './CheapestPricesList.svelte';

	export let series = null;
	export let allSeries = null; // Array of series for "Overall" view
	export let departureSeries = null; // Departure series for combining with return
	export let returnSeries = null; // Return series for combining with return
	export let leg = 'departure';
	export let filteredModels = [];
	export let selectedModel = null;

	const dispatch = createEventDispatcher();

	// Define 10 distinct colors for airlines
	const AIRLINE_COLORS = [
		'#3B82F6', // Blue
		'#EF4444', // Red
		'#10B981', // Green
		'#F59E0B', // Amber
		'#8B5CF6', // Purple
		'#EC4899', // Pink
		'#06B6D4', // Cyan
		'#F97316', // Orange
		'#84CC16', // Lime
		'#6366F1', // Indigo
	];

	const handlePost = (event) => {
		// Add airline identifier to ensure only current airline's data is used
		const airlineCode = series?.airline_code || series?.airline_name || series?.airline_id || null;
		const airlineName = series?.airline_name || series?.airline_code || null;
		
		dispatch('post', {
			...event.detail,
			airlineCode,
			airlineName
		});
	};

	const monthFormatter = new Intl.DateTimeFormat('en-US', {
		month: 'numeric',
		year: 'numeric'
	});

	const WIDTH = 1600; // Increased for zoomed view
	const HEIGHT = 400; // Increased proportionally
	const PADDING = { top: 24, right: 32, bottom: 48, left: 85 }; // Increased left padding for y-axis labels

	const createChartData = (input) => {
		if (!input?.prices || !Array.isArray(input.prices)) return [];
		return input.prices
			.map((point) => {
				const date = point?.departure_date ? new Date(point.departure_date) : null;
				const price = Number(point?.price ?? NaN);
				return date && !Number.isNaN(price)
					? {
							date,
							timestamp: date.getTime(),
							price,
							isLowest: Boolean(point?.is_lowest_price)
					  }
					: null;
			})
			.filter(Boolean)
			.sort((a, b) => a.timestamp - b.timestamp);
	};

	let data = [];
	let selectedDates = new Set();
	let overallSelectedDates = new Set(); // Separate selectedDates for Overall view (not used for list)
	let selectedDatesMap = new Map(); // Store selectedDates per calendar instance
	let previousCalendarKey = null;

	// Create unique key for this calendar instance (airline + leg + route)
	$: calendarKey = (() => {
		if (allSeries && allSeries.length > 0) {
			// "Overall" view - use a special key
			return `OVERALL-${leg}`;
		}
		if (series) {
			return `${series.airline_code || series.airline_name || series.airline_id || 'unknown'}-${leg}-${series.route_from || ''}-${series.route_to || ''}`;
		}
		return null;
	})();

	// Load or initialize selectedDates when calendarKey changes (switching between airlines/legs)
	$: {
		if (calendarKey && calendarKey !== previousCalendarKey) {
			previousCalendarKey = calendarKey;
			
			// For "Overall" view, use separate selectedDates that doesn't affect individual airlines
			if (allSeries && allSeries.length > 0) {
				if (overallSelectedDates.size === 0) {
					// Initialize with isLowest dates for Overall view
					const lowestDates = new Set();
					allDataPoints.forEach((point) => {
						if (point?.date instanceof Date && point?.isLowest === true) {
							const year = point.date.getFullYear();
							const month = String(point.date.getMonth() + 1).padStart(2, '0');
							const day = String(point.date.getDate()).padStart(2, '0');
							lowestDates.add(`${year}-${month}-${day}`);
						}
					});
					overallSelectedDates = new Set(lowestDates);
				}
				selectedDates = new Set(overallSelectedDates);
			} else if (series) {
				// For single airline view
				// Initialize both departure and return calendars if they haven't been initialized yet
				if (departureSeries) {
					const depKey = `${departureSeries.airline_code || departureSeries.airline_name || departureSeries.airline_id || 'unknown'}-departure-${departureSeries.route_from || ''}-${departureSeries.route_to || ''}`;
					if (!selectedDatesMap.has(depKey)) {
						const depLowestDates = new Set();
						const depChartData = createChartData(departureSeries);
						depChartData.forEach((point) => {
							if (point?.date instanceof Date && point?.isLowest === true) {
								const year = point.date.getFullYear();
								const month = String(point.date.getMonth() + 1).padStart(2, '0');
								const day = String(point.date.getDate()).padStart(2, '0');
								depLowestDates.add(`${year}-${month}-${day}`);
							}
						});
						selectedDatesMap.set(depKey, depLowestDates);
					}
				}
				
				if (returnSeries) {
					const retKey = `${returnSeries.airline_code || returnSeries.airline_name || returnSeries.airline_id || 'unknown'}-return-${returnSeries.route_from || ''}-${returnSeries.route_to || ''}`;
					if (!selectedDatesMap.has(retKey)) {
						const retLowestDates = new Set();
						const retChartData = createChartData(returnSeries);
						retChartData.forEach((point) => {
							if (point?.date instanceof Date && point?.isLowest === true) {
								const year = point.date.getFullYear();
								const month = String(point.date.getMonth() + 1).padStart(2, '0');
								const day = String(point.date.getDate()).padStart(2, '0');
								retLowestDates.add(`${year}-${month}-${day}`);
							}
						});
						selectedDatesMap.set(retKey, retLowestDates);
					}
				}
				
				// Load or initialize current calendar
				if (!selectedDatesMap.has(calendarKey)) {
					// Initialize with isLowest dates for this specific calendar
					const lowestDates = new Set();
					const chartData = createChartData(series);
					chartData.forEach((point) => {
						if (point?.date instanceof Date && point?.isLowest === true) {
							const year = point.date.getFullYear();
							const month = String(point.date.getMonth() + 1).padStart(2, '0');
							const day = String(point.date.getDate()).padStart(2, '0');
							lowestDates.add(`${year}-${month}-${day}`);
						}
					});
					selectedDatesMap.set(calendarKey, lowestDates);
					selectedDates = new Set(lowestDates);
				} else {
					// Load existing selection for this calendar
					selectedDates = new Set(selectedDatesMap.get(calendarKey));
				}
			}
		} else if (!calendarKey) {
			selectedDates = new Set();
		}
	}

	// Update the map immediately when selectedDates changes (from user interaction in PriceCalendar)
	// This ensures both calendars' selections are always saved and available for the combined list
	$: {
		if (calendarKey && selectedDates) {
			// For Overall view, update overallSelectedDates (but it won't affect individual airlines)
			if (allSeries && allSeries.length > 0) {
				overallSelectedDates = new Set(selectedDates);
			} else if (series) {
				// For individual airline, always update the map immediately
				selectedDatesMap.set(calendarKey, new Set(selectedDates));
			}
		}
	}

	// Create combined selectedDates from both departure and return for the list
	// This combines selections from both calendars into one unified list
	$: combinedSelectedDates = (() => {
		const combined = new Set();
		
		// For "Overall" view, use the overall calendar's selectedDates
		if (allSeries && allSeries.length > 0) {
			if (selectedDates) {
				selectedDates.forEach(date => combined.add(date));
			}
			return combined;
		}
		
		// Always get departure calendar selectedDates (from map or current if active)
		if (departureSeries) {
			const depKey = `${departureSeries.airline_code || departureSeries.airline_name || departureSeries.airline_id || 'unknown'}-departure-${departureSeries.route_from || ''}-${departureSeries.route_to || ''}`;
			// Use current selectedDates if departure tab is active, otherwise get from map
			let depDates = selectedDatesMap.get(depKey);
			if (calendarKey === depKey && selectedDates) {
				depDates = selectedDates; // Use current (most up-to-date) if this is the active calendar
			}
			if (depDates) {
				depDates.forEach(date => combined.add(date));
			}
		}
		
		// Always get return calendar selectedDates (from map or current if active)
		if (returnSeries) {
			const retKey = `${returnSeries.airline_code || returnSeries.airline_name || returnSeries.airline_id || 'unknown'}-return-${returnSeries.route_from || ''}-${returnSeries.route_to || ''}`;
			// Use current selectedDates if return tab is active, otherwise get from map
			let retDates = selectedDatesMap.get(retKey);
			if (calendarKey === retKey && selectedDates) {
				retDates = selectedDates; // Use current (most up-to-date) if this is the active calendar
			}
			if (retDates) {
				retDates.forEach(date => combined.add(date));
			}
		}
		
		// If no departure/return series, use current selectedDates
		if (combined.size === 0 && selectedDates) {
			selectedDates.forEach(date => combined.add(date));
		}
		
		return combined;
	})();

	// Process single series or multiple series
	$: data = allSeries && allSeries.length > 0 ? [] : createChartData(series);
	
	// Process multiple series for "Overall" view
	$: multiSeriesData = (() => {
		if (!allSeries || allSeries.length === 0) return [];
		return allSeries.map((s, index) => {
			const seriesData = createChartData(s);
			const airlineName = s?.airline_name ?? s?.airline_code ?? `Airline ${index + 1}`;
			const color = AIRLINE_COLORS[index % AIRLINE_COLORS.length];
			return {
				airlineName,
				airlineCode: s?.airline_code ?? s?.airline_id ?? '',
				color,
				data: seriesData
			};
		});
	})();

	// Combine all data for min/max calculations
	$: allDataPoints = (() => {
		if (allSeries && allSeries.length > 0) {
			const combined = multiSeriesData.flatMap((s) => s.data);
			// Sort by timestamp for hover detection
			return combined.sort((a, b) => a.timestamp - b.timestamp);
		}
		return data;
	})();

	$: timestamps = allDataPoints.map((d) => d.timestamp);
	$: prices = allDataPoints.map((d) => d.price);

	$: minX = timestamps.length > 0 ? Math.min(...timestamps) : 0;
	$: maxX = timestamps.length > 0 ? Math.max(...timestamps) : 0;

	const Y_STEP = 1000;
const MIN_TICK_SPACING = 60;
	const snapDown = (value, step) => Math.floor(value / step) * step;
	const snapUp = (value, step) => Math.ceil(value / step) * step;

	$: minYRaw = prices.length > 0 ? Math.min(...prices) : 0;
	$: maxYRaw = prices.length > 0 ? Math.max(...prices) : Y_STEP;
	$: minY = Number.isFinite(minYRaw) ? snapDown(minYRaw, Y_STEP) : 0;
	$: maxY = Number.isFinite(maxYRaw) ? snapUp(maxYRaw, Y_STEP) : Y_STEP;
	$: {
		if (maxY <= minY) {
			maxY = minY + Y_STEP;
		}
	}
	$: xRange = maxX - minX || 1;
	$: yRange = maxY - minY || Y_STEP;

	const innerWidth = WIDTH - PADDING.left - PADDING.right;
	const innerHeight = HEIGHT - PADDING.top - PADDING.bottom;

	const scaleX = (timestamp) => {
		if (!Number.isFinite(timestamp)) return PADDING.left;
		if (!Number.isFinite(minX) || !Number.isFinite(maxX)) return PADDING.left;
		return (
			PADDING.left + ((timestamp - minX) / xRange) * innerWidth
		);
	};

	const scaleY = (price) => {
		if (!Number.isFinite(price)) return HEIGHT - PADDING.bottom;
		return (
			PADDING.top + (1 - (price - minY) / yRange) * innerHeight
		);
	};

	const toSmoothPath = (points) => {
		if (!points || points.length === 0) return '';
		if (points.length === 1) {
			const [p] = points;
			return `M ${p.x} ${p.y}`;
		}
		const path = [`M ${points[0].x} ${points[0].y}`];
		for (let i = 0; i < points.length - 1; i += 1) {
			const p0 = points[i - 1] || points[i];
			const p1 = points[i];
			const p2 = points[i + 1];
			const p3 = points[i + 2] || p2;
			const cp1x = p1.x + (p2.x - p0.x) / 6;
			const cp1y = p1.y + (p2.y - p0.y) / 6;
			const cp2x = p2.x - (p3.x - p1.x) / 6;
			const cp2y = p2.y - (p3.y - p1.y) / 6;
			path.push(`C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`);
		}
		return path.join(' ');
	};

	$: scaledPoints = data.map((point) => ({
		...point,
		x: scaleX(point.timestamp),
		y: scaleY(point.price)
	}));

	$: pathData = toSmoothPath(scaledPoints);

	// Process multiple series for rendering
	$: multiSeriesScaled = multiSeriesData.map((seriesInfo) => ({
		...seriesInfo,
		scaledPoints: seriesInfo.data.map((point) => ({
			...point,
			x: scaleX(point.timestamp),
			y: scaleY(point.price)
		}))
	}));

	$: multiSeriesPaths = multiSeriesScaled.map((seriesInfo) => ({
		...seriesInfo,
		pathData: toSmoothPath(seriesInfo.scaledPoints)
	}));

	$: monthTicks = (() => {
		const map = new Map();
		allDataPoints.forEach((point) => {
			const key = `${point.date.getFullYear()}-${point.date.getMonth()}`;
			if (!map.has(key)) {
				map.set(key, point.date);
			}
		});
		return Array.from(map.values()).sort((a, b) => a.getTime() - b.getTime());
	})();

$: visibleMonthTicks = (() => {
	const ticks = monthTicks
		.map((date) => ({
			date,
			x: scaleX(date.getTime())
		}))
		.sort((a, b) => a.x - b.x);

	const visible = [];
	for (let i = 0; i < ticks.length; i += 1) {
		const tick = ticks[i];
		const next = ticks[i + 1];
		const nextX = next ? next.x : WIDTH - PADDING.right;
		const gap = nextX - tick.x;
		if (gap >= MIN_TICK_SPACING) {
			visible.push(tick);
		}
	}
	if (ticks.length > 0) {
		const last = ticks[ticks.length - 1];
		const secondLast = ticks[ticks.length - 2];
		const prevX = secondLast ? secondLast.x : PADDING.left;
		if (last.x - prevX >= MIN_TICK_SPACING && !visible.some((tick) => tick.x === last.x)) {
			visible.push(last);
		}
	}
	return visible;
})();

	$: yTicks = (() => {
		// Use allDataPoints to determine if we have data (works for both single and multi-series)
		if (allDataPoints.length === 0) return [];
		const ticks = [];
		for (let value = minY; value <= maxY; value += Y_STEP) {
			ticks.push(value);
		}
		if (!ticks.includes(maxY)) {
			ticks.push(maxY);
		}
		return ticks;
	})();

	const formatPrice = (price) => `HK$${Math.round(price).toLocaleString('en-US')}`;
	const formatDateLabel = (date) => monthFormatter.format(date);

	// Combine departure and return data for CheapestPricesList
	$: combinedCalendarData = (() => {
		// For "Overall" view, combine all airlines' data
		if (allSeries && allSeries.length > 0) {
			const combined = [];
			allSeries.forEach((s) => {
				const seriesData = createChartData(s);
				seriesData.forEach((point) => {
					combined.push({
						...point,
						route_from: s.route_from || '',
						route_to: s.route_to || '',
						direction: s.direction || leg
					});
				});
			});
			return combined;
		}
		
		const combined = [];
		
		// Add departure data (only for current airline)
		if (departureSeries) {
			const departureData = createChartData(departureSeries);
			departureData.forEach((point) => {
				combined.push({
					...point,
					route_from: departureSeries.route_from || '',
					route_to: departureSeries.route_to || '',
					direction: 'departure',
					airline_code: departureSeries.airline_code || departureSeries.airline_id || '',
					airline_name: departureSeries.airline_name || departureSeries.airline_code || ''
				});
			});
		}
		
		// Add return data (only for current airline)
		if (returnSeries) {
			const returnData = createChartData(returnSeries);
			returnData.forEach((point) => {
				combined.push({
					...point,
					route_from: returnSeries.route_from || '',
					route_to: returnSeries.route_to || '',
					direction: 'return',
					airline_code: returnSeries.airline_code || returnSeries.airline_id || '',
					airline_name: returnSeries.airline_name || returnSeries.airline_code || ''
				});
			});
		}
		
		// If no departure/return series, use current data
		if (combined.length === 0) {
			return data.map((point) => ({
				...point,
				route_from: series?.route_from || '',
				route_to: series?.route_to || '',
				direction: leg
			}));
		}
		
		return combined;
	})();

	let hoveredPoint = null;

	// Clear hover point when switching to "Overall" view
	$: {
		if (allSeries && allSeries.length > 0) {
			hoveredPoint = null;
		}
	}

	const handleMouseMove = (event) => {
		// Disable hover for "Overall" view (multiple airlines)
		if (allSeries && allSeries.length > 0) {
			hoveredPoint = null;
			return;
		}
		
		// Use data for single airline view
		const pointsToUse = data;
		if (!pointsToUse.length) {
			hoveredPoint = null;
			return;
		}

		const rect = event.currentTarget.getBoundingClientRect();
		const containerRect = event.currentTarget.closest('.chart-container')?.getBoundingClientRect();
		const relativeX = (event.clientX - rect.left) / rect.width;
		const svgXRaw = relativeX * WIDTH;
		const clampedX = Math.max(PADDING.left, Math.min(WIDTH - PADDING.right, svgXRaw));
		
		// Calculate container-relative position for tooltip
		const containerX = containerRect 
			? ((clampedX / WIDTH) * rect.width) + (rect.left - containerRect.left)
			: (clampedX / WIDTH) * rect.width;
		const containerY = containerRect
			? rect.top - containerRect.top
			: 0;

		let priceValue;
		let timestampValue;

		if (pointsToUse.length === 1) {
			priceValue = pointsToUse[0]?.price ?? 0;
			timestampValue = pointsToUse[0]?.timestamp ?? minX;
			const svgX = scaleX(timestampValue);
			const svgY = scaleY(priceValue);
			hoveredPoint = {
				x: svgX,
				y: svgY,
				containerX: containerX,
				containerY: containerY + (svgY / HEIGHT) * rect.height,
				price: priceValue,
				timestamp: timestampValue,
			};
			return;
		}

		const timeRatio = Math.max(
			0,
			Math.min(1, innerWidth === 0 ? 0 : (clampedX - PADDING.left) / innerWidth)
		);
		const targetTimestamp = minX + timeRatio * xRange;

		let segmentIndex = 0;
		while (
			segmentIndex < pointsToUse.length - 1 &&
			targetTimestamp > pointsToUse[segmentIndex + 1].timestamp
		) {
			segmentIndex += 1;
		}

		const p1 = pointsToUse[segmentIndex];
		const p2 =
			segmentIndex === pointsToUse.length - 1 ? pointsToUse[segmentIndex] : pointsToUse[segmentIndex + 1];

		let interpolatedPrice = p1.price;
		if (p2.timestamp !== p1.timestamp) {
			const segmentRatio =
				(targetTimestamp - p1.timestamp) / (p2.timestamp - p1.timestamp || 1);
			interpolatedPrice = p1.price + segmentRatio * (p2.price - p1.price);
		}

		priceValue = interpolatedPrice;
		timestampValue = targetTimestamp;

		const x = scaleX(targetTimestamp);
		const y = scaleY(interpolatedPrice);

		hoveredPoint = {
			x,
			y,
			containerX: containerX,
			containerY: containerY + (y / HEIGHT) * rect.height,
			price: priceValue,
			timestamp: timestampValue,
		};
	};

	const handleMouseLeave = () => {
		hoveredPoint = null;
	};
</script>

<div class="chart-container">
		<svg
			class="chart"
			viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
			preserveAspectRatio="none"
			role="img"
			on:mousemove={handleMouseMove}
			on:mouseleave={handleMouseLeave}
		>
			<!-- Y Axis -->
			<line
				x1={PADDING.left}
				y1={PADDING.top}
				x2={PADDING.left}
				y2={HEIGHT - PADDING.bottom}
				class="axis"
			/>
			{#each yTicks as tick}
				{@const y = scaleY(tick)}
				<line
					x1={PADDING.left}
					y1={y}
					x2={WIDTH - PADDING.right}
					y2={y}
					class="grid-line"
				/>
				<text x={PADDING.left - 24} y={y} class="tick-label y-label">
					{formatPrice(tick)}
				</text>
			{/each}

			<!-- X Axis -->
			<line
				x1={PADDING.left}
				y1={HEIGHT - PADDING.bottom}
				x2={WIDTH - PADDING.right}
				y2={HEIGHT - PADDING.bottom}
				class="axis"
			/>
			{#each visibleMonthTicks as tick}
				{@const x = tick.x}
				<line
					x1={x}
					y1={HEIGHT - PADDING.bottom}
					x2={x}
					y2={HEIGHT - PADDING.bottom + 6}
					class="axis-tick"
				/>
				<text x={x} y={HEIGHT - PADDING.bottom + 24} class="tick-label">
					{formatDateLabel(tick.date)}
				</text>
			{/each}

			<!-- Lines -->
			{#if allSeries && allSeries.length > 0}
				{#each multiSeriesPaths as seriesInfo}
					{#if seriesInfo.pathData}
						<path d={seriesInfo.pathData} class="line" style="stroke: {seriesInfo.color};" />
					{/if}
				{/each}
			{:else if data.length > 0}
				<path d={pathData} class="line" />
			{/if}

			<!-- Hover Point (only for single airline view) -->
			{#if hoveredPoint && !(allSeries && allSeries.length > 0)}
				<circle cx={hoveredPoint.x} cy={hoveredPoint.y} r={6} class="hover-point" />
			{/if}
		</svg>

		{#if hoveredPoint && !(allSeries && allSeries.length > 0)}
			<div
				class="chart-tooltip"
				style={`left: ${hoveredPoint.containerX ?? hoveredPoint.x}px; top: ${(hoveredPoint.containerY ?? hoveredPoint.y) - 8}px;`}
			>
				<div class="tooltip-price">{formatPrice(hoveredPoint.price)}</div>
				<div class="tooltip-date">
					{new Intl.DateTimeFormat('en-GB', {
						day: 'numeric',
						month: 'numeric',
						year: 'numeric'
					}).format(new Date(hoveredPoint.timestamp))}
				</div>
			</div>
		{/if}

	</div>

	<!-- Legend for multiple airlines -->
	{#if allSeries && allSeries.length > 0 && multiSeriesData.length > 0}
		<div class="chart-legend">
			{#each multiSeriesData as seriesInfo}
				<div class="legend-item">
					<div class="legend-color" style="background-color: {seriesInfo.color};"></div>
					<span class="legend-label">{seriesInfo.airlineName}</span>
				</div>
			{/each}
		</div>
	{/if}

	{#if allSeries && allSeries.length > 0}
		<PriceCalendar 
			calendarData={allDataPoints} 
			bind:selectedDates={overallSelectedDates}
			disabled={true}
		/>
	{:else}
		<PriceCalendar 
			calendarData={data} 
			bind:selectedDates
			disabled={false}
		/>
	{/if}
	{#if !(allSeries && allSeries.length > 0)}
		<CheapestPricesList
			calendarData={combinedCalendarData}
			selectedDates={combinedSelectedDates}
			{filteredModels}
			bind:selectedModel
			on:post={handlePost}
		/>
	{/if}

<style>
	.chart-container {
		width: 100%;
		overflow-x: auto;
		overflow-y: visible; /* Changed to visible to allow tooltip to show above */
		margin: 0 auto;
		position: relative;
		-webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
		scrollbar-width: thin; /* Firefox */
		scrollbar-color: rgba(148, 163, 184, 0.5) transparent; /* Firefox */
		z-index: 1; /* Ensure container is above other elements */
	}

	.chart-container::-webkit-scrollbar {
		height: 8px; /* Chrome, Safari, Edge */
	}

	.chart-container::-webkit-scrollbar-track {
		background: rgba(148, 163, 184, 0.1);
		border-radius: 4px;
	}

	.chart-container::-webkit-scrollbar-thumb {
		background: rgba(148, 163, 184, 0.5);
		border-radius: 4px;
	}

	.chart-container::-webkit-scrollbar-thumb:hover {
		background: rgba(148, 163, 184, 0.7);
	}

	:global(.dark) .chart-container::-webkit-scrollbar-track {
		background: rgba(148, 163, 184, 0.15);
	}

	:global(.dark) .chart-container::-webkit-scrollbar-thumb {
		background: rgba(148, 163, 184, 0.6);
	}

	:global(.dark) .chart-container::-webkit-scrollbar-thumb:hover {
		background: rgba(148, 163, 184, 0.8);
	}

	.chart {
		width: 1600px; /* Match WIDTH constant */
		height: 400px; /* Match HEIGHT constant */
		overflow: visible;
		min-width: 100%; /* Ensure it's at least full width */
	}

	/* Calendar styles moved to PriceCalendar */

	.axis {
		stroke: rgba(148, 163, 184, 0.6);
		stroke-width: 1;
	}

	.grid-line {
		stroke: rgba(148, 163, 184, 0.25);
		stroke-width: 1;
	}

	.axis-tick {
		stroke: rgba(148, 163, 184, 0.6);
		stroke-width: 1;
	}

	.tick-label {
		fill: rgba(71, 85, 105, 0.8);
		font-size: 12px;
		text-anchor: middle;
	}

	.y-label {
		text-anchor: end;
		dominant-baseline: middle;
	}

	.line {
		fill: none;
		stroke: #0f172a;
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}

	.hover-point {
		fill: #111827;
		stroke: #f8fafc;
		stroke-width: 2;
	}

	.chart-tooltip {
		position: absolute;
		transform: translate(-50%, -100%); /* Center horizontally, position above */
		background: rgba(15, 23, 42, 0.95);
		color: #f8fafc;
		padding: 0.4rem 0.7rem;
		border-radius: 0.5rem;
		font-size: 0.75rem;
		line-height: 1.1;
		pointer-events: none;
		min-width: 120px;
		text-align: center;
		box-shadow: 0 8px 16px rgba(15, 23, 42, 0.2);
		z-index: 9999; /* Ensure tooltip is above everything */
		margin-top: -8px; /* Add space above the hover point */
		white-space: nowrap; /* Prevent text wrapping */
	}

	.chart-tooltip::after {
		content: '';
		position: absolute;
		left: 50%;
		bottom: -6px;
		transform: translateX(-50%);
		border-width: 6px 6px 0 6px;
		border-style: solid;
		border-color: rgba(15, 23, 42, 0.95) transparent transparent transparent;
	}

	.tooltip-price {
		font-weight: 600;
	}

	.tooltip-date {
		margin-top: 0.15rem;
		opacity: 0.85;
	}

	.chart-legend {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		margin-top: 1rem;
		padding: 0.75rem;
		justify-content: center;
		align-items: center;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.legend-color {
		width: 12px;
		height: 12px;
		border-radius: 2px;
		flex-shrink: 0;
	}

	.legend-label {
		font-size: 0.875rem;
		color: rgba(71, 85, 105, 0.9);
		white-space: nowrap;
	}

	:global(.dark) .legend-label {
		color: rgba(226, 232, 240, 0.9);
	}

</style>

