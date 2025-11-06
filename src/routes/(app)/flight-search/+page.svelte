<script>
	import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import { navigateToPostWithFlightData } from '$lib/utils/flightPostHandler.js';
	import { goto } from '$app/navigation';
	import googleFlightsApi from '$lib/services/googleApi.js';
	import { cityList, locationCodeMap, getLocationCode, filterCities } from '$lib/utils/cityCodes';
	import SearchBox from './components/search-box.svelte';
	import ResultBox from './components/result-box.svelte';
	// No longer need adapter merging imports since we only use pre-existing merged models

	// Form state
	let searchForm = {
		startingPlace: '',
		destination: '',
		cost: '',
		tripType: 'round-trip',
		adults: 1,
		children: 0,
		seatClass: 'economy',
		stops: 'any',
		airlines: [],
		maxPrice: 2000,
		maxDuration: 12,
		departureDate: '',
		returnDate: ''
	};

	// Search results state
	let searchResults = [];
	let isSearching = false;
	let hasSearched = false;
	let selectedFlights = new Set();
	let selectedFlightObjects = []; // Store actual flight objects for display
	let isPosting = false;
	let aiStage = ''; // Track which AI stage is running
	let searchError = ''; // Track search errors
	let searchCounter = 0; // Counter to create unique IDs across searches
	
	// Autocomplete state
	let startingPlaceInput = '';
	let destinationInput = '';
	let filteredStartingPlaces = [];
	let filteredDestinations = [];
	let showStartingPlaceDropdown = false;
	let showDestinationDropdown = false;
	
	// Model selection state
	let selectedRAGModel = null;
	let selectedBaseModel = null;
	let selectedAdapter = null;
	let selectedModel = null; // For any model (including external APIs)

	// Initialize with all flights on page load
	$: if (typeof window !== 'undefined') {
		if (searchResults.length === 0 && !hasSearched) {
			// Give initial flights unique IDs
			searchResults = sampleFlights.map((flight, index) => ({
				...flight,
				id: `0_${index + 1}`
			}));
		}
	}

	// Location code mapping and city list are now imported from shared module
	// See: import { cityList, locationCodeMap, getLocationCode, filterCities } from '$lib/utils/cityCodes';

	// Handle starting place input
	const handleStartingPlaceInput = (e) => {
		startingPlaceInput = e.target.value;
	updateSearchForm({ startingPlace: startingPlaceInput });
		filteredStartingPlaces = filterCities(startingPlaceInput);
		showStartingPlaceDropdown = true;
	};

const updateSearchForm = (updates) => {
	searchForm = {
		...searchForm,
		...updates
	};
};

	// Handle destination input
	const handleDestinationInput = (e) => {
		destinationInput = e.target.value;
	updateSearchForm({ destination: destinationInput });
		filteredDestinations = filterCities(destinationInput);
		showDestinationDropdown = true;
	};

$: if (searchForm.tripType === 'one-way' && searchForm.returnDate) {
	updateSearchForm({ returnDate: '' });
}

const handleStartingPlaceFocus = () => {
	filteredStartingPlaces = filterCities(startingPlaceInput);
	showStartingPlaceDropdown = true;
};

