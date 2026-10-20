/** Date-only values are civil dates, never parsed as midnight UTC. UTC here is arithmetic only. */
export function validDate(value:string){if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;const d=new Date(value+'T12:00:00Z');return !Number.isNaN(+d)&&d.toISOString().slice(0,10)===value&&value>='1901-01-01'&&value<='2100-12-31';}
export function addDays(value:string,delta:number){const d=new Date(value+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+delta);return d.toISOString().slice(0,10);}
export function validMonth(value:string|null):value is string{return !!value&&validDate(value+'-01');}
export function moveMonth(month:string,delta:number){const d=new Date(month+'-01T12:00:00Z');d.setUTCMonth(d.getUTCMonth()+delta);return d.toISOString().slice(0,7);}
export function monthGrid(month:string){if(!validMonth(month))throw Error('Invalid month');const first=month+'-01';const weekday=(new Date(first+'T12:00:00Z').getUTCDay()+6)%7;const next=moveMonth(month,1)+'-01';const last=addDays(next,-1);const length=Math.ceil((weekday+Number(last.slice(-2)))/7)*7;return Array.from({length},(_,i)=>addDays(first,i-weekday));}
export function zonedToday(zone:string,instant=new Date()){const parts=new Intl.DateTimeFormat('en-US',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(instant);return ['year','month','day'].map(k=>parts.find(p=>p.type===k)?.value).join('-');}
export const browserZone=()=>Intl.DateTimeFormat().resolvedOptions().timeZone||'Asia/Dhaka';
export function dateLabel(value:string,full=false){return new Date(value+'T12:00:00Z').toLocaleDateString('en-GB',{timeZone:'UTC',...(full?{weekday:'long' as const,year:'numeric' as const}:{}),month:full?'long':'short',day:'numeric'});}
export function monthLabel(value:string){return new Date(value+'-01T12:00:00Z').toLocaleDateString('en-US',{timeZone:'UTC',month:'long',year:'numeric'});}
