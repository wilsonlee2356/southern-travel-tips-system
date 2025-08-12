<script>
	import { mobile, showArchivedChats, showSidebar, user } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
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
								<path d="M3 3h18v18h-18z M8 8h8v8h-8z M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0 M16 7a1 1 0 1 0 0-2a1 1 0 1 0 0 2" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>
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
					<h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-8">
						Instagram Post
					</h1>
					
					<!-- Image Upload -->
					<div class="mb-6">
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Images
						</label>
						<div class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center hover:border-gray-400 dark:hover:border-gray-500 transition cursor-pointer">
							<svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
								<path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
							</svg>
							<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
								Click to upload images or drag and drop
							</p>
							<p class="text-xs text-gray-500 dark:text-gray-500">
								PNG, JPG, GIF up to 10MB
							</p>
						</div>
					</div>
					
					<!-- Content Text -->
					<div class="mb-6">
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Content
						</label>
						<textarea 
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100 resize-none"
							rows="6"
							placeholder="Write your post content here..."
						></textarea>
					</div>
					
					<!-- Hashtags -->
					<div class="mb-6">
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Hashtags
						</label>
						<input 
							type="text"
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
							placeholder="#travel #adventure #photography"
						/>
					</div>
					
					<!-- Post Button -->
					<button class="w-full bg-black hover:bg-gray-800 text-white font-medium py-3 px-4 rounded-lg transition">
						Post to Instagram
					</button>
				</div>
			</div>
			
			<!-- Right Column - Instagram Preview -->
			<div class="w-1/2 p-6 bg-gray-50 dark:bg-gray-900">
				<div class="max-w-sm mx-auto">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
						Preview
					</h2>
					
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
								<p class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$user?.username || 'username'}</p>
							</div>
						</div>
						
						<!-- Post Image Placeholder -->
						<div class="aspect-square bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
							<svg class="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
							</svg>
						</div>
						
						<!-- Post Actions -->
						<div class="p-3">
							<div class="flex items-center space-x-4 mb-3">
								<svg class="h-6 w-6 text-gray-900 dark:text-gray-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
								</svg>
								<svg class="h-6 w-6 text-gray-900 dark:text-gray-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
								</svg>
								<svg class="h-6 w-6 text-gray-900 dark:text-gray-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
								</svg>
							</div>
							
							<!-- Post Content Preview -->
							<div class="text-sm text-gray-900 dark:text-gray-100">
								<p class="font-semibold mb-1">{$user?.username || 'username'}</p>
								<p class="text-gray-700 dark:text-gray-300 mb-2">Your post content will appear here...</p>
								<p class="text-blue-600 dark:text-blue-400">#travel #adventure #photography</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
