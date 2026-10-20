import { useState, type KeyboardEvent } from 'react';
import { Money, useMoneyFormatter, usePreferences } from '../../components/layout/ApplicationPreferences';
import { categoryColor, chartScale, formatPercent, major } from './format';
import type { InsightsData, Share } from './types';

const PLOT_HEIGHT = 210; // Figma: three 70px gridline steps above the baseline.

export function CardHeading({ title, scope, children }: { title: string; scope: React.ReactNode; children?: React.ReactNode }) {
  return <header className="in-card-heading"><div><h2>{title}</h2><p>{scope}</p></div>{children}</header>;
}

/** Income vs Expenses grouped bars (Figma 2001:81316). HTML bars keep text crisp at every desktop width. */
export function IncomeExpenseChart({ data }: { data: InsightsData }) { const formatMoney = useMoneyFormatter();
  const { hidden } = usePreferences();
  const [active, setActive] = useState<number | null>(null);
  const { buckets, has_history, scope } = data.cash_flow;
  const { ceiling } = chartScale(Math.max(0, ...buckets.flatMap(b => [b.income_minor, b.expenses_minor])));
  const axis = [3, 2, 1, 0].map(n => (ceiling * n) / 3);
  const height = (minor: number) => (ceiling ? (minor / ceiling) * PLOT_HEIGHT : 0);
  const tip = active === null ? null : buckets[active];
  const amount = (minor: number) => (hidden ? 'amount hidden' : formatMoney(major(minor)));
  function key(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (e.key === 'Escape') { setActive(null); (e.currentTarget as HTMLButtonElement).blur(); }
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const next = Math.min(buckets.length - 1, Math.max(0, index + (e.key === 'ArrowRight' ? 1 : -1)));
      (e.currentTarget.parentElement?.children[next] as HTMLButtonElement | undefined)?.focus();
    }
  }
  return <article className="in-card in-chart-card" aria-label="Income vs Expenses">
    <CardHeading title="Income vs Expenses" scope={has_history ? scope : 'Selected range · Monthly recorded totals'} />
    <div className="in-legend" aria-hidden="true"><span><i className="income" />Income</span><span><i className="expenses" />Expenses</span><b>BDT</b></div>
    {!has_history ? <div className="in-chart-empty"><h3>No transaction history yet</h3><p>Income and expenses will appear when records are added.</p></div> :
      <div className="in-plot" onMouseLeave={() => setActive(null)}>
        <div className="in-grid" aria-hidden="true">{axis.map((value, i) => <div key={i} className="in-gridline" style={{ top: 12 + i * 70 }}><span>{hidden ? <>৳ ••••</> : formatMoney(major(value))}</span></div>)}</div>
        <div className="in-groups" role="group" aria-label={`Income and expenses by period. ${scope}`}>
          {buckets.map((b, i) => <button type="button" key={b.start} className={'in-group' + (b.selected ? ' selected' : '') + (active === i ? ' active' : '')}
            aria-label={`${b.full_label}${b.selected ? ', selected period' : ''}: income ${amount(b.income_minor)}, expenses ${amount(b.expenses_minor)}`}
            aria-describedby={active === i ? 'in-chart-tooltip' : undefined}
            onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onBlur={() => setActive(null)} onClick={() => setActive(i)} onKeyDown={e => key(e, i)}>
            <span className="in-bars" aria-hidden="true">
              <span className={'in-bar income' + (b.income_minor ? '' : ' zero')} style={{ height: Math.max(2, height(b.income_minor)) }} />
              <span className={'in-bar expenses' + (b.expenses_minor ? '' : ' zero')} style={{ height: Math.max(2, height(b.expenses_minor)) }} />
            </span>
            <span className="in-group-label" aria-hidden="true">{b.label}</span>
          </button>)}
        </div>
        {tip && active !== null && <div id="in-chart-tooltip" role="tooltip" className={'in-tooltip ' + (active >= buckets.length / 2 ? 'align-end' : 'align-start')}
          style={active >= buckets.length / 2 ? { right: `${((buckets.length - active - 1) / buckets.length) * 100}%` } : { left: `calc(46px + ${(active / buckets.length) * 100}% - ${(active / buckets.length) * 46}px)` }}>
          <strong>{tip.full_label}</strong>
          <span className="income">Income <Money value={major(tip.income_minor)} /></span>
          <span>Expenses <Money value={major(tip.expenses_minor)} /></span>
        </div>}
      </div>}
    <p className="in-card-footnote">Internal wallet transfers are excluded from both series.</p>
  </article>;
}

const CIRCUMFERENCE = 2 * Math.PI * 69;

/** Where Your Money Goes (Figma 2001:81372): real category totals; list amounts reconcile with the centre total. */
export function CategoryDonut({ data, onSelect }: { data: InsightsData; onSelect: (category: Share, color: string) => void }) {
  const [focus, setFocus] = useState<string | null>(null);
  const { hidden } = usePreferences();
  const { items, total_minor } = data.categories;
  let offset = 0;
  const colored = items.map((c, i) => ({ ...c, color: categoryColor(c.name, i) }));
  return <article className="in-card in-donut-card" aria-label="Where Your Money Goes">
    <CardHeading title="Where Your Money Goes" scope={`${data.range.label} · Categorized expenses`} />
    {!total_minor ? <div className="in-chart-empty in-donut-empty"><h3>No spending history</h3><p>Category spending appears after expenses are recorded.</p></div> : <div className="in-donut-body">
      <div className="in-donut">
        <svg viewBox="0 0 160 160" aria-hidden="true">
          <circle cx="80" cy="80" r="69" fill="none" stroke="#eeede8" strokeWidth="22" />
          {colored.map(c => {
            const length = (c.amount_minor / total_minor) * CIRCUMFERENCE;
            const start = offset; offset += length;
            const gap = colored.length > 1 ? Math.min(1.5, length / 3) : 0;
            return <circle key={c.name} className={'in-segment' + (focus === c.name ? ' focused' : '')} cx="80" cy="80" r="69" fill="none" stroke={c.color} strokeWidth={focus === c.name ? 26 : 22}
              strokeDasharray={`${Math.max(0, length - gap)} ${CIRCUMFERENCE - length + gap}`} strokeDashoffset={-start} transform="rotate(-90 80 80)"
              onMouseEnter={() => setFocus(c.name)} onMouseLeave={() => setFocus(null)} onClick={() => onSelect(c, c.color)} />;
          })}
        </svg>
        <div className="in-donut-total"><strong><Money value={major(total_minor)} /></strong><span>Total expenses</span></div>
      </div>
      <ul className="in-category-list" aria-label="Expense categories">
        {colored.map(c => <li key={c.name}><button type="button" className={focus === c.name ? 'focused' : ''} onMouseEnter={() => setFocus(c.name)} onMouseLeave={() => setFocus(null)} onFocus={() => setFocus(c.name)} onBlur={() => setFocus(null)} onClick={() => onSelect(c, c.color)} aria-haspopup="dialog">
          <i style={{ background: c.color }} aria-hidden="true" />
          <span className="in-category-name">{c.name}</span>
          <strong><Money value={major(c.amount_minor)} /></strong>
          <small>{hidden ? <span aria-label="Percentage hidden">••••</span> : c.percentage === null ? '—' : formatPercent(c.percentage)}</small>
        </button></li>)}
      </ul>
    </div>}
    <p className="in-card-footnote">Percentages are rounded independently.</p>
  </article>;
}
