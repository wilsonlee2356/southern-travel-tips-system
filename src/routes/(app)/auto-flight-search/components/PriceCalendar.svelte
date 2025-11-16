<script>
export let calendarData = [];
export let selectedDates = new Set();
export let disabled = false; // Disable calendar interaction
export let direction = 'departure'; // Direction prefix for date keys
export let layout = 'calendar'; // 'calendar' for grid, 'horizontal' for one-way list
let priceByDate = new Map();
let calendarMonths = [];
let currentMonthIndex = 0;

const toggleDateSelection = (dateKey) => {
	if (disabled) return; // Don't allow selection when disabled
	selectedDates = new Set(selectedDates);
	// Prefix dateKey with direction to make it unique per calendar
	const prefixedKey = `${direction}-${dateKey}`;
	if (selectedDates.has(prefixedKey)) {
		selectedDates.delete(prefixedKey);
	} else {
		selectedDates.add(prefixedKey);
	}
};

	const monthNumericFormatter = new Intl.DateTimeFormat('en-US', {
		month: 'numeric',
		year: 'numeric'
	});

	const weekdayLabels = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

const normalizeDateKey = (date) => {
	if (!(date instanceof Date)) return '';
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
};

const formatPrice = (price) =>
	Number.isFinite(price) ? `HK$${Math.round(price).toLocaleString('en-US')}` : '-';

// Helper to extract date from various formats
const extractDate = (point) => {
	if (point?.date instanceof Date) {
		return point.date;
	}
	// Try various date field names
	const dateStr = point?.date || point?.departure || point?.departure_date || point?.outbound_date || point?.departureDate;
	if (!dateStr) return null;
	const date = new Date(dateStr);
	return date instanceof Date && !isNaN(date.getTime()) ? date : null;
};

const createPriceMap = (data) => {
	const map = new Map();
	(data || []).forEach((point) => {
		const date = extractDate(point);
		if (!date || !Number.isFinite(point?.price)) {
			return;
		}
		map.set(normalizeDateKey(date), {
			price: point.price,
			isLowest: Boolean(point?.isLowest || point?.is_lowest_price)
		});
	});
	return map;
};

const buildMonths = (data, priceMap) => {
	if (!data?.length) return [];

	const sorted = [...data]
		.map((item) => {
			const date = extractDate(item);
			if (!date) return null;
			return {
				...item,
				date,
				timestamp: date.getTime()
			};
		})
		.filter((item) => item && item.date instanceof Date && Number.isFinite(item.timestamp))
		.sort((a, b) => a.timestamp - b.timestamp);
		if (!sorted.length) return [];
		const first = new Date(sorted[0].date);
		first.setHours(0, 0, 0, 0);
		first.setDate(1);
		const last = new Date(sorted[sorted.length - 1].date);
		last.setHours(0, 0, 0, 0);
		last.setMonth(last.getMonth() + 1, 0);

		const months = [];
		const cursor = new Date(first);
		while (cursor <= last) {
			const year = cursor.getFullYear();
			const monthIndex = cursor.getMonth();
			const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
			const firstWeekday = new Date(year, monthIndex, 1).getDay();
			const cells = [];

			for (let i = 0; i < firstWeekday; i += 1) {
				cells.push({ empty: true, key: `pre-${year}-${monthIndex}-${i}` });
			}

			for (let day = 1; day <= daysInMonth; day += 1) {
				const date = new Date(year, monthIndex, day);
				const key = normalizeDateKey(date);
				const priceData = priceByDate.get(key);
				const price = priceData?.price;
				const isLowest = priceData?.isLowest || false;
				cells.push({
					empty: false,
					date,
					key,
					price,
					isLowest,
					hasPrice: Number.isFinite(price)
				});
			}

			while (cells.length % 7 !== 0) {
				const fillerIndex = cells.length;
				cells.push({ empty: true, key: `post-${year}-${monthIndex}-${fillerIndex}` });
			}

			months.push({
				key: `${year}-${monthIndex}`,
				label: monthNumericFormatter.format(new Date(year, monthIndex, 1)),
				cells
			});

			cursor.setMonth(cursor.getMonth() + 1, 1);
		}

		return months;
	};

