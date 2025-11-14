<script>
	import { createEventDispatcher } from 'svelte';
	import AIModelSelect from '$lib/components/layout/AIModelSelect.svelte';

	export let calendarData = [];
	export let selectedDates = new Set();
	export let filteredModels = [];
	export let selectedModel = null;

	const dispatch = createEventDispatcher();

	const normalizeDateKey = (date) => {
		if (!(date instanceof Date)) return '';
		const year = date.getFullYear();
		const month = String(date.getMonth() + 1).padStart(2, '0');
		const day = String(date.getDate()).padStart(2, '0');
		return `${year}-${month}-${day}`;
	};

	// Helper to check if a date is selected (handles both prefixed and non-prefixed keys)
	const isDateSelected = (date, direction) => {
		const dateKey = normalizeDateKey(date);
		// Check both prefixed and non-prefixed keys for backward compatibility
		return selectedDates.has(`${direction}-${dateKey}`) || selectedDates.has(dateKey);
	};

	const formatPrice = (price) =>
		Number.isFinite(price) ? `HK$${Math.round(price).toLocaleString('en-US')}` : '-';

	const formatDate = (date) => {
		if (!(date instanceof Date)) return '';
		return new Intl.DateTimeFormat('en-GB', {
			day: 'numeric',
			month: 'numeric',
			year: 'numeric'
		}).format(date);
	};

	const getUniqueKey = (item, index) => {
		// Create a unique key using date, direction, route, and index as fallback
		const dateKey = item.date instanceof Date ? item.date.getTime() : '';
		const direction = item.direction || '';
		const routeFrom = item.route_from || '';
		const routeTo = item.route_to || '';
		// Include index to ensure uniqueness even if all other fields match
		return `${dateKey}-${direction}-${routeFrom}-${routeTo}-${index}`;
	};

	$: cheapestPrices = (() => {
		if (!calendarData?.length || !selectedDates?.size) return [];

		// Filter for items that are in selectedDates
		const selectedPrices = calendarData
			.filter(
				(item) =>
					item?.date instanceof Date &&
					Number.isFinite(item?.price) &&
					isDateSelected(item.date, item.direction || 'departure')
			)
			.sort((a, b) => {
				// Sort by date first, then by direction (departure before return)
				if (a.timestamp !== b.timestamp) {
					return a.timestamp - b.timestamp;
				}
				// If same date, departure comes before return
				if (a.direction === 'departure' && b.direction === 'return') return -1;
				if (a.direction === 'return' && b.direction === 'departure') return 1;
				return 0;
			})
			.map((item) => ({
				date: item.date,
				price: item.price,
				formattedDate: formatDate(item.date),
				formattedPrice: formatPrice(item.price),
				route_from: item.route_from || '',
				route_to: item.route_to || '',
				direction: item.direction || '',
				airline_code: item.airline_code || '',
				airline_name: item.airline_name || ''
			}));

		return selectedPrices;
	})();

	const handlePost = () => {
		if (cheapestPrices.length === 0) {
			alert('Please select at least one date to post');
			return;
		}
		
		if (!selectedModel) {
			alert('Please select an AI model to use for content generation');
			return;
		}

		dispatch('post', {
			selectedDates: cheapestPrices,
			model: selectedModel
		});
	};
</script>

