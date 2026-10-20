import {useId,useRef,useState,type InputHTMLAttributes,type ReactNode} from 'react';
import {ApiError} from '../auth/services/authApi';

export function Notice({children,tone='info',action}:{children:ReactNode;tone?:'info'|'error'|'success';action?:ReactNode}) {
  return <div className={`st-notice ${tone}`} role={tone==='error'?'alert':'status'}><div>{children}</div>{action}</div>;
}
export function SettingsCard({title,description,children,footer}:{title:string;description?:string;children:ReactNode;footer?:ReactNode}) {
  return <section className="st-card"><header className="st-card-heading"><h2>{title}</h2>{description&&<p>{description}</p>}</header><div className="st-card-body">{children}</div>{footer&&<footer className="st-card-footer">{footer}</footer>}</section>;
}
export function FormControl({label,error,help,id:provided,...props}:InputHTMLAttributes<HTMLInputElement>&{label:string;error?:string;help?:string}) {
  const generated=useId(),id=provided||generated;
  return <div className="st-field"><label htmlFor={id}>{label}</label><input {...props} id={id} className="ov-input" aria-invalid={!!error} aria-describedby={error?`${id}-error`:help?`${id}-help`:undefined}/>{error?<p className="st-field-error" id={`${id}-error`}>{error}</p>:help?<p className="st-help" id={`${id}-help`}>{help}</p>:null}</div>;
}
export function Toggle({label,description,checked,onChange,disabled=false}:{label:string;description:string;checked:boolean;onChange:()=>void;disabled?:boolean}) {
  const id=useId();
  return <div className="st-toggle-row"><div><label id={`${id}-label`} htmlFor={id}>{label}</label><p id={`${id}-help`}>{description}</p></div><button id={id} type="button" className="st-toggle" role="switch" aria-checked={checked} aria-labelledby={`${id}-label`} aria-describedby={`${id}-help`} onClick={onChange} disabled={disabled}><span/></button></div>;
}
export function Feedback({error,success}:{error:string;success:string}) {return <>{error&&<Notice tone="error">{error}{error.includes('session has expired')&&<> <a href="/sign-in">Sign in again</a>.</>}</Notice>}{success&&<Notice tone="success">{success}</Notice>}</>;}
export function useAction() {
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[success,setSuccess]=useState('');
  const [fields,setFields]=useState<Record<string,string>>({});const locked=useRef(false);
  function reset(){setError('');setSuccess('');setFields({});}
  async function run(action:()=>Promise<string|void>) {
    if(locked.current)return;locked.current=true;setBusy(true);reset();
    try {const message=await action();if(message)setSuccess(message);}
    catch(e) {setError(e instanceof Error?e.message:'Could not complete the request. Try again.');if(e instanceof ApiError)setFields(e.fieldErrors as Record<string,string>);}
    finally {locked.current=false;setBusy(false);}
  }
  return {busy,error,success,fields,run,reset,setFields};
}
