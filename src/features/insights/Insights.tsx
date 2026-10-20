import {useFinanceRevision} from '../financeChanges';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { ApiError } from '../auth/services/authApi';
import { Icon } from '../../components/ui/Icon';
import { fetchInsights } from './api';
import { isPeriod, rangeQuery, validateCustomRange } from './format';
import { CategoryDonut, IncomeExpenseChart } from './InsightsCharts';
import { AiInsights, BudgetPerformance, FailedState, IncomeSources, LoadingState, SavingsProgress, SpendingTrends, SummaryCards } from './InsightsSections';
import { CategoryDetailsDialog, CustomRangeDialog, DateRangeMenu, ExportDialog } from './InsightsDialogs';
import type { InsightsData, InsightsPeriod, RangeQuery, Share } from './types';
import '../../styles/insights.css';

export function Insights() { const financeRevision=useFinanceRevision();
  const [params, setParams] = useSearchParams(), { refresh } = useAuth();
  const signature = params.toString();
  const query = useMemo<RangeQuery>(() => { const p = new URLSearchParams(signature); const value = p.get('period'); return { period: isPeriod(value) ? value : 'this_month', dataset: p.get('dataset') === 'demo' ? 'demo' : 'live', start: p.get('start') || undefined, end: p.get('end') || undefined }; }, [signature]);
  const [data, setData] = useState<InsightsData | null>(null), [loading, setLoading] = useState(true), [error, setError] = useState(''), [revision, setRevision] = useState(0);
  const [panel, setPanel] = useState<'custom' | 'export' | ''>(''), [category, setCategory] = useState<{ value: Share; color: string } | null>(null), [notice, setNotice] = useState('');
  useEffect(() => { const c = new AbortController(); setLoading(true); setError(''); setPanel(''); setCategory(null);
    const validation = query.period === 'custom' ? validateCustomRange(query.start ?? '', query.end ?? '') : '';
    if (validation) { setData(null); setError(validation); setLoading(false); return () => c.abort(); }
    fetchInsights(query, c.signal).then(value => { if (!c.signal.aborted) setData(value); }).catch(e => { if (!c.signal.aborted) { setError((e as Error).message); if (e instanceof ApiError && e.status === 401) void refresh(); } }).finally(() => { if (!c.signal.aborted) setLoading(false); });
    return () => c.abort();
  }, [query, revision, refresh, financeRevision]);
  useEffect(() => { if (!notice) return; const timer = setTimeout(() => setNotice(''), 6500); return () => clearTimeout(timer); }, [notice]);
  function change(period: InsightsPeriod, start?: string, end?: string) { setNotice(''); setParams(rangeQuery({ period, dataset: query.dataset, start, end })); }
  return <div className="insights-page"><div className="in-page-heading"><div><h1>Insights</h1><p>Understand your money. Discover better financial habits.</p></div><div className="in-page-actions"><DateRangeMenu period={query.period} onChange={value => value === 'custom' ? setPanel('custom') : change(value)} /><button className="ov-button in-export-button" disabled={!data || loading || !!error} onClick={() => setPanel('export')}><Icon name="download" collection="transactions" />Export Report</button></div></div>
    {error ? <FailedState message={error} onRetry={() => setRevision(v => v + 1)} /> : !data ? <LoadingState /> : <div className={'in-content' + (loading ? ' is-updating' : '')} aria-busy={loading} inert={loading ? true : undefined}>
      {data.dataset === 'demo' && <p className="in-demo-note">Sample workspace · Illustrative records, not your personal finances.</p>}
      {!data.record_count && <div className="in-empty-banner" role="status">No income or expense transactions in {data.range.label}. Choose another range or add a transaction.</div>}
      <SummaryCards data={data} /><div className="in-primary"><IncomeExpenseChart data={data} /><CategoryDonut data={data} onSelect={(value, color) => setCategory({ value, color })} /></div><SpendingTrends data={data} /><div className="in-secondary"><IncomeSources data={data} /><SavingsProgress data={data} /></div><BudgetPerformance data={data} /><AiInsights /><footer className="in-page-footer">{data.dataset === 'demo' ? 'Illustrative BDT records' : 'Recorded BDT transactions'} · Internal wallet transfers are not income or expenses. Savings rate = net cash flow ÷ income.<br />Date ranges filter transaction analytics. Budget cards compare selected-range spending within their dated periods against full limits; goal progress is a current snapshot.</footer>
    </div>}
    {loading && data && !error && <p className="in-update-status" role="status">Updating financial data…</p>}
    {panel === 'custom' && <CustomRangeDialog start={query.start || data?.range.start || ''} end={query.end || data?.range.end || ''} onClose={() => setPanel('')} onApply={(start, end) => { setPanel(''); change('custom', start, end); }} />}
    {panel === 'export' && data && <ExportDialog data={data} query={query} onClose={() => setPanel('')} onSuccess={filename => { setPanel(''); setNotice(filename); }} />}
    {category && data && <CategoryDetailsDialog category={category.value} color={category.color} data={data} onClose={() => setCategory(null)} />}
    {notice && <div className="in-toast" role="status"><div><strong>✓ Report prepared</strong><p>{notice}</p></div><button aria-label="Dismiss report notification" onClick={() => setNotice('')}>×</button></div>}
  </div>;
}
