import { ApiError } from '../auth/services/authApi';
import { rangeQuery } from './format';
import type { InsightsData, RangeQuery } from './types';

const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
function message(data: { message?: string; detail?: unknown }, fallback: string) {
  if (data.message) return data.message;
  if (typeof data.detail === 'string') return data.detail;
  if (data.detail && typeof data.detail === 'object' && 'message' in data.detail) return String((data.detail as { message: unknown }).message);
  return fallback;
}

export async function fetchInsights(query: RangeQuery, signal: AbortSignal): Promise<InsightsData> {
  let response: Response;
  try {
    response = await fetch(`${base}/api/insights?${rangeQuery(query)}`, { credentials: 'include', signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]) });
  } catch (e) {
    if (signal.aborted) throw e;
    throw new ApiError('Unable to reach your financial data. Check your connection and try again.', 0);
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(message(data, 'Could not load insights. Please try again.'), response.status);
  return data as InsightsData;
}

/** Downloads the server-generated CSV. Resolves only after the file has been received and handed to the browser. */
export async function downloadInsightsReport(query: RangeQuery, masked: boolean): Promise<{ filename: string; bytes: number }> {
  let response: Response;
  try {
    response = await fetch(`${base}/api/insights/export?${rangeQuery(query)}&masked=${masked}`, { credentials: 'include', signal: AbortSignal.timeout(30000) });
  } catch {
    throw new ApiError('Unable to prepare the report. Check your connection and try again.', 0);
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(message(data, 'Could not prepare the report. Please try again.'), response.status);
  }
  const blob = await response.blob();
  if (!blob.size) throw new ApiError('The report was empty. Please try again.', 0);
  const filename = /filename="([^"]+)"/.exec(response.headers.get('Content-Disposition') ?? '')?.[1] ?? 'fincept-insights.csv';
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return { filename, bytes: blob.size };
}
