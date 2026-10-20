import {describe,it,expect} from 'vitest';
import {validDate,monthGrid,moveMonth,addDays,zonedToday} from './dates';
describe('Planner civil date arithmetic',()=>{
 it.each([['2026-02',28],['2028-02',29],['2026-04',30],['2026-10',31]])('has correct days in %s',(m,n)=>{const g=monthGrid(m);expect(g.filter(d=>d.startsWith(m))).toHaveLength(n);expect(g.length%7).toBe(0);expect(new Date(g[0]+'T12:00:00Z').getUTCDay()).toBe(1);expect(new Date(g.at(-1)!+'T12:00:00Z').getUTCDay()).toBe(0);});
 it('matches the original October Monday-first alignment',()=>{const g=monthGrid('2026-10');expect(g[0]).toBe('2026-09-28');expect(g.at(-1)).toBe('2026-11-01');expect(g[17]).toBe('2026-10-15');});
 it('handles year boundaries and 4/5/6-row months',()=>{expect(moveMonth('2026-12',1)).toBe('2027-01');expect(moveMonth('2027-01',-1)).toBe('2026-12');expect(addDays('2028-03-01',-1)).toBe('2028-02-29');expect(monthGrid('2021-02')).toHaveLength(28);expect(monthGrid('2026-08')).toHaveLength(42);});
 it('rejects normalized invalid dates and invalid range',()=>{expect(validDate('2027-02-29')).toBe(false);expect(validDate('2028-02-29')).toBe(true);expect(validDate('2026-04-31')).toBe(false);expect(validDate('2028-13-01')).toBe(false);expect(validDate('1800-01-01')).toBe(false);expect(()=>monthGrid('bad')).toThrow();});
 it('derives today from selected timezone, not UTC or hardcoded sample',()=>{const d=new Date('2026-12-31T20:00:00Z');expect(zonedToday('Asia/Dhaka',d)).toBe('2027-01-01');expect(zonedToday('America/New_York',d)).toBe('2026-12-31');});
 it('never shifts civil event dates across DST transitions',()=>{expect(addDays('2026-03-08',1)).toBe('2026-03-09');expect(addDays('2026-11-01',1)).toBe('2026-11-02');});
 it('covers every month 1901–2100 without gaps or duplicate dates',()=>{for(let y=1901;y<=2100;y++)for(let m=1;m<=12;m++){const month=`${y}-${String(m).padStart(2,'0')}`,grid=monthGrid(month);expect(new Set(grid).size).toBe(grid.length);for(let i=1;i<grid.length;i++)expect(addDays(grid[i-1],1)).toBe(grid[i]);expect(grid.filter(x=>x.startsWith(month)).length).toBe(new Date(Date.UTC(y,m,0)).getUTCDate());}});
});
