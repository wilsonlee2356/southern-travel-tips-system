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
  import { getContext, createEventDispatcher } from 'svelte';
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
  let showAirlineDropdown = false;
  let showDurationDropdown = false;
  let showPriceDropdown = false;
  let airlineSearchQuery = '';
  let airlineDropdownExpanded = false;
  let currentAdults = 1;
  let currentChildren = 0;
  let passengerSummary = '';
  let excludedAirlines = new Set();
 const priceRange = { min: 0, max: 200000, step: 100 };
 const durationRange = { min: 1, max: 30, step: 1 };
 let isPriceDragging = false;
 let isDurationDragging = false;
  let airlineButtonRef;
  let priceDropdownRef;
  let durationDropdownRef;

  const closePassengerDropdown = () => {
     showPassengerDropdown = false;
   };

  const togglePassengerDropdown = () => {
     showPassengerDropdown = !showPassengerDropdown;
   };

  const toggleAirlineDropdown = () => {
    showAirlineDropdown = !showAirlineDropdown;
    if (!showAirlineDropdown) {
      // Reset expanded state when closing dropdown
      airlineDropdownExpanded = false;
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
    const numericValue = Number(value);
    const normalized = numericValue >= priceRange.max ? null : numericValue;
    emitFiltersChange({ maxPrice: normalized });
  };

  const handleDurationChange = (value) => {
    const numericValue = Number(value);
    const normalized = numericValue >= durationRange.max ? null : numericValue;
    emitFiltersChange({ maxDuration: normalized });
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
  $: excludedAirlines = new Set(searchForm?.excludedAirlines ?? []);
  $: hasPriceFilter = searchForm?.maxPrice != null && searchForm.maxPrice !== '' && !Number.isNaN(Number(searchForm.maxPrice));
  $: hasDurationFilter = searchForm?.maxDuration != null && searchForm.maxDuration !== '' && !Number.isNaN(Number(searchForm.maxDuration));
  $: currentMaxPrice = hasPriceFilter ? Number(searchForm.maxPrice) : priceRange.max;
  $: currentMaxDuration = hasDurationFilter ? Number(searchForm.maxDuration) : durationRange.max;
  $: priceDisplay = hasPriceFilter ? `$${currentMaxPrice}` : (i18n?.t?.('Any') ?? 'Any');
  $: durationDisplay = hasDurationFilter ? `${currentMaxDuration}h` : (i18n?.t?.('Any') ?? 'Any');
  $: totalAirlines = airlineOptions.length;
  $: selectedAirlineCount = totalAirlines - excludedAirlines.size;
  $: allAirlinesSelected = excludedAirlines.size === 0;
  $: airlineSummary = excludedAirlines.size === 0
    ? (i18n?.t?.('All airlines') ?? 'All airlines')
    : selectedAirlineCount === 0
      ? (i18n?.t?.('None selected') ?? 'None selected')
      : `${selectedAirlineCount} ${(i18n?.t?.('selected') ?? 'selected')}`;
  $: filteredAirlines = (airlineSearchQuery
    ? airlineOptions.filter(airline => 
        airline.name.toLowerCase().includes(airlineSearchQuery.toLowerCase()) ||
        airline.code.toLowerCase().includes(airlineSearchQuery.toLowerCase())
      )
    : airlineOptions
  ).sort((a, b) => a.code.localeCompare(b.code));

  const handleSelectAllAirlines = () => {
    if (allAirlinesSelected) {
      // Deselect all - exclude all airlines
      emitFiltersChange({ excludedAirlines: airlineOptions.map(a => a.code) });
    } else {
      // Select all - exclude none
      emitFiltersChange({ excludedAirlines: [] });
    }
  };

  // Watch for departure date changes and update return date if needed
  $: if (searchForm.departureDate && searchForm.returnDate) {
    if (new Date(searchForm.returnDate) < new Date(searchForm.departureDate)) {
      searchForm.returnDate = searchForm.departureDate;
    }
  }
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

  const handleStopsChange = (value) => {
    emitFiltersChange({ stops: value });
  };


  const handleAirlineToggle = (code) => {
    const updated = new Set(excludedAirlines);
    if (updated.has(code)) {
      updated.delete(code);
    } else {
      updated.add(code);
    }
    emitFiltersChange({ excludedAirlines: Array.from(updated) });
  };



 const handleWindowClick = (event) => {
    if (!event.target.closest('[data-passenger-dropdown]')) {
      closePassengerDropdown();
    }
    if (!event.target.closest('[data-airline-dropdown]')) {
      // Close dropdown when clicking outside, even if expanded
      showAirlineDropdown = false;
      airlineDropdownExpanded = false;
    }
    if (!event.target.closest('[data-price-dropdown]')) {
      showPriceDropdown = false;
    }
    if (!event.target.closest('[data-duration-dropdown]')) {
      showDurationDropdown = false;
    }
  };

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
/>

<div class="bg-white dark:bg-gray-800 rounded-t-lg rounded-b-none shadow-lg p-6 border border-gray-200 dark:border-gray-700 border-b border-b-gray-200 dark:border-b-gray-700">
   <div class="md:flex flex-wrap gap-4 mb-6">
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

    <!-- Stops Dropdown -->
    <div class="flex flex-col min-w-[180px]">
      <label for="stops" class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
         {$i18n.t('Stops')}
       </label>
       <select
        id="stops"
         class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
         bind:value={searchForm.stops}
         on:change={(e) => handleStopsChange(e.target.value)}
       >
         <option value="any">{$i18n.t('Any')}</option>
         <option value="direct">{$i18n.t('Direct')}</option>
         <option value="one-or-less">{$i18n.t('One stop or fewer')}</option>
         <option value="two-or-less">{$i18n.t('Two stops or fewer')}</option>
       </select>
     </div>

    <!-- Airlines Searchable Checklist -->
    <div class="flex flex-col min-w-[200px] relative" data-airline-dropdown>
      <span class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
         {$i18n.t('Airlines')}
      </span>
      <button
        type="button"
        class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-left text-sm text-gray-900 dark:text-gray-100 flex items-center justify-between gap-2"
        on:click={toggleAirlineDropdown}
        data-airline-dropdown
        bind:this={airlineButtonRef}
      >
        <span class="truncate">{airlineSummary}</span>
        <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {#if showAirlineDropdown}
        <div
          class="w-full z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 space-y-3 flex flex-col {airlineDropdownExpanded ? 'fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[45vw] h-[45vh]' : 'absolute top-full left-0 mt-2 w-[133.33%] md:w-full max-h-80'}"
          data-airline-dropdown
        >
          <div class="flex items-center justify-between">
            <span class="text-xs text-gray-500 dark:text-gray-400">{airlineSummary}</span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="text-xs font-medium text-gray-600 dark:text-gray-300 hover:underline"
                on:click={handleSelectAllAirlines}
              >
                {allAirlinesSelected ? $i18n.t('Deselect all') : $i18n.t('Select all')}
              </button>
              <!-- Expand button - hidden on mobile, visible on desktop -->
              <button
                type="button"
                class="hidden md:block p-1 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition"
                on:click|stopPropagation={() => airlineDropdownExpanded = !airlineDropdownExpanded}
                aria-label={airlineDropdownExpanded ? 'Minimize' : 'Expand'}
                title={airlineDropdownExpanded ? 'Minimize' : 'Expand'}
              >
                {#if airlineDropdownExpanded}
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
                  </svg>
                {:else}
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                  </svg>
                {/if}
              </button>
            </div>
          </div>
          
          <input
            type="text"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100 text-sm"
            placeholder={$i18n.t('Search airlines...')}
            bind:value={airlineSearchQuery}
          />
          
          <div class="flex-1 overflow-y-auto space-y-2 pr-1">
            {#each filteredAirlines as airline}
              <label class="flex items-center gap-3 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                <input
                  type="checkbox"
                  class="h-4 w-4 appearance-none border border-gray-600 dark:border-gray-300 rounded-sm checked:bg-black checked:border-black dark:checked:bg-gray-100 dark:checked:border-gray-100 focus:outline-none focus:ring-1 focus:ring-black dark:focus:ring-gray-100 transition"
                  checked={!excludedAirlines.has(airline.code)}
                  on:change={() => handleAirlineToggle(airline.code)}
                />
                <span class="truncate">{airline.name} ({airline.code})</span>
              </label>
            {/each}
          </div>
        </div>
      {/if}
    </div>

    <!-- Price Dropdown with Draggable -->
    <div class="flex flex-col min-w-[200px] relative" data-price-dropdown>
      <span class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
         {$i18n.t('Price')}
      </span>
      <button
        type="button"
        class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-left text-sm text-gray-900 dark:text-gray-100 flex items-center justify-between gap-2"
        on:click={() => showPriceDropdown = !showPriceDropdown}
        data-price-dropdown
        bind:this={priceDropdownRef}
      >
        <span>{priceDisplay}</span>
        <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {#if showPriceDropdown}
        <div
          class="absolute z-50 mt-2 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 space-y-3"
          data-price-dropdown
        >
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Price')}</h3>
            <span class="text-xs text-gray-500 dark:text-gray-400">{priceDisplay}</span>
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
                  {hasPriceFilter ? `$${currentMaxPrice}` : (i18n?.t?.('Any') ?? 'Any')}
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
              style="accent-color: black;"
            />
          </div>
          <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>${priceRange.min}</span>
            <span>${priceRange.max}</span>
          </div>
        </div>
      {/if}
    </div>

    <!-- Duration Dropdown with Draggable -->
    <div class="flex flex-col min-w-[200px] relative" data-duration-dropdown>
      <span class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
         {$i18n.t('Duration')}
      </span>
      <button
        type="button"
        class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-left text-sm text-gray-900 dark:text-gray-100 flex items-center justify-between gap-2"
        on:click={() => showDurationDropdown = !showDurationDropdown}
        data-duration-dropdown
        bind:this={durationDropdownRef}
      >
        <span>{durationDisplay}</span>
        <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {#if showDurationDropdown}
        <div
          class="absolute z-50 mt-2 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 space-y-3"
          data-duration-dropdown
        >
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Duration')}</h3>
            <span class="text-xs text-gray-500 dark:text-gray-400">{durationDisplay}</span>
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
                  {hasDurationFilter ? `${currentMaxDuration}h` : (i18n?.t?.('Any') ?? 'Any')}
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
              style="accent-color: black;"
            />
          </div>
          <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>{durationRange.min}h</span>
            <span>{durationRange.max}h</span>
          </div>
        </div>
      {/if}
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
        <label for="departure-date" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {$i18n.t('Departure Date')}
        </label>
        <input
          id="departure-date"
          type="date"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
          bind:value={searchForm.departureDate}
          min={new Date().toISOString().split('T')[0]}
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
            min={searchForm.departureDate || new Date().toISOString().split('T')[0]}
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

