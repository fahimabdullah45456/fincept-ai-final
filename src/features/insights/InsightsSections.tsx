import { Link } from 'react-router-dom';
import { Money, usePreferences } from '../../components/layout/ApplicationPreferences';
import { Icon } from '../../components/ui/Icon';
import { CardHeading } from './InsightsCharts';
import { comparisonText, formatPercent, major, shortDate, SOURCE_COLORS } from './format';
import type { InsightsData } from './types';

function Percent({ value }: { value: number | null }) {
  const { hidden } = usePreferences();
  return <>{hidden ? <span aria-label="Percentage hidden">••••</span> : value === null ? '—' : formatPercent(value)}</>;
}
export function SummaryCards({ data }: { data: InsightsData }) {
  const { hidden } = usePreferences();
  const s = data.summary;
  const income = comparisonText('income', s.comparison), expenses = comparisonText('expenses', s.comparison);
  return <section className="in-summary" aria-label="Financial summary">
    {[
      { title: 'Total Income', icon: 'up', className: 'peach', value: <Money value={major(s.income_minor)} />, caption: hidden ? 'Recorded income in selected range' : income.text },
      { title: 'Total Expenses', icon: 'budget', className: '', value: <Money value={major(s.expenses_minor)} />, caption: hidden ? 'Recorded expenses in selected range' : expenses.text },
      { title: 'Net Cash Flow', icon: 'wallet', className: s.net_minor < 0 ? 'net negative' : 'net', value: <Money signed value={major(s.net_minor)} />, caption: 'Income minus expenses' },
      { title: 'Savings Rate', icon: 'budget', className: '', value: <Percent value={s.savings_rate} />, caption: s.savings_rate === null ? 'No income to calculate a rate' : 'Of your total income' },
    ].map(c => <article key={c.title} className={`in-card in-summary-card ${c.className}`}><div className="in-summary-top"><span className="in-icon"><Icon collection="insights" name={c.icon} /></span><h2>{c.title}</h2></div><strong className="in-summary-value">{c.value}</strong><p>{c.caption}</p></article>)}
  </section>;
}
export function SpendingTrends({ data }: { data: InsightsData }) {
  const t = data.trends;
  return <section className="in-section" aria-labelledby="in-trends"><h2 id="in-trends">Spending Trends</h2><div className="in-three">
    <article className="in-card in-trend"><h3><span className="in-trend-icon"><Icon collection="insights" name="home" /></span>Largest Spending Category</h3><strong>{t.largest_category ? <Money value={major(t.largest_category.amount_minor)} /> : 'No spending recorded'}</strong>{t.largest_category && <span className="in-trend-aside">{t.largest_category.name}</span>}<p>{t.largest_category ? 'Your largest expense category in this range.' : 'Categories appear after expenses are recorded.'}</p></article>
    <article className="in-card in-trend"><h3><span className="in-trend-icon"><Icon collection="insights" name="bag" /></span>Shopping Spending</h3><strong><Money value={major(t.shopping_minor)} /></strong><span className="in-trend-aside">Review your purchases</span><p>See whether recent purchases align with your budget.</p></article>
    <article className="in-card in-trend"><h3><span className="in-trend-icon"><Icon collection="insights" name="up" /></span>{data.range.single_month ? 'Monthly Cash Flow' : 'Period Cash Flow'}</h3><strong className={t.net_minor >= 0 ? 'in-positive' : 'in-negative'}><Money signed value={major(t.net_minor)} /></strong><span className="in-trend-aside">Income minus expenses</span><p>{!data.record_count ? 'No income or expense records in this range.' : t.net_minor > 0 ? 'Recorded income exceeded expenses in this range.' : t.net_minor < 0 ? 'Recorded expenses exceeded income in this range.' : 'Recorded income and expenses were equal in this range.'}</p></article>
  </div></section>;
}
export function IncomeSources({ data }: { data: InsightsData }) {
  return <article className="in-card in-sources"><CardHeading title="Income Sources" scope={<>{data.range.label} · <Money value={major(data.income_sources.total_minor)} /> recorded income</>} />
    {!data.income_sources.items.length ? <div className="in-empty"><h3>No income records</h3><p>Add income records to see where your money comes from.</p></div> : <div className="in-source-list">{data.income_sources.items.map((s, i) => <div key={s.name}><div className="in-source-label"><strong>{s.name}</strong><span><Money value={major(s.amount_minor)} /> · <Percent value={s.percentage} /></span></div><div className="in-track" aria-hidden="true"><i style={{ width: `${Math.min(100, s.percentage ?? 0)}%`, background: SOURCE_COLORS[i % SOURCE_COLORS.length] }} /></div></div>)}</div>}
  </article>;
}
export function SavingsProgress({ data }: { data: InsightsData }) {
  const s = data.savings, query = data.dataset === 'demo' ? '?dataset=demo' : '';
  return <article className="in-card in-savings"><CardHeading title="Savings Progress" scope={`Current snapshot · ${shortDate(s.as_of)} · Not a period total`} />
    {!s.active_count ? <div className="in-empty"><h3>No active financial goals</h3><p>Create a goal to track savings progress.</p></div> : <><div className="in-savings-amount"><strong className="in-large"><Money value={major(s.saved_minor)} /></strong><span>of <Money value={major(s.target_minor)} /> target</span></div><div className="in-track in-track-large" aria-hidden="true"><i style={{ width: `${Math.max(0, Math.min(100, s.percentage ?? 0))}%` }} /></div><div className="in-progress-caption"><span><Money value={major(s.remaining_minor)} /> remaining</span><strong><Percent value={s.percentage} /> complete</strong></div><p className="in-encouragement">You’re making progress toward your financial goals.</p></>}
    <Link className="ov-button" to={'/financial-goals' + query}>View Financial Goals →</Link>
  </article>;
}
export function BudgetPerformance({ data }: { data: InsightsData }) {
  return <section className="in-section" aria-labelledby="in-budgets"><div className="in-section-heading"><h2 id="in-budgets">Budget Performance</h2><p>{data.range.label} spending within each budget period · Compared with full budget limits</p></div>
    {!data.budgets.count ? <article className="in-card in-empty in-no-budgets"><h3>No budgets created</h3><p>Create a budget to compare spending against a limit.</p><Link className="ov-button" to={'/budgets' + (data.dataset === 'demo' ? '?dataset=demo' : '')}>View Budgets</Link></article> : <><div className="in-three">{data.budgets.items.map(b => <article className="in-card in-budget" key={b.id}><h3>{b.name}</h3><p className="in-budget-scope">Selected-range spending</p><div className="in-budget-amount"><strong><Money value={major(b.spent_minor)} /></strong><span>of <Money value={major(b.limit_minor)} /> limit</span></div><div className={'in-track ' + (b.status === 'On Track' ? 'good' : b.status === 'Exceeded' ? 'bad' : '')} aria-hidden="true"><i style={{ width: `${Math.max(0, Math.min(100, b.percentage ?? 0))}%` }} /></div><div className="in-budget-meta"><span><Percent value={b.percentage} /> used</span><span className={'in-budget-badge ' + (b.status === 'On Track' ? 'good' : b.status === 'Exceeded' ? 'bad' : 'near')}>{b.status}</span></div><p><Money value={major(Math.abs(b.remaining_minor))} /> {b.remaining_minor < 0 ? 'over limit' : 'remaining'}</p><small>{shortDate(b.start_date)}–{shortDate(b.end_date)}{b.conflicted ? ' · Overlapping category budgets' : ''}</small></article>)}</div>{data.budgets.count > 3 && <p className="in-note">Showing 3 of {data.budgets.count} budgets. <Link to={'/budgets' + (data.dataset === 'demo' ? '?dataset=demo' : '')}>View all budgets →</Link></p>}{data.budgets.ambiguous_count > 0 && <p className="in-note">Some category budgets overlap. Ambiguous expenses are excluded from budget spending; review the overlapping plans.</p>}</>}
  </section>;
}
export function AiInsights() {
  return <section className="in-section"><div className="in-section-heading in-ai-heading"><div><h2>AI Financial Insights</h2><p>Personalized observations based on your financial activity.</p></div><span>AI PROVIDER NOT CONFIGURED</span></div><article className="in-card in-ai-unavailable"><span className="in-ai-icon"><Icon collection="insights" name="ai-sparkle" size={26} /></span><h3>AI insights are not available yet</h3><p>No AI provider is connected. Your transaction analytics above are calculated from recorded data, not generated by AI.</p></article></section>;
}
export function LoadingState() {
  return <div className="in-loading" role="status" aria-label="Loading financial data"><div className="in-summary">{[0, 1, 2, 3].map(i => <div className="in-card in-skeleton" key={i}><i /><i /><i /></div>)}</div><div className="in-primary">{[0, 1].map(i => <div className="in-card in-skeleton tall" key={i}><i /><i /><i /></div>)}</div><p>Loading financial data…</p></div>;
}
export function FailedState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <section className="in-card in-failed" role="alert"><h2>Unable to load insights</h2><p>Your records are unchanged. Check your connection and try again.</p><p className="in-error-detail">{message}</p><button className="ov-button orange" onClick={onRetry}>Try again</button></section>;
}
