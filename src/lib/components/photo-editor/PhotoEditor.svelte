<script>
	import { onMount, createEventDispatcher } from 'svelte';
	import PhotoEditorHeader from './components/PhotoEditorHeader.svelte';
	import PhotoEditorToolbar from './components/PhotoEditorToolbar.svelte';
	import PhotoEditorSubToolbar from './components/PhotoEditorSubToolbar.svelte';
	import PhotoEditorFooter from './components/PhotoEditorFooter.svelte';
	import PhotoEditorTextInput from './components/PhotoEditorTextInput.svelte';
	import { canvasToImageCoordinates, getComponentAt, getResizeHandleAt, getResizeCursor, calculateContentBounds } from './utils/canvasUtils.js';
	import { drawSelectionBox, drawTextComponent, drawImageComponent } from './utils/canvasDrawing.js';
	
	export let initialImage = null; // Base64 image or URL
	export let open = false;
	
	const dispatch = createEventDispatcher();
	
	let canvas;
	let ctx;
	let canvasContainer;
	let backgroundImage = null;
	let backgroundImageLoaded = false;
	let cachedBackgroundImage = null; // Cached Image object
	let imageCache = new Map(); // Cache for component images
	let components = []; // Array of {type: 'image'|'text', x, y, width, height, data, id}
	let selectedComponent = null;
	let isDragging = false;
	let isResizing = false;
	let isPanning = false;
	let resizeHandle = null; // 'nw', 'ne', 'sw', 'se'
	let dragOffset = { x: 0, y: 0 };
	let resizeStart = { x: 0, y: 0, width: 0, height: 0 };
	let panStart = { x: 0, y: 0, offsetX: 0, offsetY: 0 };
	let mouseDownPosition = { x: 0, y: 0 }; // Track initial mouse position to detect actual movement
	let justFinishedDrag = false; // Track if we just finished a drag operation
	let nextId = 1;
	let animationFrameId = null;
	
	// Zoom and pan state
	let zoomLevel = 1;
	let panOffset = { x: 0, y: 0 };
	
	// Toolbar state
	let activeTool = null; // 'image' or 'text'
	
	// Text editing state
	let textInput = '';
	let textInputVisible = false;
	let textInputPosition = { x: 0, y: 0 };
	let textInputSize = { width: 0, height: 0 };
	let textInputStyle = { fontSize: 24, fontFamily: 'Arial', color: '#000000' };
	let textInputElement;
	let editingTextComponent = null; // Track which text component is being edited
	
	// Image upload state
	let imageInput;
	
	// Sub toolbar state
	let showColorPicker = false;
	
	$: if (open && initialImage) {
		backgroundImage = initialImage;
		backgroundImageLoaded = false;
		cachedBackgroundImage = null;
		imageCache.clear();
		components = [];
		selectedComponent = null;
		zoomLevel = 1;
		panOffset = { x: 0, y: 0 };
		loadBackgroundImage();
		// Use setTimeout to ensure DOM is ready
		setTimeout(() => {
			updateCanvasTransform();
		}, 0);
	}
	
	$: if (open && !initialImage) {
		// Reset zoom and pan when opening without initial image
		zoomLevel = 1;
		panOffset = { x: 0, y: 0 };
		// Ensure canvas is initialized to 4000x4000
		setTimeout(() => {
			initializeCanvas();
			updateCanvasTransform();
		}, 0);
	}
	
	$: if (!open) {
		// Cleanup when editor closes
		stopDragging();
		isPanning = false;
	}
	
	// Initialize canvas when it's bound and editor is open
	// This ensures canvas is always 4000x4000 when there's no background image
	$: if (open && canvas && !backgroundImage) {
		// Use requestAnimationFrame to ensure DOM is ready
		requestAnimationFrame(() => {
			if (canvas && !backgroundImage && (canvas.width === 0 || canvas.height === 0 || canvas.width < 4000 || canvas.height < 4000)) {
				canvas.width = 4000;
				canvas.height = 4000;
				if (!ctx) {
					ctx = canvas.getContext('2d');
				}
				ctx.fillStyle = '#ffffff';
				ctx.fillRect(0, 0, canvas.width, canvas.height);
			}
		});
	}
	
	// Content bounds calculation is now handled by imported utility
	
	function resizeCanvasToContent() {
		if (!canvas) return;
		
		// If there's a background image, use its size as minimum
		let minWidth = 0;
		let minHeight = 0;
		
		if (backgroundImage && backgroundImageLoaded && cachedBackgroundImage) {
			minWidth = cachedBackgroundImage.width;
			minHeight = cachedBackgroundImage.height;
		}
		
		// Calculate content bounds
		const contentBounds = calculateContentBounds(components);
		
		// Determine canvas size
		let newWidth = minWidth;
		let newHeight = minHeight;
		let offsetX = 0;
		let offsetY = 0;
		
		if (contentBounds) {
			const padding = 50; // Add padding around content
			
			// Calculate required canvas size to fit all content
			// Handle negative coordinates by adding offset
			offsetX = Math.min(0, contentBounds.x - padding);
			offsetY = Math.min(0, contentBounds.y - padding);
			
			// Calculate width and height needed
			const requiredWidth = contentBounds.maxX - offsetX + padding;
			const requiredHeight = contentBounds.maxY - offsetY + padding;
			
			// Ensure minimum size is at least the default (4000x4000) if no background image
			// This prevents the canvas from shrinking and causing coordinate mismatches
			if (minWidth === 0 && minHeight === 0) {
				newWidth = Math.max(4000, requiredWidth);
				newHeight = Math.max(4000, requiredHeight);
			} else {
				newWidth = Math.max(minWidth, requiredWidth);
				newHeight = Math.max(minHeight, requiredHeight);
			}
		} else if (minWidth === 0 && minHeight === 0) {
			// No content and no background - use default size
			newWidth = 4000;
			newHeight = 4000;
		}
		
		// Ensure canvas never shrinks below 4000x4000 when there's no background image
		// This maintains stable coordinate system
		if (minWidth === 0 && minHeight === 0) {
			newWidth = Math.max(4000, newWidth);
			newHeight = Math.max(4000, newHeight);
		}
		
		// IMPORTANT: If canvas is already 4000x4000 and we're trying to make it smaller,
		// don't resize it (prevents coordinate system issues)
		if (minWidth === 0 && minHeight === 0 && canvas.width === 4000 && canvas.height === 4000) {
			// Only resize if we need to make it larger, not smaller
			if (newWidth <= 4000 && newHeight <= 4000) {
				return; // Don't resize, keep it at 4000x4000
			}
		}
		
		// Only resize if needed
		if (canvas.width !== newWidth || canvas.height !== newHeight) {
			// If we need to shift components due to negative coordinates
			if (offsetX < 0 || offsetY < 0) {
				// Shift all components to account for the new origin
				components.forEach(component => {
					component.x -= offsetX;
					component.y -= offsetY;
				});
			}
			
			canvas.width = newWidth;
			canvas.height = newHeight;
			ctx = canvas.getContext('2d');
			
			// If canvas was resized and we have a background, redraw it
			if (backgroundImage && backgroundImageLoaded && cachedBackgroundImage) {
				ctx.drawImage(cachedBackgroundImage, 0, 0);
			} else if (!backgroundImage) {
				// Fill with white background
				ctx.fillStyle = '#ffffff';
				ctx.fillRect(0, 0, canvas.width, canvas.height);
			}
		}
	}
	
	function initializeCanvas() {
		if (!canvas) return;
		ctx = canvas.getContext('2d');
		if (!backgroundImage) {
			canvas.width = 4000;
			canvas.height = 4000;
			ctx.fillStyle = '#ffffff';
			ctx.fillRect(0, 0, canvas.width, canvas.height);
		}
	}
	
	function loadBackgroundImage() {
		if (!canvas || !backgroundImage) {
			initializeCanvas();
			return;
		}
		
		if (!ctx) {
			ctx = canvas.getContext('2d');
		}
		
		const img = new Image();
		img.crossOrigin = 'anonymous';
		img.onload = () => {
			// Set canvas size to match image
			canvas.width = img.width;
			canvas.height = img.height;
			ctx = canvas.getContext('2d');
			
			// Cache the background image
			cachedBackgroundImage = img;
			backgroundImageLoaded = true;
			
			// Redraw all components
			redrawCanvas();
		};
		img.onerror = () => {
			// If image fails to load, initialize with default canvas
			initializeCanvas();
		};
		img.src = backgroundImage;
	}
	
	function redrawCanvas() {
		if (!canvas) return;
		
		// Ensure context exists
		if (!ctx) {
			ctx = canvas.getContext('2d');
		}
		if (!ctx) return;
		
		// Resize canvas to fit content first
		resizeCanvasToContent();
		
		// Ensure context is still valid after resize
		if (!ctx) {
			ctx = canvas.getContext('2d');
		}
		if (!ctx) return;
		
		// Clear canvas
		ctx.clearRect(0, 0, canvas.width, canvas.height);
		
		// Draw background image if loaded (use cached version)
		if (backgroundImage && backgroundImageLoaded && cachedBackgroundImage) {
			ctx.drawImage(cachedBackgroundImage, 0, 0);
			drawComponents();
		} else if (!backgroundImage) {
			// White background if no image
			ctx.fillStyle = '#ffffff';
			ctx.fillRect(0, 0, canvas.width, canvas.height);
			drawComponents();
		} else {
			drawComponents();
		}
	}
	
	function drawComponents() {
		if (!ctx) return;
		
		// Redraw all components
		components.forEach(component => {
			if (component.type === 'image') {
				// Use cached image if available
				let img = imageCache.get(component.data);
				if (img && img.complete) {
					// Image is cached and loaded, draw immediately
					drawImageComponent(ctx, component, img);
					if (component === selectedComponent) {
						drawSelectionBox(ctx, component);
					}
				} else {
					// Load and cache the image
					if (!img) {
						img = new Image();
						img.crossOrigin = 'anonymous';
						imageCache.set(component.data, img);
						img.onload = () => {
							// Redraw when image loads
							redrawCanvas();
						};
						img.src = component.data;
					}
				}
			} else if (component.type === 'text') {
				// Skip drawing text component if it's currently being edited
				if (component === editingTextComponent) {
					return;
				}
				
				drawTextComponent(ctx, component);
				
				if (component === selectedComponent) {
					drawSelectionBox(ctx, component);
				}
			}
		});
	}
	
	// Drawing and utility functions are now imported from utils
	
	function handleCanvasWheel(event) {
		if (!canvas || !event.ctrlKey || !canvasContainer) return;
		
		event.preventDefault();
		event.stopPropagation();
		
		// Get mouse position relative to the scrollable container (parent of canvasContainer)
		// The wheel event is on the scrollable div, so we need to account for scroll position
		const scrollContainer = canvasContainer.parentElement;
		if (!scrollContainer) return;
		
		const scrollRect = scrollContainer.getBoundingClientRect();
		const containerRect = canvasContainer.getBoundingClientRect();
		
		// Calculate mouse position relative to the scrollable container
		const mouseX = event.clientX - scrollRect.left + scrollContainer.scrollLeft;
		const mouseY = event.clientY - scrollRect.top + scrollContainer.scrollTop;
		
		// Calculate the point in the canvas container's local space before zoom
		const localX = (mouseX - panOffset.x) / zoomLevel;
		const localY = (mouseY - panOffset.y) / zoomLevel;
		
		// Calculate zoom factor
		const zoomFactor = event.deltaY > 0 ? 0.9 : 1.1;
		const newZoom = Math.max(0.1, Math.min(5, zoomLevel * zoomFactor));
		
		// Update zoom
		zoomLevel = newZoom;
		
		// Adjust pan to keep the point under the mouse in the same place
		panOffset.x = mouseX - localX * zoomLevel;
		panOffset.y = mouseY - localY * zoomLevel;
		
		// Update canvas transform
		updateCanvasTransform();
	}
	
	function updateCanvasTransform() {
		if (canvasContainer) {
			canvasContainer.style.transform = `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`;
			canvasContainer.style.transformOrigin = '0 0';
		}
	}
	
	function handleCanvasDoubleClick(event) {
		if (!canvas || textInputVisible || isDragging || isResizing) return;
		
		event.preventDefault();
		event.stopPropagation();
		
		const { x, y } = canvasToImageCoordinates(canvas, event, zoomLevel);
		const component = getComponentAt(components, x, y);
		
		// If double-clicking on a text component, open it for editing
		if (component && component.type === 'text') {
			editingTextComponent = component;
			selectedComponent = component;
			
			// Ensure canvas context exists for measuring
			if (!ctx && canvas) {
				ctx = canvas.getContext('2d');
			}
			
			// Set text input style to match component
			const fontSize = component.fontSize || 24;
			const fontFamily = component.fontFamily || 'Arial';
			textInputStyle = {
				fontSize: fontSize,
				fontFamily: fontFamily,
				color: component.color || '#000000'
			};
			
			// Measure text to get accurate size
			if (ctx) {
				ctx.font = `${fontSize}px ${fontFamily}`;
				const lines = component.text.split('\n');
				const widths = lines.map(line => ctx.measureText(line).width);
				const maxWidth = widths.length > 0 ? Math.max(...widths) : fontSize * 2;
				const height = lines.length > 0 ? lines.length * fontSize * 1.2 : fontSize * 1.2;
				
				// Convert canvas coordinates to container-local coordinates for text input positioning
				// The text input is positioned relative to the canvas container (which has transform)
				const rect = canvas.getBoundingClientRect();
				// rect.width already includes zoom, so extract base scale
				const baseScaleX = rect.width / (canvas.width * zoomLevel);
				const baseScaleY = rect.height / (canvas.height * zoomLevel);
				
				// Convert canvas coordinates to container-local coordinates
				// Zoom is handled by the container's transform
				textInputPosition = {
					x: component.x * baseScaleX,
					y: component.y * baseScaleY
				};
				
				// Set text input size based on measured text (container will apply zoom transform)
				textInputSize = {
					width: Math.max(200 * baseScaleX, maxWidth * baseScaleX),
					height: Math.max(30 * baseScaleY, height * baseScaleY)
				};
			} else {
				// Fallback if context not available
				const rect = canvas.getBoundingClientRect();
				const baseScaleX = rect.width / (canvas.width * zoomLevel);
				const baseScaleY = rect.height / (canvas.height * zoomLevel);
				
				textInputPosition = {
					x: component.x * baseScaleX,
					y: component.y * baseScaleY
				};
				
				textInputSize = {
					width: Math.max(200 * baseScaleX, component.width * baseScaleX),
					height: Math.max(30 * baseScaleY, component.height * baseScaleY)
				};
			}
			
			// Set the current text content
			textInput = component.text;
			textInputVisible = true;
			activeTool = 'text';
			
			redrawCanvas();
			
			// Focus text input and select all text after a short delay
			setTimeout(() => {
				textInputElement?.focus();
				textInputElement?.select();
			}, 10);
		}
	}
	
	function handleCanvasClick(event) {
		// Don't handle click if we're currently dragging/resizing
		if (!canvas || isDragging || isResizing) return;
		
		// If we just finished a drag operation, don't process click to prevent deselection
		if (justFinishedDrag) {
			justFinishedDrag = false;
			return;
		}
		
		// If we just finished a drag operation (mouse moved), don't process click
		// This prevents deselection when clicking on an already-selected component
		// Check if mouse actually moved during mousedown (indicating a drag, not just a click)
		if (mouseDownPosition.x !== 0 || mouseDownPosition.y !== 0) {
			const moved = Math.abs(event.clientX - mouseDownPosition.x) > 5 || Math.abs(event.clientY - mouseDownPosition.y) > 5;
			if (moved) {
				// Reset tracking
				mouseDownPosition = { x: 0, y: 0 };
				return;
			}
			// Reset tracking for next time
			mouseDownPosition = { x: 0, y: 0 };
		}
		
		// If text input is visible and has content, submit it first
		if (textInputVisible) {
			// Check if clicking outside the textarea
			const textareaRect = textInputElement?.getBoundingClientRect();
			if (textareaRect) {
				const clickX = event.clientX;
				const clickY = event.clientY;
				const isClickInsideTextarea = 
					clickX >= textareaRect.left &&
					clickX <= textareaRect.right &&
					clickY >= textareaRect.top &&
					clickY <= textareaRect.bottom;
				
				if (!isClickInsideTextarea) {
					// Clicking outside - submit if text has content (non-space)
					if (textInput.trim()) {
						handleTextSubmit();
					} else {
						// No content, just close
						textInputVisible = false;
						textInput = '';
						activeTool = null;
						editingTextComponent = null;
					}
					return;
				}
			}
			// Clicking inside textarea, don't handle as canvas click
			return;
		}
		
		const { x, y } = canvasToImageCoordinates(canvas, event, zoomLevel);
		
		// Check if clicking on a resize handle - if so, don't handle as click
		if (selectedComponent) {
			const handle = getResizeHandleAt(x, y, selectedComponent);
			if (handle) {
				return; // Let mousedown handle resize
			}
		}
		
		if (activeTool === 'text') {
			// Ensure canvas is properly initialized to 4000x4000 before creating text
			// This prevents coordinate calculation issues when canvas is at wrong size
			// Force initialization if canvas is not at correct size
			if (!backgroundImage) {
				if (canvas.width < 4000 || canvas.height < 4000 || canvas.width === 0 || canvas.height === 0) {
					canvas.width = 4000;
					canvas.height = 4000;
					if (!ctx) {
						ctx = canvas.getContext('2d');
					}
					ctx.fillStyle = '#ffffff';
					ctx.fillRect(0, 0, canvas.width, canvas.height);
				}
			}
			
			// Set default text input style FIRST (before calculating size)
			textInputStyle = {
				fontSize: 24,
				fontFamily: 'Arial',
				color: '#000000'
			};
			
			// Add text at click position
			// IMPORTANT: Don't call redrawCanvas() here as it might resize the canvas
			// and change scaleX/scaleY, causing coordinate mismatch
			// Convert canvas coordinates to container-local coordinates for text input positioning
			// The text input is positioned relative to the canvas container, which has transform applied
			const rect = canvas.getBoundingClientRect();
			// rect.width is the displayed width (after transform)
			// The displayed scale is: rect.width / canvas.width (this includes zoom)
			// But we need the base scale (without zoom) for container-local coordinates
			// baseScale = rect.width / (canvas.width * zoomLevel)
			// IMPORTANT: Use expected canvas size (4000x4000) when there's no background image,
			// not the actual canvas.width which might be wrong
			const expectedCanvasWidth = backgroundImage && backgroundImageLoaded && cachedBackgroundImage 
				? cachedBackgroundImage.width 
				: 4000;
			const expectedCanvasHeight = backgroundImage && backgroundImageLoaded && cachedBackgroundImage 
				? cachedBackgroundImage.height 
				: 4000;
			
			const baseScaleX = rect.width / (expectedCanvasWidth * zoomLevel);
			const baseScaleY = rect.height / (expectedCanvasHeight * zoomLevel);
			
			// The canvas container has transform: translate(panOffset) scale(zoomLevel)
			// So we need to convert canvas coordinates to container-local coordinates
			// Canvas coordinate (x, y) -> container-local: (x * baseScaleX, y * baseScaleY)
			// Note: zoom is handled by the container's transform, so we use baseScale
			textInputPosition = {
				x: x * baseScaleX,
				y: y * baseScaleY
			};
			
			// Set default text input size (will adjust as user types)
			// The text input is inside the container which has scale(zoomLevel)
			// So we need to set the size in container-local coordinates
			// Ensure canvas context exists for measuring
			if (!ctx && canvas) {
				ctx = canvas.getContext('2d');
			}
			
			// Measure an empty string to get the minimum size
			// Use a much larger minimum size for better UX, but ensure it matches rendered text when content is added
			if (ctx) {
				const fontSize = textInputStyle.fontSize || 24;
				const fontFamily = textInputStyle.fontFamily || 'Arial';
				ctx.font = `${fontSize}px ${fontFamily}`;
				// Use a much larger minimum size for empty text to make it very usable
				// When text is typed, the on:input handler will adjust to match the actual text size
				const emptyWidth = fontSize * 20; // Much larger minimum width for empty text (comfortable size)
				const emptyHeight = fontSize * 4; // Much larger minimum height for empty text
				
				// Set initial size with a minimum that's very comfortable to use
				// The size will adjust dynamically as user types to match the actual text
				textInputSize = {
					width: emptyWidth * baseScaleX,
					height: emptyHeight * baseScaleY
				};
			} else {
				// Fallback if context not available - use larger defaults
				const fontSize = textInputStyle.fontSize || 24;
				const defaultCanvasWidth = fontSize * 20;
				const defaultCanvasHeight = fontSize * 4;
				textInputSize = {
					width: defaultCanvasWidth * baseScaleX,
					height: defaultCanvasHeight * baseScaleY
				};
			}
			
			// Use requestAnimationFrame to ensure canvas is rendered before showing text input
			// This helps ensure accurate size calculations, especially on first text creation
			requestAnimationFrame(() => {
				if (canvas && textInputVisible && !editingTextComponent) {
					// Recalculate size after canvas is rendered (only for new text, not editing)
					// Use the same calculation as the initial size to maintain consistency
					const rect = canvas.getBoundingClientRect();
					const expectedCanvasWidth = backgroundImage && backgroundImageLoaded && cachedBackgroundImage 
						? cachedBackgroundImage.width 
						: 4000;
					const expectedCanvasHeight = backgroundImage && backgroundImageLoaded && cachedBackgroundImage 
						? cachedBackgroundImage.height 
						: 4000;
					const baseScaleX = rect.width / (expectedCanvasWidth * zoomLevel);
					const baseScaleY = rect.height / (expectedCanvasHeight * zoomLevel);
					
					if (ctx) {
						const fontSize = textInputStyle.fontSize || 24;
						const fontFamily = textInputStyle.fontFamily || 'Arial';
						ctx.font = `${fontSize}px ${fontFamily}`;
						// Use the same calculation as initial size for consistency
						const emptyWidth = fontSize * 20;
						const emptyHeight = fontSize * 4;
						
						// Match the initial size calculation
						textInputSize = {
							width: emptyWidth * baseScaleX,
							height: emptyHeight * baseScaleY
						};
					}
				}
			});
			
			textInputVisible = true;
			textInput = '';
			selectedComponent = null;
			editingTextComponent = null;
			// Don't redraw here - it will happen when text is submitted
			// Focus text input after a short delay
			setTimeout(() => {
				textInputElement?.focus();
			}, 10);
		} else {
			// Select component
			const component = getComponentAt(components, x, y);
			// Only update selection if it's different from current selection
			// This prevents flickering when clicking on an already-selected component
			if (component !== selectedComponent) {
				selectedComponent = component;
				redrawCanvas();
			}
		}
	}
	
	function stopDragging() {
		if (isDragging || isResizing || isPanning) {
			// Mark that we just finished a drag operation (if it was actually a drag, not just a click)
			const wasDragging = isDragging || isResizing;
			
			// Remove global listeners
			window.removeEventListener('mousemove', handleWindowMouseMove);
			window.removeEventListener('mouseup', handleWindowMouseUp);
			
			isDragging = false;
			isResizing = false;
			isPanning = false;
			resizeHandle = null;
			if (animationFrameId) {
				cancelAnimationFrame(animationFrameId);
				animationFrameId = null;
			}
			if (canvas) {
				canvas.style.cursor = 'default';
			}
			
			// Set flag to prevent click handler from deselecting after drag
			if (wasDragging) {
				justFinishedDrag = true;
				// Clear flag after a short delay to allow click event to be ignored
				setTimeout(() => {
					justFinishedDrag = false;
				}, 50);
			}
			
			// Final redraw to ensure everything is in place
			redrawCanvas();
		}
	}
	
	function handleCanvasMouseDown(event) {
		if (!canvas || textInputVisible) return;
		
		// Track initial mouse position to detect if this is a click or drag
		mouseDownPosition = { x: event.clientX, y: event.clientY };
		
		// Clean up any previous drag state first
		stopDragging();
		
		event.preventDefault();
		event.stopPropagation();
		
		// Check if Ctrl is pressed - if so, start panning
		if (event.ctrlKey || event.metaKey) {
			isPanning = true;
			panStart = {
				x: event.clientX,
				y: event.clientY,
				offsetX: panOffset.x,
				offsetY: panOffset.y
			};
			if (canvas) {
				canvas.style.cursor = 'grabbing';
			}
			
			// Add global mouse listeners for panning outside canvas
			window.addEventListener('mousemove', handleWindowMouseMove);
			window.addEventListener('mouseup', handleWindowMouseUp);
			return;
		}
		
		const { x, y } = canvasToImageCoordinates(canvas, event, zoomLevel);
		
		// Check if clicking on a resize handle first
		if (selectedComponent) {
			const handle = getResizeHandleAt(x, y, selectedComponent);
			if (handle) {
				isResizing = true;
				resizeHandle = handle;
				resizeStart = {
					x: selectedComponent.x,
					y: selectedComponent.y,
					width: selectedComponent.width,
					height: selectedComponent.height,
					mouseX: x,
					mouseY: y
				};
				canvas.style.cursor = getResizeCursor(handle);
				
				// Add global mouse listeners for resizing outside canvas
				window.addEventListener('mousemove', handleWindowMouseMove);
				window.addEventListener('mouseup', handleWindowMouseUp);
				redrawCanvas();
				return;
			}
		}
		
		const component = getComponentAt(components, x, y);
		if (component) {
			selectedComponent = component;
			isDragging = true;
			dragOffset = {
				x: x - component.x,
				y: y - component.y
			};
			canvas.style.cursor = 'grabbing';
			
			// Add global mouse listeners for dragging outside canvas
			window.addEventListener('mousemove', handleWindowMouseMove);
			window.addEventListener('mouseup', handleWindowMouseUp);
		} else {
			selectedComponent = null;
		}
		
		redrawCanvas();
	}
	
	function handleWindowMouseMove(event) {
		if (!canvas) return;
		
		event.preventDefault();
		event.stopPropagation();
		
		// Handle panning first (Ctrl + drag)
		if (isPanning) {
			const deltaX = event.clientX - panStart.x;
			const deltaY = event.clientY - panStart.y;
			
			panOffset.x = panStart.offsetX + deltaX;
			panOffset.y = panStart.offsetY + deltaY;
			
			updateCanvasTransform();
			return;
		}
		
		if (!selectedComponent) return;
		
		// Use the same coordinate conversion as canvasToImageCoordinates for consistency
		// Create a synthetic event object for canvasToImageCoordinates
		const syntheticEvent = {
			clientX: event.clientX,
			clientY: event.clientY
		};
		const { x, y } = canvasToImageCoordinates(canvas, syntheticEvent, zoomLevel);
		
		if (isResizing && resizeHandle) {
			// Calculate new dimensions based on which handle is being dragged
			const deltaX = x - resizeStart.mouseX;
			const deltaY = y - resizeStart.mouseY;
			
			let newX = resizeStart.x;
			let newY = resizeStart.y;
			let newWidth = resizeStart.width;
			let newHeight = resizeStart.height;
			
			// Minimum size to prevent negative dimensions
			const minSize = 10;
			
			switch (resizeHandle) {
				case 'nw': // top-left
					newX = resizeStart.x + deltaX;
					newY = resizeStart.y + deltaY;
					newWidth = resizeStart.width - deltaX;
					newHeight = resizeStart.height - deltaY;
					if (newWidth < minSize) {
						newWidth = minSize;
						newX = resizeStart.x + resizeStart.width - minSize;
					}
					if (newHeight < minSize) {
						newHeight = minSize;
						newY = resizeStart.y + resizeStart.height - minSize;
					}
					break;
				case 'ne': // top-right
					newY = resizeStart.y + deltaY;
					newWidth = resizeStart.width + deltaX;
					newHeight = resizeStart.height - deltaY;
					if (newWidth < minSize) newWidth = minSize;
					if (newHeight < minSize) {
						newHeight = minSize;
						newY = resizeStart.y + resizeStart.height - minSize;
					}
					break;
				case 'sw': // bottom-left
					newX = resizeStart.x + deltaX;
					newWidth = resizeStart.width - deltaX;
					newHeight = resizeStart.height + deltaY;
					if (newWidth < minSize) {
						newWidth = minSize;
						newX = resizeStart.x + resizeStart.width - minSize;
					}
					if (newHeight < minSize) newHeight = minSize;
					break;
				case 'se': // bottom-right
					newWidth = resizeStart.width + deltaX;
					newHeight = resizeStart.height + deltaY;
					if (newWidth < minSize) newWidth = minSize;
					if (newHeight < minSize) newHeight = minSize;
					break;
			}
			
			selectedComponent.x = newX;
			selectedComponent.y = newY;
			selectedComponent.width = newWidth;
			selectedComponent.height = newHeight;
		} else if (isDragging) {
			selectedComponent.x = x - dragOffset.x;
			selectedComponent.y = y - dragOffset.y;
		} else {
			return;
		}
		
		// Use requestAnimationFrame for smooth redraws
		if (animationFrameId) {
			cancelAnimationFrame(animationFrameId);
		}
		animationFrameId = requestAnimationFrame(() => {
			redrawCanvas();
		});
	}
	
	function handleWindowMouseUp(event) {
		event.preventDefault();
		event.stopPropagation();
		
		// Check if mouse actually moved (indicating a drag, not just a click)
		const moved = mouseDownPosition.x !== 0 && mouseDownPosition.y !== 0 && 
			(Math.abs(event.clientX - mouseDownPosition.x) > 5 || Math.abs(event.clientY - mouseDownPosition.y) > 5);
		
		// Only stop dragging if we actually moved the mouse (not just a click)
		// This prevents deselection when clicking on an already-selected component
		if (isDragging || isResizing) {
			if (moved || isResizing) {
				stopDragging();
			} else {
				// Just a click, clean up the drag state but keep selection
				isDragging = false;
				isResizing = false;
				resizeHandle = null;
				window.removeEventListener('mousemove', handleWindowMouseMove);
				window.removeEventListener('mouseup', handleWindowMouseUp);
				if (animationFrameId) {
					cancelAnimationFrame(animationFrameId);
					animationFrameId = null;
				}
				if (canvas) {
					canvas.style.cursor = 'default';
				}
				// Don't reset mouseDownPosition yet - let handleCanvasClick check it
			}
		} else {
			stopDragging();
		}
		
		// Reset mouse position tracking after a short delay to allow handleCanvasClick to check it
		// If it was a drag, we don't want handleCanvasClick to process the click
		setTimeout(() => {
			mouseDownPosition = { x: 0, y: 0 };
		}, 50);
	}
	
	function handleCanvasMouseMove(event) {
		if (!canvas) return;
		
		// Show pan cursor when Ctrl is held (even if not panning yet)
		if (event.ctrlKey || event.metaKey) {
			if (!isPanning && !isDragging && !isResizing) {
				canvas.style.cursor = 'grab';
			}
			return;
		}
		
		if (!isDragging && !isResizing && !isPanning) {
			const { x, y } = canvasToImageCoordinates(canvas, event, zoomLevel);
			
			// Check if hovering over a resize handle
			if (selectedComponent) {
				const handle = getResizeHandleAt(x, y, selectedComponent);
				if (handle) {
					canvas.style.cursor = getResizeCursor(handle);
					return;
				}
			}
			
			const component = getComponentAt(components, x, y);
			canvas.style.cursor = component ? 'grab' : 'default';
		}
	}
	
	function handleCanvasMouseUp(event) {
		event?.preventDefault();
		event?.stopPropagation();
		stopDragging();
	}
	
	function handleImageButtonClick() {
		activeTool = activeTool === 'image' ? null : 'image';
		if (activeTool === 'image') {
			imageInput?.click();
		}
		textInputVisible = false;
	}
	
	function handleTextButtonClick() {
		activeTool = activeTool === 'text' ? null : 'text';
		textInputVisible = false;
	}
	
	function handleImageUpload(event) {
		const file = event.target.files?.[0];
		if (!file) return;
		
		// Validate file type
		if (!file.type.startsWith('image/')) {
			alert('Please upload an image file');
			return;
		}
		
		// Validate file size (10MB)
		if (file.size > 10 * 1024 * 1024) {
			alert('File size must be less than 10MB');
			return;
		}
		
		const reader = new FileReader();
		reader.onload = (e) => {
			const img = new Image();
			img.onload = () => {
				// Ensure canvas is initialized
				if (!canvas) return;
				
				// Initialize canvas if not already done
				if (!ctx) {
					ctx = canvas.getContext('2d');
				}
				
				// Ensure canvas has dimensions
				if (canvas.width === 0 || canvas.height === 0) {
					initializeCanvas();
				}
				
				// Use original image dimensions
				const width = img.width;
				const height = img.height;
				
				// Add image component at top-left corner (0, 0) initially
				// The canvas will resize to fit it automatically
				const x = 0;
				const y = 0;
				
				// Cache the image immediately
				imageCache.set(e.target.result, img);
				
				components = [...components, {
					id: nextId++,
					type: 'image',
					x,
					y,
					width,
					height,
					data: e.target.result
				}];
				
				selectedComponent = components[components.length - 1];
				
				// Redraw immediately since image is already loaded
				// This will also resize the canvas to fit the content
				redrawCanvas();
			};
			img.src = e.target.result;
		};
		reader.readAsDataURL(file);
		
		// Reset input
		event.target.value = '';
		activeTool = null;
	}
	
	function handleTextSubmit() {
		// Only submit if text has non-space content
		if (!textInput.trim()) {
			// If editing and text becomes empty, remove the component
			if (editingTextComponent) {
				components = components.filter(c => c !== editingTextComponent);
				selectedComponent = null;
			}
			textInputVisible = false;
			textInput = '';
			activeTool = null;
			editingTextComponent = null;
			redrawCanvas();
			return;
		}
		
		// Ensure canvas context exists
		if (!ctx && canvas) {
			ctx = canvas.getContext('2d');
		}
		if (!ctx) return;
		
		// Use the text input style for measuring
		const fontSize = editingTextComponent ? (editingTextComponent.fontSize || 24) : textInputStyle.fontSize;
		const fontFamily = editingTextComponent ? (editingTextComponent.fontFamily || 'Arial') : textInputStyle.fontFamily;
		
		// Measure text to determine width and height
		ctx.font = `${fontSize}px ${fontFamily}`;
		const lines = textInput.split('\n');
		const widths = lines.map(line => ctx.measureText(line).width);
		const maxWidth = widths.length > 0 ? Math.max(...widths) : fontSize * 2; // Default width if empty
		const height = lines.length > 0 ? lines.length * fontSize * 1.2 : fontSize * 1.2;
		
		if (editingTextComponent) {
			// Update existing text component
			editingTextComponent.text = textInput;
			editingTextComponent.width = maxWidth;
			editingTextComponent.height = height;
			selectedComponent = editingTextComponent;
			editingTextComponent = null;
		} else {
			// Create new text component
			// IMPORTANT: Calculate coordinates using the EXPECTED canvas size (4000x4000 when no background)
			// not the actual canvas.width which might be wrong
			// Convert container-local coordinates back to canvas coordinates
			const rect = canvas.getBoundingClientRect();
			// Use expected canvas size, not actual canvas.width which might be wrong
			const expectedCanvasWidth = backgroundImage && backgroundImageLoaded && cachedBackgroundImage 
				? cachedBackgroundImage.width 
				: 4000;
			const expectedCanvasHeight = backgroundImage && backgroundImageLoaded && cachedBackgroundImage 
				? cachedBackgroundImage.height 
				: 4000;
			// rect.width already includes zoom, so we need to extract the base scale
			// rect.width = canvas.width * baseScale * zoomLevel
			// So baseScale = rect.width / (canvas.width * zoomLevel)
			const baseScaleX = rect.width / (expectedCanvasWidth * zoomLevel);
			const baseScaleY = rect.height / (expectedCanvasHeight * zoomLevel);
			
			// textInputPosition is in container-local coordinates (x * baseScaleX, y * baseScaleY)
			// Convert back to canvas coordinates: container-local / baseScale
			const canvasX = textInputPosition.x / baseScaleX;
			const canvasY = textInputPosition.y / baseScaleY;
			
			const newComponent = {
				id: nextId++,
				type: 'text',
				x: canvasX,
				y: canvasY,
				width: maxWidth,
				height: height,
				text: textInput,
				color: textInputStyle.color,
				fontSize: textInputStyle.fontSize,
				fontFamily: textInputStyle.fontFamily
			};
			
			// Add component first
			components = [...components, newComponent];
			selectedComponent = newComponent;
			
			// Now redraw - if canvas resizes, component coordinates are already in canvas space so they'll be correct
			textInput = '';
			textInputVisible = false;
			activeTool = null;
			redrawCanvas();
			return; // Return early to avoid duplicate redraw
		}
		
		textInput = '';
		textInputVisible = false;
		activeTool = null;
		redrawCanvas();
	}
	
	function handleDelete() {
		if (selectedComponent) {
			const index = components.indexOf(selectedComponent);
			if (index > -1) {
				components = components.filter(c => c !== selectedComponent);
				selectedComponent = null;
				redrawCanvas();
			}
		}
	}
	
	function handlePreview() {
		if (!canvas) return;
		
		// Export canvas as base64 image
		const dataUrl = canvas.toDataURL('image/png');
		dispatch('preview', { image: dataUrl });
	}
	
	function handleSave() {
		if (!canvas) return;
		
		// Export canvas as base64 image
		const dataUrl = canvas.toDataURL('image/png');
		dispatch('save', { image: dataUrl });
		open = false;
	}
	
	function handleCancel() {
		dispatch('cancel');
		open = false;
	}
	
	// Handle keyboard shortcuts
	function handleKeyDown(event) {
		if (event.key === 'Delete' || event.key === 'Backspace') {
			if (selectedComponent && !textInputVisible) {
				handleDelete();
			}
		} else if (event.key === 'Escape') {
			textInputVisible = false;
			selectedComponent = null;
			activeTool = null;
			redrawCanvas();
		}
	}
	
	onMount(() => {
		initializeCanvas();
		updateCanvasTransform();
	});