const handleDestinationFocus = () => {
	filteredDestinations = filterCities(destinationInput);
	showDestinationDropdown = true;
};

	// Select starting place from dropdown
	const selectStartingPlace = (city) => {
		startingPlaceInput = city.display;
	updateSearchForm({ startingPlace: city.code });
		showStartingPlaceDropdown = false;
	};

	// Select destination from dropdown
	const selectDestination = (city) => {
		destinationInput = city.display;
	updateSearchForm({ destination: city.code });
		showDestinationDropdown = false;
	};

	// Close dropdowns when clicking outside
	const handleClickOutside = (e) => {
		if (!e.target.closest('.autocomplete-container')) {
			showStartingPlaceDropdown = false;
			showDestinationDropdown = false;
		}
	};

	// Sample flight data for demonstration
	const sampleFlights = [
		{
			id: 1,
			airline: '國泰航空',
			airlineCode: 'CX',
			startingPlace: '香港',
			startingPlaceCode: 'HKG',
			destination: '首爾',
			destinationCode: 'ICN',
			cost: 2690,
			currency: 'HKD',
			seatClass: '經濟艙',
			departureDate: '2024-02-15',
			departureTime: '08:30',
			arrivalDate: '2024-02-15',
			arrivalTime: '13:45',
			ticketValidDate: '2024-02-20',
			duration: '5h 15m',
			segments: 1,
			luggageInfo: '20kg',
			amadeusData: null
		},
		{
			id: 2,
			airline: '長榮航空',
			airlineCode: 'BR',
			startingPlace: '香港',
			startingPlaceCode: 'HKG',
			destination: '台北',
			destinationCode: 'TPE',
			cost: 1200,
			currency: 'HKD',
			seatClass: '經濟艙',
			departureDate: '2024-02-16',
			departureTime: '14:20',
			arrivalDate: '2024-02-16',
			arrivalTime: '16:10',
			ticketValidDate: '2024-02-22',
			duration: '1h 50m',
			segments: 1,
			luggageInfo: '20kg',
			amadeusData: null
		},
		{
			id: 3,
			airline: '全日空航空',
			airlineCode: 'NH',
			startingPlace: '香港',
			startingPlaceCode: 'HKG',
			destination: '大阪',
			destinationCode: 'KIX',
			cost: 2900,
			currency: 'HKD',
			seatClass: '經濟艙',
			departureDate: '2024-02-17',
			departureTime: '09:15',
			arrivalDate: '2024-02-17',
			arrivalTime: '14:30',
			ticketValidDate: '2024-02-23',
			duration: '5h 15m',
			segments: 1,
			luggageInfo: '20kg',
			amadeusData: null
		},
		{
			id: 4,
			airline: '阿聯酋航空',
			airlineCode: 'EK',
			startingPlace: '香港',
			startingPlaceCode: 'HKG',
			destination: '杜拜',
			destinationCode: 'DXB',
			cost: 2950,
			currency: 'HKD',
			seatClass: '經濟艙',
			departureDate: '2024-02-18',
			departureTime: '23:45',
			arrivalDate: '2024-02-19',
			arrivalTime: '05:20',
			ticketValidDate: '2024-02-24',
			duration: '8h 35m',
			segments: 1,
			luggageInfo: '20kg',
			amadeusData: null
		},
		{
			id: 5,
			airline: '英國航空',
			airlineCode: 'BA',
			startingPlace: '香港',
			startingPlaceCode: 'HKG',
			destination: '倫敦',
			destinationCode: 'LHR',
			cost: 9000,
			currency: 'HKD',
			seatClass: '商務艙',
			departureDate: '2024-02-19',
			departureTime: '23:30',
			arrivalDate: '2024-02-20',
			arrivalTime: '06:15',
			ticketValidDate: '2024-02-25',
			duration: '12h 45m',
			segments: 1,
			luggageInfo: '20kg',
			amadeusData: null
		}
	];

	// Search function
	const handleSearch = async () => {
		isSearching = true;
		hasSearched = true;
		searchError = '';
		
		// Keep selected flights when starting new search (don't clear)
		// Increment search counter to create unique IDs
		searchCounter++;

		try {
			console.log('Looking up origin code for:', searchForm.startingPlace);
			const originCode = getLocationCode(searchForm.startingPlace);
			console.log('Origin code result:', originCode);

			console.log('Looking up destination code for:', searchForm.destination);
			const destinationCode = getLocationCode(searchForm.destination);
			console.log('Destination code result:', destinationCode);

			if (!originCode || !destinationCode) {
				const missingFields = [];
				if (!originCode) missingFields.push('origin');
				if (!destinationCode) missingFields.push('destination');
				throw new Error(`Please enter valid ${missingFields.join(' and ')} cities. Use specific city names or airport codes (e.g., "Tokyo", "NRT", "Osaka", "KIX").`);
			}

			if (!searchForm.departureDate) {
				throw new Error('Please select a departure date');
			}

			if (searchForm.tripType !== 'one-way' && searchForm.returnDate) {
				const departureDate = new Date(searchForm.departureDate);
				const returnDate = new Date(searchForm.returnDate);
				if (returnDate <= departureDate) {
					throw new Error('Return date must be after departure date');
				}
			}

			const flightTypeMap = {
				'round-trip': 'round_trip',
				'one-way': 'one_way',
				'multi-city': 'multi_city'
			};

			const travelClassMap = {
				'economy': 'economy',
				'premium economy': 'premium_economy',
				'business': 'business',
				'first class': 'first'
			};

			const normalizedSeatClass = (searchForm.seatClass || 'economy').toLowerCase();
			const adultsCount = Math.max(1, Number(searchForm.adults) || 1);
			const childrenCount = Math.max(0, Number(searchForm.children) || 0);

			const searchParams = {
				engine: 'google_flights',
				flight_type: flightTypeMap[searchForm.tripType] || 'round_trip',
				departure_id: originCode,
				arrival_id: destinationCode,
				outbound_date: searchForm.departureDate,
				travel_class: travelClassMap[normalizedSeatClass] || 'economy',
				adults: adultsCount
			};

			if (childrenCount > 0) {
				searchParams.children = childrenCount;
			}

			if (searchForm.tripType !== 'one-way' && searchForm.returnDate) {
				searchParams.return_date = searchForm.returnDate;
			}

			console.log('Google Flights API Search Parameters:', searchParams);

			const googleFlightsResponse = await googleFlightsApi.searchFlights(searchParams);
			console.log('Google Flights API raw response:', googleFlightsResponse);

			// Temporarily disable displaying results until transformation is ready
			searchResults = [];
		} catch (error) {
			console.error('Search error:', error);
			searchError = error.message || 'An error occurred while searching for flights';
			searchResults = [];
		} finally {
			isSearching = false;
		}
	};

	// Reset search
	const resetSearch = () => {
	updateSearchForm({
		startingPlace: '',
		destination: '',
		cost: '',
		tripType: 'round-trip',
		adults: 1,
		children: 0,
		seatClass: 'economy',
		stops: 'any',
		airlines: [],
		maxPrice: 2000,
		maxDuration: 12,
		departureDate: '',
		returnDate: ''
	});
		startingPlaceInput = '';
		destinationInput = '';
		filteredStartingPlaces = [];
		filteredDestinations = [];
		showStartingPlaceDropdown = false;
		showDestinationDropdown = false;
		searchCounter = 0;
		searchResults = sampleFlights.map((flight, index) => ({
			...flight,
			id: `0_${index + 1}`
		}));
		hasSearched = false;
		selectedFlights.clear();
		selectedFlightObjects = [];
		searchError = '';
	};

	// Handle checkbox selection
	const toggleFlightSelection = (flightId) => {
		if (selectedFlights.has(flightId)) {
			selectedFlights.delete(flightId);
			// Remove from selected flight objects
			selectedFlightObjects = selectedFlightObjects.filter(f => f.id !== flightId);
		} else {
			selectedFlights.add(flightId);
			// Add to selected flight objects
			const flight = searchResults.find(f => f.id === flightId);
			if (flight && !selectedFlightObjects.find(f => f.id === flightId)) {
				selectedFlightObjects = [...selectedFlightObjects, flight];
			}
		}
		selectedFlights = selectedFlights; // Trigger reactivity
	};

	// Handle select all checkbox
	const toggleSelectAll = () => {
		// Check if all current search results are selected
		const allCurrentSelected = searchResults.every(flight => selectedFlights.has(flight.id));
		
		if (allCurrentSelected) {
			// Deselect all current search results (but keep others)
			searchResults.forEach(flight => selectedFlights.delete(flight.id));
			// Remove from selected flight objects
			selectedFlightObjects = selectedFlightObjects.filter(
				f => !searchResults.find(sr => sr.id === f.id)
			);
		} else {
			// Select all current search results (add to existing selections)
			searchResults.forEach(flight => {
				selectedFlights.add(flight.id);
				// Add to selected flight objects if not already there
				if (!selectedFlightObjects.find(f => f.id === flight.id)) {
					selectedFlightObjects = [...selectedFlightObjects, flight];
				}
			});
		}
		selectedFlights = selectedFlights; // Trigger reactivity
	};

	// Handle post action
	const handlePost = async () => {
		if (selectedFlights.size === 0) {
			alert('Please select at least one flight to post');
			return;
		}
		
		if (!selectedRAGModel && !selectedBaseModel && !selectedAdapter && !selectedModel) {
			alert('Please select an AI model to use for content generation');
			return;
		}
		
		isPosting = true;
		aiStage = 'initializing';
		
		try {
			// Use selectedFlightObjects instead of filtering searchResults
			const selectedFlightData = selectedFlightObjects;
			
			// Handle model selection
			let modelToUse = null;
			
			if (selectedModel) {
				// Use any selected model (including external APIs like Gemini)
				modelToUse = {
					id: selectedModel.id,
					name: selectedModel.name || selectedModel.id,
					owned_by: selectedModel.owned_by,
					is_external_model: selectedModel.owned_by && selectedModel.owned_by !== 'ollama'
				};
				aiStage = 'stage1';
				console.log('Using selected model:', modelToUse);
			} else if (selectedBaseModel) {
				// Use base model with RAG (if available)
				modelToUse = {
					ollama_model_name: selectedBaseModel,
					base_model: selectedBaseModel,
					adapter_name: null,
					is_base_model_only: true,
					rag_model: selectedRAGModel
				};
				aiStage = 'stage1';
			} else if (selectedAdapter) {
				// Use adapter - create a model reference for the RAG model that should exist
				aiStage = 'stage1';
				console.log('Using adapter:', selectedAdapter);
				
				// Create the expected RAG model name based on the adapter export ID
				const expectedRAGModelName = `${selectedAdapter.export_id}_rag_ollama:latest`;
				console.log('Expected RAG model name:', expectedRAGModelName);
				
				modelToUse = {
					rag_model_name: `${selectedAdapter.export_id}_rag`,
					ollama_model_name: expectedRAGModelName,
					adapter_name: selectedAdapter.adapter_name,
					base_model: 'qwen2.5:14b',
					export_id: selectedAdapter.export_id,
					is_adapter_rag: true
				};
			} else if (selectedRAGModel) {
				// Use already-merged RAG model
				aiStage = 'stage1';
				console.log('Using existing RAG model:', selectedRAGModel);
				
				modelToUse = {
					rag_model_name: selectedRAGModel.rag_model_name,
					ollama_model_name: selectedRAGModel.ollama_model_name,
					adapter_name: selectedRAGModel.adapter_name,
					base_model: selectedRAGModel.base_model,
					rag_model: selectedRAGModel
				};
			}
			
			// Use the flight post handler to navigate to Post page with data and AI analysis
			await navigateToPostWithFlightData(selectedFlightData, goto, (stage) => {
				aiStage = stage;
			}, modelToUse);
		} catch (error) {
			console.error('Error posting flight data:', error);
			alert(`Error generating AI analysis: ${error.message}`);
		} finally {
			isPosting = false;
			aiStage = '';
		}
	};
