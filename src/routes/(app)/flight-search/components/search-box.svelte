<style>
  input[type='range']::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    height: 16px;
    width: 16px;
    border-radius: 9999px;
    background: black;
    border: 2px solid white;
    cursor: pointer;
  }

  input[type='range']::-moz-range-thumb {
    height: 16px;
    width: 16px;
    border-radius: 9999px;
    background: black;
    border: 2px solid white;
    cursor: pointer;
  }

  input[type='range']::-ms-thumb {
    height: 16px;
    width: 16px;
    border-radius: 9999px;
    background: black;
    border: 2px solid white;
    cursor: pointer;
  }

input[type='range'] {
  position: relative;
}

:global(.dark) input[type='range']::-webkit-slider-thumb {
    background: white;
    border-color: black;
  }

  :global(.dark) input[type='range']::-moz-range-thumb {
    background: white;
    border-color: black;
  }

  :global(.dark) input[type='range']::-ms-thumb {
    background: white;
    border-color: black;
  }
</style>
 <script>
  import { getContext, createEventDispatcher, tick, onMount } from 'svelte';
  import { airlineOptions } from '$lib/utils/airlines';

  const i18n = getContext('i18n');
 const dispatch = createEventDispatcher();
 
  export let searchError = '';
   export let searchForm;
   export let isSearching = false;
   export let startingPlaceInput = '';
   export let destinationInput = '';
   export let filteredStartingPlaces = [];
   export let filteredDestinations = [];
   export let showStartingPlaceDropdown = false;
   export let showDestinationDropdown = false;
 
   export let onSearch = () => {};
   export let onReset = () => {};
   export let onStartingPlaceInput = () => {};
   export let onDestinationInput = () => {};
   export let onStartingPlaceFocus = () => {};
   export let onDestinationFocus = () => {};
   export let onSelectStartingPlace = () => {};
   export let onSelectDestination = () => {};

  let showPassengerDropdown = false;
  let showAdvancedFilters = false;
  let showAirlineDropdown = false;
  let currentAdults = 1;
  let currentChildren = 0;
  let passengerSummary = '';
  let selectedAirlines = new Set();
  const priceRange = { min: 0, max: 20000, step: 50 };
  const durationRange = { min: 1, max: 30, step: 1 };
 let isPriceDragging = false;
 let isDurationDragging = false;
  let airlineButtonRef;
  let airlineDropdownRect = { top: 0, left: 0, width: 0, maxHeight: 360 };

  const closePassengerDropdown = () => {
     showPassengerDropdown = false;
   };

  const togglePassengerDropdown = () => {
     showPassengerDropdown = !showPassengerDropdown;
   };

  const toggleAdvancedFilters = () => {
    showAdvancedFilters = !showAdvancedFilters;
  };

  const updateAirlineDropdownPosition = () => {
    if (typeof window === 'undefined' || !airlineButtonRef) return;
    const rect = airlineButtonRef.getBoundingClientRect();
    const minWidth = 280;
    const gutter = 12;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const maxWidth = Math.min(viewportWidth - gutter * 2, Math.max(rect.width, minWidth));
    let left = rect.left;
    if (left + maxWidth > viewportWidth - gutter) {
      left = viewportWidth - gutter - maxWidth;
    }

    const top = rect.bottom + 8;
    const availableBelow = Math.max(0, viewportHeight - rect.bottom - 16);
    const desiredHeight = availableBelow * (4 / 3);
    const maxHeight = Math.max(320, Math.min(desiredHeight || viewportHeight * 0.6, viewportHeight - 80));

    airlineDropdownRect = {
      top,
      left,
      width: maxWidth,
      maxHeight
    };
  };

  const toggleAirlineDropdown = async () => {
    showAirlineDropdown = !showAirlineDropdown;
    if (showAirlineDropdown) {
      await tick();
      updateAirlineDropdownPosition();
    }
  };

  const emitPassengerChange = (adults, children) => {
    dispatch('passengerschange', {
      adults,
      children
    });
  };

  const emitFiltersChange = (updates) => {
    dispatch('filterschange', updates);
  };

 const handlePriceChange = (value) => {
    emitFiltersChange({ maxPrice: Number(value) });
  };

  const handleDurationChange = (value) => {
    emitFiltersChange({ maxDuration: Number(value) });
  };

  const incrementAdults = () => {
    const nextAdults = Math.min(9, currentAdults + 1);
    emitPassengerChange(nextAdults, currentChildren);
  };

  const decrementAdults = () => {
    const nextAdults = Math.max(1, currentAdults - 1);
    emitPassengerChange(nextAdults, currentChildren);
  };

  const incrementChildren = () => {
    const nextChildren = Math.min(9, currentChildren + 1);
    emitPassengerChange(currentAdults, nextChildren);
  };

  const decrementChildren = () => {
    const nextChildren = Math.max(0, currentChildren - 1);
    emitPassengerChange(currentAdults, nextChildren);
  };

  const formatPassengerSummary = (adults, children) => {
    const adultLabel = `${adults} ${adults === 1 ? 'Adult' : 'Adults'}`;
    const childLabel = `${children} ${children === 1 ? 'Child' : 'Children'}`;
    return children > 0 ? `${adultLabel}, ${childLabel}` : adultLabel;
  };

  $: currentAdults = Number(searchForm?.adults ?? 1);
  $: currentChildren = Number(searchForm?.children ?? 0);
  $: passengerSummary = formatPassengerSummary(currentAdults, currentChildren);
  $: selectedAirlines = new Set(searchForm?.airlines ?? []);
  $: currentMaxPrice = Number(searchForm?.maxPrice ?? priceRange.max);
  $: currentMaxDuration = Number(searchForm?.maxDuration ?? durationRange.max);
  $: priceThumbPosition = priceRange.max === priceRange.min
    ? 0
    : Math.min(
        100,
        Math.max(
          0,
          ((currentMaxPrice - priceRange.min) / (priceRange.max - priceRange.min)) * 100
        )
      );
  $: durationThumbPosition = durationRange.max === durationRange.min
    ? 0
    : Math.min(
        100,
        Math.max(
          0,
          ((currentMaxDuration - durationRange.min) / (durationRange.max - durationRange.min)) * 100
        )
      );
  $: airlineSummary = selectedAirlines.size === 0
    ? (i18n?.t?.('All airlines') ?? 'All airlines')
    : `${selectedAirlines.size} ${(i18n?.t?.('selected') ?? 'selected')}`;

  const handleStopsChange = (value) => {
    emitFiltersChange({ stops: value });
  };


  const handleAirlineToggle = (code) => {
    const updated = new Set(selectedAirlines);
    if (updated.has(code)) {
      updated.delete(code);
    } else {
      updated.add(code);
    }
    emitFiltersChange({ airlines: Array.from(updated) });
  };



 const handleWindowClick = (event) => {
    if (!event.target.closest('[data-passenger-dropdown]')) {
      closePassengerDropdown();
    }
    if (!event.target.closest('[data-airline-dropdown]')) {
      showAirlineDropdown = false;
    }
  };
  const handleWindowScroll = () => {
    if (showAirlineDropdown) {
      updateAirlineDropdownPosition();
    }
  };

  const handleDocumentScrollCapture = () => {
    if (showAirlineDropdown) {
      updateAirlineDropdownPosition();
    }
  };

  onMount(() => {
    document.addEventListener('scroll', handleDocumentScrollCapture, true);
    window.addEventListener('resize', handleWindowScroll);
    return () => {
      document.removeEventListener('scroll', handleDocumentScrollCapture, true);
      window.removeEventListener('resize', handleWindowScroll);
    };
  });

  const handleWindowKeydown = (event) => {
    if (event.key === 'Escape') {
      closePassengerDropdown();
    }
  };

  const handleWindowPointerUp = () => {
    isPriceDragging = false;
    isDurationDragging = false;
  };

 </script>

