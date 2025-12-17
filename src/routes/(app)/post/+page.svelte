<script>
	import { mobile, showArchivedChats, showSidebar, user, posts } from '$lib/stores';
	import { getContext } from 'svelte';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getFlightDataFromStorage, createFlightPostContent } from '$lib/utils/flightPostHandler.js';
	import { cityList } from '$lib/utils/cityCodes';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { createNewPost, getPostList, getPostById } from '$lib/apis/posts';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	// Tab state
let activeTab = 'website-blog';
	
	// Form content state
	let postContent = '';
	let postHashtags = '';
	let scenicImage = null;
	let flightInfoImage = null;
	
	// Website blog form fields
	let header = '';
	let firstComment = '';
	let airlineName = '';
	let returnPrice = '';
	let extraComment = '';
	let departureDate = '';
	let flightTime = '';
	let ticketValidity = '';
	let luggageInfo = '';
	let summary = '';

	// Image editing state
	let showEditImageModal = false;
	let originalScenicImage = null;  // Original image without overlays
	let editDestination = '';
	let editPromoteText = '';
	let editAirline = '';
	let editPrice = '';
	let isUpdatingImage = false;  // Loading state for image update
	
	// Post saving state
	let postSaved = false;
	let currentFlightData = null;
	
	// Mobile preview panel state
	let showMobilePreview = false;
	let hasFlightDataFromRedirect = false;
	let previewAutoOpened = false;
	
	// Auto-open preview on mobile when redirected from flight-search
	$: if ($mobile && hasFlightDataFromRedirect && !previewAutoOpened && !showMobilePreview) {
		// Small delay to ensure DOM is ready
		setTimeout(() => {
			showMobilePreview = true;
			previewAutoOpened = true;
		}, 200);
	}
	
const translateDestinationToChinese = (destination) => {
	if (!destination || typeof destination !== 'string') return destination;
	const normalized = destination.trim().toLowerCase();
	const match = cityList.find(
		(city) =>
			city.name.toLowerCase() === normalized ||
			city.chinese.toLowerCase() === normalized ||
			city.code.toLowerCase() === normalized
	);
	return match?.chinese || destination;
};