{#if cheapestPrices.length > 0}
	<div class="cheapest-prices-container">
		<div class="cheapest-prices-header">
			<span class="cheapest-prices-title">Selected Lowest Price List</span>
			<span class="cheapest-prices-count">{cheapestPrices.length} dates</span>
		</div>
		<div class="cheapest-prices-list">
			{#each cheapestPrices as item, index (getUniqueKey(item, index))}
				<div class="cheapest-price-item">
					<div class="cheapest-price-left">
						<span class="cheapest-price-date">{item.formattedDate}</span>
						{#if item.route_from && item.route_to}
							<span class="cheapest-price-route">
								{item.route_from} → {item.route_to}
							</span>
						{/if}
					</div>
					<span class="cheapest-price-value">{item.formattedPrice}</span>
				</div>
			{/each}
		</div>

		<!-- AI Model Selection and Post Button -->
		<div class="cheapest-prices-actions">
			<div class="cheapest-prices-model-select">
				<AIModelSelect
					id="cheapest-model-select"
					{filteredModels}
					bind:selectedModel
				/>
			</div>

			<button
				class="cheapest-prices-post-button"
				disabled={!selectedModel || cheapestPrices.length === 0}
				on:click={handlePost}
			>
				Post
			</button>
		</div>
	</div>
{/if}

<style>
	.cheapest-prices-container {
		margin-top: 1rem;
		width: 100%;
	}

	.cheapest-prices-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.cheapest-prices-title {
		font-weight: 600;
		font-size: 0.875rem;
		color: #0f172a;
	}

	:global(.dark) .cheapest-prices-title {
		color: #f8fafc;
	}

	.cheapest-prices-count {
		font-size: 0.75rem;
		color: rgba(71, 85, 105, 0.8);
	}

	:global(.dark) .cheapest-prices-count {
		color: rgba(226, 232, 240, 0.7);
	}

	.cheapest-prices-list {
		max-height: 200px;
		overflow-y: auto;
		border: 1px solid rgba(148, 163, 184, 0.3);
		border-radius: 0.5rem;
		background: rgba(255, 255, 255, 0.5);
	}

	:global(.dark) .cheapest-prices-list {
		background: rgba(15, 23, 42, 0.5);
		border-color: rgba(148, 163, 184, 0.2);
	}

	.cheapest-prices-list::-webkit-scrollbar {
		width: 6px;
	}

	.cheapest-prices-list::-webkit-scrollbar-track {
		background: rgba(148, 163, 184, 0.1);
		border-radius: 3px;
	}

	.cheapest-prices-list::-webkit-scrollbar-thumb {
		background: rgba(148, 163, 184, 0.4);
		border-radius: 3px;
	}

	.cheapest-prices-list::-webkit-scrollbar-thumb:hover {
		background: rgba(148, 163, 184, 0.6);
	}

	.cheapest-price-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 0.75rem;
		border-bottom: 1px solid rgba(148, 163, 184, 0.15);
		transition: background 0.15s ease;
	}

	.cheapest-price-left {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		flex: 1;
	}

	.cheapest-price-item:last-child {
		border-bottom: none;
	}

	.cheapest-price-item:hover {
		background: rgba(148, 163, 184, 0.08);
	}

	:global(.dark) .cheapest-price-item:hover {
		background: rgba(148, 163, 184, 0.12);
	}

	.cheapest-price-date {
		font-size: 0.75rem;
		color: rgba(71, 85, 105, 0.9);
		font-weight: 500;
	}

	:global(.dark) .cheapest-price-date {
		color: rgba(226, 232, 240, 0.9);
	}

	.cheapest-price-route {
		font-size: 0.7rem;
		color: rgba(71, 85, 105, 0.7);
		font-weight: 400;
	}

	:global(.dark) .cheapest-price-route {
		color: rgba(226, 232, 240, 0.7);
	}

	.cheapest-price-value {
		font-size: 0.8rem;
		font-weight: 600;
		color: #0f172a;
	}

	:global(.dark) .cheapest-price-value {
		color: #f8fafc;
	}

	.cheapest-prices-actions {
		margin-top: 1rem;
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 1rem;
		padding-top: 1rem;
		border-top: 1px solid rgba(148, 163, 184, 0.2);
	}

	.cheapest-prices-model-select {
		flex: 1;
		max-width: 300px;
	}


	.cheapest-prices-post-button {
		flex-shrink: 0;
		padding: 0.5rem 1.5rem;
		background: #0f172a;
		color: #f8fafc;
		font-weight: 500;
		border-radius: 0.5rem;
		border: none;
		cursor: pointer;
		transition: background 0.2s ease;
		font-size: 0.875rem;
	}

	.cheapest-prices-post-button:hover:not(:disabled) {
		background: #1e293b;
	}

	.cheapest-prices-post-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	:global(.dark) .cheapest-prices-post-button {
		background: #f8fafc;
		color: #0f172a;
	}

	:global(.dark) .cheapest-prices-post-button:hover:not(:disabled) {
		background: #e2e8f0;
	}
</style>

