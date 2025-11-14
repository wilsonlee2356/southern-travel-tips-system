<script>
	export let filteredModels = [];
	export let selectedModel = null;
	export let id = 'ai-model-select';
	export let label = 'AI Model';
	export let placeholder = 'Select a model...';
	export let disabled = false;
	export let classNames = '';
	export let onModelChange = null; // Optional callback for custom change handling

	// Support both formats: {id, name} or {value, label}
	$: normalizedModels = filteredModels.map((model) => {
		if (model.value && model.label) {
			// Format: {value, label} (from FlightResultsTable)
			return {
				id: model.value,
				name: model.label,
				original: model
			};
		} else {
			// Format: {id, name} (from auto-flight-search)
			return {
				id: model.id,
				name: model.name || model.id,
				original: model
			};
		}
	});

	$: currentValue = (() => {
		if (!selectedModel) return '';
		if (typeof selectedModel === 'string') {
			return selectedModel;
		}
		// Try to find matching model
		const found = normalizedModels.find((m) => {
			return m.original === selectedModel || m.id === `model:${selectedModel.id}` || m.id === selectedModel.id;
		});
		return found?.id || '';
	})();

	const handleChange = (event) => {
		const selectedValue = event.target.value;
		if (onModelChange) {
			onModelChange(event);
		} else {
			// Default behavior: set selectedModel to the original model object or value
			if (selectedValue) {
				const selected = normalizedModels.find((m) => m.id === selectedValue);
				selectedModel = selected?.original || selectedValue;
			} else {
				selectedModel = null;
			}
		}
	};
</script>

<div class="ai-model-select-container">
	<label for={id} class="ai-model-select-label">
		{label}
	</label>
	<div class="ai-model-select-wrapper">
		<select
			{id}
			value={currentValue}
			on:change={handleChange}
			class="ai-model-select {classNames}"
			{disabled}
		>
			<option value="">{placeholder}</option>
			{#each normalizedModels as model}
				<option value={model.id}>
					{model.name}
				</option>
			{/each}
		</select>
		<svg
			class="ai-model-select-arrow"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</div>
</div>

<style>
	.ai-model-select-container {
		display: flex;
		flex-direction: column;
		width: 100%;
	}

	.ai-model-select-label {
		display: block;
		font-size: 0.875rem;
		font-weight: 500;
		color: rgba(71, 85, 105, 0.9);
		margin-bottom: 0.5rem;
	}

	:global(.dark) .ai-model-select-label {
		color: rgba(226, 232, 240, 0.9);
	}

	.ai-model-select-wrapper {
		position: relative;
		width: 100%;
	}

	.ai-model-select {
		width: 100%;
		padding: 0.5rem 2.5rem 0.5rem 0.75rem;
		border: 1px solid rgba(148, 163, 184, 0.3);
		border-radius: 0.5rem;
		background: rgba(255, 255, 255, 0.9);
		color: #0f172a;
		font-size: 0.875rem;
		appearance: none;
		-webkit-appearance: none;
		-moz-appearance: none;
		cursor: pointer;
	}

	:global(.dark) .ai-model-select {
		background: rgba(15, 23, 42, 0.8);
		border-color: rgba(148, 163, 184, 0.4);
		color: #f8fafc;
	}

	.ai-model-select:focus {
		outline: none;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.5);
		border-color: rgba(59, 130, 246, 0.5);
	}

	.ai-model-select:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.ai-model-select-arrow {
		position: absolute;
		right: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		width: 1rem;
		height: 1rem;
		pointer-events: none;
		color: rgba(71, 85, 105, 0.8);
	}

	:global(.dark) .ai-model-select-arrow {
		color: rgba(226, 232, 240, 0.7);
	}
</style>

