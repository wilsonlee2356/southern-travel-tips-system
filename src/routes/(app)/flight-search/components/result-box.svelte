<script>
  import { getContext } from 'svelte';
  import { models } from '$lib/stores';
  import FlightResultsTable from '$lib/components/FlightResultsTable.svelte';
  import AIModelSelect from '$lib/components/layout/AIModelSelect.svelte';

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

  // Popup state
  let showSelectedFlightsPopup = false;
  let expandedPopupRows = new Set();

  const togglePopupRowExpansion = (flightId) => {
    const next = new Set(expandedPopupRows);
    if (next.has(flightId)) {
      next.delete(flightId);
    } else {
      next.add(flightId);
    }
    expandedPopupRows = next;
  };

  // Helper functions for formatting
  const sanitizeString = (value) => (typeof value === 'string' ? value.trim() : null);

  const formatDateDisplay = (value) => {
    const sanitized = sanitizeString(value);
    if (!sanitized) return null;
    const date = new Date(sanitized);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString();
    }
    return sanitized;
  };

  const formatTimeDisplay = (value) => {
    const sanitized = sanitizeString(value);
    if (!sanitized) return '—';
    if (sanitized.includes(':') && sanitized.split(':').length === 3) {
      return sanitized.substring(0, 5);
    }
    return sanitized;
  };

  const formatDateTimeInline = (label, dateValue, timeValue) => {
    const sanitizedLabel = sanitizeString(label);
    if (sanitizedLabel) return sanitizedLabel;
    const timePart = formatTimeDisplay(timeValue);
    const datePart = formatDateDisplay(dateValue);
    const pieces = [];
    if (timePart && timePart !== '—') pieces.push(timePart);
    if (datePart) pieces.push(datePart);
    return pieces.length ? pieces.join(' ') : '—';
  };

  // Handle AI model selection change
  function handleAIModelChange(event) {
    const selectedValue = event.target.value;
    
    selectedAdapter = null;
    selectedRAGModel = null;
    selectedBaseModel = null;
    selectedModel = null;
    
    if (!selectedValue) return;
    
    const fullModelId = selectedValue.substring(6);
    selectedModel = ($models || []).find(m => m.id === fullModelId) || null;
  }
  
  // Allowed model patterns
  const allowedModelPatterns = [
    /^gpt-4$/i,
    /^gpt-?4\.1$/i,
    /^gpt-?5\.1$/i,
    /^gpt-?5\.2$/i,
    /^gemini-?2\.5-?flash$/i,
    /^gemini-?2\.0-?flash$/i,
    /^gemini-?2\.0-?flash-?live$/i
  ];

  const isAllowedModel = (model) => {
    if (model?.owned_by === 'ollama') {
      return true;
    }
    if (!model?.owned_by) {
      const hasOllamaProperties = model?.details || model?.ollama || (model?.model && model?.external === false);
      if (hasOllamaProperties) {
        return true;
      }
    }
    
    let modelId = (model?.id || '').toLowerCase().trim();
    let modelName = (model?.name || '').toLowerCase().trim();
    
    if (modelId.startsWith('models/')) {
      modelId = modelId.substring(7);
    }
    if (modelName.startsWith('models/')) {
      modelName = modelName.substring(7);
    }
    
    return allowedModelPatterns.some(pattern => {
      return pattern.test(modelId) || pattern.test(modelName);
    });
  };

  // AI model options
  $: aiModelOptions = (() => {
    const filtered = ($models || []).filter(model => isAllowedModel(model));
    
    return filtered.map(model => ({
      value: `model:${model.id}`,
      label: `${model.name || model.id}${model.owned_by && model.owned_by !== 'ollama' ? ` (${model.owned_by})` : ''}`,
      type: 'all_models',
      modelId: model.id,
      ownedBy: model.owned_by
    }));
  })();
  
  $: currentSelectedValue = selectedModel ? `model:${selectedModel.id}` : '';

  // Close popup when clicking outside
  function handleBackdropClick(event) {
    if (event.target === event.currentTarget) {
      showSelectedFlightsPopup = false;
    }
  }

  // Close popup on Escape key
  function handleKeydown(event) {
    if (event.key === 'Escape' && showSelectedFlightsPopup) {
      showSelectedFlightsPopup = false;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

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

<!-- Floating Button for Selected Flights -->
{#if selectedFlights && selectedFlights.size > 0}
  <button
    type="button"
    class="fixed bottom-6 right-6 z-50 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg p-4 flex items-center gap-2 transition-all hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
    on:click={() => showSelectedFlightsPopup = true}
    aria-label="View selected flights"
  >
    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"></path>
    </svg>
    <span class="font-semibold text-lg">{selectedFlights.size}</span>
  </button>
{/if}

<!-- Selected Flights Popup Modal -->
{#if showSelectedFlightsPopup && selectedFlights && selectedFlights.size > 0}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 dark:bg-gray-900/50 backdrop-blur-sm"
    on:click={handleBackdropClick}
    role="dialog"
    aria-modal="true"
    aria-labelledby="selected-flights-title"
  >
    <div
      class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col"
      on:click|stopPropagation
    >
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 id="selected-flights-title" class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {$i18n.t('Selected Flights')} ({selectedFlights.size})
        </h3>
        <button
          type="button"
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
          on:click={() => showSelectedFlightsPopup = false}
          aria-label="Close"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      
      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- Mobile Layout - visible on screens < 768px -->
        <div class="block md:hidden space-y-3">
          {#each selectedFlightObjects as flight (flight.id)}
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border border-gray-200 dark:border-gray-700">
              <!-- Remove Button -->
              <div class="mb-3 flex justify-end">
                <button
                  type="button"
                  class="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                  on:click={() => onToggleFlight(flight.id)}
                  aria-label="Remove flight"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>
              
              <!-- Top Row: Departure → Arrival | Price -->
              <div class="flex items-start justify-between mb-3">
                <div class="flex items-center gap-2 flex-1 min-w-0">
                  <!-- Departure -->
                  <div class="flex flex-col items-start">
                    <div class="text-base font-semibold text-gray-900 dark:text-gray-100">
                      {formatTimeDisplay(flight.departureTime) || '—'}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {flight.startingPlaceCode || '—'}
                    </div>
                  </div>
                  
                  <!-- Arrow -->
                  <svg class="w-4 h-4 text-gray-400 flex-shrink-0 mt-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                  
                  <!-- Arrival -->
                  <div class="flex flex-col items-start">
                    <div class="text-base font-semibold text-gray-900 dark:text-gray-100">
                      {formatTimeDisplay(flight.arrivalTime) || '—'}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {flight.destinationCode || '—'}
                    </div>
                  </div>
                </div>
                
                <!-- Price -->
                <div class="ml-3 flex-shrink-0">
                  <div class="text-lg font-semibold text-green-600 dark:text-green-400">
                    {#if flight.displayPrice}
                      {flight.displayPrice}
                    {:else if flight.cost != null}
                      {flight.currency || '$'}{flight.cost}
                    {:else}
                      —
                    {/if}
                  </div>
                </div>
              </div>
              
              <!-- Bottom Row: Airline Icon with Duration and Airline Name -->
              <div class="flex items-start gap-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <!-- Airline Icon -->
                <div class="flex-shrink-0">
                  {#if flight.airlineLogo}
                    <img src={flight.airlineLogo} alt="Airline logo" class="h-8 w-8 object-contain rounded-full border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900" loading="lazy" />
                  {:else}
                    <div class="h-8 w-8 rounded-full border border-gray-200 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                      <span class="text-xs text-gray-500 dark:text-gray-400">{flight.airlineCode || '—'}</span>
                    </div>
                  {/if}
                </div>
                
                <!-- Duration, Stops, and Airline Name - aligned left with icon -->
                <div class="flex flex-col items-start flex-1">
                  <div class="flex items-center gap-2 mb-1">
                    <span class="text-sm text-gray-600 dark:text-gray-400">
                      {flight.duration || 'N/A'}
                    </span>
                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {flight.segments > 1 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}">
                      {flight.segments > 1 ? `${flight.segments - 1} stop${flight.segments > 2 ? 's' : ''}` : 'Direct'}
                    </span>
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">
                    {flight.airline || 'N/A'}
                  </div>
                </div>
              </div>
            </div>
          {/each}
        </div>

        <!-- Desktop Table Layout - visible on screens >= 768px -->
        <div class="hidden md:block overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {$i18n.t('Airline')}
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {$i18n.t('From')}
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {$i18n.t('To')}
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {$i18n.t('Price')}
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {$i18n.t('Class')}
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {$i18n.t('Duration')}
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {$i18n.t('Stops')}
                </th>
                <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  <span class="sr-only">{$i18n.t('Actions')}</span>
                </th>
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {#each selectedFlightObjects as flight (flight.id)}
                <tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td class="px-4 py-4 whitespace-nowrap">
                    <div class="flex items-center gap-3">
                      {#if flight.airlineLogo}
                        <img
                          src={flight.airlineLogo}
                          alt={`${flight.airline ?? 'Airline'} logo`}
                          class="h-6 w-6 object-contain rounded-full border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900"
                          loading="lazy"
                        />
                      {/if}
                      <div>
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {flight.airline}
                        </div>
                        {#if flight.airlineCode}
                          <div class="text-xs text-gray-500 dark:text-gray-400">
                            {flight.airlineCode}
                          </div>
                        {/if}
                      </div>
                    </div>
                  </td>
                  <td class="px-4 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900 dark:text-gray-100">
                      {flight.startingPlace}
                    </div>
                    {#if flight.startingPlaceCode}
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {flight.startingPlaceCode}
                      </div>
                    {/if}
                  </td>
                  <td class="px-4 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900 dark:text-gray-100">
                      {flight.destination}
                    </div>
                    {#if flight.destinationCode}
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {flight.destinationCode}
                      </div>
                    {/if}
                  </td>
                  <td class="px-4 py-4 whitespace-nowrap">
                    <div class="text-sm font-semibold text-green-600 dark:text-green-400">
                      {#if flight.displayPrice}
                        {flight.displayPrice}
                      {:else if flight.cost != null}
                        {flight.currency || '$'}{flight.cost}
                      {:else}
                        —
                      {/if}
                    </div>
                  </td>
                  <td class="px-4 py-4 whitespace-nowrap">
                    {#if flight.seatClass}
                      <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {(flight.seatClass || '').toLowerCase() === 'business' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'}">
                        {flight.seatClass}
                      </span>
                    {:else}
                      <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                        {$i18n.t('N/A')}
                      </span>
                    {/if}
                  </td>
                  <td class="px-4 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900 dark:text-gray-100">
                      {flight.duration || 'N/A'}
                    </div>
                  </td>
                  <td class="px-4 py-4 whitespace-nowrap">
                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {flight.segments > 1 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}">
                      {flight.segments > 1 ? `${flight.segments - 1} stop${flight.segments > 2 ? 's' : ''}` : 'Direct'}
                    </span>
                  </td>
                  <td class="px-4 py-4 whitespace-nowrap text-right">
                    <div class="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        class="inline-flex items-center justify-center rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                        on:click={() => togglePopupRowExpansion(flight.id)}
                        aria-expanded={expandedPopupRows.has(flight.id)}
                        aria-label={expandedPopupRows.has(flight.id) ? $i18n.t('Hide details') : $i18n.t('Show details')}
                      >
                        <span class={`transform transition-transform ${expandedPopupRows.has(flight.id) ? 'rotate-180' : ''}`}>
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                          </svg>
                        </span>
                      </button>
                      <button
                        type="button"
                        class="inline-flex items-center justify-center rounded-full border border-red-300 dark:border-red-600 px-2.5 py-1 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
                        on:click={() => onToggleFlight(flight.id)}
                        aria-label="Remove flight"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
                {#if expandedPopupRows.has(flight.id)}
                  <tr class="bg-gray-50 dark:bg-gray-900/60">
                    <td colspan="8" class="px-6 py-4">
                      <div class="flex items-start justify-between gap-6">
                        <div class="flex flex-col items-center justify-between text-gray-300 dark:text-gray-600 self-stretch ml-70">
                          <span class="h-2 w-2 rounded-full bg-current transform translate-y-2"></span>
                          <div class="w-px flex-1 border-l border-dashed border-current"></div>
                          <span class="h-2 w-2 rounded-full bg-current transform -translate-y-2"></span>
                        </div>
                        <div class="flex flex-col items-start gap-6 flex-1">
                          <div class="flex flex-col">
                            <div class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                              {formatTimeDisplay(flight.departureTime)}
                              {#if flight.departureAirportName}
                                <span class="text-xs text-gray-500 dark:text-gray-400">{flight.departureAirportName}</span>
                              {/if}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                              {formatDateDisplay(flight.departureLocalDate) ?? '—'}
                            </div>
                          </div>
                          <div class="text-sm font-medium text-gray-700 dark:text-gray-300">
                            路程時間：{flight.totalDurationLabel}
                          </div>
                          <div class="flex flex-col">
                            <div class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                              {formatTimeDisplay(flight.arrivalTime)}
                              {#if flight.arrivalAirportName}
                                <span class="text-xs text-gray-500 dark:text-gray-400">{flight.arrivalAirportName}</span>
                              {/if}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                              {formatDateDisplay(flight.arrivalLocalDate) ?? '—'}
                            </div>
                          </div>
                        </div>
                        <div class="flex flex-col items-start text-sm text-gray-600 dark:text-gray-300 min-w-[200px]">
                          <div class="flex flex-col gap-3">
                            {#if flight.flightNumber}
                              <div class="flex items-center gap-3">
                                <div class="flex items-center justify-center w-6 h-6">
                                  <img src="/flight.png" alt="Flight number" class="w-6 h-6 object-contain" loading="lazy" />
                                </div>
                                <span>{flight.flightNumber}</span>
                              </div>
                            {/if}
                            {#if flight.seatClass}
                              <div class="flex items-center gap-3">
                                <div class="flex items-center justify-center w-6 h-6">
                                  <img src="/seat.png" alt="Travel class" class="w-6 h-6 object-contain" loading="lazy" />
                                </div>
                                <span>{flight.seatClass}</span>
                              </div>
                            {/if}
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Footer with AI Model Selection and Post Button -->
      <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
        <div class="flex flex-col gap-4">
          <!-- AI Model Selection -->
          <div class="flex items-center gap-4 flex-wrap">
            <div class="flex flex-col flex-1 min-w-[250px]">
              <AIModelSelect
                id="ai-model-select-popup"
                filteredModels={aiModelOptions}
                selectedModel={currentSelectedValue}
                placeholder="Select AI Model..."
                disabled={isPosting}
                onModelChange={handleAIModelChange}
              />
            </div>
            
            {#if selectedModel}
              <div class="flex flex-col flex-1 min-w-[250px]">
                <div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Selected Model
                </div>
                <div class="px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm">
                  <span class="text-gray-600 dark:text-gray-300">Model: <strong>{selectedModel.name || selectedModel.id}</strong></span>
                  {#if selectedModel.owned_by && selectedModel.owned_by !== 'ollama'}
                    <br><span class="text-indigo-600 dark:text-indigo-400">Provider: <strong>{selectedModel.owned_by}</strong></span>
                  {/if}
                </div>
              </div>
            {/if}
          </div>
          
          <!-- Post Button -->
          <div class="flex justify-end">
            <button
              class="bg-black hover:bg-gray-800 text-white font-medium py-3 px-8 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isPosting || !selectedModel}
              on:click={onPost}
            >
              {#if isPosting}
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {#if aiStage === 'initializing'}
                  Initializing AI Analysis...
                {:else if aiStage === 'stage1'}
                  Stage 1: Large Model Analysis...
                {:else if aiStage === 'generating_scenic_image'}
                  Generating Scenic Image...
                {:else}
                  Stage 2: Content Refinement...
                {/if}
              {:else}
                <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h18v18h-18z M8 8h8v8h-8z M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0 M16 7a1 1 0 1 0 0-2a1 1 0 1 0 0 2"></path>
                </svg>
                {$i18n.t('Post')} ({selectedFlights.size})
              {/if}
            </button>
          </div>
          
          <!-- Selection info -->
          {#if selectedModel}
            <div class="text-sm text-gray-600 dark:text-gray-400">
              Using model: <span class="font-medium">{selectedModel.name || selectedModel.id}</span>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