</script>

<svelte:window on:click={handleClickOutside} />

<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
		<div class=" flex items-center">
			{#if $mobile}
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class=" self-center p-1.5">
								<Sidebar />
							</div>
						</button>
					</Tooltip>
				</div>
			{/if}

			<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
				<div class="">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium bg-transparent py-1 touch-auto pointer-events-auto"
					>
						<a class="min-w-fit transition flex items-center gap-2" href="/flight-search">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								class="size-5 text-gray-900 dark:text-gray-100"
							>
								<path
									d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linejoin="round"
									stroke-linecap="round"
								/>
							</svg>
							{$i18n.t('Flight Search')}
						</a>
					</div>
				</div>

				<div class=" self-center flex items-center gap-1">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[240px]"
							role={$user?.role}
							help={true}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<button
								class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								aria-label="User Menu"
							>
								<div class=" self-center">
									<img
										src={$user?.profile_image_url}
										class="size-6 object-cover rounded-full"
										alt="User profile"
										draggable="false"
									/>
								</div>
							</button>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</nav>

	<div class="pb-1 flex-1 max-h-full overflow-y-auto @container">
		<div class="max-w-7xl mx-auto p-6">
			<!-- Page Header -->
			<div class="mb-8">
				<h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
					{$i18n.t('Flight Search')}
				</h1>
				<p class="text-gray-600 dark:text-gray-400">
					{$i18n.t('Find the best flight deals for your next trip')}
				</p>
			</div>

			<!-- Search Form -->
			<SearchBox
				{searchError}
				{searchForm}
				{isSearching}
				{startingPlaceInput}
				{destinationInput}
				{filteredStartingPlaces}
				{filteredDestinations}
				{showStartingPlaceDropdown}
				{showDestinationDropdown}
				onSearch={handleSearch}
				onReset={resetSearch}
				onStartingPlaceInput={handleStartingPlaceInput}
				onDestinationInput={handleDestinationInput}
				onStartingPlaceFocus={handleStartingPlaceFocus}
				onDestinationFocus={handleDestinationFocus}
				onSelectStartingPlace={selectStartingPlace}
				onSelectDestination={selectDestination}
				on:passengerschange={(event) => {
					const { adults, children } = event.detail;
					updateSearchForm({ adults, children });
				}}
				on:filterschange={(event) => {
					updateSearchForm(event.detail);
				}}
			/>

			<!-- Search Results -->
			<ResultBox
				{searchResults}
				{selectedFlights}
				{selectedFlightObjects}
				onToggleFlight={toggleFlightSelection}
				onToggleSelectAll={toggleSelectAll}
				onPost={handlePost}
				{isPosting}
				{aiStage}
				bind:selectedRAGModel
				bind:selectedBaseModel
				bind:selectedAdapter
				bind:selectedModel
			/>
		</div>
	</div>
</div>
