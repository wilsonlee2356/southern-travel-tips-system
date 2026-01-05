/**
 * Canvas drawing utility functions
 */

/**
 * Draw selection box around a component
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {Object} component - Component object
 */
export function drawSelectionBox(ctx, component) {
	if (!ctx) return;
	
	ctx.strokeStyle = '#3b82f6';
	ctx.lineWidth = 2;
	ctx.setLineDash([5, 5]);
	ctx.strokeRect(component.x - 2, component.y - 2, component.width + 4, component.height + 4);
	ctx.setLineDash([]);
	
	// Draw resize handles at corners (only for image components)
	if (component.type === 'image') {
		const handleSize = 8;
		const handles = [
			{ x: component.x, y: component.y, type: 'nw' }, // top-left
			{ x: component.x + component.width, y: component.y, type: 'ne' }, // top-right
			{ x: component.x, y: component.y + component.height, type: 'sw' }, // bottom-left
			{ x: component.x + component.width, y: component.y + component.height, type: 'se' } // bottom-right
		];
		
		ctx.fillStyle = '#3b82f6';
		ctx.strokeStyle = '#ffffff';
		ctx.lineWidth = 2;
		handles.forEach(handle => {
			ctx.beginPath();
			ctx.rect(handle.x - handleSize/2, handle.y - handleSize/2, handleSize, handleSize);
			ctx.fill();
			ctx.stroke();
		});
	}
}

/**
 * Draw a text component on the canvas
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {Object} component - Text component object
 */
export function drawTextComponent(ctx, component) {
	if (!ctx) return;
	
	ctx.fillStyle = component.color || '#000000';
	ctx.font = `${component.fontSize || 24}px ${component.fontFamily || 'Arial'}`;
	ctx.textAlign = 'left';
	ctx.textBaseline = 'top';
	
	// Handle multi-line text
	const lines = component.text.split('\n');
	lines.forEach((line, index) => {
		ctx.fillText(line, component.x, component.y + (index * (component.fontSize || 24) * 1.2));
	});
}

/**
 * Draw an image component on the canvas
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {Object} component - Image component object
 * @param {Image} image - Loaded Image object
 */
export function drawImageComponent(ctx, component, image) {
	if (!ctx || !image || !image.complete) return;
	ctx.drawImage(image, component.x, component.y, component.width, component.height);
}

