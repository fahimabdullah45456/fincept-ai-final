import {ApiError} from '../auth/services/authApi';
import type {Dataset} from '../transactions/types';
export type WalletKind='cash'|'bank'|'mobile'|'savings';
export type Wallet={id:string;name:string;kind:WalletKind;currency:string;archived:number;status:'active'|'inactive';balance_minor:number;opening_minor:number;opening_date:string;provider:string;identifier_last4:string;notes:string;version:number;created_at:string;updated_at:string;position:number};
export type Summary=Record<'total'|WalletKind,{balance_minor:number;count:number}>;
export type Collection={items:Wallet[];summary:Summary};
export type Activity={id:string;title:string;kind:string;occurred_at:string;delta_minor:number};
export type Details={wallet:Wallet;activity:Activity[]};
export const kindLabels:Record<WalletKind,string>={cash:'Cash',bank:'Bank Account',mobile:'Mobile Banking',savings:'Savings'};
export const kindIcons:Record<WalletKind,string>={cash:'cash',bank:'bank',mobile:'phone',savings:'target'};
const base=(import.meta.env.VITE_API_BASE_URL||'').replace(/\/$/,'');
export async function walletRequest<T>(path:string,dataset:Dataset,method='GET',body?:unknown,signal?:AbortSignal):Promise<T>{
 let r:Response;try{r=await fetch(`${base}/api/wallets${path}?dataset=${dataset}`,{method,credentials:'include',body:body===undefined?undefined:JSON.stringify(body),headers:method==='GET'?undefined:{'Content-Type':'application/json','X-Fincept-Request':'1'},signal:signal?AbortSignal.any([signal,AbortSignal.timeout(15000)]):AbortSignal.timeout(15000)});}catch(e){if(signal?.aborted)throw e;throw new ApiError('Unable to reach Wallets. Check your connection and retry.',0);}
 const data=await r.json().catch(()=>({}));if(!r.ok)throw new ApiError(data.message||'Could not complete this wallet request.',r.status,data.field_errors||{});return data;
}
export function selectWallets(items:Wallet[],archived:boolean,search:string,kind:string,sort:string){const q=search.trim().toLocaleLowerCase();return items.filter(w=>Boolean(w.archived)===archived&&(!kind||w.kind===kind)&&(!q||[w.name,w.provider,kindLabels[w.kind],w.identifier_last4].some(x=>x.toLocaleLowerCase().includes(q)))).sort((a,b)=>sort==='highest'?b.balance_minor-a.balance_minor||a.position-b.position:sort==='name'?a.name.localeCompare(b.name):a.position-b.position);}
export function readView():'grid'|'list'{try{return localStorage.getItem('fincept.wallets.view')==='list'?'list':'grid';}catch{return 'grid';}}
export function saveView(view:'grid'|'list'){try{localStorage.setItem('fincept.wallets.view',view);}catch{/* Non-sensitive UI preference only. */}}
