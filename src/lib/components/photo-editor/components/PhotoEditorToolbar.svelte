<script>
	export let activeTool;
	export let hasSelectedComponent;
	export let onImageClick;
	export let onTextClick;
	export let onDeleteClick;
</script>

<div class="flex items-center gap-2 p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
	<button
		on:click={onImageClick}
		class="w-9 h-9 flex items-center justify-center rounded-md {activeTool === 'image' ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'}"
		title="Add Image"
	>
		<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
		</svg>
	</button>
	<button
		on:click={onTextClick}
		class="w-9 h-9 flex items-center justify-center rounded-md {activeTool === 'text' ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'}"
		title="Add Text"
	>
		<span class="text-lg font-bold leading-none">T</span>
	</button>
	{#if hasSelectedComponent}
		<button
			on:click={onDeleteClick}
			class="w-9 h-9 flex items-center justify-center rounded-md bg-red-500 text-white hover:bg-red-600 ml-auto"
			title="Delete Selected (Delete key)"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
			</svg>
		</button>
	{/if}
</div>

