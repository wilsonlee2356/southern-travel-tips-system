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
</script>

{#if searchResults.length > 0}
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
  />
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

