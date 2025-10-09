<script>
	import { mobile, showArchivedChats, showSidebar, user } from '$lib/stores';
	import { getContext } from 'svelte';
	import { onMount } from 'svelte';
	import { getFlightDataFromStorage, createFlightPostContent } from '$lib/utils/flightPostHandler.js';

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

	// Handle incoming flight data from flight search
	onMount(() => {
		const flightData = getFlightDataFromStorage();
		if (flightData) {
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
				header = flightData.aiAnalysis.header;
				firstComment = flightData.aiAnalysis.content;
				summary = flightData.aiAnalysis.summary;
			} else {
				// Fallback to default values
				header = `Flight Deal: ${flightData.airline}`;
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
		}
	});
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
		<div class="flex h-full">
			<!-- Left Column - User Input -->
			<div class="w-1/2 p-6 border-r border-gray-200 dark:border-gray-700">
				<div class="max-w-lg mx-auto">
					<!-- Tab Navigation -->
					<div class="mb-8">
						<div class="flex space-x-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
							<button
								class="flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors {activeTab === 'website-blog' 
									? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
								on:click={() => activeTab = 'website-blog'}
							>
								<div class="flex items-center justify-center gap-2">
									<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
										<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
									</svg>
									Website Blog
								</div>
							</button>
							<button
								class="flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors {activeTab === 'instagram' 
									? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
								on:click={() => activeTab = 'instagram'}
							>
								<div class="flex items-center justify-center gap-2">
									<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
										<path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
									</svg>
									Instagram
								</div>
							</button>
							<button
								class="flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors {activeTab === 'facebook' 
									? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
								on:click={() => activeTab = 'facebook'}
							>
								<div class="flex items-center justify-center gap-2">
									<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
										<path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
									</svg>
									Facebook
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
						<!-- Ticket Screenshot -->
						<div class="mb-6">
							<label for="ticket-screenshot" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Country Image
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

			<!-- Right Column - Post Preview -->
			<div class="w-1/2 p-6 bg-gray-50 dark:bg-gray-900">
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
	</div>
</div>
