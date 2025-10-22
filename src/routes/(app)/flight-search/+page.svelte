<script>
	import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import { navigateToPostWithFlightData } from '$lib/utils/flightPostHandler.js';
	import { goto } from '$app/navigation';
	import { amadeusApi } from '$lib/services/amadeusApi.js';
	import FlightResultsTable from '$lib/components/FlightResultsTable.svelte';
	// No longer need adapter merging imports since we only use pre-existing merged models

	// Form state
	let searchForm = {
		startingPlace: '',
		destination: '',
		cost: '',
		seatClass: 'economy',
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
	let useAmadeusApi = true; // Toggle between mock and real API
	let searchCounter = 0; // Counter to create unique IDs across searches
	
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

	// Location code mapping for common cities
	const locationCodeMap = {
		// Direct airport code mappings (most important - these should be checked first)
		'HKG': 'HKG',
		'ICN': 'ICN',
		'NRT': 'NRT',
		'KIX': 'KIX',
		'TPE': 'TPE',
		'SIN': 'SIN',
		'BKK': 'BKK',
		'DXB': 'DXB',
		'LHR': 'LHR',
		'JFK': 'JFK',
		'LAX': 'LAX',
		'SYD': 'SYD',
		'CDG': 'CDG',
		'FRA': 'FRA',
		'AMS': 'AMS',
		'YVR': 'YVR',
		'YYZ': 'YYZ',
		'NGO': 'NGO',
		'FUK': 'FUK',
		'CTS': 'CTS',
		'OKA': 'OKA',
		'KHH': 'KHH',
		'PEK': 'PEK',
		'PVG': 'PVG',
		'CAN': 'CAN',
		'SZX': 'SZX',
		'CTU': 'CTU',
		'XIY': 'XIY',
		'NKG': 'NKG',
		'TAO': 'TAO',
		'TSN': 'TSN',
		'CKG': 'CKG',
		'URC': 'URC',
		'HRB': 'HRB',
		'DLC': 'DLC',
		'SJW': 'SJW',
		'TYN': 'TYN',
		'INC': 'INC',
		'LHW': 'LHW',
		'XNN': 'XNN',
		'KMG': 'KMG',
		'LXA': 'LXA',
		'HAK': 'HAK',
		'FOC': 'FOC',
		'XMN': 'XMN',
		'CSX': 'CSX',
		'WUH': 'WUH',
		'CGO': 'CGO',
		'JIN': 'JIN',
		'YNT': 'YNT',
		'WEH': 'WEH',
		'LYG': 'LYG',
		'NTG': 'NTG',
		'WNZ': 'WNZ',
		'NGB': 'NGB',
		'HGH': 'HGH',
		'MEL': 'MEL',
		'BNE': 'BNE',
		'PER': 'PER',
		'ADL': 'ADL',
		'CBR': 'CBR',
		'HOB': 'HOB',
		'DRW': 'DRW',
		'CNS': 'CNS',
		'TSV': 'TSV',
		'OOL': 'OOL',
		'MCY': 'MCY',
		'ROK': 'ROK',
		'FCO': 'FCO',
		'MAD': 'MAD',
		'BCN': 'BCN',
		'ZUR': 'ZUR',
		'VIE': 'VIE',
		'CPH': 'CPH',
		'ARN': 'ARN',
		'OSL': 'OSL',
		'HEL': 'HEL',
		'WAW': 'WAW',
		'PRG': 'PRG',
		'BUD': 'BUD',
		'ATH': 'ATH',
		'IST': 'IST',
		'AUH': 'AUH',
		'DOH': 'DOH',
		'KWI': 'KWI',
		'BAH': 'BAH',
		'JED': 'JED',
		'RUH': 'RUH',
		'CAI': 'CAI',
		'JNB': 'JNB',
		'CPT': 'CPT',
		'LOS': 'LOS',
		'NBO': 'NBO',
		'ADD': 'ADD',
		'KRT': 'KRT',
		'KGL': 'KGL',
		'DAR': 'DAR',
		'LUN': 'LUN',
		'GBE': 'GBE',
		'WDH': 'WDH',
		'MPM': 'MPM',
		'BJM': 'BJM',
		
		// City name mappings
		'香港': 'HKG',
		'hong kong': 'HKG',
		'首爾': 'ICN',
		'seoul': 'ICN',
		'高雄': 'KHH',
		'kaohsiung': 'KHH',
		'大阪': 'KIX',
		'osaka': 'KIX',
		'杜拜': 'DXB',
		'dubai': 'DXB',
		'倫敦': 'LHR',
		'london': 'LHR',
		'紐約': 'JFK',
		'new york': 'JFK',
		'洛杉磯': 'LAX',
		'los angeles': 'LAX',
		'東京': 'NRT',
		'tokyo': 'NRT',
		'台北': 'TPE',
		'taipei': 'TPE',
		'新加坡': 'SIN',
		'singapore': 'SIN',
		'曼谷': 'BKK',
		'bangkok': 'BKK',
		'雪梨': 'SYD',
		'sydney': 'SYD',
		'巴黎': 'CDG',
		'paris': 'CDG',
		'法蘭克福': 'FRA',
		'frankfurt': 'FRA',
		'阿姆斯特丹': 'AMS',
		'amsterdam': 'AMS',
		'溫哥華': 'YVR',
		'vancouver': 'YVR',
		'多倫多': 'YYZ',
		'toronto': 'YYZ',
		// Japan airports
		'名古屋': 'NGO',
		'nagoya': 'NGO',
		'福岡': 'FUK',
		'fukuoka': 'FUK',
		'札幌': 'CTS',
		'sapporo': 'CTS',
		'沖繩': 'OKA',
		'okinawa': 'OKA',
		'japan': 'NRT', // Default to Tokyo for Japan
		'japanese': 'NRT'
	};

	// Function to get location code from city name
	const getLocationCode = (cityName) => {
		if (!cityName) return '';
		
		// Clean the input - remove extra spaces and convert to uppercase for airport codes
		const cleanName = cityName.trim();
		
		// First try exact match (case insensitive for city names, case sensitive for airport codes)
		const exactMatch = locationCodeMap[cleanName.toLowerCase()] || locationCodeMap[cleanName.toUpperCase()];
		if (exactMatch) return exactMatch;
		
		// Try partial match for city names (case insensitive)
		for (const [key, code] of Object.entries(locationCodeMap)) {
			if (key.toLowerCase().includes(cleanName.toLowerCase()) || cleanName.toLowerCase().includes(key.toLowerCase())) {
				return code;
			}
		}
		
		// If no match found, return null to indicate invalid input
		// This will trigger the validation error in the search function
		return null;
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
			cost: 2250,
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
			cost: 18000,
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
			if (useAmadeusApi) {
				// Use Amadeus API for real flight search
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

				// Validate return date if provided
				if (searchForm.returnDate) {
					const departureDate = new Date(searchForm.departureDate);
					const returnDate = new Date(searchForm.returnDate);
					
					if (returnDate <= departureDate) {
						throw new Error('Return date must be after departure date');
					}
					
					// Check if return date is not too far in the future (Amadeus has limits)
					const maxReturnDate = new Date();
					maxReturnDate.setFullYear(maxReturnDate.getFullYear() + 1);
					if (returnDate > maxReturnDate) {
						throw new Error('Return date cannot be more than 1 year in the future');
					}
				}

				// Map seat class to Amadeus format
				const travelClassMap = {
					'economy': 'ECONOMY',
					'business': 'BUSINESS'
				};

				const searchParams = {
					originLocationCode: originCode,
					destinationLocationCode: destinationCode,
					departureDate: searchForm.departureDate,
					adults: 1,
					travelClass: travelClassMap[searchForm.seatClass] || 'ECONOMY',
					max: 20
				};

				// Add return date if provided and valid
				if (searchForm.returnDate) {
					searchParams.returnDate = searchForm.returnDate;
				}

				console.log('Amadeus API Search Parameters:', searchParams);

				// Call Amadeus API
				const amadeusResponse = await amadeusApi.searchFlightOffers(searchParams);
				
				// Transform the response to match our UI structure
				let transformedResults = amadeusApi.transformFlightData(amadeusResponse);

				// Apply cost filter if specified
				if (searchForm.cost) {
					const maxCost = parseFloat(searchForm.cost);
					transformedResults = transformedResults.filter(flight => flight.cost <= maxCost);
				}

				// Make IDs unique across searches by prefixing with search counter
				transformedResults = transformedResults.map((flight, index) => ({
					...flight,
					id: `${searchCounter}_${index + 1}`
				}));

				searchResults = transformedResults;
			} else {
				// Use mock data (fallback)
				await new Promise(resolve => setTimeout(resolve, 1000));

				let filteredResults = sampleFlights.filter(flight => {
					const matchesStartingPlace = !searchForm.startingPlace || 
						flight.startingPlace.toLowerCase().includes(searchForm.startingPlace.toLowerCase());
					const matchesDestination = !searchForm.destination || 
						flight.destination.toLowerCase().includes(searchForm.destination.toLowerCase());
					const matchesSeatClass = !searchForm.seatClass || 
						flight.seatClass.toLowerCase() === searchForm.seatClass.toLowerCase();
					const matchesCost = !searchForm.cost || 
						flight.cost <= parseInt(searchForm.cost);

					return matchesStartingPlace && matchesDestination && matchesSeatClass && matchesCost;
				});

				// Make IDs unique across searches by prefixing with search counter
				filteredResults = filteredResults.map((flight, index) => ({
					...flight,
					id: `${searchCounter}_${index + 1}`
				}));

				searchResults = filteredResults;
			}
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
		searchForm = {
			startingPlace: '',
			destination: '',
			cost: '',
			seatClass: 'economy',
			departureDate: '',
			returnDate: ''
		};
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
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
				<div class="flex items-center justify-between mb-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
						{$i18n.t('Search Flights')}
					</h2>
					<div class="flex items-center gap-2">
						<label for="api-mode-toggle" class="text-sm text-gray-600 dark:text-gray-400">API Mode:</label>
						<label for="api-mode-toggle" class="inline-flex items-center cursor-pointer">
							<input
								id="api-mode-toggle"
								type="checkbox"
								class="form-checkbox h-4 w-4 text-blue-600 transition duration-150 ease-in-out"
								bind:checked={useAmadeusApi}
							/>
							<span class="ml-2 text-sm text-gray-700 dark:text-gray-300">
								{useAmadeusApi ? 'Amadeus API' : 'Mock Data'}
							</span>
						</label>
					</div>
				</div>

				<!-- Error Display -->
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
				
				<form on:submit|preventDefault={handleSearch} class="space-y-6">
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
						<!-- Starting Place -->
						<div>
							<label for="starting-place" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Starting Place')}
							</label>
							<input
								id="starting-place"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								placeholder="e.g., Hong Kong, HKG, Los Angeles, LAX"
								bind:value={searchForm.startingPlace}
								required
							/>
						</div>

						<!-- Destination -->
						<div>
							<label for="destination" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Destination')}
							</label>
							<input
								id="destination"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								placeholder="e.g., Seoul, ICN, New York, JFK"
								bind:value={searchForm.destination}
								required
							/>
						</div>

						<!-- Cost -->
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

						<!-- Seat Class -->
						<div>
							<label for="seat-class" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Seat Class')}
							</label>
							<select
								id="seat-class"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
								bind:value={searchForm.seatClass}
							>
								<option value="economy">{$i18n.t('Economy')}</option>
								<option value="business">{$i18n.t('Business')}</option>
							</select>
						</div>

						<!-- Departure Date -->
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

						<!-- Return Date -->
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
					</div>

					<!-- Action Buttons -->
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
							on:click={resetSearch}
							class="flex-1 sm:flex-none bg-gray-500 hover:bg-gray-600 text-white font-medium py-3 px-6 rounded-lg transition"
						>
							{$i18n.t('Reset')}
						</button>
					</div>
				</form>
			</div>

			<!-- Search Results -->
			{#if searchResults.length > 0}
			<FlightResultsTable
				flights={searchResults}
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
			{:else}
				<!-- No Results -->
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
		</div>
	</div>
</div>
