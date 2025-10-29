<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let savedSearches = [];
	export let selectedSearchId = null;
	export let loadingSearches = new Set();

	const selectSearch = (searchId) => {
		dispatch('selectSearch', searchId);
	};

	const runSearch = (searchId) => {
		dispatch('runSearch', searchId);
	};

	const deleteSearch = (searchId) => {
		dispatch('deleteSearch', searchId);
	};
</script>

<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4">
	<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
		Saved Searches
	</h3>
	<div class="space-y-2">
		{#each savedSearches as search (search.id)}
			<div 
				class="p-3 rounded-lg border cursor-pointer transition-all {
					selectedSearchId === search.id 
						? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
						: 'border-gray-300 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700'
				}"
				role="button"
				tabindex="0"
				on:click={() => selectSearch(search.id)}
				on:keydown={(e) => e.key === 'Enter' && selectSearch(search.id)}
			>
				<!-- Route -->
				<div class="font-medium text-gray-900 dark:text-gray-100 text-sm mb-2">
					{search.departureDisplay} → {search.destinationDisplay}
				</div>
				
				<!-- Time -->
				<div class="text-xs text-gray-600 dark:text-gray-400 mb-2">
					🕐 Daily at {search.autoSearchTime}
				</div>
				
				<!-- Status -->
				<div class="flex items-center justify-between">
					<span class="text-xs {
						search.enabled ? 'text-green-600 dark:text-green-400' : 'text-gray-500'
					}">
						{search.enabled ? '✓ Enabled' : '✗ Disabled'}
					</span>
					
					<div class="flex gap-1">
						<!-- Refresh Mini Button -->
						<button
							on:click|stopPropagation={() => runSearch(search.id)}
							disabled={loadingSearches.has(search.id)}
							class="px-2 py-1 bg-black hover:bg-gray-800 text-white rounded text-xs transition disabled:opacity-50"
							title="Refresh"
						>
							{#if loadingSearches.has(search.id)}
								<svg class="animate-spin h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
							{:else}
								<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
								</svg>
							{/if}
						</button>
						<!-- Delete Mini Button -->
						<button
							on:click|stopPropagation={() => deleteSearch(search.id)}
							class="px-2 py-1 bg-black hover:bg-gray-800 text-white rounded text-xs transition"
							title="Delete"
						>
							<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
							</svg>
						</button>
					</div>
				</div>
			</div>
		{/each}
	</div>
</div>

