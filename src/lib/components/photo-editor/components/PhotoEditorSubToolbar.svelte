<script>
	import { createEventDispatcher } from 'svelte';
	
	export let selectedComponent = null;
	export let showColorPicker = false;
	export let isCreatingText = false; // True when creating new text (not editing existing)
	
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
		event.stopPropagation(); // Prevent event from bubbling
		const color = event.target.value;
		dispatch('updateColor', { color });
	}
	
	function handleFontSizeChange(event) {
		event.stopPropagation(); // Prevent event from bubbling
		const fontSize = parseInt(event.target.value);
		if (!isNaN(fontSize) && fontSize > 0) {
			dispatch('updateFontSize', { fontSize });
		}
	}
</script>

{#if selectedComponent}
	<div 
		class="sub-toolbar-container border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-2 flex items-center gap-4"
		on:mousedown={(e) => {
			// Prevent text input from losing focus when clicking on sub toolbar
			// Only prevent if we're creating text and clicking on non-interactive elements
			// Allow interactive elements (select, input) to work normally
			if (isCreatingText) {
				const target = e.target;
				// Don't prevent default for interactive elements (select, input, button)
				// Also check if clicking on option elements inside select or label wrapping select
				if (target.tagName === 'SELECT' || 
					target.tagName === 'OPTION' || 
					target.tagName === 'INPUT' || 
					target.tagName === 'BUTTON' || 
					target.closest('select') || 
					target.closest('input[type="color"]') ||
					(target.tagName === 'LABEL' && target.querySelector('select'))) {
					// Allow the interactive element to work normally - don't interfere at all
					return;
				}
				// For other elements (labels without selects, divs), prevent default to keep text input focused
				e.preventDefault();
				// Re-focus the text input after a short delay to keep it focused
				setTimeout(() => {
					const textInput = document.querySelector('textarea[placeholder*="Enter text"]');
					// Only refocus if select is not open (check if select has focus)
					const selectElements = document.querySelectorAll('select');
					let selectHasFocus = false;
					for (const select of selectElements) {
						if (document.activeElement === select || select.matches(':focus')) {
							selectHasFocus = true;
							break;
						}
					}
					if (textInput && !selectHasFocus) {
						textInput.focus();
					}
				}, 10);
			}
		}}
	>
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
						on:blur={(e) => {
							// When select loses focus, refocus text input if we're creating text
							if (isCreatingText) {
								setTimeout(() => {
									const textInput = document.querySelector('textarea[placeholder*="Enter text"]');
									if (textInput && document.activeElement?.tagName !== 'SELECT') {
										textInput.focus();
									}
								}, 50);
							}
						}}
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

