<script>
  import { getContext } from 'svelte';
  import FlightResultsTable from '$lib/components/FlightResultsTable.svelte';

  const i18n = getContext('i18n');

  export let searchResults = [];
  export let selectedFlights;
  export let selectedFlightObjects = [];
  export let onToggleFlight = () => {};
  export let onToggleSelectAll = () => {};
  export let onPost = () => {};
  export let isPosting = false;
  export let aiStage = '';

  export let selectedRAGModel = null;
  export let selectedBaseModel = null;
  export let selectedAdapter = null;
  export let selectedModel = null;
export let showCalendarButton = false;
export let onOpenCalendar = () => {};
export let showBarChartButton = false;
export let onOpenBarChart = () => {};
export let otherFlights = [];
</script>

{#if searchResults.length > 0}
  <div class="space-y-4">
    <FlightResultsTable
      flights={searchResults}
      {selectedFlights}
      {selectedFlightObjects}
      {onToggleFlight}
      {onToggleSelectAll}
      {onPost}
      {isPosting}
      {aiStage}
      bind:selectedRAGModel
      bind:selectedBaseModel
      bind:selectedAdapter
      bind:selectedModel
      title={$i18n.t('Best flight')}
    />

    {#if showCalendarButton || showBarChartButton}
      <div class="flex justify-end gap-3">
        {#if showCalendarButton}
          <button
          type="button"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500"
          on:click={() => {
            console.log('View Price Calendar button clicked');
            if (typeof onOpenCalendar === 'function') {
              onOpenCalendar();
            }
          }}
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="16" y1="2" x2="16" y2="6"></line>
            <line x1="8" y1="2" x2="8" y2="6"></line>
            <line x1="3" y1="10" x2="21" y2="10"></line>
          </svg>
          {$i18n.t('View Price Calendar')}
          </button>
        {/if}

        {#if showBarChartButton}
          <button
            type="button"
            class="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-blue-400 dark:border-blue-500 text-sm font-medium text-blue-600 dark:text-blue-300 bg-white dark:bg-gray-800 hover:bg-blue-50 dark:hover:bg-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500"
            on:click={() => {
              console.log('View Price Trend Chart button clicked');
              if (typeof onOpenBarChart === 'function') {
                onOpenBarChart();
              }
            }}
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="4" y1="19" x2="4" y2="10"></line>
              <line x1="10" y1="19" x2="10" y2="5"></line>
              <line x1="16" y1="19" x2="16" y2="8"></line>
              <line x1="22" y1="19" x2="22" y2="12"></line>
            </svg>
            {$i18n.t('View Price Trend')}
          </button>
        {/if}
      </div>
    {/if}

    {#if otherFlights.length}
      <FlightResultsTable
        flights={otherFlights}
        {selectedFlights}
        {selectedFlightObjects}
        {onToggleFlight}
        {onToggleSelectAll}
        {onPost}
        {isPosting}
        {aiStage}
        bind:selectedRAGModel
        bind:selectedBaseModel
        bind:selectedAdapter
        bind:selectedModel
        title={$i18n.t('Other flights')}
      />
    {/if}
  </div>
{:else}
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
    <div class="text-center py-12">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.29-1.009-5.824-2.709M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
        {$i18n.t('No flights found')}
      </h3>
      <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
        {$i18n.t('Try adjusting your search criteria')}
      </p>
    </div>
  </div>
{/if}

