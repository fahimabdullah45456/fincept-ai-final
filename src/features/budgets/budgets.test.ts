import {describe,it,expect} from 'vitest';
import {periodEnd,progress,categoryIcon,monthLabel,dateLabel} from './api';
describe('budget presentation helpers',()=>{
 it('handles leap months, cross-year weeks and explicit custom dates',()=>{expect(periodEnd('2024-02-01','monthly')).toBe('2024-02-29');expect(periodEnd('2026-12-29','weekly')).toBe('2027-01-04');expect(periodEnd('2026-10-19','custom')).toBe('2026-10-19');});
 it('clamps geometry without replacing the raw financial percentage',()=>{expect(progress(120)).toBe(100);expect(progress(0)).toBe(0);expect(progress(null,10)).toBe(100);expect(progress(null)).toBe(0);expect(progress(-1)).toBe(0);});
 it('uses the inspected category vectors and readable local calendar labels',()=>{expect(categoryIcon('Food & Dining')).toBe('food');expect(categoryIcon('Transportation')).toBe('car');expect(categoryIcon('Health')).toBe('health');expect(categoryIcon('Custom')).toBe('budget');expect(monthLabel('2026-10')).toBe('October 2026');expect(dateLabel('2026-10-01')).toContain('Oct');});
});
