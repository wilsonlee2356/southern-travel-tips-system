<script>
	export let onClose;
</script>

<div class="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
	<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100">Photo Editor</h2>
	<button
		on:click={onClose}
		class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
	>
		<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
		</svg>
	</button>
</div>

