import {describe,it,expect} from 'vitest';
import {calculate,amountReducer,draft} from './calculator';
describe('safe amount calculator',()=>{
 it.each([['1000+250',125000],['800',80000],['0.1+0.2',30],['1.005',101],['(12+3)×2',3000],['500×10%',5000],['500+10%',50010],['1/8',13],['-1.005',-101],['2+3*4',1400]])('%s rounds decimal half-up', (expression,expected)=>expect(calculate(expression)).toBe(expected));
 it.each(['1/0','(2+3','2**3','alert(1)','1e3','Infinity','1;2','1..2','1+','9'.repeat(161),'('.repeat(30)+'1'+')'.repeat(30)])('rejects %s safely',s=>expect(()=>calculate(s)).toThrow());
 it('shares direct input, quick amounts and evaluation in one draft',()=>{let s=draft('1000+250');expect(s.status).toBe('pending');expect(s.amountMinor).toBeNull();s=amountReducer(s,{type:'quick',minor:10000});expect(s.error).toMatch(/Finish/);s=amountReducer(s,{type:'evaluate'});expect(s.amountMinor).toBe(125000);expect(s.status).toBe('ready');s=amountReducer(s,{type:'type',value:'800'});expect(s.amountMinor).toBe(80000);s=amountReducer(s,{type:'quick',minor:10000});expect(s.amountMinor).toBe(90000);});
});
