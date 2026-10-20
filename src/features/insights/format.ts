import type { Comparison, InsightsPeriod, RangeQuery } from './types';

export const PERIOD_OPTIONS: { value: InsightsPeriod; label: string }[] = [
  { value: 'this_month', label: 'This Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: 'last_3_months', label: 'Last 3 Months' },
  { value: 'this_year', label: 'This Year' },
  { value: 'custom', label: 'Custom Range' },
];
export const periodLabel = (period: InsightsPeriod) => PERIOD_OPTIONS.find(o => o.value === period)?.label ?? 'This Month';
export const isPeriod = (value: string | null): value is InsightsPeriod => PERIOD_OPTIONS.some(o => o.value === value);

/** Minor units (paisa) to the major-unit value expected by the shared Money component. */
export const major = (minor: number) => minor / 100;

/** One decimal at most, without a trailing “.0” (26.5%, 24%). */
export function formatPercent(value: number) {
  return `${value.toLocaleString('en-US', { maximumFractionDigits: 1 })}%`;
}

/** Real period comparison text. A missing previous value never yields a percentage. */
export function comparisonText(kind: 'income' | 'expenses', comparison: Comparison | null) {
  const noun = kind === 'income' ? 'income' : 'expenses';
  if (!comparison) return { text: `Recorded ${noun} in selected range`, direction: 'none' as const };
  const value = kind === 'income' ? comparison.income_change : comparison.expense_change;
  if (value === null) return { text: `No ${comparison.label} ${noun} to compare`, direction: 'none' as const };
  if (value === 0) return { text: `No change vs ${comparison.label}`, direction: 'none' as const };
  return value > 0
    ? { text: `↑ ${formatPercent(value)} higher vs ${comparison.label}`, direction: 'up' as const }
    : { text: `↓ ${formatPercent(Math.abs(value))} lower vs ${comparison.label}`, direction: 'down' as const };
}

/** Three equal gridline steps rounded to 1/2/2.5/5 × 10ⁿ (e.g. a ৳52,000 maximum → ৳20,000 steps). */
export function chartScale(maxMinor: number) {
  if (maxMinor <= 0) return { step: 0, ceiling: 0 };
  const raw = maxMinor / 3;
  const power = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(n => n * power).find(n => n >= raw) ?? 10 * power;
  return { step, ceiling: step * 3 };
}

const CATEGORY_COLORS: [RegExp, string][] = [
  [/^food/i, '#f9733b'],
  [/^transport/i, '#7ba68c'],
  [/^shopping/i, '#e2b165'],
  [/bills|utilit|housing|rent/i, '#596a7a'],
  [/^entertainment/i, '#a18bc4'],
  [/^health/i, '#cf8e9f'],
  [/^other$/i, '#b5b0a3'],
];
const FALLBACK = ['#8fb3c9', '#d3a27f', '#9aa66f', '#c79ac0', '#7f8581', '#e0c27a'];
/** Original Figma category palette; categories outside it receive stable distinct fallbacks. */
export function categoryColor(name: string, index: number) {
  return CATEGORY_COLORS.find(([pattern]) => pattern.test(name))?.[1] ?? FALLBACK[index % FALLBACK.length];
}
export const SOURCE_COLORS = ['#f9733b', '#e2b165', '#b5b0a3', '#7ba68c', '#596a7a', '#a18bc4'];

export function rangeQuery(query: RangeQuery) {
  const values: Record<string, string> = { period: query.period, dataset: query.dataset };
  if (query.period === 'custom' && query.start && query.end) { values.start = query.start; values.end = query.end; }
  return new URLSearchParams(values).toString();
}

const ISO = /^\d{4}-\d{2}-\d{2}$/;
function parse(value: string) {
  if (!ISO.test(value)) return null;
  const date = new Date(value + 'T12:00:00Z');
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value ? null : date;
}
/** Mirrors backend period_range validation for custom dates. */
export function validateCustomRange(start: string, end: string): string {
  if (!start || !end) return 'Choose both a start date and an end date.';
  const a = parse(start), b = parse(end);
  if (!a || !b) return 'Enter valid calendar dates.';
  if (a.getUTCFullYear() < 1901 || b.getUTCFullYear() > 2100) return 'Dates must fall between 1901 and 2100.';
  if (b < a) return 'The end date must be on or after the start date.';
  if ((b.getTime() - a.getTime()) / 86400000 > 731) return 'Choose a range of at most 732 days.';
  return '';
}

export function shortDate(value: string) {
  return new Date(value.slice(0, 10) + 'T12:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}
