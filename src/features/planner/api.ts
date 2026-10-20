import {ApiError} from '../auth/services/authApi';
import type {Dataset} from '../transactions/types';
import type {Goal} from '../goals/api';
export const categories=['Personal','Financial','Bill Payment','Occasion Preparation','Other'] as const;
export const statuses=['To Do','In Progress','Completed','Cancelled'] as const;
export type Task={id:string;title:string;description:string;due_date:string;due_time:string|null;timezone:string;category:typeof categories[number];priority:'Low'|'Medium'|'High';status:typeof statuses[number];plan_id:string|null;version:number};
export type Plan=Goal & {occasion_type:string;custom_type:string;start_date:string;frequency:'Weekly'|'Monthly';planned_minor:number;days_remaining:number;weeks:number;months:number;weekly_minor:number|null;monthly_estimate_minor:number|null;plan_status:string};
export type Collection={items:Task[];plans:Plan[];today:string;timezone:string;month:string;range_start:string;range_end:string;total:number;summary:{upcoming_tasks:number;overdue_tasks:number;upcoming_occasions:number;target_minor:number;saved_minor:number;remaining_minor:number}};
const base=(import.meta.env.VITE_API_BASE_URL||'').replace(/\/$/,'');
export async function plannerRequest<T>(path:string,dataset:Dataset,method='GET',body?:unknown,signal?:AbortSignal):Promise<T>{let r:Response;try{r=await fetch(`${base}/api/planner${path}${path.includes('?')?'&':'?'}dataset=${dataset}`,{method,credentials:'include',headers:method==='GET'?undefined:{'Content-Type':'application/json','X-Fincept-Request':'1'},body:body===undefined?undefined:JSON.stringify(body),signal:signal?AbortSignal.any([signal,AbortSignal.timeout(15000)]):AbortSignal.timeout(15000)});}catch(e){if(signal?.aborted)throw e;throw new ApiError('Unable to reach Planner. Check your connection and retry.',0);}const data=await r.json().catch(()=>({}));if(!r.ok)throw new ApiError(data.message||'Could not complete this Planner request.',r.status,data.field_errors||{});return data;}
