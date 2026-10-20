import type { FieldErrors, SignInValues, SignUpValues } from '../validation';
export type User = {id:string;full_name:string;email:string};
export class ApiError extends Error {
  constructor(message:string, public status:number, public fieldErrors:FieldErrors={}) {super(message);this.name='ApiError';}
}
const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/,'');
async function request<T>(path:string, body?:unknown): Promise<T> {
  let response: Response;
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
  try {response=await fetch(`${base}/api${path}`, {method:body===undefined?'GET':'POST',credentials:'include',headers:{...(body===undefined?{}:{'Content-Type':'application/json','X-Fincept-Request':'1'})},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});}
  catch {throw new ApiError('Unable to reach the authentication service. Check your connection and try again.',0);}
  finally {clearTimeout(timeout);}
  if(response.status===204) return undefined as T;
  const data=await response.json().catch(()=>({}));
  if(!response.ok) throw new ApiError(data.message || 'Something went wrong. Please try again.',response.status,data.field_errors||{});
  return data as T;
}
export const authApi={
  me:()=>request<{user:User}>('/auth/me'),
  login:(v:SignInValues)=>request<{user:User}>('/auth/login',{...v,email:v.email.trim()}),
  register:(v:SignUpValues)=>request<{user:User}>('/auth/register',{...v,email:v.email.trim(),full_name:v.full_name.trim()}),
  logout:()=>request<void>('/auth/logout',{}),
};
