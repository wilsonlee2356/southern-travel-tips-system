<script>
	import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
	import { getContext, onMount } from 'svelte';
	import googleFlightsApi from '$lib/services/googleApi.js';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	// Active section for accordion
	let activeSection = 'basic';
	
	// Search mode: 'standard' or 'calendar'
	let searchMode = 'standard';

	// Basic search parameters
	let departure = '';
	let destination = '';
	let outboundDate = '';
	let returnDate = '';
	let flightType = 'round_trip';
	
	// Calendar search parameters
	let outboundDateStart = '';
	let outboundDateEnd = '';
	let returnDateStart = '';
	let returnDateEnd = '';
	
	// Language and location
	let language = 'en';
	let country = 'US';
	let currency = 'HKD';
	
	// Passengers
	let adults = 1;
	let children = 0;
	let infantsInSeat = 0;
	let infantsOnLap = 0;
	
	// Flight preferences
	let travelClass = 'economy';
	let stops = 'any';
	let sortBy = '';
	let maxPrice = '';
	
	// Baggage
	let carryOnBags = '';
	let checkedBags = '';
	
	// Airlines
	let includedAirlines = '';
	let excludedAirlines = '';
	
	// Airports
	let includedConnectingAirports = '';
	let excludedConnectingAirports = '';
	
	// Time preferences
	let outboundTimes = '';
	let returnTimes = '';
	
	// Advanced filters
	let emissions = false;
	let layoverDurationMin = '';
	let layoverDurationMax = '';
	let maxFlightDuration = '';
	let separateTickets = '';
	let showCheapestFlights = false;
	let showHiddenFlights = false;
	
	// Multi-city
	let multiCitySegments = [
		{ departure: '', arrival: '', date: '' },
		{ departure: '', arrival: '', date: '' }
	];
	
	// Pagination/Booking
	let departureToken = '';
	let bookingToken = '';
	
	// Results
	let searching = false;
	let searchResults = null;
	let errorMessage = '';
	let selectedFlight = null;
	let calendarResults = null;

	// Add segment to multi-city
	const addSegment = () => {
		multiCitySegments = [...multiCitySegments, { departure: '', arrival: '', date: '' }];
	};

	// Remove segment from multi-city
	const removeSegment = (index) => {
		if (multiCitySegments.length > 2) {
			multiCitySegments = multiCitySegments.filter((_, i) => i !== index);
		}
	};

	// Toggle section
	const toggleSection = (section) => {
		activeSection = activeSection === section ? '' : section;
	};

	// Transform SearchAPI calendar format to price_grid format
	const transformCalendarToPriceGrid = (calendar, flightType) => {
		if (!calendar || !Array.isArray(calendar) || calendar.length === 0) {
			return [];
		}

		if (flightType === 'round_trip') {
			// Group by departure date
			const groupedByDeparture = {};
			
			calendar.forEach(item => {
				if (!item.departure || !item.return || !item.price) return;
				
				if (!groupedByDeparture[item.departure]) {
					groupedByDeparture[item.departure] = {
						departure_date: item.departure,
						return_dates: [],
						prices: [],
						is_lowest_price: []
					};
				}
				
				groupedByDeparture[item.departure].return_dates.push(item.return);
				groupedByDeparture[item.departure].prices.push(item.price);
				groupedByDeparture[item.departure].is_lowest_price.push(item.is_lowest_price || false);
			});
			
			// Convert to array and sort by departure date
			return Object.values(groupedByDeparture).sort((a, b) => 
				new Date(a.departure_date) - new Date(b.departure_date)
			);
		} else {
			// One-way flights: simple transformation
			return calendar.map(item => ({
				departure_date: item.departure,
				price: item.price,
				is_lowest_price: item.is_lowest_price || false
			})).sort((a, b) => 
				new Date(a.departure_date) - new Date(b.departure_date)
			);
		}
	};

	// Handle calendar search
	const handleCalendarSearch = async () => {
		errorMessage = '';
		
		if (!departure || !destination) {
			errorMessage = 'Please fill in departure city and destination.';
			return;
		}
		
		if (!outboundDateStart || !outboundDateEnd) {
			errorMessage = 'Please select outbound date range.';
			return;
		}
		
		if (flightType === 'round_trip' && (!returnDateStart || !returnDateEnd)) {
			errorMessage = 'Please select return date range for round trip.';
			return;
		}

		searching = true;
		calendarResults = null;
		searchResults = null;
		selectedFlight = null;

		try {
			const params = {
				engine: 'google_flights_calendar',
				departure_id: departure,
				arrival_id: destination,
				outbound_date: outboundDateStart, // Anchor date (same as range start)
				outbound_date_start: outboundDateStart,
				outbound_date_end: outboundDateEnd,
				flight_type: flightType,
				currency: currency,
				hl: language,
				gl: country
			};

			// Add return dates for round trip
			if (flightType === 'round_trip') {
				params.return_date = returnDateStart; // Anchor date (same as range start)
				params.return_date_start = returnDateStart;
				params.return_date_end = returnDateEnd;
			}

			// Add passengers
			if (adults > 0) params.adults = adults;
			if (children > 0) params.children = children;
			if (infantsInSeat > 0) params.infants_in_seat = infantsInSeat;
			if (infantsOnLap > 0) params.infants_on_lap = infantsOnLap;

			// Add basic preferences
			if (travelClass !== 'economy') params.travel_class = travelClass;

		console.log('Calendar search params:', params);
		const response = await googleFlightsApi.searchFlights(params);
		console.log('Calendar API response:', response);

		// Transform SearchAPI calendar format to price_grid format
		if (response.calendar && Array.isArray(response.calendar)) {
			response.price_grid = transformCalendarToPriceGrid(response.calendar, flightType);
		}

		calendarResults = response;
		} catch (error) {
			console.error('Calendar search error:', error);
			errorMessage = error.message || 'Failed to search flights calendar. Please try again.';
		} finally {
			searching = false;
		}
	};

	// Handle search submission
	const handleSearch = async () => {
		// If in calendar mode, use calendar search
		if (searchMode === 'calendar') {
			return handleCalendarSearch();
		}
		
		errorMessage = '';
		
		// Validate based on flight type
		if (flightType === 'multi_city') {
			const validSegments = multiCitySegments.filter(s => s.departure && s.arrival && s.date);
			if (validSegments.length < 2) {
				errorMessage = 'Please provide at least 2 complete flight segments for multi-city search.';
				return;
			}
		} else {
			if (!departure || !destination || !outboundDate) {
				errorMessage = 'Please fill in departure city, destination, and departure date.';
				return;
			}
			if (flightType === 'round_trip' && !returnDate) {
				errorMessage = 'Please select a return date for round trip.';
				return;
			}
		}

		searching = true;
		searchResults = null;
		calendarResults = null;
		selectedFlight = null;

		try {
			const params = {
				engine: 'google_flights',
				currency: currency,
				hl: language,
				gl: country,
				flight_type: flightType
			};

			// Add basic parameters for non-multi-city
			if (flightType !== 'multi_city') {
				params.departure_id = departure;
				params.arrival_id = destination;
				params.outbound_date = outboundDate;
				if (flightType === 'round_trip' && returnDate) {
					params.return_date = returnDate;
				}
			} else {
				// Build multi-city JSON
				const validSegments = multiCitySegments.filter(s => s.departure && s.arrival && s.date);
				params.multi_city_json = JSON.stringify(validSegments.map(s => ({
					departure_id: s.departure,
					arrival_id: s.arrival,
					date: s.date
				})));
			}

			// Add passengers
			if (adults > 0) params.adults = adults;
			if (children > 0) params.children = children;
			if (infantsInSeat > 0) params.infants_in_seat = infantsInSeat;
			if (infantsOnLap > 0) params.infants_on_lap = infantsOnLap;

			// Add preferences
			if (travelClass !== 'economy') params.travel_class = travelClass;
			if (stops !== 'any') params.stops = stops;
			if (sortBy) params.sort_by = sortBy;
			if (maxPrice) params.max_price = parseInt(maxPrice);

			// Add baggage
			if (carryOnBags) params.carry_on_bags = parseInt(carryOnBags);
			if (checkedBags) params.checked_bags = parseInt(checkedBags);

			// Add airlines
			if (includedAirlines) params.included_airlines = includedAirlines;
			if (excludedAirlines) params.excluded_airlines = excludedAirlines;

			// Add airports
			if (includedConnectingAirports) params.included_connecting_airports = includedConnectingAirports;
			if (excludedConnectingAirports) params.excluded_connecting_airports = excludedConnectingAirports;

			// Add time preferences
			if (outboundTimes) params.outbound_times = outboundTimes;
			if (returnTimes) params.return_times = returnTimes;

			// Add advanced filters
			if (emissions) params.emissions = '1';
			if (layoverDurationMin) params.layover_duration_min = parseInt(layoverDurationMin);
			if (layoverDurationMax) params.layover_duration_max = parseInt(layoverDurationMax);
			if (maxFlightDuration) params.max_flight_duration = parseInt(maxFlightDuration);
			if (separateTickets) params.separate_tickets = separateTickets;
			if (showCheapestFlights) params.show_cheapest_flights = true;
			if (showHiddenFlights) params.show_hidden_flights = true;

			// Add pagination/booking tokens
			if (departureToken) params.departure_token = departureToken;
			if (bookingToken) params.booking_token = bookingToken;

			console.log('Searching with params:', params);
			const response = await googleFlightsApi.searchFlights(params);
			console.log('Google Flights API response:', response);

			searchResults = response;
		} catch (error) {
			console.error('Search error:', error);
			errorMessage = error.message || 'Failed to search flights. Please try again.';
		} finally {
			searching = false;
		}
	};

	// View booking options for a flight
	const viewBookingOptions = async (flight) => {
		if (!flight.booking_token) return;
		
		searching = true;
		try {
			const params = {
				engine: 'google_flights',
				booking_token: flight.booking_token,
				currency: currency,
				hl: language,
				gl: country
			};
			
			const response = await googleFlightsApi.searchFlights(params);
			selectedFlight = {
				...flight,
				bookingOptions: response.booking_options || [],
				selectedFlights: response.selected_flights || []
			};
		} catch (error) {
			console.error('Booking options error:', error);
			errorMessage = 'Failed to load booking options.';
		} finally {
			searching = false;
		}
	};

	// Format price
	const formatPrice = (price) => {
		if (!price) return 'N/A';
		return new Intl.NumberFormat('en-HK', {
			style: 'currency',
			currency: currency,
			minimumFractionDigits: 0
		}).format(price);
	};

	// Format duration (minutes to hours/minutes)
	const formatDuration = (minutes) => {
		if (!minutes) return 'N/A';
		const hours = Math.floor(minutes / 60);
		const mins = minutes % 60;
		return `${hours}h ${mins}m`;
	};

	// Format date/time
	const formatDateTime = (dateStr, timeStr) => {
		if (!dateStr || !timeStr) return '';
		return `${dateStr} ${timeStr}`;
	};

	// Get today's date in YYYY-MM-DD format
	const getTodayDate = () => {
		const today = new Date();
		return today.toISOString().split('T')[0];
	};

	// Format date for display (short format)
	const formatShortDate = (dateStr) => {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	};

	// Get min/max prices from calendar data
	const getCalendarPriceRange = (calendarData) => {
		if (!calendarData || !calendarData.length) return { min: 0, max: 0 };
		const prices = calendarData.map(item => item.price).filter(p => p);
		return {
			min: Math.min(...prices),
			max: Math.max(...prices)
		};
	};

	// Get color for price cell based on value
	const getPriceColor = (price, minPrice, maxPrice) => {
		if (!price || !minPrice || !maxPrice) return 'bg-gray-100 dark:bg-gray-700';
		const range = maxPrice - minPrice;
		const position = (price - minPrice) / range;
		
		if (position < 0.33) return 'bg-green-100 dark:bg-green-900/30 text-green-900 dark:text-green-100';
		if (position < 0.67) return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-900 dark:text-yellow-100';
		return 'bg-red-100 dark:bg-red-900/30 text-red-900 dark:text-red-100';
	};

	onMount(() => {
		const today = getTodayDate();
		outboundDate = today;
		outboundDateStart = today;
		
		// Set default end dates (7 days from today)
		const nextWeek = new Date();
		nextWeek.setDate(nextWeek.getDate() + 7);
		const nextWeekStr = nextWeek.toISOString().split('T')[0];
		outboundDateEnd = nextWeekStr;
		
		// Set return dates (14 days from today)
		const twoWeeks = new Date();
		twoWeeks.setDate(twoWeeks.getDate() + 14);
		returnDateStart = nextWeekStr;
		returnDateEnd = twoWeeks.toISOString().split('T')[0];
	});
