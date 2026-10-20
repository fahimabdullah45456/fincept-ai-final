import {createContext,useContext,useEffect,useRef,useState,type ReactNode,type ButtonHTMLAttributes} from 'react';
const CloseContext=createContext<(()=>void)|null>(null);
let modalCount=0,originalOverflow='';
export function DialogCloseButton({children,className='ov-button',...props}:ButtonHTMLAttributes<HTMLButtonElement>){const close=useContext(CloseContext);return <button {...props} type="button" className={className} onClick={()=>close?.()}>{children}</button>;}
/** Native modal focus trapping/restoration plus a reduced-motion-aware exit transition. */
export function Dialog({title,onClose,beforeClose,children,className='',initialFocusSelector}:{title:string;onClose:()=>void;beforeClose?:()=>boolean;children:ReactNode;className?:string;initialFocusSelector?:string}){
 const ref=useRef<HTMLDialogElement>(null),timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);const [closing,setClosing]=useState(false);
 useEffect(()=>{const el=ref.current!;const previousFocus=document.activeElement instanceof HTMLElement?document.activeElement:null;if(modalCount++===0){originalOverflow=document.body.style.overflow;document.body.style.overflow='hidden';}el.showModal();if(initialFocusSelector)el.querySelector<HTMLElement>(initialFocusSelector)?.focus();return()=>{clearTimeout(timer.current);el.close();if(--modalCount===0)document.body.style.overflow=originalOverflow;if(previousFocus?.isConnected&&(!document.querySelector('dialog[open]')||previousFocus.closest('dialog[open]')))previousFocus.focus({preventScroll:true});};},[]);
 function close(){if(closing||beforeClose?.()===false)return;if(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches){onClose();return;}setClosing(true);timer.current=setTimeout(onClose,200);}
 return <CloseContext.Provider value={close}><dialog ref={ref} className={`application-dialog ${className}${closing?' is-closing':''}`} aria-label={title} onCancel={e=>{e.preventDefault();close();}} onClick={e=>{if(e.target===e.currentTarget)close();}}><div className="dialog-heading"><h2>{title}</h2><button type="button" aria-label="Close dialog" onClick={close}>×</button></div>{children}</dialog></CloseContext.Provider>;
}
