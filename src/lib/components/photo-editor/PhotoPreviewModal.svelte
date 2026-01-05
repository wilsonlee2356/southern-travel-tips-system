<script>
	export let open = false;
	export let image = null;
</script>

{#if open && image}
	<div class="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm" on:click={() => open = false}>
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl mx-4 max-h-[90vh] overflow-auto" on:click|stopPropagation>
			<!-- Header -->
			<div class="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
				<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100">Preview</h2>
				<button
					on:click={() => open = false}
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
				>
					<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			
			<!-- Preview Image -->
			<div class="p-4 flex justify-center bg-gray-100 dark:bg-gray-900">
				<img
					src={image}
					alt="Preview"
					class="max-w-full max-h-[70vh] object-contain rounded"
				/>
			</div>
			
			<!-- Footer -->
			<div class="flex justify-end p-4 border-t border-gray-200 dark:border-gray-700">
				<button
					on:click={() => open = false}
					class="px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700"
				>
					Close
				</button>
			</div>
		</div>
	</div>
{/if}

