<script>
	export let series = null;
	export let leg = 'departure';

	const monthFormatter = new Intl.DateTimeFormat('en-US', {
		month: 'numeric',
		year: 'numeric'
	});
	const dayFormatter = new Intl.DateTimeFormat('en-US', {
		month: 'short',
		day: 'numeric'
	});

	const WIDTH = 640;
	const HEIGHT = 260;
	const PADDING = { top: 24, right: 32, bottom: 48, left: 56 };

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

	$: data = createChartData(series);

	$: timestamps = data.map((d) => d.timestamp);
	$: prices = data.map((d) => d.price);

	$: minX = Math.min(...timestamps);
	$: maxX = Math.max(...timestamps);

	const Y_STEP = 1000;
const MIN_TICK_SPACING = 60;
	const snapDown = (value, step) => Math.floor(value / step) * step;
	const snapUp = (value, step) => Math.ceil(value / step) * step;

	$: minYRaw = Math.min(...prices);
	$: maxYRaw = Math.max(...prices);
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

	$: monthTicks = (() => {
		const map = new Map();
		data.forEach((point) => {
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
		if (data.length === 0) return [];
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

	let hoveredPoint = null;

	const handleMouseMove = (event) => {
		if (!scaledPoints.length) {
			hoveredPoint = null;
			return;
		}

		const rect = event.currentTarget.getBoundingClientRect();
		const relativeX = (event.clientX - rect.left) / rect.width;
		const svgXRaw = relativeX * WIDTH;
		const clampedX = Math.max(PADDING.left, Math.min(WIDTH - PADDING.right, svgXRaw));

		let priceValue;
		let timestampValue;

		if (scaledPoints.length === 1) {
			priceValue = data[0]?.price ?? 0;
			timestampValue = data[0]?.timestamp ?? minX;
			hoveredPoint = {
				x: scaleX(timestampValue),
				y: scaleY(priceValue),
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
			segmentIndex < scaledPoints.length - 1 &&
			targetTimestamp > data[segmentIndex + 1].timestamp
		) {
			segmentIndex += 1;
		}

		const p1 = data[segmentIndex];
		const p2 =
			segmentIndex === data.length - 1 ? data[segmentIndex] : data[segmentIndex + 1];

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
			price: priceValue,
			timestamp: timestampValue,
		};
	};

	const handleMouseLeave = () => {
		hoveredPoint = null;
	};
</script>

{#if data.length === 0}
	<div class="chart-empty">
		No price data available yet for this {leg} leg.
	</div>
{:else}
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
				<text x={PADDING.left - 12} y={y} class="tick-label y-label">
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

			<!-- Line -->
			<path d={pathData} class="line" />

			<!-- Hover Point -->
			{#if hoveredPoint}
				<circle cx={hoveredPoint.x} cy={hoveredPoint.y} r={6} class="hover-point" />
			{/if}
		</svg>

		{#if hoveredPoint}
			<div
				class="chart-tooltip"
				style={`left: calc(${(hoveredPoint.x / WIDTH) * 100}% - 64px); top: ${(
					PADDING.top / HEIGHT
				) * 100}%;`}
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
{/if}

<style>
	.chart-container {
		width: 100%;
		max-width: 720px;
		margin: 0 auto;
		position: relative;
	}

	.chart {
		width: 100%;
		height: 280px;
		overflow: visible;
	}

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
		transform: translateY(-100%);
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

	.chart-empty {
		min-height: 140px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(148, 163, 184, 0.1);
		color: rgba(71, 85, 105, 0.8);
		border: 1px dashed rgba(148, 163, 184, 0.4);
		border-radius: 0.75rem;
	}
</style>

