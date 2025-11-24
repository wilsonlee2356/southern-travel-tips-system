import type { RequestHandler } from './$types';
import { error, json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const SEARCH_API_ENDPOINT = 'https://www.searchapi.io/api/v1/search';

export const GET: RequestHandler = async ({ url, fetch }) => {
	const apiKey = env.GOOGLE_FLIGHTS_API_KEY || env.SEARCHAPI_KEY || env.SERPAPI_API_KEY;

	if (!apiKey) {
		throw error(
			500,
			'Server is not configured. Please set GOOGLE_FLIGHTS_API_KEY or SEARCHAPI_KEY in your environment.'
		);
	}

	const qp = new URLSearchParams();
	qp.append('engine', url.searchParams.get('engine') || 'google_ai_mode');
	qp.append('api_key', apiKey);

	for (const [key, value] of url.searchParams.entries()) {
		if (key === 'api_key' || key === 'engine') {
			continue;
		}
		qp.append(key, value);
	}

	const requestUrl = `${SEARCH_API_ENDPOINT}?${qp.toString()}`;
	console.log('Calling SearchAPI.io (Google AI Mode):', requestUrl.replace(apiKey, '***'));

	const res = await fetch(requestUrl, {
		method: 'GET',
		headers: {
			Accept: 'application/json'
		}
	});

	if (!res.ok) {
		let detail = await res.text();
		try {
			const parsed = JSON.parse(detail);
			detail = parsed?.error || parsed?.message || detail;
		} catch {
			// Ignore JSON parse errors
		}
		console.error('SearchAPI Google AI Mode error:', detail);
		throw error(res.status, detail);
	}

	const data = await res.json();
	return json(data);
};


