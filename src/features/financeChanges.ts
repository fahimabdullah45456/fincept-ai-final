/** Invalidation signals contain no financial values. Routes still fetch canonical server data. */
import {useEffect,useState} from 'react';
const event='fincept:finance-changed',key='fincept.finance.revision';
export function notifyFinanceChanged(){window.dispatchEvent(new Event(event));try{localStorage.setItem(key,crypto.randomUUID());}catch{/* Same-tab invalidation still works when storage is unavailable. */}}
export function useFinanceRevision(){const [revision,setRevision]=useState(0);useEffect(()=>{const update=()=>setRevision(n=>n+1);const storage=(e:StorageEvent)=>{if(e.key===key)update();};window.addEventListener(event,update);window.addEventListener('storage',storage);return()=>{window.removeEventListener(event,update);window.removeEventListener('storage',storage);};},[]);return revision;}