</script>

<svelte:window on:keydown={handleKeyDown} />

{#if open}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-6xl mx-4 max-h-[90vh] flex flex-col">
			<!-- Header -->
			<PhotoEditorHeader onClose={handleCancel} />
			
			<!-- Toolbar -->
			<PhotoEditorToolbar
				activeTool={activeTool}
				hasSelectedComponent={!!selectedComponent}
				onImageClick={handleImageButtonClick}
				onTextClick={handleTextButtonClick}
				onDeleteClick={handleDelete}
			/>
			
			<!-- Sub Toolbar (shows when component is selected) -->
			<PhotoEditorSubToolbar
				selectedComponent={selectedComponent}
				bind:showColorPicker
				on:updateSize={(e) => {
					if (selectedComponent) {
						selectedComponent.width = e.detail.width;
						selectedComponent.height = e.detail.height;
						redrawCanvas();
					}
				}}
				on:updateColor={(e) => {
					if (selectedComponent && selectedComponent.type === 'text') {
						// Update the color property - ensure it's a valid color string
						const newColor = e.detail.color || '#000000';
						// Find the component in the array and update it
						const index = components.indexOf(selectedComponent);
						if (index !== -1) {
							// Update the component's color directly (both references point to same object)
							components[index].color = newColor;
							selectedComponent.color = newColor;
							// Force immediate redraw canvas to show the color change
							redrawCanvas();
						}
					}
				}}
				on:updateFontSize={(e) => {
					if (selectedComponent && selectedComponent.type === 'text') {
						selectedComponent.fontSize = e.detail.fontSize;
						// Recalculate text dimensions based on new font size
						if (ctx && selectedComponent.text) {
							ctx.font = `${e.detail.fontSize}px ${selectedComponent.fontFamily || 'Arial'}`;
							const lines = selectedComponent.text.split('\n');
							const widths = lines.map(line => ctx.measureText(line).width);
							const maxWidth = widths.length > 0 ? Math.max(...widths) : e.detail.fontSize * 2;
							const height = lines.length > 0 ? lines.length * e.detail.fontSize * 1.2 : e.detail.fontSize * 1.2;
							selectedComponent.width = maxWidth;
							selectedComponent.height = height;
						}
						redrawCanvas();
					}
				}}
				on:toggleColorPicker={(e) => {
					showColorPicker = e.detail.show;
				}}
			/>
			
			<!-- Canvas Container -->
			<div class="flex-1 overflow-auto p-4 bg-gray-100 dark:bg-gray-900 relative" on:wheel={handleCanvasWheel}>
				<div bind:this={canvasContainer} class="w-full bg-white dark:bg-gray-800 shadow-lg relative">
					<canvas
						bind:this={canvas}
						class="cursor-move w-full h-auto"
						on:click={handleCanvasClick}
						on:dblclick={handleCanvasDoubleClick}
						on:mousedown={handleCanvasMouseDown}
						on:mousemove={handleCanvasMouseMove}
						on:mouseup={handleCanvasMouseUp}
						on:mouseleave={(e) => {
							// Update cursor when leaving canvas, but don't stop drag
							if (!isDragging && canvas) {
								canvas.style.cursor = 'default';
							}
						}}
					></canvas>
					
					<!-- Text Input Overlay -->
					<PhotoEditorTextInput
						visible={textInputVisible}
						position={textInputPosition}
						size={textInputSize}
						style={textInputStyle}
						bind:value={textInput}
						zoomLevel={zoomLevel}
						canvas={canvas}
						ctx={ctx}
						editingTextComponent={editingTextComponent}
						onInput={(newSize) => {
							textInputSize = newSize;
						}}
						on:input={(e) => {
							textInput = e.detail;
						}}
						onKeyDown={(e) => {
							if (e.key === 'Enter' && !e.shiftKey) {
								e.preventDefault();
								handleTextSubmit();
							} else if (e.key === 'Escape') {
								textInputVisible = false;
								textInput = '';
								activeTool = null;
							}
						}}
						onBlur={() => {
							// Auto-submit when textarea loses focus if text has content
							if (textInput.trim()) {
								handleTextSubmit();
							} else {
								// If editing and text becomes empty, remove the component
								if (editingTextComponent) {
									components = components.filter(c => c !== editingTextComponent);
									selectedComponent = null;
								}
								textInputVisible = false;
								textInput = '';
								activeTool = null;
								editingTextComponent = null;
								redrawCanvas();
							}
						}}
					/>
				</div>
			</div>
			
			<!-- Footer Actions -->
			<PhotoEditorFooter
				onCancel={handleCancel}
				onPreview={handlePreview}
				onSave={handleSave}
			/>
		</div>
	</div>
{/if}

<input
	bind:this={imageInput}
	type="file"
	accept="image/*"
	class="hidden"
	on:change={handleImageUpload}
/>
