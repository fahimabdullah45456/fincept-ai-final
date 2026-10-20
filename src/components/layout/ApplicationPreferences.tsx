import {createContext,useCallback,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {settingsRequest,defaultFinancial,type FinancialPreferences,type Preferences,type SettingsResource} from '../../features/settings/api';
type ContextValue = {
  hidden:boolean;toggle:()=>void;privacyStorageError:string;periodLabel:string;setPeriodLabel:(label:string)=>void;
  settings:SettingsResource|null;settingsLoading:boolean;settingsError:string;savingSettings:boolean;
  reloadSettings:()=>Promise<void>;saveSettings:(preferences:Preferences)=>Promise<void>;
  formatAmount:(value:number)=>string;
};
const Context=createContext<ContextValue|null>(null);
/** Browser-local monetary privacy stays the sole global privacy source. Account display
 * preferences come from the existing backend, never another per-page preference store. */
export function ApplicationPreferences({children,accountId}:{children:ReactNode;accountId?:string}) {
  const [hidden,setHidden]=useState(()=>{try{return localStorage.getItem('fincept.money.hidden')==='true';}catch{return false;}});
  const [privacyStorageError,setPrivacyStorageError]=useState('');
  const [periodLabel,setPeriodLabel]=useState('');
  const [settings,setSettings]=useState<SettingsResource|null>(null);
  const [settingsLoading,setLoading]=useState(!!accountId),[settingsError,setError]=useState('');
  const [savingSettings,setSaving]=useState(false), locked=useRef(false);
  const controller=useRef<AbortController|null>(null);
  const reloadSettings=useCallback(async()=>{
    if(!accountId)return;
    controller.current?.abort();const next=new AbortController();controller.current=next;
    setLoading(true);setError('');
    try{const result=await settingsRequest<SettingsResource>('','GET',undefined,next.signal);if(!next.signal.aborted)setSettings(result);}
    catch(e){if(!next.signal.aborted)setError(e instanceof Error?e.message:'Settings could not be loaded.');}
    finally{if(!next.signal.aborted)setLoading(false);}
  },[accountId]);
  useEffect(()=>{setSettings(null);void reloadSettings();return()=>controller.current?.abort();},[reloadSettings]);
  useEffect(()=>{const sync=(e:StorageEvent)=>{if(e.key==='fincept.money.hidden'||e.key===null)setHidden(e.newValue==='true');};window.addEventListener('storage',sync);return()=>window.removeEventListener('storage',sync);},[]);
  async function saveSettings(preferences:Preferences) {
    if(locked.current)throw Error('A settings save is already in progress.');
    if(!settings)throw Error('Load saved settings before making changes.');
    locked.current=true;setSaving(true);
    try {
      const saved=await settingsRequest<{preferences:Preferences;version:number}>('/preferences','PATCH',{...preferences,version:settings.version});
      setSettings(current=>current?{...current,...saved}:null);
    } finally{locked.current=false;setSaving(false);}
  }
  function toggle(){const next=!hidden;try{localStorage.setItem('fincept.money.hidden',String(next));setPrivacyStorageError('');}catch{setPrivacyStorageError('Browser storage is blocked. This privacy choice works in the current session but may not persist after closing the app.');}setHidden(next);}
  const financial=settings?.preferences.financial||defaultFinancial;
  return <Context.Provider value={{hidden,toggle,privacyStorageError,periodLabel,setPeriodLabel,settings,settingsLoading,settingsError,savingSettings,reloadSettings,saveSettings,formatAmount:value=>formatMoney(value,financial)}}>{children}</Context.Provider>;
}
export function usePreferences(){const value=useContext(Context);if(!value)throw new Error('ApplicationPreferences missing');return value;}
export function formatMoney(value:number,financial:FinancialPreferences=defaultFinancial){return '৳'+Math.abs(value).toLocaleString('en-US',{useGrouping:financial.number_grouping,minimumFractionDigits:financial.decimal_style==='fixed'?2:0,maximumFractionDigits:2});}
export function useMoneyFormatter(){return usePreferences().formatAmount;}
export function Money({value,signed=false}:{value:number;signed?:boolean}){const {hidden,formatAmount}=usePreferences();return <span className="money">{hidden?<span aria-label="Amount hidden">••••</span>:`${value<0?'−':signed&&value>0?'+':''}${formatAmount(value)}`}</span>;}
