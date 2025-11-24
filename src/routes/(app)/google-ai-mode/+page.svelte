<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { fetchGoogleAiModeResults } from '$lib/services/googleAiModeApi.js';

	const i18n = getContext('i18n');

	type FormState = {
		q: string;
		url: string;
		location: string;
		uule: string;
		hl: string;
		gl: string;
		engine: string;
		zero_retention: boolean;
	};

	type GoogleAiModePayload = {
		engine?: string;
		q?: string;
		url?: string;
		location?: string;
		uule?: string;
		hl?: string;
		gl?: string;
		api_key?: string;
		zero_retention?: boolean;
	};

	const initialFormState = (): FormState => ({
		q: '',
		url: '',
		location: '',
		uule: '',
		hl: '',
		gl: '',
		engine: 'google_ai_mode',
		zero_retention: false
	});

	let form = initialFormState();
	let loading = false;
	let errorMessage = '';
	let response: Record<string, unknown> | null = null;
	let controller: AbortController | null = null;

	const buildPayload = (): GoogleAiModePayload => {
		const payload: GoogleAiModePayload = {
			engine: form.engine?.trim() || 'google_ai_mode'
		};

		const optionalEntries: Array<[keyof FormState, string]> = [
			['q', form.q.trim()],
			['url', form.url.trim()],
			['location', form.location.trim()],
			['uule', form.uule.trim()],
			['hl', form.hl.trim()],
			['gl', form.gl.trim()]
		];

		for (const [key, value] of optionalEntries) {
			if (value) {
				payload[key] = value;
			}
		}

		if (form.zero_retention) {
			payload.zero_retention = true;
		}

		return payload;
	};

	const resetForm = () => {
		cancelRequest();
		form = initialFormState();
		response = null;
		errorMessage = '';
	};

	const handleSubmit = async (event: SubmitEvent) => {
		event.preventDefault();

		if (loading) {
			return;
		}

		if (!form.q.trim() && !form.url.trim()) {
			errorMessage = 'Provide a query or an image URL';
			return;
		}

		if (form.location.trim() && form.uule.trim()) {
			errorMessage = 'Location and UULE cannot be used together';
			return;
		}

		errorMessage = '';
		response = null;
		cancelRequest();

		controller = new AbortController();
		loading = true;

		try {
			const result = await fetchGoogleAiModeResults(
				buildPayload(),
				controller.signal
			);
			response = result;
		} catch (error) {
			if ((error as Error)?.name === 'AbortError') {
				errorMessage = 'Request cancelled';
			} else {
				errorMessage = (error as Error)?.message ?? String(error);
			}
		} finally {
			loading = false;
		}
	};

	const cancelRequest = () => {
		if (controller) {
			controller.abort();
			controller = null;
		}
	};

	onDestroy(cancelRequest);
</script>

<svelte:head>
	<title>Google AI Mode</title>
</svelte:head>

