import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { ApplicationPreferences, usePreferences } from '../../components/layout/ApplicationPreferences';
import { CategoryDonut, IncomeExpenseChart } from './InsightsCharts';
import type { InsightsData } from './types';
const data = {
  range: { label: 'October 2026' },
  cash_flow: { has_history: true, scope: 'Selected period highlighted', buckets: [
    { start: '2026-09-01', label: 'Sep', full_label: 'September 2026', income_minor: 4000000, expenses_minor: 3000000, selected: false },
    { start: '2026-10-01', label: 'Oct', full_label: 'October 2026', income_minor: 5200000, expenses_minor: 3820000, selected: true },
  ] },
  categories: { total_minor: 3820000, items: [{ name: 'Shopping', amount_minor: 3820000, percentage: 100, count: 2 }] },
} as InsightsData;
function Charts({ onSelect = () => {} }: { onSelect?: () => void }) {
  const { toggle } = usePreferences();
  return <><button onClick={toggle}>Toggle privacy</button><IncomeExpenseChart data={data} /><CategoryDonut data={data} onSelect={onSelect} /></>;
}
beforeEach(() => localStorage.clear());
describe('Insights accessible charts', () => {
  it('provides focus tooltips and removes them on Escape', () => {
    render(<ApplicationPreferences><Charts /></ApplicationPreferences>);
    const bar = screen.getByRole('button', { name: /October 2026, selected period: income ৳52,000/ });
    fireEvent.focus(bar); expect(screen.getByRole('tooltip')).toHaveTextContent('Income ৳52,000');
    fireEvent.keyDown(bar, { key: 'Escape' }); expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });
  it('masks monetary text and aria labels immediately while a tooltip is open', () => {
    render(<ApplicationPreferences><Charts /></ApplicationPreferences>);
    fireEvent.focus(screen.getByRole('button', { name: /October 2026, selected period/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Toggle privacy' }));
    expect(screen.getByRole('tooltip')).not.toHaveTextContent('52,000');
    expect(screen.getByRole('button', { name: /October 2026, selected period/ })).toHaveAttribute('aria-label', 'October 2026, selected period: income amount hidden, expenses amount hidden');
    expect(document.body.textContent).not.toMatch(/52,000|38,200/);
  });
  it('opens category drill-down from a native keyboard-accessible button', () => {
    const select = vi.fn(); render(<ApplicationPreferences><Charts onSelect={select} /></ApplicationPreferences>);
    const category = screen.getByRole('button', { name: /Shopping/ });
    expect(category).toHaveAttribute('aria-haspopup', 'dialog'); fireEvent.focus(category); expect(category).toHaveClass('focused');
    fireEvent.click(category); expect(select).toHaveBeenCalledWith(expect.objectContaining(data.categories.items[0]), '#e2b165');
  });
});
