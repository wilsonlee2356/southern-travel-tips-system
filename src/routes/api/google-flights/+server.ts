import type { RequestHandler } from './$types';
import { error, json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export const GET: RequestHandler = async ({ url, fetch }) => {
    const departure_id = url.searchParams.get('departure_id');
    const arrival_id = url.searchParams.get('arrival_id');
    const outbound_date = url.searchParams.get('outbound_date');
    const return_date = url.searchParams.get('return_date');
    const adults = url.searchParams.get('adults') || '1';
    const currency = url.searchParams.get('currency') || 'USD';

    // Try multiple env var names for flexibility (note: VITE_* vars are client-only, not available on server)
    const apiKey = env.GOOGLE_FLIGHTS_API_KEY || env.SERPAPI_API_KEY;
    
    if (!apiKey) {
        throw error(500, 'Server is not configured. Please set GOOGLE_FLIGHTS_API_KEY (without VITE_ prefix) in your .env file');
    }
    if (!departure_id || !arrival_id || !outbound_date) {
        throw error(400, 'Missing required parameters');
    }

    const qp = new URLSearchParams({
        engine: 'google_flights',
        api_key: apiKey,
        departure_id,
        arrival_id,
        outbound_date,
        adults,
        currency
    });
    if (return_date) qp.append('return_date', return_date);

    const serpUrl = `https://serpapi.com/search.json?${qp}`;
    const res = await fetch(serpUrl, { method: 'GET' });
    if (!res.ok) {
        let detail = await res.text();
        try {
            const js = JSON.parse(detail);
            detail = js?.error || js?.message || detail;
        } catch {}
        throw error(res.status, detail);
    }
    const data = await res.json();
    return json(data);
};


