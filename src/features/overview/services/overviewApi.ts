import { ApiError } from '../../auth/services/authApi';
const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
export function queryString(values: object) { return new URLSearchParams(Object.entries(values).filter(([, v]) => v !== undefined && v !== '').map(([k, v]) => [k, String(v)])).toString(); }
export async function overviewRequest<T>(path: string, signal?: AbortSignal, post = false): Promise<T> { let response: Response; try {
    response = await fetch(`${base}/api/overview/${path}`, { signal, credentials: 'include', method: post ? 'POST' : 'GET', headers: post ? { 'Content-Type': 'application/json', 'X-Fincept-Request': '1' } : undefined, body: post ? '{}' : undefined });
}
catch (e) {
    if (signal?.aborted)
        throw e;
    throw new ApiError('Unable to reach your financial data. Check your connection and retry.', 0);
} const data = await response.json().catch(() => ({})); if (!response.ok)
    throw new ApiError(data.message || (typeof data.detail === 'string' ? data.detail : 'Could not load financial data. Please retry.'), response.status); return data; }
