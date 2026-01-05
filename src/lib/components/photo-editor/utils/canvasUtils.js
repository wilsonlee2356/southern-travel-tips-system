/**
 * Canvas utility functions for coordinate conversion and component detection
 */

/**
 * Convert screen coordinates to canvas coordinates
 * @param {HTMLCanvasElement} canvas - The canvas element
 * @param {Object} event - Mouse event with clientX and clientY
 * @param {number} zoomLevel - Current zoom level
 * @returns {{x: number, y: number}} Canvas coordinates
 */
export function canvasToImageCoordinates(canvas, event, zoomLevel = 1) {
	if (!canvas) return { x: 0, y: 0 };
	const rect = canvas.getBoundingClientRect();
	
	// rect already accounts for the container's transform (translate + scale)
	// Get position relative to canvas element in screen space
	const screenX = event.clientX - rect.left;
	const screenY = event.clientY - rect.top;
	
	// Convert to container-local coordinates (before zoom transform)
	// The container is scaled by zoomLevel, so divide by it
	const localX = screenX / zoomLevel;
	const localY = screenY / zoomLevel;
	
	// Now convert from container-local to canvas coordinates
	// rect.width is the displayed width (after zoom), so base width = rect.width / zoomLevel
	// baseScale = baseWidth / canvas.width = (rect.width / zoomLevel) / canvas.width
	const baseScaleX = (rect.width / zoomLevel) / canvas.width;
	const baseScaleY = (rect.height / zoomLevel) / canvas.height;
	
	// Convert to canvas coordinates
	const x = localX / baseScaleX;
	const y = localY / baseScaleY;
	
	return { x, y };
}

/**
 * Get component at the given canvas coordinates
 * @param {Array} components - Array of component objects
 * @param {number} x - Canvas x coordinate
 * @param {number} y - Canvas y coordinate
 * @returns {Object|null} Component at the coordinates, or null
 */
export function getComponentAt(components, x, y) {
	// Check in reverse order (top to bottom)
	for (let i = components.length - 1; i >= 0; i--) {
		const comp = components[i];
		if (x >= comp.x && x <= comp.x + comp.width &&
			y >= comp.y && y <= comp.y + comp.height) {
			return comp;
		}
	}
	return null;
}

/**
 * Get resize handle at the given coordinates for an image component
 * @param {number} x - Canvas x coordinate
 * @param {number} y - Canvas y coordinate
 * @param {Object} component - Component object (must be type 'image')
 * @returns {string|null} Handle type ('nw', 'ne', 'sw', 'se') or null
 */
export function getResizeHandleAt(x, y, component) {
	if (!component || component.type !== 'image') return null;
	
	const handleSize = 8;
	const tolerance = handleSize / 2 + 2; // Add some tolerance for easier clicking
	
	const handles = [
		{ x: component.x, y: component.y, type: 'nw' }, // top-left
		{ x: component.x + component.width, y: component.y, type: 'ne' }, // top-right
		{ x: component.x, y: component.y + component.height, type: 'sw' }, // bottom-left
		{ x: component.x + component.width, y: component.y + component.height, type: 'se' } // bottom-right
	];
	
	for (const handle of handles) {
		const dx = x - handle.x;
		const dy = y - handle.y;
		const distance = Math.sqrt(dx * dx + dy * dy);
		if (distance <= tolerance) {
			return handle.type;
		}
	}
	
	return null;
}

/**
 * Get cursor style for resize handle
 * @param {string} handle - Handle type ('nw', 'ne', 'sw', 'se')
 * @returns {string} CSS cursor value
 */
export function getResizeCursor(handle) {
	const cursors = {
		'nw': 'nw-resize',
		'ne': 'ne-resize',
		'sw': 'sw-resize',
		'se': 'se-resize'
	};
	return cursors[handle] || 'default';
}

/**
 * Calculate bounding box for all components
 * @param {Array} components - Array of component objects
 * @returns {Object|null} Bounds object with x, y, width, height, maxX, maxY, or null if no components
 */
export function calculateContentBounds(components) {
	if (components.length === 0) {
		return null;
	}
	
	let minX = Infinity;
	let minY = Infinity;
	let maxX = -Infinity;
	let maxY = -Infinity;
	
	components.forEach(component => {
		minX = Math.min(minX, component.x);
		minY = Math.min(minY, component.y);
		maxX = Math.max(maxX, component.x + component.width);
		maxY = Math.max(maxY, component.y + component.height);
	});
	
	return {
		x: minX,
		y: minY,
		width: maxX - minX,
		height: maxY - minY,
		maxX: maxX,
		maxY: maxY
	};
}