<svelte:window
  on:click={handleWindowClick}
  on:keydown={handleWindowKeydown}
  on:mouseup={handleWindowPointerUp}
  on:pointerup={handleWindowPointerUp}
  on:touchend={handleWindowPointerUp}
  on:touchcancel={handleWindowPointerUp}
  on:scroll={handleWindowScroll}
  on:resize={handleWindowScroll}
/>

<div class="bg-white dark:bg-gray-800 rounded-t-lg rounded-b-none shadow-lg p-6 border border-gray-200 dark:border-gray-700 border-b border-b-gray-200 dark:border-b-gray-700">
   <div class="flex flex-wrap gap-4 mb-6">
    <div class="flex flex-col min-w-[160px]">
      <label for="trip-type" class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
         {$i18n.t('Trip Type')}
       </label>
       <select
        id="trip-type"
         class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
         bind:value={searchForm.tripType}
       >
         <option value="round-trip">{$i18n.t('Round Trip')}</option>
         <option value="one-way">{$i18n.t('One Way')}</option>
        <option value="multi-city">{$i18n.t('Multiple City')}</option>
       </select>
     </div>

    <div class="flex flex-col min-w-[200px] relative">
      <span class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
         {$i18n.t('Passengers')}
      </span>
       <button
         type="button"
        class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-left text-sm text-gray-900 dark:text-gray-100 flex items-center justify-between gap-2"
        on:click={togglePassengerDropdown}
        data-passenger-dropdown
       >
        <span>{passengerSummary}</span>
         <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
         </svg>
       </button>

       {#if showPassengerDropdown}
        <div
          class="absolute z-50 mt-2 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 space-y-4"
          role="dialog"
          tabindex="-1"
          data-passenger-dropdown
        >
           <div class="flex items-center justify-between">
             <div>
               <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Adults')}</div>
               <div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Ages 12 and up')}</div>
             </div>
             <div class="flex items-center gap-2">
               <button type="button" class="w-8 h-8 flex items-center justify-center border border-gray-300 dark:border-gray-600 rounded-full text-lg" on:click={decrementAdults}>−</button>
               <span class="min-w-[24px] text-center text-sm text-gray-900 dark:text-gray-100">{currentAdults}</span>
               <button type="button" class="w-8 h-8 flex items-center justify-center border border-gray-300 dark:border-gray-600 rounded-full text-lg" on:click={incrementAdults}>+</button>
             </div>
           </div>

           <div class="flex items-center justify-between">
             <div>
               <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Children')}</div>
               <div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Ages 2-11')}</div>
             </div>
             <div class="flex items-center gap-2">
               <button type="button" class="w-8 h-8 flex items-center justify-center border border-gray-300 dark:border-gray-600 rounded-full text-lg" on:click={decrementChildren}>−</button>
               <span class="min-w-[24px] text-center text-sm text-gray-900 dark:text-gray-100">{currentChildren}</span>
               <button type="button" class="w-8 h-8 flex items-center justify-center border border-gray-300 dark:border-gray-600 rounded-full text-lg" on:click={incrementChildren}>+</button>
             </div>
           </div>

           <button type="button" class="w-full bg-black hover:bg-gray-800 text-white text-sm font-medium py-2 rounded-lg transition" on:click={closePassengerDropdown}>
             {$i18n.t('Done')}
           </button>
         </div>
       {/if}
     </div>

    <div class="flex flex-col min-w-[180px]">
      <label for="cabin-class" class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
         {$i18n.t('Cabin Class')}
       </label>
       <select
        id="cabin-class"
         class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
         bind:value={searchForm.seatClass}
       >
         <option value="economy">{$i18n.t('Economy')}</option>
         <option value="premium economy">{$i18n.t('Premium Economy')}</option>
         <option value="business">{$i18n.t('Business')}</option>
         <option value="first class">{$i18n.t('First Class')}</option>
       </select>
     </div>
   </div>

  {#if searchError}
    <div class="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
      <div class="flex">
        <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
        </svg>
        <div class="ml-3">
          <h3 class="text-sm font-medium text-red-800 dark:text-red-200">
            Search Error
          </h3>
          <div class="mt-2 text-sm text-red-700 dark:text-red-300">
            {searchError}
          </div>
        </div>
      </div>
    </div>
  {/if}

  <form on:submit|preventDefault={onSearch} class="space-y-6">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div class="autocomplete-container relative">
        <label for="starting-place" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {$i18n.t('Starting Place')}
        </label>
        <input
          id="starting-place"
          type="text"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
          placeholder="e.g., Hong Kong, Seoul, Tokyo..."
          value={startingPlaceInput}
          on:input={onStartingPlaceInput}
          on:focus={onStartingPlaceFocus}
          autocomplete="off"
          required
        />
        {#if showStartingPlaceDropdown && filteredStartingPlaces.length > 0}
          <div class="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {#each filteredStartingPlaces as city}
              <button
                type="button"
                class="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-sm text-gray-900 dark:text-gray-100"
                on:click={() => onSelectStartingPlace(city)}
              >
                {city.display}
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <div class="autocomplete-container relative">
        <label for="destination" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {$i18n.t('Destination')}
        </label>
        <input
          id="destination"
          type="text"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
          placeholder="e.g., Seoul, Tokyo, Singapore..."
          value={destinationInput}
          on:input={onDestinationInput}
          on:focus={onDestinationFocus}
          autocomplete="off"
          required
        />
        {#if showDestinationDropdown && filteredDestinations.length > 0}
          <div class="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {#each filteredDestinations as city}
              <button
                type="button"
                class="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-sm text-gray-900 dark:text-gray-100"
                on:click={() => onSelectDestination(city)}
              >
                {city.display}
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <div>
        <label for="cost" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {$i18n.t('Max Cost ($)')}
        </label>
        <input
          id="cost"
          type="number"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
          placeholder="e.g., 500"
          bind:value={searchForm.cost}
          min="0"
        />
      </div>

      <div>
        <label for="departure-date" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {$i18n.t('Departure Date')}
        </label>
        <input
          id="departure-date"
          type="date"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
          bind:value={searchForm.departureDate}
        />
      </div>

      {#if searchForm.tripType !== 'one-way'}
        <div>
          <label for="return-date" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {$i18n.t('Return Date')}
          </label>
          <input
            id="return-date"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
            bind:value={searchForm.returnDate}
          />
        </div>
      {/if}
    </div>

    <div class="flex flex-col sm:flex-row gap-4 pt-4">
      <button
        type="submit"
        class="flex-1 bg-black hover:bg-gray-800 text-white font-medium py-3 px-6 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        disabled={isSearching}
      >
        {#if isSearching}
          <div class="flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {$i18n.t('Searching...')}
          </div>
        {:else}
          <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
          {$i18n.t('Search Flights')}
        {/if}
      </button>
      <button
        type="button"
        on:click={onReset}
        class="flex-1 sm:flex-none bg-gray-500 hover:bg-gray-600 text-white font-medium py-3 px-6 rounded-lg transition"
      >
        {$i18n.t('Reset')}
      </button>
    </div>
  </form>

</div>

<div class="-mt-px mb-10 relative">
  <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 border-t-0 rounded-b-lg rounded-t-none shadow-lg px-4 py-3 relative z-10">
    <button
      type="button"
      class="w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
      on:click={toggleAdvancedFilters}
      aria-expanded={showAdvancedFilters}
    >
      <span>{$i18n.t('Additional Filters')}</span>
      <svg class={`w-5 h-5 transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showAdvancedFilters}
      <div class="absolute inset-x-0 top-full z-30 mt-3">
        <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl overflow-hidden">
          <div class={`p-4 sm:p-6 space-y-6 max-h-[70vh] ${showAirlineDropdown ? 'overflow-visible' : 'overflow-y-auto'}`}>
            <div class="space-y-2">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Stops')}</h3>
              <div class="flex flex-wrap gap-2">
                {#each [
                  { value: 'any', label: $i18n.t('Any') },
                  { value: 'direct', label: $i18n.t('Direct') },
                  { value: 'one-or-less', label: $i18n.t('One stop or fewer') },
                  { value: 'two-or-less', label: $i18n.t('Two stops or fewer') }
                ] as option}
                  {#key option.value}
                    <label
                      class={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold cursor-pointer transition border 
                        ${searchForm.stops === option.value 
                          ? 'bg-black text-white border-black dark:bg-white dark:text-black dark:border-white'
                          : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100 dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-600'}`}
                    >
                      <input
                        type="radio"
                        name="stops-filter"
                        class="sr-only"
                        value={option.value}
                        checked={searchForm.stops === option.value}
                        on:change={() => handleStopsChange(option.value)}
                      />
                      <span>{option.label}</span>
                    </label>
                  {/key}
                {/each}
              </div>
            </div>

            <div class="space-y-3 relative" data-airline-dropdown>
              <div class="flex items-center justify-between">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Airlines')}</h3>
                <span class="text-xs text-gray-500 dark:text-gray-400">{airlineSummary}</span>
              </div>

              <button
                type="button"
                class="w-full flex items-center justify-between gap-3 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                on:click={toggleAirlineDropdown}
                aria-expanded={showAirlineDropdown}
                data-airline-dropdown
                bind:this={airlineButtonRef}
              >
                <span class="truncate text-left">{airlineSummary}</span>
                <svg class={`w-4 h-4 transition-transform ${showAirlineDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {#if showAirlineDropdown}
                <div
                  class="fixed bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-2xl p-4 space-y-4 z-[1100]"
                  style={`top: ${airlineDropdownRect.top}px; left: ${airlineDropdownRect.left}px; width: ${airlineDropdownRect.width}px; max-height: ${airlineDropdownRect.maxHeight}px; overflow-y: auto;`}
                  data-airline-dropdown
                >
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-gray-500 dark:text-gray-400">{airlineSummary}</span>
                    <button
                      type="button"
                      class="text-xs font-medium text-gray-600 dark:text-gray-300 hover:underline"
                      on:click={() => emitFiltersChange({ airlines: [] })}
                    >
                      {$i18n.t('Clear')}
                    </button>
                  </div>

                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
                    {#each airlineOptions as airline}
                      <label class="flex items-center gap-3 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                        <input
                          type="checkbox"
                          class="h-4 w-4 appearance-none border border-gray-600 dark:border-gray-300 rounded-sm checked:bg-black checked:border-black dark:checked:bg-gray-100 dark:checked:border-gray-100 focus:outline-none focus:ring-1 focus:ring-black dark:focus:ring-gray-100 transition"
                          checked={selectedAirlines.has(airline.code)}
                          on:change={() => handleAirlineToggle(airline.code)}
                        />
                        <span class="truncate">{airline.name}</span>
                      </label>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>

            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Price')}</h3>
                <span class="text-xs text-gray-500 dark:text-gray-400">${currentMaxPrice}</span>
              </div>
              <div class="relative pt-6 overflow-visible">
                {#if isPriceDragging}
                  <div
                    class="absolute top-0 pointer-events-none"
                    style={`left: ${priceThumbPosition}%;`}
                  >
                    <div
                      class="relative -top-2 inline-flex items-center justify-center px-3 py-1 bg-black text-white text-xs font-semibold rounded-full shadow whitespace-nowrap"
                      style="transform: translate(-50%, -130%); min-width: 2.75rem; z-index: 9999;"
                    >
                      ${currentMaxPrice}
                    </div>
                  </div>
                {/if}
                <input
                  type="range"
                  min={priceRange.min}
                  max={priceRange.max}
                  step={priceRange.step}
                  value={currentMaxPrice}
                  class="w-full h-2 rounded-full bg-gray-200 dark:bg-gray-700 appearance-none cursor-pointer"
                  on:input={(event) => handlePriceChange(event.target.value)}
                  on:focus={() => (isPriceDragging = true)}
                  on:blur={() => (isPriceDragging = false)}
                  on:pointerdown={() => (isPriceDragging = true)}
                  on:pointerup={() => (isPriceDragging = false)}
                  on:mousedown={() => (isPriceDragging = true)}
                  on:mouseup={() => (isPriceDragging = false)}
                  on:touchstart={() => (isPriceDragging = true)}
                  on:touchend={() => (isPriceDragging = false)}
                  style="
                    accent-color: black;
                  "
                />
              </div>
              <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>${priceRange.min}</span>
                <span>${priceRange.max}</span>
              </div>
            </div>

            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Duration')}</h3>
                <span class="text-xs text-gray-500 dark:text-gray-400">{currentMaxDuration}h</span>
              </div>
              <div class="relative pt-6 overflow-visible">
                {#if isDurationDragging}
                  <div
                    class="absolute top-0 pointer-events-none"
                    style={`left: ${durationThumbPosition}%;`}
                  >
                    <div
                      class="relative -top-2 inline-flex items-center justify-center px-3 py-1 bg-black text-white text-xs font-semibold rounded-full shadow whitespace-nowrap"
                      style="transform: translate(-50%, -130%); min-width: 2.75rem; z-index: 9999;"
                    >
                      {currentMaxDuration}h
                    </div>
                  </div>
                {/if}
                <input
                  type="range"
                  min={durationRange.min}
                  max={durationRange.max}
                  step={durationRange.step}
                  value={currentMaxDuration}
                  class="w-full h-2 rounded-full bg-gray-200 dark:bg-gray-700 appearance-none cursor-pointer"
                  on:input={(event) => handleDurationChange(event.target.value)}
                  on:focus={() => (isDurationDragging = true)}
                  on:blur={() => (isDurationDragging = false)}
                  on:pointerdown={() => (isDurationDragging = true)}
                  on:pointerup={() => (isDurationDragging = false)}
                  on:mousedown={() => (isDurationDragging = true)}
                  on:mouseup={() => (isDurationDragging = false)}
                  on:touchstart={() => (isDurationDragging = true)}
                  on:touchend={() => (isDurationDragging = false)}
                  style="
                    accent-color: black;
                  "
                />
              </div>
              <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>{durationRange.min}h</span>
                <span>{durationRange.max}h</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

