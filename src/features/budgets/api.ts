import {ApiError} from '../auth/services/authApi';
import type {Dataset} from '../transactions/types';
export type Budget={id:string;name:string;category:string;limit_minor:number;spent_minor:number;remaining_minor:number;percentage:number|null;status:'On Track'|'Near Limit'|'Exceeded';at_risk:boolean;conflicted:boolean;start_date:string;end_date:string;reset_period:'weekly'|'monthly'|'custom';alert_threshold:50|75|90|100|null;notes:string;version:number};
export type Summary={limit_minor:number;spent_minor:number;remaining_minor:number;percentage:number|null;risk_count:number};
export type Collection={items:Budget[];total:number;filtered_count:number;summary:Summary;alerts:Budget[];ambiguous_count:number;categories:string[];period:{start:string;end:string}};
export type Details={budget:Budget;items:{id:string;title:string;description:string;occurred_at:string;amount_minor:number}[];total:number;page:number;limit:number;period:{start:string;end:string};ambiguous_count:number};
const base=(import.meta.env.VITE_API_BASE_URL||'').replace(/\/$/,'');
export async function budgetRequest<T>(path:string,dataset:Dataset,method='GET',body?:unknown,signal?:AbortSignal):Promise<T>{
 let response:Response;try{response=await fetch(`${base}/api/budgets${path}${path.includes('?')?'&':'?'}dataset=${dataset}`,{method,credentials:'include',headers:method==='GET'?undefined:{'Content-Type':'application/json','X-Fincept-Request':'1'},body:body===undefined?undefined:JSON.stringify(body),signal:signal?AbortSignal.any([signal,AbortSignal.timeout(15000)]):AbortSignal.timeout(15000)});}catch(e){if(signal?.aborted)throw e;throw new ApiError('Unable to reach Budgets. Check your connection and retry.',0);}
 const data=await response.json().catch(()=>({}));if(!response.ok)throw new ApiError(data.message||'Could not complete this budget request.',response.status,data.field_errors||{});return data;
}
export function periodEnd(start:string,period:Budget['reset_period']){const d=new Date(start+'T12:00:00');if(Number.isNaN(+d))return start;if(period==='weekly')d.setDate(d.getDate()+6);else if(period==='monthly')d.setMonth(d.getMonth()+1,0);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
export function monthLabel(month:string){return new Date(month+'-01T12:00:00').toLocaleDateString('en-GB',{month:'long',year:'numeric'});}
export function dateLabel(date:string){return new Date(date+'T12:00:00').toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'});}
export function categoryIcon(category:string){return /food|dining/i.test(category)?'food':/shopping/i.test(category)?'bag':/transport/i.test(category)?'car':/bill|utilit|housing/i.test(category)?'home':/entertain/i.test(category)?'film':/health/i.test(category)?'health':'budget';}
export function progress(percent:number|null,spent=0){return Math.max(0,Math.min(100,percent??(spent>0?100:0)));}
