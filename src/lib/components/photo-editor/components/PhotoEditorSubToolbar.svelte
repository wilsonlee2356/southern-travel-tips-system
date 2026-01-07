<script>
	import { createEventDispatcher } from 'svelte';
	
	export let selectedComponent = null;
	export let showColorPicker = false;
	
	const dispatch = createEventDispatcher();
	let colorInputElement;
	
	// Close color picker when clicking outside
	function handleClickOutside(event) {
		if (showColorPicker && !event.target.closest('.color-picker-container')) {
			showColorPicker = false;
			dispatch('toggleColorPicker', { show: false });
		}
	}
	
	function handleWidthChange(event) {
		const value = parseInt(event.target.value);
		if (!isNaN(value) && value > 0 && selectedComponent) {
			dispatch('updateSize', {
				width: value,
				height: selectedComponent.height
			});
		}
	}
	
	function handleHeightChange(event) {
		const value = parseInt(event.target.value);
		if (!isNaN(value) && value > 0 && selectedComponent) {
			dispatch('updateSize', {
				width: selectedComponent.width,
				height: value
			});
		}
	}
	
	function handleColorChange(event) {
		const color = event.target.value;
		dispatch('updateColor', { color });
	}
	
	function handleFontSizeChange(event) {
		const fontSize = parseInt(event.target.value);
		if (!isNaN(fontSize) && fontSize > 0) {
			dispatch('updateFontSize', { fontSize });
		}
	}
</script>

{#if selectedComponent}
	<div class="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-2 flex items-center gap-4">
		{#if selectedComponent.type === 'image'}
			<!-- Image Sub Toolbar -->
			<div class="flex items-center gap-2">
				<label class="text-sm font-medium text-gray-700 dark:text-gray-300">Width:</label>
				<input
					type="number"
					value={selectedComponent.width}
					on:change={handleWidthChange}
					class="w-20 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
					min="1"
				/>
				<label class="text-sm font-medium text-gray-700 dark:text-gray-300">Height:</label>
				<input
					type="number"
					value={selectedComponent.height}
					on:change={handleHeightChange}
					class="w-20 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
					min="1"
				/>
			</div>
		{:else if selectedComponent.type === 'text'}
			<!-- Text Sub Toolbar -->
			<div class="flex items-center gap-4">
				<!-- Color Picker - Combined button and input -->
				<div class="relative color-picker-container flex items-center">
					<label class="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors cursor-pointer">
						<input
							bind:this={colorInputElement}
							type="color"
							value={selectedComponent.color || '#000000'}
							on:input={handleColorChange}
							on:change={handleColorChange}
							class="cursor-pointer border-0 rounded"
							style="width: 20px; height: 20px; min-width: 20px; min-height: 20px; border: none; outline: none; -webkit-appearance: none; -moz-appearance: none; appearance: none; padding: 0;"
							title="Change text color"
						/>
						<span class="text-gray-700 dark:text-gray-300">Color</span>
					</label>
				</div>
				
				<!-- Font Size Dropdown -->
				<div class="flex items-center gap-2">
					<label class="text-sm font-medium text-gray-700 dark:text-gray-300">Font Size:</label>
					<select
						value={selectedComponent.fontSize || 24}
						on:change={handleFontSizeChange}
						class="px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 cursor-pointer"
					>
						<option value="12">12</option>
						<option value="14">14</option>
						<option value="16">16</option>
						<option value="18">18</option>
						<option value="20">20</option>
						<option value="24">24</option>
						<option value="28">28</option>
						<option value="32">32</option>
						<option value="36">36</option>
						<option value="40">40</option>
						<option value="48">48</option>
						<option value="56">56</option>
						<option value="64">64</option>
						<option value="72">72</option>
					</select>
				</div>
			</div>
		{/if}
	</div>
{/if}

