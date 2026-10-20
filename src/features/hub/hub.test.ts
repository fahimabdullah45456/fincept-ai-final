import {describe,it,expect} from 'vitest';
import {conversion,currencyAmount,type Rates} from './api';
import {minor} from '../debt/api';
const data:Rates={base:'USD',rates:{USD:1,BDT:120,JPY:150},as_of:'2026-10-20T00:00:00Z',fetched_at:'2026-10-20T01:00:00Z',source:'Fixture',source_url:'https://example.com',status:'cached'};
describe('currency conversion and integer money',()=>{
 it('uses genuine supplied rates and base identity only',()=>{expect(conversion('2.50','USD','BDT',data)).toBe(300);expect(conversion('3','USD','USD')).toBe(3);expect(conversion('3','BDT','USD',data)).toBeNull();});
 it.each(['-1','NaN','Infinity','1e3','','1.1234567','1000000000001'])('rejects invalid amount %s',n=>expect(conversion(n,'USD','BDT',data)).toBeNull());
 it('supports zero without division and handles missing data',()=>{expect(conversion('0','USD','BDT',data)).toBe(0);expect(conversion('5','USD','CAD',data)).toBeNull();expect(conversion('5','USD','BDT')).toBeNull();});
 it('uses JPY zero decimal minor units',()=>{expect(currencyAmount(123.5,'JPY')).toBe('¥124');expect(currencyAmount(123.5,'USD')).toBe('$123.50');});
 it('never parses money with binary fractional multiplication',()=>{expect(minor('0.29')).toBe(29);expect(minor('123456.01')).toBe(12345601);expect(()=>minor('1.001')).toThrow();expect(()=>minor('-1')).toThrow();});
});