<div class="page">
	<header class="page-header">
		<div>
			<p class="kicker">SearchAPI.io · Google</p>
			<h1>{$i18n.t('Google AI Mode')}</h1>
			<p class="subtitle">
				Interact with Google's experimental AI search results through SearchAPI.io. Supply a text
				query, image URL, or both, and inspect the structured JSON response. Requests are authorized
				with the server-side GOOGLE_FLIGHTS_API_KEY, so no client API key is required.
			</p>
		</div>
	</header>

	<section class="card">
		<form class="form-grid" on:submit|preventDefault={handleSubmit}>
			<div class="form-control">
				<label for="engine">Engine</label>
				<input
					id="engine"
					placeholder="google_ai_mode"
					bind:value={form.engine}
					autocomplete="off"
				/>
				<small>Defaults to google_ai_mode. Override only if SearchAPI adds variants.</small>
			</div>

			<div class="form-control">
				<label for="query">Query *</label>
				<input
					id="query"
					placeholder="Best street food in Seoul"
					bind:value={form.q}
					autocomplete="off"
				/>
				<small>Required unless an image URL is provided.</small>
			</div>

			<div class="form-control">
				<label for="image-url">Image URL</label>
				<input
					id="image-url"
					type="url"
					placeholder="https://example.com/photo.png"
					bind:value={form.url}
					autocomplete="off"
				/>
				<small>Optional Lens-style lookup. Requires a public image URL.</small>
			</div>

			<div class="form-control">
				<label for="location">Location</label>
				<input
					id="location"
					placeholder="New York, United States"
					bind:value={form.location}
					autocomplete="off"
				/>
				<small>Canonical location string. Cannot be combined with UULE.</small>
			</div>

			<div class="form-control">
				<label for="uule">UULE</label>
				<input
					id="uule"
					placeholder="w+CAIQICI_..."
					bind:value={form.uule}
					autocomplete="off"
				/>
				<small>Advanced Google-encoded location. Mutually exclusive with Location.</small>
			</div>

			<div class="form-control">
				<label for="hl">Interface Language (hl)</label>
				<input id="hl" placeholder="en" bind:value={form.hl} autocomplete="off" />
			</div>

			<div class="form-control">
				<label for="gl">Geolocation Country (gl)</label>
				<input id="gl" placeholder="us" bind:value={form.gl} autocomplete="off" />
			</div>

			<div class="form-control checkbox-row">
				<label for="zero-retention">Zero Retention</label>
				<input
					id="zero-retention"
					type="checkbox"
					bind:checked={form.zero_retention}
				/>
				<small>Enterprise feature. Enables no-logging mode when supported.</small>
			</div>

			<div class="form-actions">
				<button type="submit" class="primary" disabled={loading}>
					{#if loading}
						<span class="spinner" aria-hidden="true" /> {$i18n.t('Loading')}...
					{:else}
						{$i18n.t('Submit')}
					{/if}
				</button>
				<button type="button" on:click={resetForm} disabled={loading}>
					{$i18n.t('Reset')}
				</button>
				<button type="button" class="ghost" on:click={cancelRequest} disabled={!loading}>
					{$i18n.t('Cancel')}
				</button>
			</div>
		</form>
	</section>

	{#if errorMessage}
		<section class="card error">
			<p>{errorMessage}</p>
		</section>
	{/if}

	<section class="card results">
		<div class="results-header">
			<h2>Response Preview</h2>
			<p>{response ? 'Latest response from SearchAPI.io' : 'Submit a query to see results.'}</p>
		</div>

		{#if response}
			<pre>{JSON.stringify(response, null, 2)}</pre>
		{:else}
			<div class="placeholder">
				<p>No response yet.</p>
			</div>
		{/if}
	</section>
</div>

<style>
	:global(body) {
		background: var(--color-gray-50, #f9fafb);
	}

	.page {
		padding: 2rem clamp(1rem, 4vw, 3rem) 3rem;
		max-width: 960px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.page-header h1 {
		font-size: clamp(1.8rem, 4vw, 2.4rem);
		margin-bottom: 0.5rem;
	}

	.kicker {
		font-size: 0.85rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--color-gray-500, #6b7280);
		margin-bottom: 0.25rem;
	}

	.subtitle {
		color: var(--color-gray-600, #4b5563);
		max-width: 60ch;
	}

	.card {
		background: var(--color-white, #fff);
		border: 1px solid rgba(15, 23, 42, 0.08);
		border-radius: 1rem;
		padding: 1.5rem;
		box-shadow: 0 8px 30px rgba(15, 23, 42, 0.08);
	}

	.card.error {
		border-color: rgba(239, 68, 68, 0.3);
		color: #b91c1c;
		background: #fef2f2;
	}

	.form-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem 1.25rem;
	}

	.form-control {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	label {
		font-weight: 600;
		color: var(--color-gray-800, #1f2937);
	}

	input[type='text'],
	input[type='password'],
	input[type='url'] {
		border: 1px solid rgba(15, 23, 42, 0.15);
		border-radius: 0.65rem;
		padding: 0.7rem 0.85rem;
		font-size: 0.95rem;
		background: var(--color-white, #fff);
		color: inherit;
	}

	input:focus {
		outline: 2px solid rgba(59, 130, 246, 0.35);
		outline-offset: 2px;
	}

	small {
		font-size: 0.78rem;
		color: var(--color-gray-500, #6b7280);
	}

	.checkbox-row {
		flex-direction: row;
		align-items: center;
		gap: 0.5rem;
	}

	.form-actions {
		grid-column: 1 / -1;
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}

	button {
		border-radius: 0.65rem;
		padding: 0.65rem 1.2rem;
		font-weight: 600;
		border: 1px solid transparent;
		cursor: pointer;
		background: #e5e7eb;
		color: #111827;
	}

	button.primary {
		background: linear-gradient(135deg, #1e3a8a, #2563eb);
		color: white;
		box-shadow: 0 10px 20px rgba(37, 99, 235, 0.25);
	}

	button.ghost {
		background: transparent;
		border-color: rgba(15, 23, 42, 0.2);
	}

	button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.spinner {
		width: 1rem;
		height: 1rem;
		border-radius: 50%;
		border: 2px solid rgba(255, 255, 255, 0.6);
		border-top-color: white;
		margin-right: 0.4rem;
		display: inline-block;
		animation: spin 0.8s linear infinite;
	}

	.results-header {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		margin-bottom: 1rem;
	}

	pre {
		background: #0f172a;
		color: #e2e8f0;
		padding: 1rem;
		border-radius: 0.75rem;
		overflow: auto;
		max-height: 480px;
		font-size: 0.85rem;
	}

	.placeholder {
		color: var(--color-gray-500, #6b7280);
		font-style: italic;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	@media (max-width: 640px) {
		.form-actions {
			flex-direction: column;
			align-items: stretch;
		}
	}
</style>

