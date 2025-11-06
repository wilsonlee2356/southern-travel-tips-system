import type { RequestHandler } from './$types';
import { error, json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export const GET: RequestHandler = async ({ url, fetch }) => {
    // Try multiple env var names for flexibility
    const apiKey = env.GOOGLE_FLIGHTS_API_KEY || env.SEARCHAPI_KEY || env.SERPAPI_API_KEY;
    
    if (!apiKey) {
        throw error(500, 'Server is not configured. Please set GOOGLE_FLIGHTS_API_KEY or SEARCHAPI_KEY in your .env file');
    }

    // Build query parameters by forwarding all client parameters
    const qp = new URLSearchParams();
    
    // Add engine parameter (required by SearchAPI)
    qp.append('engine', 'google_flights');
    
    // Add API key
    qp.append('api_key', apiKey);
    
    // Forward all client parameters
    for (const [key, value] of url.searchParams.entries()) {
        if (key !== 'api_key') { // Don't override the server's API key
            qp.append(key, value);
        }
    }

    // Use SearchAPI.io endpoint (supports comprehensive Google Flights parameters)
    const searchApiUrl = `https://www.searchapi.io/api/v1/search?${qp}`;
    console.log('Calling SearchAPI.io:', searchApiUrl.replace(apiKey, '***'));
    
    const res = await fetch(searchApiUrl, { 
        method: 'GET',
        headers: {
            'Accept': 'application/json'
        }
    });
    
    if (!res.ok) {
        let detail = await res.text();
        try {
            const js = JSON.parse(detail);
            detail = js?.error || js?.message || detail;
        } catch {}
        console.error('SearchAPI error:', detail);
        throw error(res.status, detail);
    }
    
    const data = await res.json();
    return json(data);
};


