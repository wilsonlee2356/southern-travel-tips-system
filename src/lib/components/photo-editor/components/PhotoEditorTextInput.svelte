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
	{@const displayFontSize = style.fontSize * scaleX * zoomLevel}
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
					const scaleX = rect.width / canvas.width;
					const scaleY = rect.height / canvas.height;
					
					onInput({
						width: Math.max(200 * zoomLevel, maxWidth * scaleX * zoomLevel),
						height: Math.max(30 * zoomLevel, height * scaleY * zoomLevel)
					});
				}
			}}
			on:blur={onBlur}
		></textarea>
	</div>
{/if}

