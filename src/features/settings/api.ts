import {ApiError, type User} from '../auth/services/authApi';
export type NotificationPreferences = {budget_alerts:boolean;goal_updates:boolean;payment_reminders:boolean;product_updates:boolean};
export type FinancialPreferences = {number_grouping:boolean;decimal_style:'flexible'|'fixed'};
export type Preferences = {notifications:NotificationPreferences;financial:FinancialPreferences};
export type SettingsResource = {preferences:Preferences;version:number;notification_delivery:boolean;currency:string;capabilities:{restore:boolean;delete_account:boolean;clear_demo:boolean};integrations:{id:string;name:string;status:'not_configured'|'unavailable';description:string}[]};
export type Security = {active_sessions:number;current_expires_at:string|null};
export const defaultFinancial:FinancialPreferences = {number_grouping:true,decimal_style:'flexible'};
const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/,'');
export async function settingsRequest<T>(path='', method='GET', body?:unknown, signal?:AbortSignal):Promise<T> {
  let response:Response;
  try {
    response=await fetch(`${base}/api/settings${path}`, {method,credentials:'include',
      headers:method==='GET'?undefined:{'Content-Type':'application/json','X-Fincept-Request':'1'},
      body:body===undefined?undefined:JSON.stringify(body),
      signal:signal?AbortSignal.any([signal,AbortSignal.timeout(20000)]):AbortSignal.timeout(20000)});
  } catch(e) {
    if(signal?.aborted) throw e;
    throw new ApiError('Unable to reach Settings. Check your connection and try again.',0);
  }
  const result=await response.json().catch(()=>({}));
  if(!response.ok) throw new ApiError(response.status===401?'Your session has expired. Please sign in again.':result.message||'Could not complete this request.',response.status,result.field_errors||{});
  return result as T;
}
export function updateProfile(full_name:string) {return settingsRequest<{user:User}>('/profile','PATCH',{full_name});}
export async function downloadExport(format:'csv'|'json',scope:string) {
  let response:Response;
  try {response=await fetch(`${base}/api/settings/export?${new URLSearchParams({format,scope,dataset:'live'})}`,{credentials:'include',signal:AbortSignal.timeout(60000)});}
  catch {throw new ApiError('Export could not be downloaded. Check your connection and try again.',0);}
  if(!response.ok) {const data=await response.json().catch(()=>({}));throw new ApiError(data.message||'Export failed. Please try again.',response.status);}
  const blob=await response.blob();
  const url=URL.createObjectURL(blob), a=document.createElement('a');
  a.href=url;a.download=response.headers.get('Content-Disposition')?.match(/filename="([\w.-]+)"/)?.[1]||`fincept-export.${format==='csv'?'zip':'json'}`;
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
