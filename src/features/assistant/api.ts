import {ApiError} from '../auth/services/authApi';
export type Summary={title:string;period:{start:string;end:string;label:string};income_minor:number;expenses_minor:number;net_minor:number;savings_rate:number|null};
export type ActionOperation={operation:'budget.create'|'budget.update'|'goal.create'|'goal.update'|'transaction.create'|'transaction.update';record_id?:string|null;data:Record<string,string|number|null>};
export type ActionPlan={operations:ActionOperation[];expected_budget_total_minor?:number|null};
export type ActionItem={operation:ActionOperation['operation'];before:Record<string,string|number|null>|null;record:Record<string,string|number|null>};
export type ActionPreview={items:ActionItem[];budget_total_minor:number;atomic:boolean;saved_at?:string};
export type Proposal={id:string;conversation_id:string;request_id:string;version:number;status:'pending'|'expired'|'cancelled'|'executed';created_at:string;updated_at:string;expires_at:string;plan:ActionPlan;preview:ActionPreview;result:ActionPreview|null};
export type ActionOptions={wallets:{id:string;name:string}[];categories:{kind:string;name:string}[];budget_categories:string[];goal_categories:string[]};
export type Message={id:string;role:'user'|'assistant';content:string;created_at:string;request_id:string;summary:Summary|null;proposal?:Proposal|null};
export type ChatRequest={id:string;content:string;status:'pending'|'failed'|'completed';error_code:string|null;error_message:string|null;created_at:string};
export type Conversation={id:string;title:string;updated_at:string};
export type History={items:(Conversation&{preview:string})[];has_more:boolean;next_offset:number};
export type Detail={conversation:Conversation;messages:Message[];request:ChatRequest|null;has_more:boolean;next_before:number|null};
export type SendResult={messages:Message[];request:ChatRequest};
export type Status={configured:boolean;connection_verified:boolean;message:string};
export class ChatError extends ApiError {constructor(message:string,status:number,public result?:SendResult,public code?:string){super(message,status);}}
const base=(import.meta.env.VITE_API_BASE_URL||'').replace(/\/$/,'');
export async function chatApi<T>(path:string,dataset:'live'|'demo',method='GET',body?:unknown,signal?:AbortSignal):Promise<T>{
 let response:Response;
 try{response=await fetch(`${base}/api/assistant${path}${path.includes('?')?'&':'?'}dataset=${dataset}`,{method,credentials:'include',headers:method==='GET'?undefined:{'Content-Type':'application/json','X-Fincept-Request':'1'},body:body===undefined?undefined:JSON.stringify(body),signal:signal?AbortSignal.any([signal,AbortSignal.timeout(40000)]):AbortSignal.timeout(40000)});}
 catch(e){if(signal?.aborted)throw e;throw new ChatError('Connection interrupted. Check your network and try again. The same request ID will be reused.',0);}
 let data;
 try{data=await response.json();}
 catch(e){if(signal?.aborted)throw e;throw new ChatError('Unable to read the assistant response. Please try again.',response.status);}
 if(signal?.aborted)throw new DOMException('Request aborted','AbortError');
 if(!response.ok)throw new ChatError(data.message||'Unable to load the assistant. Please try again.',response.status,data.request?{...data,messages:data.messages||[]}:undefined,data.code);
 return data as T;
}
export const questions=[
 {title:'Understand my spending',question:'Where did most of my money go this month?'},
 {title:'Review my budget',question:'Which of my budgets are close to their limits?'},
 {title:'Savings goals',question:'How much more do I need to save for my goals?'},
 {title:'Cash flow',question:'How much money did I have left this month?'},
];
/** Free-form financial prose cannot be reliably redacted with a currency regex (words, foreign notation).
 * Conservatively conceal it in privacy mode; stored messages and calculations are untouched. */
export function privateText(text:string,hidden:boolean){return hidden?'Message text hidden for monetary privacy.':text;}
export function mergeMessages(current:Message[],incoming:Message[]){const map=new Map(current.map(m=>[m.id,m]));for(const m of incoming)map.set(m.id,m);return Array.from(map.values());}
export function readableTime(value:string){return new Date(value).toLocaleString('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});}
