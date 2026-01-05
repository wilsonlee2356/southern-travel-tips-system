<script>
	export let onCancel;
	export let onPreview;
	export let onSave;
</script>

<div class="flex justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
	<button
		on:click={onCancel}
		class="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
	>
		Cancel
	</button>
	<button
		on:click={onPreview}
		class="px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700"
	>
		Preview
	</button>
	<button
		on:click={onSave}
		class="px-4 py-2 text-white bg-green-600 rounded-md hover:bg-green-700"
	>
		Save
	</button>
</div>