$: priceByDate = createPriceMap(calendarData);
$: calendarMonths = buildMonths(calendarData, priceByDate);
$: {
	if (!calendarMonths.length) {
		currentMonthIndex = 0;
	} else if (currentMonthIndex >= calendarMonths.length) {
		currentMonthIndex = calendarMonths.length - 1;
	}
}

const showPreviousMonth = () => {
	if (currentMonthIndex > 0) {
		currentMonthIndex -= 1;
	}
};

const showNextMonth = () => {
	if (currentMonthIndex < calendarMonths.length - 1) {
		currentMonthIndex += 1;
	}
};
</script>

{#if calendarData?.length}
	{#if layout === 'horizontal'}
		<!-- Horizontal list layout for one-way trips -->
		<div class="horizontal-calendar-container">
			<div class="horizontal-calendar-wrapper">
				<div class="horizontal-dates-row">
					{#each calendarData as item, index (`${item.timestamp ?? (item.date?.getTime ? item.date.getTime() : '')}-${index}`)}
						{@const date = extractDate(item)}
						{#if date instanceof Date}
							{@const dateKey = normalizeDateKey(date)}
							{@const prefixedKey = `${direction}-${dateKey}`}
							{@const isSelected = !disabled && selectedDates.has(prefixedKey)}
							{@const hasPrice = item.price !== undefined && Number.isFinite(item.price)}
							{@const isLowest = Boolean(item?.isLowest || item?.is_lowest_price)}
							<div
								class="horizontal-date-item {hasPrice ? 'has-price' : 'no-price'} {isSelected ? 'selected' : ''} {disabled ? 'disabled' : ''}"
								role={hasPrice && !disabled ? 'button' : undefined}
								on:click={() => {
									if (hasPrice && !disabled) {
										toggleDateSelection(dateKey);
									}
								}}
								on:keydown={(e) => {
									if (hasPrice && !disabled && (e.key === 'Enter' || e.key === ' ')) {
										e.preventDefault();
										toggleDateSelection(dateKey);
									}
								}}
							>
								<div class="horizontal-date-label">
									{new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(date)}
								</div>
								<div class="horizontal-price {isLowest ? 'is-lowest' : ''}">
									{hasPrice ? formatPrice(item.price) : '-'}
								</div>
							</div>
						{/if}
					{/each}
				</div>
			</div>
		</div>
	{:else}
		<!-- Calendar grid layout for round trips -->
		{#if calendarMonths.length}
			<div class="calendar-container">
				<div class="calendar-wrapper">
					<div class="calendar-nav">
						<button
							type="button"
							class="nav-button"
							on:click={showPreviousMonth}
							disabled={currentMonthIndex === 0}
						>
							←
						</button>
						<div class="calendar-month-label">
							{calendarMonths[currentMonthIndex]?.label}
						</div>
						<button
							type="button"
							class="nav-button"
							on:click={showNextMonth}
							disabled={currentMonthIndex === calendarMonths.length - 1}
						>
							→
						</button>
					</div>
					<div class="calendar-grid">
					{#each weekdayLabels as weekday}
						<div class="calendar-weekday">{weekday}</div>
					{/each}
					{#each calendarMonths[currentMonthIndex]?.cells as cell (cell.key)}
						{#if cell.empty}
							<div class="calendar-day empty"></div>
						{:else}
							{@const dateKey = normalizeDateKey(cell.date)}
							{@const prefixedKey = `${direction}-${dateKey}`}
							{@const isSelected = !disabled && selectedDates.has(prefixedKey)}
							<div
								class="calendar-day {cell.hasPrice ? 'has-price' : 'no-price'} {isSelected ? 'selected' : ''} {disabled ? 'disabled' : ''}"
								role={cell.hasPrice && !disabled ? 'button' : undefined}
								on:click={() => {
									if (cell.hasPrice && !disabled) {
										toggleDateSelection(dateKey);
									}
								}}
								on:keydown={(e) => {
									if (cell.hasPrice && !disabled && (e.key === 'Enter' || e.key === ' ')) {
										e.preventDefault();
										toggleDateSelection(dateKey);
									}
								}}
							>
								<span class="calendar-date">{cell.date.getDate()}</span>
								<span class="calendar-price {cell.isLowest ? 'is-lowest' : ''}">
									{cell.hasPrice ? formatPrice(cell.price) : '-'}
								</span>
							</div>
						{/if}
					{/each}
					</div>
				</div>
			</div>
		{:else}
			<div class="calendar-empty">
				Daily price calendar will appear once data is available.
			</div>
		{/if}
	{/if}
{:else}
	<div class="calendar-empty">
		Daily price calendar will appear once data is available.
	</div>
{/if}

<style>
.calendar-container {
	margin-top: 1rem;
	display: flex;
	flex-direction: column;
	gap: 0.65rem;
	width: 100%;
}

.calendar-wrapper {
	aspect-ratio: 1;
	width: 100%;
	max-width: 480px;
	margin: 0 auto;
	display: flex;
	flex-direction: column;
	gap: 0.4rem;
}

.calendar-nav {
	display: flex;
	align-items: center;
	justify-content: space-between;
	flex-shrink: 0;
}

.calendar-month-label {
	font-weight: 600;
	color: #0f172a;
	font-size: 0.875rem;
}

:global(.dark) .calendar-month-label {
	color: #f8fafc;
}

.calendar-grid {
	display: grid;
	grid-template-columns: repeat(7, minmax(0, 1fr));
	gap: 0.2rem;
	max-width: 100%;
	width: 100%;
	flex: 1;
	min-height: 0;
	box-sizing: border-box;
	overflow: visible;
}

.nav-button {
	padding: 0.3rem 0.5rem;
	border-radius: 0.4rem;
	border: 1px solid rgba(148, 163, 184, 0.6);
	background: rgba(255, 255, 255, 0.9);
	color: #0f172a;
	font-weight: 500;
	font-size: 1rem;
	transition: background 0.15s ease, color 0.15s ease;
	display: flex;
	align-items: center;
	justify-content: center;
	min-width: 2rem;
}

.nav-button:hover:not(:disabled) {
	background: rgba(15, 23, 42, 0.08);
}

.nav-button:disabled {
	opacity: 0.4;
	cursor: not-allowed;
}

:global(.dark) .nav-button {
	background: rgba(15, 23, 42, 0.8);
	color: #f8fafc;
	border-color: rgba(148, 163, 184, 0.5);
}

	.calendar-weekday {
		aspect-ratio: 1;
		text-align: center;
		font-size: 0.65rem;
		color: rgba(71, 85, 105, 0.8);
		font-weight: 600;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		max-width: 100%;
		box-sizing: border-box;
	}

	.calendar-day {
		aspect-ratio: 1;
		border-radius: 50%;
		padding: 0.15rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		background: transparent;
		width: 100%;
		max-width: 100%;
		box-sizing: border-box;
		overflow: hidden;
		transition: background 0.2s ease, border-radius 0.2s ease;
	}

	.calendar-day.has-price {
		background: transparent;
		border: none;
		cursor: pointer;
	}

	.calendar-day.has-price.selected {
		position: relative;
	}

	.calendar-day.has-price.selected::before {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 60%;
		height: 60%;
		background: rgba(148, 163, 184, 0.25);
		border-radius: 0.2rem;
		z-index: 0;
	}

	.calendar-day.has-price:hover:not(.disabled) {
		background: #0f172a;
		border-radius: 0.4rem;
	}

	.calendar-day.disabled {
		cursor: default;
	}

	.calendar-day.has-price.selected:hover:not(.disabled)::before {
		display: none;
	}

	.calendar-day.has-price.selected:hover:not(.disabled) {
		background: #0f172a;
	}

	.calendar-day.no-price {
		opacity: 0.6;
		cursor: default;
	}

	.calendar-day.empty {
		background: transparent;
		border: none;
		cursor: default;
	}

	.calendar-date {
		font-weight: 600;
		color: #0f172a;
		transition: color 0.2s ease;
		font-size: 0.65rem;
		position: relative;
		z-index: 1;
	}

	:global(.dark) .calendar-date {
		color: #f8fafc;
	}

	.calendar-day.has-price:hover:not(.disabled) .calendar-date {
		color: #f8fafc;
	}

	.calendar-price {
		font-size: 0.75rem;
		margin-top: 0.2rem;
		color: rgba(71, 85, 105, 0.95);
		transition: color 0.2s ease;
		position: relative;
		z-index: 1;
	}

	.calendar-price.is-lowest {
		color: #10b981;
		font-weight: 700;
	}

	:global(.dark) .calendar-price {
		color: rgba(226, 232, 240, 0.9);
	}

	:global(.dark) .calendar-price.is-lowest {
		color: #34d399;
	}

	.calendar-day.has-price:hover:not(.disabled) .calendar-price {
		color: #f8fafc;
	}

	.calendar-day.has-price:hover:not(.disabled) .calendar-price.is-lowest {
		color: #f8fafc;
	}

	.calendar-empty {
		margin-top: 1rem;
		min-height: 80px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 0.75rem;
		border: 1px dashed rgba(148, 163, 184, 0.4);
		color: rgba(71, 85, 105, 0.75);
		font-size: 0.85rem;
		text-align: center;
		padding: 0.75rem;
	}

	:global(.dark) .calendar-empty {
		border-color: rgba(148, 163, 184, 0.3);
		color: rgba(226, 232, 240, 0.65);
	}

	/* Horizontal layout styles for one-way trips */
	.horizontal-calendar-container {
		margin-top: 1rem;
		width: 100%;
	}

	.horizontal-calendar-wrapper {
		width: 100%;
		overflow-x: auto;
		overflow-y: visible;
		padding: 0.5rem 0;
	}

	.horizontal-dates-row {
		display: flex;
		gap: 0.5rem;
		min-width: min-content;
		padding: 0 0.25rem;
	}

	.horizontal-date-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: flex-start;
		min-width: 60px;
		padding: 0.5rem 0.4rem;
		border-radius: 0.5rem;
		background: transparent;
		border: 1px solid transparent;
		cursor: pointer;
		transition: background 0.2s ease, border-color 0.2s ease;
		flex-shrink: 0;
	}

	.horizontal-date-item.has-price:hover:not(.disabled) {
		background: rgba(15, 23, 42, 0.08);
		border-color: rgba(148, 163, 184, 0.3);
	}

	.horizontal-date-item.has-price.selected {
		background: rgba(148, 163, 184, 0.15);
		border-color: rgba(148, 163, 184, 0.5);
	}

	.horizontal-date-item.has-price.selected:hover:not(.disabled) {
		background: rgba(15, 23, 42, 0.12);
	}

	.horizontal-date-item.no-price {
		opacity: 0.4;
		cursor: default;
	}

	.horizontal-date-item.disabled {
		cursor: default;
		opacity: 0.6;
	}

	.horizontal-date-label {
		font-size: 0.7rem;
		font-weight: 600;
		color: #0f172a;
		margin-bottom: 0.3rem;
		text-align: center;
		white-space: nowrap;
	}

	:global(.dark) .horizontal-date-label {
		color: #f8fafc;
	}

	.horizontal-price {
		font-size: 0.75rem;
		color: rgba(71, 85, 105, 0.95);
		font-weight: 500;
		text-align: center;
		white-space: nowrap;
	}

	.horizontal-price.is-lowest {
		color: #10b981;
		font-weight: 700;
	}

	:global(.dark) .horizontal-price {
		color: rgba(226, 232, 240, 0.9);
	}

	:global(.dark) .horizontal-price.is-lowest {
		color: #34d399;
	}

	.horizontal-date-item.has-price:hover:not(.disabled) .horizontal-date-label {
		color: #0f172a;
	}

	.horizontal-date-item.has-price:hover:not(.disabled) .horizontal-price {
		color: rgba(71, 85, 105, 0.95);
	}

	:global(.dark) .horizontal-date-item.has-price:hover:not(.disabled) .horizontal-date-label {
		color: #f8fafc;
	}

	:global(.dark) .horizontal-date-item.has-price:hover:not(.disabled) .horizontal-price {
		color: rgba(226, 232, 240, 0.9);
	}
</style>

