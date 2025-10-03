<script>
	import { mobile, showSidebar, user, showArchivedChats, models } from '$lib/stores';
	import { getContext } from 'svelte';
	import { onMount } from 'svelte';
	import { generateTextCompletion } from '$lib/apis/ollama/index';
	// Note: Web content extraction moved to server-side API

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	// Form state
	let formData = {
		urls: [''], // Array of URL fields - start with one
		photos: [] // Array of uploaded photos
	};

	// Generated content state
	let generatedPost = {
		content: '',
		image: null,
		caption: '',
		hashtags: ''
	};

	// UI state
	let isGenerating = false;
	let generationStatus = '';
	let uploadedImages = [];

	// Add URL field
	const addUrlField = () => {
		formData.urls = [...formData.urls, ''];
	};

	// Remove URL field
	const removeUrlField = (index) => {
		formData.urls = formData.urls.filter((_, i) => i !== index);
	};

	// Handle photo upload
	const handlePhotoUpload = (event) => {
		const files = Array.from(event.target.files);
		uploadedImages = [...uploadedImages, ...files];
		formData.photos = uploadedImages;
	};

	// Remove uploaded photo
	const removePhoto = (index) => {
		uploadedImages = uploadedImages.filter((_, i) => i !== index);
		formData.photos = uploadedImages;
	};

	// Generate post content using Ollama
	const generatePost = async () => {
		if (formData.urls.every(url => !url.trim()) && formData.photos.length === 0) {
			alert('Please provide at least one URL or upload at least one photo');
			return;
		}

		isGenerating = true;
		generationStatus = 'Extracting content from URLs...';

		try {
			const token = localStorage.getItem('token') || '';
			
			// Extract content from URLs using server-side API
			let extractedContent = '';
			const validUrls = formData.urls.filter(url => url.trim());
			
			if (validUrls.length > 0) {
				generationStatus = `Extracting content from ${validUrls.length} URL(s)...`;
				
				for (const url of validUrls) {
					try {
						console.log(`Extracting content from: ${url}`);
						
						// Call server-side API to extract web content
						const response = await fetch('/api/extract-web-content', {
							method: 'POST',
							headers: {
								'Content-Type': 'application/json',
							},
							body: JSON.stringify({
								url: url,
								options: {
									includeImages: true,
									includeLinks: true,
									waitForTimeout: 90000, // Extended to 90 seconds
									maxRetries: 3 // Allow 3 retry attempts
								}
							})
						});
						
						if (response.ok) {
							const extractionResult = await response.json();
							console.log(`Successfully extracted content from: ${url}`);
							console.log('Extraction result:', extractionResult);
							
							// Add extracted content to the combined content
							const urlContent = `
URL: ${url}
Title: ${extractionResult.content?.title || 'No title'}
Description: ${extractionResult.content?.description || 'No description'}
Main Content: ${extractionResult.content?.textContent?.substring(0, 2000) || 'No content'}...
Word Count: ${extractionResult.content?.wordCount || 0}
`;
							extractedContent += urlContent;
						} else {
							console.error(`Failed to extract content from ${url}:`, response.statusText);
							extractedContent += `\nURL: ${url}\nError: Failed to extract content (${response.status})\n`;
						}
					} catch (extractionError) {
						console.error(`Error extracting from ${url}:`, extractionError);
						extractedContent += `\nURL: ${url}\nError: ${extractionError.message}\n`;
					}
				}
			}
			
			// Add photos information
			const photosText = formData.photos.length > 0 ? `\n\nUploaded ${formData.photos.length} photo(s): ${formData.photos.map(p => p.name).join(', ')}` : '';
			
			// Log the extracted content
			console.log('=== EXTRACTED WEB CONTENT ===');
			console.log(extractedContent);
			console.log('=============================');
			
			// Prepare the prompt for qwen2.5:32b model
			const prompt = `你是一個專業的文本提取專家。請從以下網頁內容中提取最相關的原始文本內容，不要進行任何改寫、總結或解釋，只提取原始相關信息。

網頁內容：
${extractedContent}${photosText}

請按照以下步驟進行：

1. 識別網頁中的主要相關內容（新聞、文章等）
2. 提取原始的標題或標頭文字
3. 提取原始的正文內容
4. 保持文本的原始格式和用詞，不要修改任何文字

輸出格式：
標題：[直接提取網頁中的原始標題或主要標頭，不超過30個字，保持原文不變]
內容：[直接提取網頁中的原始正文內容，保持原文格式，提取最相關的段落，不進行任何改寫或總結]

要求：
- 只提取最相關的原始文本內容
- 不要進行任何文字修改、改寫或總結
- 保持原文的語言和用詞
- 不要添加任何解釋或分析
- 不要輸出無關的導航、廣告、版權信息等內容
- 只輸出標題和內容兩個部分`;

			// Use qwen2.5:32b model specifically
			const model = 'qwen2.5:32b';
			
			console.log('Using model:', model);
			console.log('Token available:', !!token);
			
			generationStatus = 'Generating content with qwen2.5:32b...';
			
			const response = await generateTextCompletion(token, model, prompt);
			
			console.log('Response received:', response);
			
			if (response && response.ok) {
				// Handle streaming response
				const reader = response.body?.getReader();
				const decoder = new TextDecoder();
				let generatedText = '';
				
				if (reader) {
					while (true) {
						const { done, value } = await reader.read();
						if (done) break;
						
						const chunk = decoder.decode(value);
						const lines = chunk.split('\n');
						
						for (const line of lines) {
							if (line.trim()) {
								try {
									const data = JSON.parse(line);
									if (data.response) {
										generatedText += data.response;
									}
								} catch (e) {
									// Skip invalid JSON lines
								}
							}
						}
					}
				}
				
				// Log the generated content from qwen2.5:32b
				console.log('=== GENERATED CONTENT FROM qwen2.5:32b ===');
				console.log(generatedText);
				console.log('==========================================');
				
				if (generatedText) {
					// Parse the Chinese response format for console logging
					const titleMatch = generatedText.match(/標題：\s*(.+?)(?=內容：|$)/s);
					const contentMatch = generatedText.match(/內容：\s*(.+?)$/s);
					
					if (titleMatch && contentMatch) {
						const chineseTitle = titleMatch[1].trim();
						const chineseContent = contentMatch[1].trim();
						
						// Log the Chinese output to console
						console.log('=== CHINESE OUTPUT ===');
						console.log('標題:', chineseTitle);
						console.log('內容:', chineseContent);
						console.log('=====================');
					}
					
					// Parse for UI display (fallback to original format)
					const captionMatch = generatedText.match(/CAPTION:\s*(.+?)(?=HASHTAGS:|$)/s);
					const hashtagsMatch = generatedText.match(/HASHTAGS:\s*(.+?)(?=DESCRIPTION:|$)/s);
					const descriptionMatch = generatedText.match(/DESCRIPTION:\s*(.+?)$/s);
					
					generatedPost = {
						content: captionMatch ? captionMatch[1].trim() : generatedText,
						caption: captionMatch ? captionMatch[1].trim() : generatedText,
						hashtags: hashtagsMatch ? hashtagsMatch[1].trim() : '#travel #lifestyle #adventure',
						description: descriptionMatch ? descriptionMatch[1].trim() : 'AI-generated travel content'
					};
					
					// Use the first uploaded image if available
					if (uploadedImages.length > 0) {
						generatedPost.image = uploadedImages[0];
					}
					
					generationStatus = 'Content generated successfully!';
				} else {
					throw new Error('No content generated');
				}
			} else {
				throw new Error('Failed to generate content');
			}
		} catch (error) {
			console.error('Error generating post:', error);
			generationStatus = `Error: ${error.message || 'Failed to generate content'}`;
			alert(`Error generating content: ${error.message || 'Please check your connection and try again.'}`);
		} finally {
			isGenerating = false;
		}
	};

	// Reset form
	const resetForm = () => {
		formData = {
			urls: [''],
			photos: []
		};
		uploadedImages = [];
		generatedPost = {
			content: '',
			image: null,
			caption: '',
			hashtags: ''
		};
		generationStatus = '';
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
						<a class="min-w-fit transition flex items-center gap-2" href="/content-generator">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								class="size-5 text-gray-900 dark:text-gray-100"
							>
								<path
									d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linejoin="round"
									stroke-linecap="round"
								/>
							</svg>
							{$i18n.t('Content Generator')}
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
			<!-- Left Column - Input Form -->
			<div class="w-1/2 p-6 border-r border-gray-200 dark:border-gray-700">
				<div class="max-w-lg mx-auto">
					<h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-8">
						{$i18n.t('Content Generator')}
					</h1>
					<p class="text-gray-600 dark:text-gray-400 mb-8">
						Provide URLs and photos to generate engaging social media content
					</p>

					<!-- URL Fields -->
					<div class="mb-8">
						<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
							URLs to Analyze
						</h2>
						
						{#each formData.urls as url, index}
							<div class="flex items-center gap-2 mb-3">
								<input
									type="url"
									class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-gray-100"
									placeholder="Enter URL (e.g., travel blog, destination page)"
									bind:value={formData.urls[index]}
								/>
								{#if formData.urls.length > 1}
									<button
										type="button"
										class="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition"
										on:click={() => removeUrlField(index)}
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
										</svg>
									</button>
								{/if}
							</div>
						{/each}
						
						<button
							type="button"
							class="text-blue-600 hover:text-blue-700 text-sm font-medium"
							on:click={addUrlField}
						>
							+ Add another URL
						</button>
					</div>

					<!-- Photo Upload -->
					<div class="mb-8">
						<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
							Upload Photos
						</h2>
						
						<div
							class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center hover:border-gray-400 dark:hover:border-gray-500 transition cursor-pointer"
							on:click={() => document.getElementById('photo-upload').click()}
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
								Click to upload photos or drag and drop
							</p>
							<p class="text-xs text-gray-500 dark:text-gray-500">PNG, JPG, GIF up to 10MB each</p>
						</div>
						
						<input
							id="photo-upload"
							type="file"
							multiple
							accept="image/*"
							class="hidden"
							on:change={handlePhotoUpload}
						/>

						<!-- Uploaded Photos Preview -->
						{#if uploadedImages.length > 0}
							<div class="mt-4">
								<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Uploaded Photos ({uploadedImages.length})
								</h3>
								<div class="grid grid-cols-2 gap-2">
									{#each uploadedImages as image, index}
										<div class="relative">
											<img
												src={URL.createObjectURL(image)}
												alt="Uploaded photo"
												class="w-full h-24 object-cover rounded-lg"
											/>
											<button
												class="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition"
												on:click={() => removePhoto(index)}
											>
												<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
												</svg>
											</button>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>

					<!-- Generate Button -->
					<div class="space-y-4">
						<button
							class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
							disabled={isGenerating || (formData.urls.every(url => !url.trim()) && formData.photos.length === 0)}
							on:click={generatePost}
						>
							{#if isGenerating}
								<div class="flex items-center justify-center">
									<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									Generating...
								</div>
							{:else}
								<svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
								</svg>
								Generate Post
							{/if}
						</button>

						<button
							type="button"
							class="w-full bg-gray-500 hover:bg-gray-600 text-white font-medium py-3 px-4 rounded-lg transition"
							on:click={resetForm}
						>
							Reset Form
						</button>
					</div>

					<!-- Generation Status -->
					{#if generationStatus}
						<div class="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
							<p class="text-sm text-blue-700 dark:text-blue-300">{generationStatus}</p>
						</div>
					{/if}
				</div>
			</div>

			<!-- Right Column - Generated Post Preview -->
			<div class="w-1/2 p-6 bg-gray-50 dark:bg-gray-900">
				<div class="max-w-sm mx-auto">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Generated Post</h2>
					
					{#if generatedPost.content}
						<!-- Instagram-style Post Preview -->
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

							<!-- Post Image -->
							{#if generatedPost.image}
								<div class="aspect-square bg-gray-200 dark:bg-gray-700">
									<img
										src={URL.createObjectURL(generatedPost.image)}
										alt="Generated post image"
										class="w-full h-full object-cover"
									/>
								</div>
							{:else}
								<div class="aspect-square bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
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
							{/if}

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

								<!-- Post Content -->
								<div class="text-sm text-gray-900 dark:text-gray-100">
									<p class="font-semibold mb-1">{$user?.username || 'username'}</p>
									<p class="text-gray-700 dark:text-gray-300 mb-2">
										{generatedPost.caption}
									</p>
									{#if generatedPost.hashtags}
										<p class="text-blue-600 dark:text-blue-400">{generatedPost.hashtags}</p>
									{/if}
								</div>
							</div>
						</div>

						<!-- Post Details -->
						<div class="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
							<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Post Details</h3>
							<div class="space-y-2 text-sm">
								<div>
									<span class="font-medium text-gray-700 dark:text-gray-300">Caption:</span>
									<p class="text-gray-600 dark:text-gray-400">{generatedPost.caption}</p>
								</div>
								<div>
									<span class="font-medium text-gray-700 dark:text-gray-300">Hashtags:</span>
									<p class="text-gray-600 dark:text-gray-400">{generatedPost.hashtags}</p>
								</div>
								{#if generatedPost.description}
									<div>
										<span class="font-medium text-gray-700 dark:text-gray-300">Description:</span>
										<p class="text-gray-600 dark:text-gray-400">{generatedPost.description}</p>
									</div>
								{/if}
							</div>
						</div>
					{:else}
						<!-- Empty State -->
						<div class="text-center py-12">
							<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
							</svg>
							<h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
								No content generated yet
							</h3>
							<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
								Add URLs and photos, then click "Generate Post" to create content
							</p>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>