</script>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<nav class="px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
		<div class="flex items-center">
			{#if $mobile}
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class="self-center p-1.5">
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
						<a class="min-w-fit transition flex items-center gap-2" href="/google-flight-search">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								class="size-5 text-gray-900 dark:text-gray-100"
							>
								<path
									d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linejoin="round"
									stroke-linecap="round"
								/>
							</svg>
							{$i18n.t('Google Flight Search')}
						</a>
					</div>
				</div>

				<div class="self-center flex items-center gap-1">
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
								<div class="self-center">
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
					{$i18n.t('Google Flight Search')}
				</h1>
				<p class="text-gray-600 dark:text-gray-400">
					{$i18n.t('Comprehensive flight search with advanced filters and options')}
				</p>
			</div>

			<!-- Search Mode Tabs -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
				<div class="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-700">
					<button
						type="button"
						on:click={() => { searchMode = 'standard'; calendarResults = null; }}
						class="px-4 py-2 font-medium transition {searchMode === 'standard' 
							? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400' 
							: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}"
					>
						Standard Search
					</button>
					<button
						type="button"
						on:click={() => { searchMode = 'calendar'; searchResults = null; }}
						class="px-4 py-2 font-medium transition {searchMode === 'calendar' 
							? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400' 
							: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}"
					>
						📅 Price Calendar
					</button>
				</div>
			</div>

			<!-- Search Form -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
				<form on:submit|preventDefault={handleSearch}>
					
					<!-- Basic Search Section -->
					<div class="mb-6">
						<button
							type="button"
							on:click={() => toggleSection('basic')}
							class="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-650 transition"
						>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
								Basic Search Parameters
							</h3>
							<svg
								class="w-5 h-5 transform transition-transform {activeSection === 'basic' ? 'rotate-180' : ''}"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
							</svg>
						</button>
						
						{#if activeSection === 'basic'}
							<div class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
								<!-- Flight Type -->
								<div>
									<label for="flightType" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Flight Type *
									</label>
									<select
										id="flightType"
										bind:value={flightType}
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									>
										<option value="round_trip">Round Trip</option>
										<option value="one_way">One Way</option>
										{#if searchMode !== 'calendar'}
											<option value="multi_city">Multi-City</option>
										{/if}
									</select>
									{#if searchMode === 'calendar'}
										<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
											💡 Calendar view shows price grid for round trip or one way flights
										</p>
									{/if}
								</div>

								{#if flightType !== 'multi_city'}
									<!-- Departure City -->
									<div>
										<label for="departure" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											Departure City/Airport *
										</label>
										<input
											id="departure"
											type="text"
											bind:value={departure}
											placeholder="e.g., HKG, JFK, LAX"
											class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
											required
										/>
									</div>

									<!-- Destination City -->
									<div>
										<label for="destination" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											Destination City/Airport *
										</label>
										<input
											id="destination"
											type="text"
											bind:value={destination}
											placeholder="e.g., HKG, JFK, LAX"
											class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
											required
										/>
									</div>

									{#if searchMode === 'standard'}
										<!-- Outbound Date -->
										<div>
											<label for="outboundDate" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
												Outbound Date *
											</label>
											<input
												id="outboundDate"
												type="date"
												bind:value={outboundDate}
												min={getTodayDate()}
												class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
												required
											/>
										</div>

										<!-- Return Date -->
										{#if flightType === 'round_trip'}
											<div>
												<label for="returnDate" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
													Return Date *
												</label>
												<input
													id="returnDate"
													type="date"
													bind:value={returnDate}
													min={outboundDate || getTodayDate()}
													class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
													required
												/>
											</div>
										{/if}
									{:else}
									<!-- Calendar Mode Date Ranges -->
									<div class="col-span-full">
										<h4 class="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">
											📅 Outbound Date Range
										</h4>
										<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
											<div>
												<label for="outboundDateStart" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
													Start Date *
												</label>
												<input
													id="outboundDateStart"
													type="date"
													bind:value={outboundDateStart}
													min={getTodayDate()}
													class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
													required
												/>
											</div>
											<div>
												<label for="outboundDateEnd" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
													End Date *
												</label>
												<input
													id="outboundDateEnd"
													type="date"
													bind:value={outboundDateEnd}
													min={outboundDateStart || getTodayDate()}
													class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
													required
												/>
											</div>
										</div>
									</div>

									{#if flightType === 'round_trip'}
										<div class="col-span-full">
											<h4 class="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">
												🔄 Return Date Range
											</h4>
											<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
												<div>
													<label for="returnDateStart" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
														Start Date *
													</label>
													<input
														id="returnDateStart"
														type="date"
														bind:value={returnDateStart}
														min={outboundDateEnd || outboundDateStart || getTodayDate()}
														class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
														required
													/>
												</div>
												<div>
													<label for="returnDateEnd" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
														End Date *
													</label>
													<input
														id="returnDateEnd"
														type="date"
														bind:value={returnDateEnd}
														min={returnDateStart || outboundDateEnd || getTodayDate()}
														class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
														required
													/>
												</div>
											</div>
										</div>
									{/if}
									{/if}
								{/if}

								<!-- Language -->
								<div>
									<label for="language" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Language
									</label>
									<select
										id="language"
										bind:value={language}
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									>
										<option value="en">English</option>
										<option value="zh-CN">Chinese (Simplified)</option>
										<option value="zh-TW">Chinese (Traditional)</option>
										<option value="es">Spanish</option>
										<option value="fr">French</option>
										<option value="de">German</option>
										<option value="ja">Japanese</option>
										<option value="ko">Korean</option>
									</select>
								</div>

								<!-- Country -->
								<div>
									<label for="country" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Country
									</label>
									<select
										id="country"
										bind:value={country}
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									>
										<option value="US">United States</option>
										<option value="HK">Hong Kong</option>
										<option value="CN">China</option>
										<option value="GB">United Kingdom</option>
										<option value="CA">Canada</option>
										<option value="AU">Australia</option>
										<option value="JP">Japan</option>
										<option value="KR">South Korea</option>
									</select>
								</div>

								<!-- Currency -->
								<div>
									<label for="currency" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Currency
									</label>
									<select
										id="currency"
										bind:value={currency}
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									>
										<option value="HKD">HKD (Hong Kong Dollar)</option>
										<option value="USD">USD (US Dollar)</option>
										<option value="EUR">EUR (Euro)</option>
										<option value="GBP">GBP (British Pound)</option>
										<option value="CNY">CNY (Chinese Yuan)</option>
										<option value="JPY">JPY (Japanese Yen)</option>
										<option value="KRW">KRW (South Korean Won)</option>
									</select>
								</div>
							</div>

							<!-- Multi-City Segments -->
							{#if flightType === 'multi_city'}
								<div class="mt-4">
									<h4 class="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">
										Flight Segments
									</h4>
									{#each multiCitySegments as segment, i}
										<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-3 p-3 border border-gray-300 dark:border-gray-600 rounded-lg">
											<div>
												<label for="seg-dep-{i}" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
													Departure *
												</label>
												<input
													id="seg-dep-{i}"
													type="text"
													bind:value={segment.departure}
													placeholder="e.g., HKG"
													class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
												/>
											</div>
											<div>
												<label for="seg-arr-{i}" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
													Arrival *
												</label>
												<input
													id="seg-arr-{i}"
													type="text"
													bind:value={segment.arrival}
													placeholder="e.g., JFK"
													class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
												/>
											</div>
											<div>
												<label for="seg-date-{i}" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
													Date *
												</label>
												<input
													id="seg-date-{i}"
													type="date"
													bind:value={segment.date}
													min={getTodayDate()}
													class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
												/>
											</div>
											<div class="flex items-end">
												<button
													type="button"
													on:click={() => removeSegment(i)}
													disabled={multiCitySegments.length <= 2}
													class="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
												>
													Remove
												</button>
											</div>
										</div>
									{/each}
									<button
										type="button"
										on:click={addSegment}
										class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
									>
										+ Add Segment
									</button>
								</div>
							{/if}
						{/if}
					</div>

					<!-- Passengers Section -->
					<div class="mb-6">
						<button
							type="button"
							on:click={() => toggleSection('passengers')}
							class="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-650 transition"
						>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
								Passengers
							</h3>
							<svg
								class="w-5 h-5 transform transition-transform {activeSection === 'passengers' ? 'rotate-180' : ''}"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
							</svg>
						</button>
						
						{#if activeSection === 'passengers'}
							<div class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
								<div>
									<label for="adults" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Adults (12+)
									</label>
									<input
										id="adults"
										type="number"
										bind:value={adults}
										min="1"
										max="9"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="children" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Children (2-11)
									</label>
									<input
										id="children"
										type="number"
										bind:value={children}
										min="0"
										max="9"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="infantsInSeat" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Infants in Seat
									</label>
									<input
										id="infantsInSeat"
										type="number"
										bind:value={infantsInSeat}
										min="0"
										max="9"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="infantsOnLap" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Infants on Lap
									</label>
									<input
										id="infantsOnLap"
										type="number"
										bind:value={infantsOnLap}
										min="0"
										max="9"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
							</div>
						{/if}
					</div>

					<!-- Flight Preferences Section -->
					<div class="mb-6">
						<button
							type="button"
							on:click={() => toggleSection('preferences')}
							class="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-650 transition"
						>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
								Flight Preferences
							</h3>
							<svg
								class="w-5 h-5 transform transition-transform {activeSection === 'preferences' ? 'rotate-180' : ''}"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
							</svg>
						</button>
						
						{#if activeSection === 'preferences'}
							<div class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
								<div>
									<label for="travelClass" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Travel Class
									</label>
									<select
										id="travelClass"
										bind:value={travelClass}
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									>
										<option value="economy">Economy</option>
										<option value="premium_economy">Premium Economy</option>
										<option value="business">Business</option>
										<option value="first_class">First Class</option>
									</select>
								</div>
								<div>
									<label for="stops" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Number of Stops
									</label>
									<select
										id="stops"
										bind:value={stops}
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									>
										<option value="any">Any</option>
										<option value="nonstop">Nonstop</option>
										<option value="one_stop_or_fewer">1 Stop or Fewer</option>
										<option value="two_stops_or_fewer">2 Stops or Fewer</option>
									</select>
								</div>
								<div>
									<label for="sortBy" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Sort By
									</label>
									<select
										id="sortBy"
										bind:value={sortBy}
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									>
										<option value="">Top Flights (Default)</option>
										<option value="price">Price</option>
										<option value="departure_time">Departure Time</option>
										<option value="arrival_time">Arrival Time</option>
										<option value="duration">Duration</option>
										<option value="emissions">Emissions</option>
									</select>
								</div>
								<div>
									<label for="maxPrice" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Max Price ({currency})
									</label>
									<input
										id="maxPrice"
										type="number"
										bind:value={maxPrice}
										min="0"
										placeholder="No limit"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="carryOnBags" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Carry-on Bags
									</label>
									<input
										id="carryOnBags"
										type="number"
										bind:value={carryOnBags}
										min="0"
										placeholder="Any"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="checkedBags" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Checked Bags
									</label>
									<input
										id="checkedBags"
										type="number"
										bind:value={checkedBags}
										min="0"
										placeholder="Any"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
							</div>
						{/if}
					</div>

					<!-- Airlines & Airports Section -->
					<div class="mb-6">
						<button
							type="button"
							on:click={() => toggleSection('airlines')}
							class="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-650 transition"
						>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
								Airlines & Connecting Airports
							</h3>
							<svg
								class="w-5 h-5 transform transition-transform {activeSection === 'airlines' ? 'rotate-180' : ''}"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
							</svg>
						</button>
						
						{#if activeSection === 'airlines'}
							<div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
								<div>
									<label for="includedAirlines" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Included Airlines (comma-separated)
									</label>
									<input
										id="includedAirlines"
										type="text"
										bind:value={includedAirlines}
										placeholder="e.g., AA,UA,DL"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="excludedAirlines" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Excluded Airlines (comma-separated)
									</label>
									<input
										id="excludedAirlines"
										type="text"
										bind:value={excludedAirlines}
										placeholder="e.g., AA,UA,DL"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="includedConnectingAirports" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Included Connecting Airports
									</label>
									<input
										id="includedConnectingAirports"
										type="text"
										bind:value={includedConnectingAirports}
										placeholder="e.g., LAX,SFO,ORD"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="excludedConnectingAirports" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Excluded Connecting Airports
									</label>
									<input
										id="excludedConnectingAirports"
										type="text"
										bind:value={excludedConnectingAirports}
										placeholder="e.g., LAX,SFO,ORD"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
							</div>
						{/if}
					</div>

					<!-- Advanced Filters Section -->
					<div class="mb-6">
						<button
							type="button"
							on:click={() => toggleSection('advanced')}
							class="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-650 transition"
						>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
								Advanced Filters
							</h3>
							<svg
								class="w-5 h-5 transform transition-transform {activeSection === 'advanced' ? 'rotate-180' : ''}"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
							</svg>
						</button>
						
						{#if activeSection === 'advanced'}
							<div class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
								<div>
									<label for="outboundTimes" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Outbound Times (hours 0-23)
									</label>
									<input
										id="outboundTimes"
										type="text"
										bind:value={outboundTimes}
										placeholder="e.g., 6,7,8,9"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="returnTimes" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Return Times (hours 0-23)
									</label>
									<input
										id="returnTimes"
										type="text"
										bind:value={returnTimes}
										placeholder="e.g., 14,15,16,17"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="layoverDurationMin" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Min Layover (minutes)
									</label>
									<input
										id="layoverDurationMin"
										type="number"
										bind:value={layoverDurationMin}
										min="0"
										placeholder="No minimum"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="layoverDurationMax" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Max Layover (minutes)
									</label>
									<input
										id="layoverDurationMax"
										type="number"
										bind:value={layoverDurationMax}
										min="0"
										placeholder="No maximum"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="maxFlightDuration" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Max Flight Duration (minutes)
									</label>
									<input
										id="maxFlightDuration"
										type="number"
										bind:value={maxFlightDuration}
										min="0"
										placeholder="No maximum"
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									/>
								</div>
								<div>
									<label for="separateTickets" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Separate Tickets
									</label>
									<select
										id="separateTickets"
										bind:value={separateTickets}
										class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									>
										<option value="">Any</option>
										<option value="0">Hide</option>
										<option value="1">Show</option>
									</select>
								</div>
								<div class="flex items-center space-x-2">
									<input
										id="emissions"
										type="checkbox"
										bind:checked={emissions}
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
									/>
									<label for="emissions" class="text-sm font-medium text-gray-700 dark:text-gray-300">
										Less Emissions Only
									</label>
								</div>
								<div class="flex items-center space-x-2">
									<input
										id="showCheapestFlights"
										type="checkbox"
										bind:checked={showCheapestFlights}
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
									/>
									<label for="showCheapestFlights" class="text-sm font-medium text-gray-700 dark:text-gray-300">
										Show Cheapest Flights
									</label>
								</div>
								<div class="flex items-center space-x-2">
									<input
										id="showHiddenFlights"
										type="checkbox"
										bind:checked={showHiddenFlights}
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
									/>
									<label for="showHiddenFlights" class="text-sm font-medium text-gray-700 dark:text-gray-300">
										Show Hidden Flights
									</label>
								</div>
							</div>
						{/if}
					</div>

					<!-- Error Message -->
					{#if errorMessage}
						<div class="mb-4 p-3 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg text-red-700 dark:text-red-300 text-sm">
							{errorMessage}
						</div>
					{/if}

					<!-- Search Button -->
					<div class="flex justify-end">
						<button
							type="submit"
							disabled={searching}
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						>
							{#if searching}
								<svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								Searching...
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
									<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
								</svg>
								Search Flights
							{/if}
						</button>
					</div>
				</form>
			</div>

			<!-- Calendar Results -->
			{#if calendarResults}
				<div class="space-y-6">
					<!-- Search Metadata -->
					{#if calendarResults.search_metadata}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4">
							<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-3">Price Calendar</h2>
							<div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
								<div>
									<span class="text-gray-600 dark:text-gray-400">Route:</span>
									<span class="ml-2 font-medium text-gray-900 dark:text-gray-100">{departure} → {destination}</span>
								</div>
								<div>
									<span class="text-gray-600 dark:text-gray-400">Status:</span>
									<span class="ml-2 font-medium text-gray-900 dark:text-gray-100">{calendarResults.search_metadata.status}</span>
								</div>
								{#if calendarResults.search_metadata.request_url}
									<div class="col-span-2">
										<a href={calendarResults.search_metadata.request_url} target="_blank" class="text-blue-600 hover:underline">
											View on Google Flights →
										</a>
									</div>
								{/if}
							</div>
						</div>
					{/if}

					<!-- Price Grid/Table -->
					{#if calendarResults.price_grid}
						{@const priceRange = getCalendarPriceRange(calendarResults.price_grid)}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
							<div class="flex justify-between items-center mb-4">
								<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
									Price Grid
								</h2>
								<div class="text-sm">
									<span class="text-gray-600 dark:text-gray-400">Price range:</span>
									<span class="ml-2 font-bold text-green-600 dark:text-green-400">{formatPrice(priceRange.min)}</span>
									<span class="mx-1">-</span>
									<span class="font-bold text-red-600 dark:text-red-400">{formatPrice(priceRange.max)}</span>
								</div>
							</div>

						<!-- Legend -->
						<div class="mb-4 flex flex-wrap gap-4 text-sm">
							<div class="flex items-center gap-2">
								<div class="w-4 h-4 bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded"></div>
								<span class="text-gray-600 dark:text-gray-400">Low Price</span>
							</div>
							<div class="flex items-center gap-2">
								<div class="w-4 h-4 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 rounded"></div>
								<span class="text-gray-600 dark:text-gray-400">Medium Price</span>
							</div>
							<div class="flex items-center gap-2">
								<div class="w-4 h-4 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded"></div>
								<span class="text-gray-600 dark:text-gray-400">High Price</span>
							</div>
							<div class="flex items-center gap-2">
								<span class="text-green-600 dark:text-green-400 font-semibold">⭐</span>
								<span class="text-gray-600 dark:text-gray-400">Lowest Price</span>
							</div>
						</div>

							<!-- Scrollable table container -->
							<div class="overflow-x-auto">
								<table class="w-full border-collapse">
									<thead>
										<tr>
											<th class="p-3 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50">
												{flightType === 'round_trip' ? 'Outbound → Return' : 'Outbound Date'}
											</th>
											{#if flightType === 'round_trip' && calendarResults.price_grid[0]?.return_dates}
												{#each calendarResults.price_grid[0].return_dates as returnDate}
													<th class="p-3 text-center text-sm font-semibold text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50">
														{formatShortDate(returnDate)}
													</th>
												{/each}
											{:else}
												<th class="p-3 text-center text-sm font-semibold text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50">
													Price
												</th>
											{/if}
										</tr>
									</thead>
									<tbody>
										{#each calendarResults.price_grid as row}
											<tr>
												<td class="p-3 text-sm font-medium text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50">
													{formatShortDate(row.departure_date)}
												</td>
												{#if flightType === 'round_trip' && row.prices}
													{#each row.prices as price, idx}
														<td class="p-3 text-center border border-gray-300 dark:border-gray-600 {getPriceColor(price, priceRange.min, priceRange.max)}">
															{#if price}
																<div class="font-bold">{formatPrice(price)}</div>
																{#if row.is_lowest_price && row.is_lowest_price[idx]}
																	<div class="text-xs font-semibold text-green-600 dark:text-green-400 mt-1">
																		⭐ Lowest
																	</div>
																{/if}
																{#if row.flights && row.flights[idx]}
																	<div class="text-xs opacity-75 mt-1">
																		{formatDuration(row.flights[idx].total_duration)}
																	</div>
																{/if}
															{:else}
																<span class="text-gray-400">—</span>
															{/if}
														</td>
													{/each}
												{:else}
													<td class="p-3 text-center border border-gray-300 dark:border-gray-600 {getPriceColor(row.price, priceRange.min, priceRange.max)}">
														{#if row.price}
															<div class="font-bold">{formatPrice(row.price)}</div>
															{#if row.is_lowest_price}
																<div class="text-xs font-semibold text-green-600 dark:text-green-400 mt-1">
																	⭐ Lowest
																</div>
															{/if}
															{#if row.total_duration}
																<div class="text-xs opacity-75 mt-1">
																	{formatDuration(row.total_duration)}
																</div>
															{/if}
														{:else}
															<span class="text-gray-400">—</span>
														{/if}
													</td>
												{/if}
											</tr>
										{/each}
									</tbody>
								</table>
							</div>

							<p class="text-sm text-gray-600 dark:text-gray-400 mt-4">
								💡 Tip: Click on a date combination in Google Flights to see full flight details
							</p>
						</div>
					{/if}

					<!-- No Results -->
					{#if !calendarResults.price_grid || calendarResults.price_grid.length === 0}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
							<svg class="mx-auto h-16 w-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
							</svg>
							<h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
								No price data available
							</h3>
							<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
								{calendarResults.error || 'Try adjusting your date ranges or search criteria'}
							</p>
						</div>
					{/if}
				</div>
			{/if}

			<!-- Search Results -->
			{#if searchResults}
				<div class="space-y-6">
					
					<!-- Search Metadata -->
					{#if searchResults.search_metadata}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4">
							<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-3">Search Information</h2>
							<div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
								<div>
									<span class="text-gray-600 dark:text-gray-400">Status:</span>
									<span class="ml-2 font-medium text-gray-900 dark:text-gray-100">{searchResults.search_metadata.status}</span>
								</div>
								<div>
									<span class="text-gray-600 dark:text-gray-400">Total Time:</span>
									<span class="ml-2 font-medium text-gray-900 dark:text-gray-100">{searchResults.search_metadata.total_time_taken?.toFixed(2)}s</span>
								</div>
								{#if searchResults.search_metadata.request_url}
									<div class="col-span-2">
										<a href={searchResults.search_metadata.request_url} target="_blank" class="text-blue-600 hover:underline">
											View on Google Flights →
										</a>
									</div>
								{/if}
							</div>
						</div>
					{/if}

					<!-- Price Insights -->
					{#if searchResults.price_insights}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
							<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">Price Insights</h2>
							<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
								<div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
									<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">Lowest Price</div>
									<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">
										{formatPrice(searchResults.price_insights.lowest_price)}
									</div>
								</div>
								<div class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
									<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">Price Level</div>
									<div class="text-2xl font-bold text-green-600 dark:text-green-400 capitalize">
										{searchResults.price_insights.price_level || 'N/A'}
									</div>
								</div>
								{#if searchResults.price_insights.typical_price_range}
									<div class="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
										<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">Typical Range</div>
										<div class="text-lg font-bold text-purple-600 dark:text-purple-400">
											{formatPrice(searchResults.price_insights.typical_price_range.low_price)} - {formatPrice(searchResults.price_insights.typical_price_range.high_price)}
										</div>
									</div>
								{/if}
							</div>
						</div>
					{/if}

					<!-- Best Flights -->
					{#if searchResults.best_flights && searchResults.best_flights.length > 0}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
							<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
								Best Flights ({searchResults.best_flights.length})
							</h2>
							
							<div class="space-y-4">
								{#each searchResults.best_flights as flight}
									<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition">
										<div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
											<!-- Flight Info -->
											<div class="flex-1">
												{#if flight.airline_logo}
													<img src={flight.airline_logo} alt="Airline" class="h-8 mb-2" />
												{/if}
												
												{#each flight.flights || [] as segment, i}
													<div class="mb-3 {i > 0 ? 'mt-3 pt-3 border-t border-gray-200 dark:border-gray-700' : ''}">
														<div class="flex items-center gap-3 text-sm mb-1">
															<span class="font-semibold text-gray-900 dark:text-gray-100">
																{segment.airline || 'N/A'}
															</span>
															<span class="text-gray-600 dark:text-gray-400">
																{segment.flight_number || ''}
															</span>
															<span class="text-gray-600 dark:text-gray-400">
																{segment.airplane || ''}
															</span>
														</div>
														
														<div class="flex items-center gap-3">
															<div class="text-center">
																<div class="text-lg font-bold text-gray-900 dark:text-gray-100">
																	{segment.departure_airport?.time || ''}
																</div>
																<div class="text-sm text-gray-600 dark:text-gray-400">
																	{segment.departure_airport?.id || ''}
																</div>
																<div class="text-xs text-gray-500 dark:text-gray-500">
																	{segment.departure_airport?.date || ''}
																</div>
															</div>
															
															<div class="flex-1 flex flex-col items-center">
																<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">
																	{formatDuration(segment.duration)}
																</div>
																<div class="w-full h-px bg-gray-300 dark:bg-gray-600 relative">
																	<svg class="absolute -right-1 -top-1 w-3 h-3 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
																		<path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"></path>
																	</svg>
																</div>
																{#if segment.travel_class}
																	<div class="text-xs text-gray-500 dark:text-gray-500 mt-1 capitalize">
																		{segment.travel_class}
																	</div>
																{/if}
															</div>
															
															<div class="text-center">
																<div class="text-lg font-bold text-gray-900 dark:text-gray-100">
																	{segment.arrival_airport?.time || ''}
																</div>
																<div class="text-sm text-gray-600 dark:text-gray-400">
																	{segment.arrival_airport?.id || ''}
																</div>
																<div class="text-xs text-gray-500 dark:text-gray-500">
																	{segment.arrival_airport?.date || ''}
																</div>
															</div>
														</div>

														<!-- Amenities -->
														{#if segment.detected_extensions}
															<div class="mt-2 flex flex-wrap gap-2 text-xs">
																{#if segment.detected_extensions.wifi}
																	<span class="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
																		WiFi: {segment.detected_extensions.wifi}
																	</span>
																{/if}
																{#if segment.detected_extensions.seat_type}
																	<span class="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
																		{segment.detected_extensions.seat_type}
																	</span>
																{/if}
																{#if segment.detected_extensions.has_power_and_usb_outlets}
																	<span class="px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded">
																		Power & USB
																	</span>
																{/if}
																{#if segment.detected_extensions.has_personal_video_screen}
																	<span class="px-2 py-1 bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-300 rounded">
																		Video Screen
																	</span>
																{/if}
															</div>
														{/if}
													</div>
													
													<!-- Layover -->
													{#if i < (flight.flights?.length || 0) - 1 && flight.layovers && flight.layovers[i]}
														<div class="my-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded text-sm">
															<span class="text-yellow-700 dark:text-yellow-300">
																⏱ Layover in {flight.layovers[i].id}: {formatDuration(flight.layovers[i].duration)}
																{#if flight.layovers[i].is_overnight}
																	<span class="ml-2 text-xs">(Overnight)</span>
																{/if}
															</span>
														</div>
													{/if}
												{/each}

												<!-- Carbon Emissions -->
												{#if flight.carbon_emissions}
													<div class="mt-3 text-sm text-gray-600 dark:text-gray-400">
														<span class="font-medium">CO₂:</span>
														{flight.carbon_emissions.this_flight}kg
														{#if flight.carbon_emissions.difference_percent}
															<span class="ml-2 {flight.carbon_emissions.difference_percent < 0 ? 'text-green-600' : 'text-red-600'}">
																({flight.carbon_emissions.difference_percent > 0 ? '+' : ''}{flight.carbon_emissions.difference_percent}% vs typical)
															</span>
														{/if}
													</div>
												{/if}

												<!-- Extensions -->
												{#if flight.extensions && flight.extensions.length > 0}
													<div class="mt-2 flex flex-wrap gap-2 text-xs">
														{#each flight.extensions as ext}
															<span class="text-gray-600 dark:text-gray-400">{ext}</span>
														{/each}
													</div>
												{/if}
											</div>

											<!-- Price and Actions -->
											<div class="lg:text-right flex flex-row lg:flex-col items-center lg:items-end gap-3">
												<div>
													<div class="text-3xl font-bold text-blue-600 dark:text-blue-400">
														{formatPrice(flight.price)}
													</div>
													<div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
														Total: {formatDuration(flight.total_duration)}
													</div>
												</div>
												{#if flight.booking_token}
													<button
														on:click={() => viewBookingOptions(flight)}
														class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm transition"
													>
														View Booking
													</button>
												{/if}
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Other Flights -->
					{#if searchResults.other_flights && searchResults.other_flights.length > 0}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
							<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
								Other Flights ({searchResults.other_flights.length})
							</h2>
							
							<div class="space-y-4">
								{#each searchResults.other_flights.slice(0, 10) as flight}
									<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition">
										<!-- Similar structure as best flights, condensed -->
										<div class="flex justify-between items-center">
											<div class="flex-1">
												{#if flight.flights && flight.flights[0]}
													<div class="text-sm">
														<span class="font-semibold">{flight.flights[0].airline}</span>
														<span class="mx-2">•</span>
														<span>{flight.flights[0].departure_airport?.time} {flight.flights[0].departure_airport?.id}</span>
														<span class="mx-2">→</span>
														<span>{flight.flights[flight.flights.length - 1].arrival_airport?.time} {flight.flights[flight.flights.length - 1].arrival_airport?.id}</span>
														<span class="mx-2">•</span>
														<span class="text-gray-600 dark:text-gray-400">{formatDuration(flight.total_duration)}</span>
													</div>
												{/if}
											</div>
											<div class="text-right">
												<div class="text-xl font-bold text-blue-600 dark:text-blue-400">
													{formatPrice(flight.price)}
												</div>
												{#if flight.booking_token}
													<button
														on:click={() => viewBookingOptions(flight)}
														class="mt-1 text-sm text-blue-600 hover:underline"
													>
														View Booking
													</button>
												{/if}
											</div>
										</div>
									</div>
								{/each}
								{#if searchResults.other_flights.length > 10}
									<div class="text-center text-gray-600 dark:text-gray-400 text-sm">
										Showing 10 of {searchResults.other_flights.length} flights
									</div>
								{/if}
							</div>
						</div>
					{/if}

					<!-- No Results -->
					{#if (!searchResults.best_flights || searchResults.best_flights.length === 0) && (!searchResults.other_flights || searchResults.other_flights.length === 0) && searchResults.error}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
							<svg class="mx-auto h-16 w-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
							</svg>
							<h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
								No flights found
							</h3>
							<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
								{searchResults.error || 'Try adjusting your search criteria'}
							</p>
						</div>
					{/if}
				</div>
			{/if}

			<!-- Booking Options Modal -->
			{#if selectedFlight}
				<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
						<div class="p-6">
							<div class="flex justify-between items-center mb-4">
								<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Booking Options</h2>
								<button
									on:click={() => selectedFlight = null}
									class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
								>
									<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
									</svg>
								</button>
							</div>

							{#if selectedFlight.bookingOptions && selectedFlight.bookingOptions.length > 0}
								<div class="space-y-4">
									{#each selectedFlight.bookingOptions as option}
										<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
											<div class="flex justify-between items-start mb-3">
												<div>
													<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
														{option.book_with || 'Provider'}
													</h3>
													{#if option.option_title}
														<p class="text-sm text-gray-600 dark:text-gray-400">{option.option_title}</p>
													{/if}
												</div>
												<div class="text-right">
													<div class="text-2xl font-bold text-green-600 dark:text-green-400">
														{formatPrice(option.price)}
													</div>
												</div>
											</div>

											{#if option.extensions && option.extensions.length > 0}
												<div class="mb-3 space-y-1">
													{#each option.extensions as ext}
														<div class="text-sm text-gray-600 dark:text-gray-400">{ext}</div>
													{/each}
												</div>
											{/if}

											{#if option.baggage_prices && option.baggage_prices.length > 0}
												<div class="mb-3">
													<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Baggage:</h4>
													{#each option.baggage_prices as baggage}
														<div class="text-sm text-gray-600 dark:text-gray-400">{baggage}</div>
													{/each}
												</div>
											{/if}

											{#if option.booking_request?.url}
												<a
													href={option.booking_request.url}
													target="_blank"
													class="inline-block px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition"
												>
													Book Now →
												</a>
											{/if}
										</div>
									{/each}
								</div>
							{:else}
								<p class="text-gray-600 dark:text-gray-400">No booking options available.</p>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
