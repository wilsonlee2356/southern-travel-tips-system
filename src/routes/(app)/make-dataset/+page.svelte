<script>
    import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
    import { getContext } from 'svelte';
    import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
    import Tooltip from '$lib/components/common/Tooltip.svelte';
    import Sidebar from '$lib/components/icons/Sidebar.svelte';

    const i18n = getContext('i18n');

    // Dataset state
    let datasetItems = [
        { id: 1, prompt: '', response: '' }
    ];
    let nextId = 2;

    // Add new data input
    function addDataInput() {
        datasetItems = [...datasetItems, { id: nextId, prompt: '', response: '' }];
        nextId++;
    }

    // Remove data input
    function removeDataInput(id) {
        if (datasetItems.length > 1) {
            datasetItems = datasetItems.filter(item => item.id !== id);
        }
    }

    // Update prompt
    function updatePrompt(id, value) {
        datasetItems = datasetItems.map(item => 
            item.id === id ? { ...item, prompt: value } : item
        );
    }

    // Update response
    function updateResponse(id, value) {
        datasetItems = datasetItems.map(item => 
            item.id === id ? { ...item, response: value } : item
        );
    }

    // Download dataset as JSON
    function downloadDataset() {
        const dataset = datasetItems
            .filter(item => item.prompt.trim() && item.response.trim())
            .map(item => ({
                prompt: item.prompt,
                response: item.response
            }));
        
        if (dataset.length === 0) {
            alert('Please add at least one complete data entry (both prompt and response filled)');
            return;
        }

        const jsonData = JSON.stringify(dataset, null, 2);
        const blob = new Blob([jsonData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dataset-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
</script>

<svelte:head>
    <title>Make Dataset - Southern Travel Tips</title>
</svelte:head>

<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: 'md:max-w-full'} md:ml-0"
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
						<a class="min-w-fit transition flex items-center gap-2" href="/make-dataset">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="size-5 text-gray-900 dark:text-gray-100">
								<path
									d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linejoin="round"
									stroke-linecap="round"
								/>
								<path
									d="M14 2v6h6"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linejoin="round"
									stroke-linecap="round"
								/>
								<path
									d="M16 13H8"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
								<path
									d="M16 17H8"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
								<path
									d="M10 9H8"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
							</svg>
							{$i18n.t('Make Dataset')}
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
									/>
								</div>
								<div class="ml-2 text-left">
									<div class="text-xs font-medium text-gray-900 dark:text-white truncate">
										{$user?.name || $user?.email}
									</div>
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
					{$i18n.t('Make Dataset')}
				</h1>
			</div>

			<!-- Main Content -->
			<div class="space-y-6">
				<!-- Dataset Creation Interface -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					<div class="mb-6">
						<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
							Create Training Dataset
						</h2>
						<p class="text-gray-600 dark:text-gray-400">
							Add prompt-response pairs to create a dataset for model fine-tuning. Each entry should contain a prompt and its corresponding response.
						</p>
					</div>

					<!-- Dataset Info -->
					<div class="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
						<div class="flex items-start">
							<svg class="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
							</svg>
							<div>
								<h3 class="text-sm font-medium text-blue-800 dark:text-blue-200">
									Dataset Information
								</h3>
								<p class="mt-1 text-sm text-blue-700 dark:text-blue-300">
									Current dataset contains <strong>{datasetItems.length}</strong> entries. 
									<strong>Recommended size: 10-20 data entries</strong> for effective fine-tuning.
									Only entries with both prompt and response filled will be included in the downloaded JSON file.
									This dataset can be used for fine-tuning your AI models.
								</p>
							</div>
						</div>
					</div>

					<!-- Dataset Items -->
					<div class="space-y-4">
						{#each datasetItems as item, index}
							<div class="relative bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
								<!-- Remove button (only show for items after the first one) -->
								{#if index > 0}
									<button
										on:click={() => removeDataInput(item.id)}
										class="absolute top-2 right-2 w-6 h-6 flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-full transition-colors"
										title="Remove this entry"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
										</svg>
									</button>
								{/if}

								<div class="space-y-3">
									<!-- Prompt Input -->
									<div>
										<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Prompt {index + 1}
										</label>
										<textarea
											bind:value={item.prompt}
											on:input={(e) => updatePrompt(item.id, e.target.value)}
											class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none"
											rows="3"
											placeholder="Enter your prompt here..."
										></textarea>
									</div>

									<!-- Response Input -->
									<div>
										<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Response {index + 1}
										</label>
										<textarea
											bind:value={item.response}
											on:input={(e) => updateResponse(item.id, e.target.value)}
											class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none"
											rows="3"
											placeholder="Enter the expected response here..."
										></textarea>
									</div>
								</div>
							</div>
						{/each}
					</div>

					<!-- Add Button -->
					<div class="mt-6 flex justify-center">
						<button
							on:click={addDataInput}
							class="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
						>
							<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
							</svg>
							Add Data Entry
						</button>
					</div>

					<!-- Download Button -->
					<div class="mt-6 flex justify-center">
						<button
							on:click={downloadDataset}
							class="flex items-center px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors"
						>
							<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
							</svg>
							Download Dataset as JSON
						</button>
					</div>

				</div>
			</div>
		</div>
	</div>
</div>