const formatHeaderWithDestination = (headerText, destination, fallback = 'Flight Deal') => {
	const translatedDestination = translateDestinationToChinese(destination);
	const destinationTag = translatedDestination ? `【${translatedDestination}】` : '';
	let baseHeader = headerText && headerText.trim() ? headerText.trim() : fallback;
	if (destinationTag && !baseHeader.includes(destinationTag)) {
		baseHeader = `${destinationTag} ${baseHeader}`.trim();
	}
	return baseHeader;
};

	// Function to save post to database
	async function savePostToDatabase() {
		if (!currentFlightData || postSaved) return;
		
		try {
			const postData = {
				title: header || `${currentFlightData.destination} Flight Deal`,
				post_content: postContent || createFlightPostContent(currentFlightData),
				flight_data: currentFlightData,
				ai_analysis: currentFlightData.aiAnalysis || {},
				scenic_image: scenicImage,
				original_scenic_image: originalScenicImage,
				flight_info_image: flightInfoImage
			};
			
			const result = await createNewPost(localStorage.token, postData);
			if (result) {
				postSaved = true;
				console.log('Post saved to database:', result);
				
				// Refresh the post list in the sidebar
				const updatedPosts = await getPostList(localStorage.token);
				posts.set(updatedPosts);
			}
		} catch (error) {
			console.error('Error saving post:', error);
		}
	}

	// Load post data when URL changes (reactive to post ID changes)
	$: {
		const postId = $page.url.searchParams.get('id');
		if (postId) {
			loadPostFromHistory(postId);
		}
	}
	
	// Function to load post from history
	async function loadPostFromHistory(postId) {
		try {
			const savedPost = await getPostById(localStorage.token, postId);
			if (savedPost) {
				console.log('Loading saved post:', savedPost);
				
				// Load flight data first
				const flightData = savedPost.flight_data;
				
				// Populate all fields from saved post
				header = formatHeaderWithDestination(
					savedPost.ai_analysis?.header || savedPost.title || '',
					flightData?.destination || '',
					savedPost.title || 'Flight Deal'
				);
				firstComment = savedPost.ai_analysis?.content || '';
				summary = savedPost.ai_analysis?.summary || '';
				postContent = savedPost.post_content || '';
				if (flightData) {
					airlineName = flightData.airline || '';
					returnPrice = flightData.returnPrice?.toString() || '';
					departureDate = flightData.departureDate || '';
					flightTime = flightData.flightTime || '';
					luggageInfo = flightData.luggageInfo || '';
					ticketValidity = flightData.ticketValidDate || '';
					extraComment = `Departure: ${new Date(flightData.departureDate).toLocaleDateString()}\nFlight Time: ${flightData.flightTime}\nPrice: $${flightData.returnPrice}`;
					
					// For editing
					editDestination = flightData.destination || '';
					editAirline = flightData.airline || '';
					editPrice = flightData.returnPrice?.toString() || '';
					editPromoteText = savedPost.ai_analysis?.promote_text || '';
					
					currentFlightData = flightData;
				}
				
				// Load images
				scenicImage = savedPost.scenic_image;
				originalScenicImage = savedPost.original_scenic_image;
				flightInfoImage = savedPost.flight_info_image;
				
				// Generate hashtags
				if (flightData?.airline) {
					postHashtags = `#FlightDeals #Travel #${flightData.airline.replace(/\s+/g, '')} #TravelTips #CheapFlights`;
				}
				
				// Mark as already saved
				postSaved = true;
			}
		} catch (error) {
			console.error('Error loading post:', error);
		}
	}

	// Handle incoming flight data from flight search OR load post from history
	onMount(async () => {
		// Check if we're loading a saved post from history
		const postId = $page.url.searchParams.get('id');
		
		if (!postId) {
			// Load from flight search (new post flow) only if no post ID
		const flightData = getFlightDataFromStorage();
		if (flightData) {
			// Mark that we have flight data from redirect (will trigger auto-open on mobile)
			hasFlightDataFromRedirect = true;
			// Populate form fields with flight data
			airlineName = flightData.airline;
			returnPrice = flightData.returnPrice.toString();
			departureDate = flightData.departureDate;
			flightTime = flightData.flightTime;
			luggageInfo = flightData.luggageInfo;
			
			// Store scenic image if available
			if (flightData.scenicImage) {
				scenicImage = flightData.scenicImage;
				console.log('Scenic image loaded in post page:', {
					isBase64: scenicImage.startsWith('data:image'),
					isEdited: scenicImage.startsWith('data:image'),
					imageType: scenicImage.startsWith('data:image') ? 'Edited (base64)' : 'Original (URL)'
				});
			}
				
				// Store original image and text data for editing
				if (flightData.originalScenicImage) {
					originalScenicImage = flightData.originalScenicImage;
				}
				editDestination = flightData.destination || '';
				// Get promote_text from aiAnalysis if available
				editPromoteText = flightData.promoteText || flightData.aiAnalysis?.promote_text || '';
				editAirline = flightData.airline || '';
				editPrice = flightData.returnPrice?.toString() || '';
			
			// Store flight info image if available
			if (flightData.flightInfoImage) {
				flightInfoImage = flightData.flightInfoImage;
				console.log('Flight info image loaded in post page:', {
					isBase64: flightInfoImage.startsWith('data:image'),
					imageType: flightInfoImage.startsWith('data:image') ? 'Flight Info (base64)' : 'Flight Info (URL)'
				});
			}
			
			// Use AI analysis if available, otherwise fallback to defaults
			if (flightData.aiAnalysis) {
				header = formatHeaderWithDestination(
					flightData.aiAnalysis.header,
					flightData.destination || '',
					`Flight Deal: ${flightData.airline || ''}`
				);
				firstComment = flightData.aiAnalysis.content;
				summary = flightData.aiAnalysis.summary;
			} else {
				// Fallback to default values
				header = formatHeaderWithDestination(
					'',
					flightData.destination || '',
					`Flight Deal: ${flightData.airline || ''}`
				);
				firstComment = `Great flight deal found! ${flightData.airline} from ${flightData.startingPlace} to ${flightData.destination}`;
				summary = flightData.multipleFlights 
					? `Found ${flightData.flightCount} great flight deals!\n\nTotal Price: $${flightData.returnPrice}\nRoutes: ${flightData.allRoutes}\n\nPerfect for multi-city travel or group bookings.`
					: `Excellent flight deal with ${flightData.airline}!\n\nRoute: ${flightData.startingPlace} → ${flightData.destination}\nPrice: $${flightData.returnPrice}\nClass: ${flightData.seatClass}\n\nBook now before prices increase!`;
			}
			
			// Set other fields
			extraComment = `Departure: ${new Date(flightData.departureDate).toLocaleDateString()}\nFlight Time: ${flightData.flightTime}\nPrice: $${flightData.returnPrice}`;
			ticketValidity = flightData.ticketValidDate;
			
			// Auto-generate post content for social media
			postContent = createFlightPostContent(flightData);
			postHashtags = `#FlightDeals #Travel #${flightData.airline.replace(/\s+/g, '')} #TravelTips #CheapFlights`;
				
				// Store flight data and save to database
				currentFlightData = flightData;
				savePostToDatabase();
			}
		}
	});
	
	// Function to handle image text editing
	async function handleEditImage() {
		if (isUpdatingImage) return; // Prevent multiple clicks
		
		try {
			if (!originalScenicImage) {
				alert('Original image not available for editing');
				return;
			}
			
			isUpdatingImage = true; // Set loading state
			
			const token = localStorage.getItem('token') || '';
			
			// Call the regenerate API directly
			const response = await fetch(`${WEBUI_API_BASE_URL}/pollinations/regenerate-with-text`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...(token && { Authorization: `Bearer ${token}` })
				},
				body: JSON.stringify({
					original_image_base64: originalScenicImage,
					destination: editDestination,
					promote_text: editPromoteText,
					airline: editAirline,
					price: editPrice
				})
			});
			
			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
			}
			
			const result = await response.json();
			
			if (result.success) {
				// Update the scenic image with the newly edited version
				scenicImage = result.image_base64;
				showEditImageModal = false;
				console.log('Image text updated successfully');
			} else {
				alert('Failed to update image text');
			}
		} catch (error) {
			console.error('Error editing image:', error);
			alert('Error editing image: ' + error.message);
		} finally {
			isUpdatingImage = false; // Reset loading state
		}
	}
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
						<a class="min-w-fit transition flex items-center gap-2" href="/post">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								class="size-5 text-gray-900 dark:text-gray-100"
							>
								<path
									d="M3 3h18v18h-18z M8 8h8v8h-8z M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0 M16 7a1 1 0 1 0 0-2a1 1 0 1 0 0 2"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linejoin="round"
									stroke-linecap="round"
								/>
							</svg>
							{$i18n.t('Post')}
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
		<div class="flex flex-col md:flex-row h-full">
			<!-- Left Column - User Input -->
			<div class="w-full md:w-1/2 p-6 md:border-r border-gray-200 dark:border-gray-700">
				<div class="max-w-lg mx-auto">
					<!-- Tab Navigation -->
					<div class="mb-8">
						<div class="flex space-x-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg overflow-hidden">
							<button
								class="flex-1 min-w-0 py-2 px-2 md:px-4 text-sm font-medium rounded-md transition-colors {activeTab === 'website-blog' 
									? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
								on:click={() => activeTab = 'website-blog'}
							>
								<div class="flex items-center justify-center gap-1 md:gap-2 overflow-hidden">
									<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
										<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
									</svg>
									<span class="truncate whitespace-nowrap">Website Blog</span>
								</div>
							</button>
							<button
								class="flex-1 min-w-0 py-2 px-2 md:px-4 text-sm font-medium rounded-md transition-colors {activeTab === 'instagram' 
									? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
								on:click={() => activeTab = 'instagram'}
							>
								<div class="flex items-center justify-center gap-1 md:gap-2 overflow-hidden">
									<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
										<path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
									</svg>
									<span class="truncate whitespace-nowrap">Instagram</span>
								</div>
							</button>
							<button
								class="flex-1 min-w-0 py-2 px-2 md:px-4 text-sm font-medium rounded-md transition-colors {activeTab === 'facebook' 
									? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
								on:click={() => activeTab = 'facebook'}
							>
								<div class="flex items-center justify-center gap-1 md:gap-2 overflow-hidden">
									<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
										<path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
									</svg>
									<span class="truncate whitespace-nowrap">Facebook</span>
								</div>
							</button>
						</div>
					</div>
					
					<h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-8">
						{activeTab === 'website-blog' ? 'Website Blog' : activeTab === 'instagram' ? 'Instagram' : 'Facebook'} Post
					</h1>

					{#if activeTab === 'website-blog'}
						<!-- Website Blog Form Fields -->
						
						<!-- Header -->
						<div class="mb-6">
							<label for="header" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Header
							</label>
							<input
								id="header"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
								placeholder="Enter blog header..."
								bind:value={header}
							/>
						</div>

						<!-- First Comment -->
						<div class="mb-6">
							<label for="first-comment" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								First Comment
							</label>
							<textarea
								id="first-comment"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100 resize-none"
								rows="3"
								placeholder="Enter first comment..."
								bind:value={firstComment}
							></textarea>
						</div>

						<!-- Airline Name -->
						<div class="mb-6">
							<label for="airline-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Airline Name
							</label>
							<input
								id="airline-name"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
								placeholder="Enter airline name..."
								bind:value={airlineName}
							/>
						</div>

						<!-- Return Price -->
						<div class="mb-6">
							<label for="return-price" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Return Price
							</label>
							<input
								id="return-price"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
								placeholder="Enter return price..."
								bind:value={returnPrice}
							/>
						</div>

						<!-- Extra Comment -->
						<div class="mb-6">
							<label for="extra-comment" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Extra Comment
							</label>
							<textarea
								id="extra-comment"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100 resize-none"
								rows="3"
								placeholder="Enter extra comment..."
								bind:value={extraComment}
							></textarea>
						</div>

						<!-- Ticket Screenshot -->
						<div class="mb-6">
							<label for="ticket-screenshot" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Ticket Screenshot
							</label>
							<div
								id="ticket-screenshot"
								class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center hover:border-gray-400 dark:hover:border-gray-500 transition cursor-pointer"
							>
								<svg
									class="mx-auto h-12 w-12 text-gray-400"
									stroke="currentColor"
									fill="none"
									viewBox="0 0 48 48"
								>
									<path
										d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
									/>
								</svg>
								<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
									Click to upload ticket screenshot or drag and drop
								</p>
								<p class="text-xs text-gray-500 dark:text-gray-500">PNG, JPG, GIF up to 10MB</p>
							</div>
						</div>

						<!-- Departure Date -->
						<div class="mb-6">
							<label for="departure-date" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Departure Date
							</label>
							<input
								id="departure-date"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
								placeholder="Enter departure date..."
								bind:value={departureDate}
							/>
						</div>

						<!-- Flight Time -->

						<div class="mb-6">
							<label for="flight-time" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Flight Time
							</label>
							<input
								id="flight-time"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
								placeholder="Enter flight time..."
								bind:value={flightTime}
							/>
						</div>
						<!-- Ticket Validity -->
						<div class="mb-6">
							<label for="ticket-validity" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Ticket Validity
							</label>
							<input
								id="ticket-validity"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
								placeholder="Enter ticket validity..."
								bind:value={ticketValidity}
							/>
						</div>

						<!-- Luggage Info -->
						<div class="mb-6">
							<label for="luggage-info" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Luggage Info
							</label>
							<input
								id="luggage-info"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
								placeholder="Enter luggage information..."
								bind:value={luggageInfo}
							/>
						</div>

						<!-- Summary -->
						<div class="mb-6">
							<label for="summary" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Summary
							</label>
							<textarea
								id="summary"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100 resize-none"
								rows="4"
								placeholder="Enter summary..."
								bind:value={summary}
							></textarea>
						</div>
						<!-- Website Blog Image -->
						<!-- Generated Image -->
						<div class="mb-6">
							<label for="ticket-screenshot" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Generated image
							</label>
							<button
								id="ticket-screenshot"
								type="button"
								on:click={() => showEditImageModal = true}
								class="w-full border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center hover:border-gray-400 dark:hover:border-gray-500 transition cursor-pointer group"
							>
								<svg
									class="mx-auto h-12 w-12 text-gray-400"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
									/>
								</svg>
								<p class="mt-3 text-base font-medium text-gray-700 dark:text-gray-300">
									Edit Text on Image
								</p>
								<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
									Click to customize text overlay on your generated image
								</p>
							</button>
						</div>
					{:else}
						<!-- Social Media Form Fields (Instagram/Facebook) -->
						
						<!-- Image Upload -->
						<div class="mb-6">
							<label for="image-upload" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Images
							</label>
							<div
								id="image-upload"
								class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center hover:border-gray-400 dark:hover:border-gray-500 transition cursor-pointer"
							>
								<svg
									class="mx-auto h-12 w-12 text-gray-400"
									stroke="currentColor"
									fill="none"
									viewBox="0 0 48 48"
								>
									<path
										d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
									/>
								</svg>
								<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
									Click to upload images or drag and drop
								</p>
								<p class="text-xs text-gray-500 dark:text-gray-500">PNG, JPG, GIF up to 10MB</p>
							</div>
						</div>

						<!-- Content Text -->
						<div class="mb-6">
							<label for="post-content" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Content
							</label>
							<textarea
								id="post-content"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100 resize-none"
								rows="6"
								placeholder="Write your post content here..."
								bind:value={postContent}
							></textarea>
						</div>

						<!-- Hashtags -->
						<div class="mb-6">
							<label for="post-hashtags" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Hashtags
							</label>
							<input
								id="post-hashtags"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
								placeholder="#travel #adventure #photography"
								bind:value={postHashtags}
							/>
						</div>
					{/if}

					<!-- Post Button -->
					<button
						class="w-full {activeTab === 'website-blog' ? 'bg-green-600 hover:bg-green-700' : activeTab === 'instagram' ? 'bg-black hover:bg-gray-800' : 'bg-blue-600 hover:bg-blue-700'} text-white font-medium py-3 px-4 rounded-lg transition"
					>
						{activeTab === 'website-blog' ? 'Publish Blog' : activeTab === 'instagram' ? 'Post to Instagram' : 'Post to Facebook'}
					</button>
				</div>
			</div>

			<!-- Right Column - Post Preview (Desktop) -->
			<div class="hidden md:block w-1/2 p-6 bg-gray-50 dark:bg-gray-900">
				<div class="max-w-sm mx-auto">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Preview</h2>
					
					{#if activeTab === 'website-blog'}
						<!-- Website Blog Preview - Blank -->
						<div class="bg-white rounded-lg shadow-lg p-8 text-left">
							<div class="text-black dark:text-black">
								<p class="text-lg font-bold mb-2" style="color: #2799d5;">{header}</p>
								<p class="text-sm mb-2">
									<span style="color: red;">請即Like</span> <span style="color: #2799d5; text-decoration: underline;">又飛啦！<span class="font-bold">Facebook Page</span></span>
								</p>
								{#if firstComment}
									<p class="text-sm mb-2">{firstComment}</p>
								{/if}
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">航空公司：<span style="color: black;">{airlineName}</span></p>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">來回連稅價錢：<span style="color: black;">HK${returnPrice}起</span></p>
								<p class="text-sm mb-2 font-bold text-black">{extraComment}</p>
								{#if flightInfoImage}
									<div class="flex items-center justify-center overflow-hidden relative">
										<img
											src={flightInfoImage}
											alt="Flight information card"
											class="w-full h-auto object-contain"
											style="max-height: 160px;"
										/>
									</div>
								{:else}
									<div class="bg-gray-300 h-40 flex items-center justify-center">
										<p class="text-gray-500">Image</p>
									</div>
								{/if}
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">參考出發日期（視乎供應）：</p>
								{#if departureDate}
									<p class="text-sm mt-2">{departureDate}</p>
								{/if}<br>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">參考航班時間（航班時間或會有變，以預訂時為準）：</p>
								{#if flightTime}
									<p class="text-sm mt-2">{flightTime}</p>
								{/if}<br>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">機票有效期：</p>
								{#if ticketValidity}
									<p class="text-sm mt-2">{ticketValidity}</p>
								{/if}<br>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">行李:</p>
								{#if luggageInfo}
									<p class="text-sm mt-2">{luggageInfo}</p>
								{/if}<br>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">結論：<span class="text-sm mt-2 text-black">{summary}</span></p> 
								
								<p class="text-sm mt-2">【預訂網址】<span style="color: #2799d5; text-decoration: underline;">https://hk.trip.com/</span></p>
								<p class="text-sm mt-2">（覺得抵可Whatsapp同LINE Share俾朋友）</p>
								{#if scenicImage}
									<div class="flex items-center justify-center overflow-hidden relative">
										<img
											src={scenicImage}
											alt="Scenic destination image with promotional banner"
											class="w-full h-auto object-contain"
											style="max-height: 400px;"
										/>
									</div>
								{:else}
									<div class="bg-gray-300 h-40 flex items-center justify-center">
										<p class="text-gray-500">Image</p>
									</div>
								{/if}
								<p class="text-sm mt-2">#以上價錢只供參考，或有浮動。如有出入，則以預訂網址為準。以上圖片只供參考。優惠受條款及細則約束，建議預訂前先行細閱</p>
							</div>
						</div>
					{:else if activeTab === 'instagram'}
						<!-- Instagram Post Preview -->
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
							<!-- Post Header -->
							<div class="flex items-center p-3 border-b border-gray-200 dark:border-gray-700">
								<img
									src={$user?.profile_image_url}
									class="w-8 h-8 object-cover rounded-full"
									alt="User profile"
									draggable="false"
								/>
								<div class="ml-3">
									<p class="text-sm font-semibold text-gray-900 dark:text-gray-100">
										{$user?.username || 'username'}
									</p>
								</div>
							</div>

							<!-- Post Image Placeholder -->
							<div
								class="aspect-square bg-gray-200 dark:bg-gray-700 flex items-center justify-center"
							>
								<svg
									class="h-12 w-12 text-gray-400"
									fill="none"
									viewBox="0 0 24 24"
									stroke="currentColor"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
									/>
								</svg>
							</div>

							<!-- Post Actions -->
							<div class="p-3">
								<div class="flex items-center space-x-4 mb-3">
									<svg
										class="h-6 w-6 text-gray-900 dark:text-gray-100"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
										/>
									</svg>
									<svg
										class="h-6 w-6 text-gray-900 dark:text-gray-100"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
										/>
									</svg>
									<svg
										class="h-6 w-6 text-gray-900 dark:text-gray-100"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"
										/>
									</svg>
								</div>

								<!-- Post Content Preview -->
								<div class="text-sm text-gray-900 dark:text-gray-100">
									<p class="font-semibold mb-1">{$user?.username || 'username'}</p>
									<p class="text-gray-700 dark:text-gray-300 mb-2">
										{postContent || 'Your post content will appear here...'}
									</p>
									{#if postHashtags}
										<p class="text-blue-600 dark:text-blue-400">{postHashtags}</p>
									{/if}
								</div>
							</div>
						</div>
					{:else}
						<!-- Facebook Post Preview -->
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
							<!-- Post Header -->
							<div class="flex items-center p-3 border-b border-gray-200 dark:border-gray-700">
								<img
									src={$user?.profile_image_url}
									class="w-10 h-10 object-cover rounded-full"
									alt="User profile"
									draggable="false"
								/>
								<div class="ml-3">
									<p class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$user?.username || 'username'}</p>
									<p class="text-xs text-gray-500 dark:text-gray-400">2 hours ago</p>
								</div>
								<div class="ml-auto">
									<svg class="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
										<path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
									</svg>
								</div>
							</div>
							
							<!-- Post Content -->
							<div class="p-3">
								<p class="text-sm text-gray-900 dark:text-gray-100 mb-3">{postContent || 'Your post content will appear here...'}</p>
								{#if postHashtags}
									<p class="text-blue-600 dark:text-blue-400 text-sm">{postHashtags}</p>
								{/if}
							</div>
							
							<!-- Post Image Placeholder -->
							<div class="bg-gray-200 dark:bg-gray-700 flex items-center justify-center" style="height: 200px;">
								<svg class="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
								</svg>
							</div>
							
							<!-- Post Actions -->
							<div class="p-3 border-t border-gray-200 dark:border-gray-700">
								<div class="flex items-center justify-between text-sm">
									<div class="flex items-center space-x-6">
										<button class="flex items-center space-x-1 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400">
											<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
												<path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.834a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
											</svg>
											<span>Like</span>
										</button>
										<button class="flex items-center space-x-1 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400">
											<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C3.512 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd" />
											</svg>
											<span>Comment</span>
										</button>
										<button class="flex items-center space-x-1 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400">
											<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
												<path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
											</svg>
											<span>Share</span>
										</button>
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
		
		<!-- Mobile Preview Button (Fixed Bottom Right) -->
		<button
			class="fixed bottom-6 right-6 md:hidden z-40 w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center transition-all duration-200 hover:scale-110"
			on:click={() => showMobilePreview = true}
			aria-label="Show preview"
		>
			<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
			</svg>
		</button>
		
		<!-- Mobile Preview Slide-out Panel -->
		{#if showMobilePreview}
			<!-- Backdrop -->
			<div
				class="fixed inset-0 bg-black/50 z-50 md:hidden transition-opacity duration-300"
				on:click={() => showMobilePreview = false}
				on:keydown={(e) => e.key === 'Escape' && (showMobilePreview = false)}
				role="button"
				tabindex="0"
				aria-label="Close preview"
			></div>
			
			<!-- Slide-out Panel -->
			<div
				class="fixed top-0 right-0 h-full w-full max-w-sm bg-gray-50 dark:bg-gray-900 z-50 md:hidden shadow-2xl transform transition-transform duration-300 ease-out overflow-y-auto translate-x-0"
				role="dialog"
				aria-modal="true"
				aria-label="Post preview"
			>
				<!-- Panel Header -->
				<div class="sticky top-0 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-between z-10">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">Preview</h2>
					<button
						class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
						on:click={() => showMobilePreview = false}
						aria-label="Close preview"
					>
						<svg class="w-6 h-6 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
	</div>
				
				<!-- Panel Content - Same preview content as desktop -->
				<div class="p-6">
					{#if activeTab === 'website-blog'}
						<!-- Website Blog Preview -->
						<div class="bg-white rounded-lg shadow-lg p-8 text-left">
							<div class="text-black dark:text-black">
								<p class="text-lg font-bold mb-2" style="color: #2799d5;">{header}</p>
								<p class="text-sm mb-2">
									<span style="color: red;">請即Like</span> <span style="color: #2799d5; text-decoration: underline;">又飛啦！<span class="font-bold">Facebook Page</span></span>
								</p>
								{#if firstComment}
									<p class="text-sm mb-2">{firstComment}</p>
								{/if}
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">航空公司：<span style="color: black;">{airlineName}</span></p>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">來回連稅價錢：<span style="color: black;">HK${returnPrice}起</span></p>
								<p class="text-sm mb-2 font-bold text-black">{extraComment}</p>
								{#if flightInfoImage}
									<div class="flex items-center justify-center overflow-hidden relative">
										<img
											src={flightInfoImage}
											alt="Flight information card"
											class="w-full h-auto object-contain"
											style="max-height: 160px;"
										/>
									</div>
								{:else}
									<div class="bg-gray-300 h-40 flex items-center justify-center">
										<p class="text-gray-500">Image</p>
									</div>
								{/if}
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">參考出發日期（視乎供應）：</p>
								{#if departureDate}
									<p class="text-sm mt-2">{departureDate}</p>
								{/if}<br>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">參考航班時間（航班時間或會有變，以預訂時為準）：</p>
								{#if flightTime}
									<p class="text-sm mt-2">{flightTime}</p>
								{/if}<br>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">機票有效期：</p>
								{#if ticketValidity}
									<p class="text-sm mt-2">{ticketValidity}</p>
								{/if}<br>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">行李:</p>
								{#if luggageInfo}
									<p class="text-sm mt-2">{luggageInfo}</p>
								{/if}<br>
								<p class="text-sm mb-2 font-bold" style="color: #d47a60;">結論：<span class="text-sm mt-2 text-black">{summary}</span></p> 
								
								<p class="text-sm mt-2">【預訂網址】<span style="color: #2799d5; text-decoration: underline;">https://hk.trip.com/</span></p>
								<p class="text-sm mt-2">（覺得抵可Whatsapp同LINE Share俾朋友）</p>
								{#if scenicImage}
									<div class="flex items-center justify-center overflow-hidden relative">
										<img
											src={scenicImage}
											alt="Scenic destination image with promotional banner"
											class="w-full h-auto object-contain"
											style="max-height: 400px;"
										/>
									</div>
								{:else}
									<div class="bg-gray-300 h-40 flex items-center justify-center">
										<p class="text-gray-500">Image</p>
									</div>
								{/if}
								<p class="text-sm mt-2">#以上價錢只供參考，或有浮動。如有出入，則以預訂網址為準。以上圖片只供參考。優惠受條款及細則約束，建議預訂前先行細閱</p>
							</div>
						</div>
					{:else if activeTab === 'instagram'}
						<!-- Instagram Post Preview -->
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
							<!-- Post Header -->
							<div class="flex items-center p-3 border-b border-gray-200 dark:border-gray-700">
								<img
									src={$user?.profile_image_url}
									class="w-8 h-8 object-cover rounded-full"
									alt="User profile"
									draggable="false"
								/>
								<div class="ml-3">
									<p class="text-sm font-semibold text-gray-900 dark:text-gray-100">
										{$user?.username || 'username'}
									</p>
								</div>
							</div>

							<!-- Post Image Placeholder -->
							<div
								class="aspect-square bg-gray-200 dark:bg-gray-700 flex items-center justify-center"
							>
								<svg
									class="h-12 w-12 text-gray-400"
									fill="none"
									viewBox="0 0 24 24"
									stroke="currentColor"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
									/>
								</svg>
							</div>

							<!-- Post Actions -->
							<div class="p-3">
								<div class="flex items-center space-x-4 mb-3">
									<svg
										class="h-6 w-6 text-gray-900 dark:text-gray-100"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
										/>
									</svg>
									<svg
										class="h-6 w-6 text-gray-900 dark:text-gray-100"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
										/>
									</svg>
									<svg
										class="h-6 w-6 text-gray-900 dark:text-gray-100"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"
										/>
									</svg>
								</div>

								<!-- Post Content Preview -->
								<div class="text-sm text-gray-900 dark:text-gray-100">
									<p class="font-semibold mb-1">{$user?.username || 'username'}</p>
									<p class="text-gray-700 dark:text-gray-300 mb-2">
										{postContent || 'Your post content will appear here...'}
									</p>
									{#if postHashtags}
										<p class="text-blue-600 dark:text-blue-400">{postHashtags}</p>
									{/if}
								</div>
							</div>
						</div>
					{:else}
						<!-- Facebook Post Preview -->
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
							<!-- Post Header -->
							<div class="flex items-center p-3 border-b border-gray-200 dark:border-gray-700">
								<img
									src={$user?.profile_image_url}
									class="w-10 h-10 object-cover rounded-full"
									alt="User profile"
									draggable="false"
								/>
								<div class="ml-3">
									<p class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$user?.username || 'username'}</p>
									<p class="text-xs text-gray-500 dark:text-gray-400">2 hours ago</p>
								</div>
								<div class="ml-auto">
									<svg class="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
										<path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
									</svg>
								</div>
							</div>
							
							<!-- Post Content -->
							<div class="p-3">
								<p class="text-sm text-gray-900 dark:text-gray-100 mb-3">{postContent || 'Your post content will appear here...'}</p>
								{#if postHashtags}
									<p class="text-blue-600 dark:text-blue-400 text-sm">{postHashtags}</p>
								{/if}
							</div>
							
							<!-- Post Image Placeholder -->
							<div class="bg-gray-200 dark:bg-gray-700 flex items-center justify-center" style="height: 200px;">
								<svg class="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
								</svg>
							</div>
							
							<!-- Post Actions -->
							<div class="p-3 border-t border-gray-200 dark:border-gray-700">
								<div class="flex items-center justify-between text-sm">
									<div class="flex items-center space-x-6">
										<button class="flex items-center space-x-1 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400">
											<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
												<path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.834a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
											</svg>
											<span>Like</span>
										</button>
										<button class="flex items-center space-x-1 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400">
											<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C3.512 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd" />
											</svg>
											<span>Comment</span>
										</button>
										<button class="flex items-center space-x-1 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400">
											<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
												<path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
											</svg>
											<span>Share</span>
										</button>
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- Edit Image Text Modal -->
{#if showEditImageModal}
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/10 backdrop-blur-sm">
	<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
		<div class="p-6">
			<div class="flex justify-between items-center mb-6">
				<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Edit Text on Image</h2>
				<button
					on:click={() => showEditImageModal = false}
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
				>
					<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			
			<div class="space-y-4">
				<!-- Destination -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Destination (目的地)
					</label>
					<input
						type="text"
						bind:value={editDestination}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
						placeholder="e.g., 東京, 首爾"
					/>
				</div>
				
				<!-- Promote Text -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Promotion Text (宣傳文字)
					</label>
					<textarea
						bind:value={editPromoteText}
						rows="3"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
						placeholder="e.g., 多航班及日子選擇！\n凌晨去晚返都有！"
					></textarea>
					<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Use \n for line breaks</p>
				</div>
				
				<!-- Airline -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Airline (航空公司)
					</label>
					<input
						type="text"
						bind:value={editAirline}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
						placeholder="e.g., 中華航空, 國泰航空"
					/>
				</div>
				
				<!-- Price -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Price (價錢)
					</label>
					<input
						type="text"
						bind:value={editPrice}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
						placeholder="e.g., 3,500"
					/>
				</div>
			</div>
			
			<!-- Action Buttons -->
			<div class="mt-6 flex justify-end space-x-3">
				<button
					on:click={() => showEditImageModal = false}
					disabled={isUpdatingImage}
					class="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					Cancel
				</button>
				<button
					on:click={handleEditImage}
					disabled={isUpdatingImage}
					class="px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
				>
					{#if isUpdatingImage}
						<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Updating...
					{:else}
						Update Image
					{/if}
				</button>
			</div>
		</div>
	</div>
</div>
{/if}
