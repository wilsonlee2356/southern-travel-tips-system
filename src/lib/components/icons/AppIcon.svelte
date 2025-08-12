<script lang="ts">
	export let className = '';
	export let strokeWidth = '2';
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	stroke-linecap="round"
	stroke-linejoin="round"
	class={className}
>
	<!-- Simple upward-pointing triangle -->
	<path d="M12 4l8 16H4z" fill="currentColor" />
</svg>
