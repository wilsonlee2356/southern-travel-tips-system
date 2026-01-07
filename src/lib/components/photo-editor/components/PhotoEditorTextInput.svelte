<script>
	import { createEventDispatcher } from 'svelte';
	
	export let visible;
	export let position;
	export let size;
	export let style;
	export let value = '';
	export let zoomLevel;
	export let canvas;
	export let ctx;
	export let editingTextComponent;
	export let onInput;
	export let onKeyDown;
	export let onBlur;
	
	const dispatch = createEventDispatcher();
	
	let textInputElement;
	let actualBaseScaleX = 0.2; // Default to a reasonable scale (e.g., 4000px canvas displayed at 800px = 0.2)
	let actualBaseScaleY = 0.2;
	
	$: if (visible && canvas) {
		// Calculate base scale immediately when visible
		const rect = canvas.getBoundingClientRect();
		// Use expected canvas size (4000x4000 when canvas.width is small), not actual canvas.width
		const expectedCanvasWidth = canvas.width >= 4000 ? canvas.width : 4000;
		const expectedCanvasHeight = canvas.height >= 4000 ? canvas.height : 4000;
		
		if (rect.width > 0 && rect.height > 0 && expectedCanvasWidth > 0 && expectedCanvasHeight > 0 && zoomLevel > 0) {
			const calculatedBaseScaleX = rect.width / (expectedCanvasWidth * zoomLevel);
			const calculatedBaseScaleY = rect.height / (expectedCanvasHeight * zoomLevel);
			
			// Only update if the calculated values are reasonable (between 0.01 and 10)
			if (calculatedBaseScaleX > 0.01 && calculatedBaseScaleX < 10) {
				actualBaseScaleX = calculatedBaseScaleX;
			}
			if (calculatedBaseScaleY > 0.01 && calculatedBaseScaleY < 10) {
				actualBaseScaleY = calculatedBaseScaleY;
			}
		}
		
		// Recalculate after canvas is fully rendered
		requestAnimationFrame(() => {
			requestAnimationFrame(() => {
				if (canvas && visible) {
					const rect = canvas.getBoundingClientRect();
					const expectedCanvasWidth = canvas.width >= 4000 ? canvas.width : 4000;
					const expectedCanvasHeight = canvas.height >= 4000 ? canvas.height : 4000;
					
					if (rect.width > 0 && rect.height > 0 && expectedCanvasWidth > 0 && expectedCanvasHeight > 0 && zoomLevel > 0) {
						const calculatedBaseScaleX = rect.width / (expectedCanvasWidth * zoomLevel);
						const calculatedBaseScaleY = rect.height / (expectedCanvasHeight * zoomLevel);
						
						if (calculatedBaseScaleX > 0.01 && calculatedBaseScaleX < 10) {
							actualBaseScaleX = calculatedBaseScaleX;
						}
						if (calculatedBaseScaleY > 0.01 && calculatedBaseScaleY < 10) {
							actualBaseScaleY = calculatedBaseScaleY;
						}
					}
				}
			});
		});
	}
	
	$: if (visible && textInputElement) {
		setTimeout(() => {
			textInputElement?.focus();
			if (editingTextComponent) {
				textInputElement?.select();
			}
		}, 10);
	}
</script>

{#if visible && canvas}
	{@const rect = canvas.getBoundingClientRect()}
	{@const scaleX = rect.width / canvas.width}
	{@const scaleY = rect.height / canvas.height}
	{@const expectedCanvasWidth = canvas.width >= 4000 ? canvas.width : 4000}
	{@const expectedCanvasHeight = canvas.height >= 4000 ? canvas.height : 4000}
	{@const calculatedBaseScaleX = rect.width > 0 && expectedCanvasWidth > 0 && zoomLevel > 0 ? rect.width / (expectedCanvasWidth * zoomLevel) : actualBaseScaleX}
	{@const calculatedBaseScaleY = rect.height > 0 && expectedCanvasHeight > 0 && zoomLevel > 0 ? rect.height / (expectedCanvasHeight * zoomLevel) : actualBaseScaleY}
	{@const baseScaleX = (calculatedBaseScaleX > 0.01 && calculatedBaseScaleX < 10) ? calculatedBaseScaleX : actualBaseScaleX}
	{@const baseScaleY = (calculatedBaseScaleY > 0.01 && calculatedBaseScaleY < 10) ? calculatedBaseScaleY : actualBaseScaleY}
	{@const displayFontSize = style.fontSize * baseScaleX}
	{@const displayLineHeight = displayFontSize * 1.2}
	<div
		class="absolute bg-transparent z-10"
		style="left: {position.x}px; top: {position.y}px; transform: translate(0, 0);"
	>
		<textarea
			bind:this={textInputElement}
			bind:value
			class="resize-none bg-transparent placeholder-gray-500 dark:placeholder-gray-400 outline-none border-dotted border border-blue-500"
			style="width: {size.width}px; height: {size.height}px; font-size: {displayFontSize}px; font-family: {style.fontFamily}; color: {style.color}; padding: 0; line-height: {displayLineHeight}px;"
			placeholder="Enter text... (Shift+Enter for new line)"
			on:keydown={onKeyDown}
			on:input={(e) => {
				// Dispatch input event for two-way binding
				dispatch('input', e.target.value);
				
				// Update textarea size based on content
				if (!editingTextComponent && canvas && ctx) {
					const fontSize = style.fontSize;
					const fontFamily = style.fontFamily;
					ctx.font = `${fontSize}px ${fontFamily}`;
					const lines = e.target.value.split('\n');
					const widths = lines.map(line => ctx.measureText(line).width);
					const maxWidth = widths.length > 0 ? Math.max(...widths) : fontSize * 2;
					const height = lines.length > 0 ? lines.length * fontSize * 1.2 : fontSize * 1.2;
					
					const rect = canvas.getBoundingClientRect();
					// Use expected canvas size (4000x4000 when canvas.width is small), not actual canvas.width
					const expectedCanvasWidth = canvas.width >= 4000 ? canvas.width : 4000;
					const expectedCanvasHeight = canvas.height >= 4000 ? canvas.height : 4000;
					const baseScaleX = rect.width / (expectedCanvasWidth * zoomLevel);
					const baseScaleY = rect.height / (expectedCanvasHeight * zoomLevel);
					// The container scales by zoomLevel, so we set size in container-local coordinates
					// Use the measured text size, but ensure a minimum size for usability
					// This ensures the input box matches the rendered text size, but is never too small
					const minWidth = fontSize * 20 * baseScaleX; // Much larger minimum width for empty/short text
					const minHeight = fontSize * 4 * baseScaleY; // Much larger minimum height for empty text
					onInput({
						width: Math.max(minWidth, maxWidth * baseScaleX),
						height: Math.max(minHeight, height * baseScaleY)
					});
				}
			}}
			on:blur={onBlur}
		></textarea>
	</div>
{/if}

