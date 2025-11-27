// /**
//  * Minimal Grok (xAI) test client.
//  * Documentation: https://docs.x.ai/docs/guides/chat
//  */

// const XAI_CHAT_ENDPOINT = 'https://api.x.ai/v1/messages';
// const DEFAULT_MODEL = 'grok-3';

// /**
//  * Resolve the API key from either browser (Vite) or Node environments.
//  * @returns {string}
//  */
// function resolveXaiApiKey() {
// 	const env = typeof window === 'undefined' ? process?.env ?? {} : import.meta.env ?? {};
// 	return env.XAI_API_KEY || env.VITE_XAI_API_KEY || '';
// }

// /**
//  * Build a Grok compliant payload from a friendly options object.
//  * @param {Object} options
//  * @param {Array<{role: string, content: string}>} [options.messages]
//  * @param {string} [options.prompt] - Convenience helper; added as user message when `messages` missing.
//  * @param {string} [options.systemPrompt] - Convenience helper; added as system message when `messages` missing.
//  * @param {string} [options.model]
//  * @param {number} [options.temperature]
//  * @param {boolean} [options.stream]
//  * @returns {Object}
//  */
// export function buildGrokPayload(options = {}) {
// 	const {
// 		messages,
// 		prompt = 'Say hello to confirm connectivity.',
// 		systemPrompt = 'You are Grok, helping verify API connectivity.',
// 		model = DEFAULT_MODEL,
// 		temperature = 0.7,
// 		stream = false,
// 		max_tokens: maxTokens = 512,
// 		...rest
// 	} = options;

// 	const finalMessages =
// 		Array.isArray(messages) && messages.length > 0
// 			? messages
// 			: [
// 					{
// 						role: 'user',
// 						content: systemPrompt ? `${systemPrompt}\n\n${prompt}` : prompt
// 					}
// 				];

// 	return {
// 		model,
// 		messages: finalMessages,
// 		stream,
// 		max_tokens: maxTokens,
// 		temperature,
// 		...rest
// 	};
// }

// /**
//  * Execute a Grok chat completion request.
//  * @param {Object} options - Same as buildGrokPayload, plus Fetch options.
//  * @param {AbortSignal} [options.signal]
//  * @returns {Promise<Object>} Raw JSON response from xAI.
//  */
// export async function callGrokApi(options = {}) {
// 	const apiKey = resolveXaiApiKey();
// 	if (!apiKey) {
// 		throw new Error('Missing xAI API key. Set XAI_API_KEY or VITE_XAI_API_KEY.');
// 	}

// 	const { signal, ...payloadOptions } = options;
// 	const payload = buildGrokPayload(payloadOptions);

// 	const response = await fetch(XAI_CHAT_ENDPOINT, {
// 		method: 'POST',
// 		headers: {
// 			'Content-Type': 'application/json',
// 			Authorization: `Bearer ${apiKey}`
// 		},
// 		body: JSON.stringify(payload),
// 		signal
// 	});

// 	if (!response.ok) {
// 		let errorPayload = await response.text();
// 		try {
// 			errorPayload = JSON.parse(errorPayload);
// 		} catch {
// 			// keep raw text
// 		}
// 		throw new Error(`Grok request failed (${response.status}): ${JSON.stringify(errorPayload)}`);
// 	}

// 	return response.json();
// }

// /**
//  * Convenience helper to run a quick connectivity test and return the assistant text.
//  * @param {string} prompt
//  * @returns {Promise<string>} Assistant text or empty string.
//  */
// function collectContentText(content) {
// 	if (!content) {
// 		return '';
// 	}

// 	if (typeof content === 'string') {
// 		return content;
// 	}

// 	if (Array.isArray(content)) {
// 		return content
// 			.map((chunk) => {
// 				if (typeof chunk === 'string') {
// 					return chunk;
// 				}
// 				if (chunk?.text) {
// 					return chunk.text;
// 				}
// 				if (chunk?.value) {
// 					return chunk.value;
// 				}
// 				return '';
// 			})
// 			.filter(Boolean)
// 			.join(' ')
// 			.trim();
// 	}

// 	if (typeof content === 'object') {
// 		return content.text || content.value || '';
// 	}

// 	return '';
// }

// function extractAssistantText(result) {
// 	if (!result || typeof result !== 'object') {
// 		return '';
// 	}

// 	if (Array.isArray(result.messages)) {
// 		const assistantMessage = result.messages.find((message) => message.role === 'assistant');
// 		const text = collectContentText(assistantMessage?.content);
// 		if (text) {
// 			return text;
// 		}
// 	}

// 	if (Array.isArray(result.output)) {
// 		const text = collectContentText(result.output);
// 		if (text) {
// 			return text;
// 		}
// 	}

// 	if (Array.isArray(result.choices)) {
// 		for (const choice of result.choices) {
// 			const text =
// 				collectContentText(choice?.message?.content) ||
// 				collectContentText(choice?.delta?.content);
// 			if (text) {
// 				return text;
// 			}
// 		}
// 	}

// 	return collectContentText(result.content);
// }

// export async function runGrokConnectivityTest(prompt = 'Reply with a short hello message.') {
// 	const result = await callGrokApi({ prompt, stream: false, max_tokens: 512 });
// 	return extractAssistantText(result);
// }

// export default {
// 	callGrokApi,
// 	buildGrokPayload,
// 	runGrokConnectivityTest
// };

