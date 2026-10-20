import {useState} from 'react';
import {Dialog, DialogCloseButton} from '../../components/ui/Dialog';
import {Icon} from '../../components/ui/Icon';
import {txRequest} from './api';
import type {Dataset} from './types';
import '../../styles/transaction-corrections.css';

export const categoryIcons=['receipt','wallet','calendar','plus','clock','check'] as const;
export const categoryColors=['#f9733b','#32865a','#c84c42','#5378c8','#9b6cc3','#777873'] as const;

/** Original Create custom category frame 2001:32339; existing category API and ownership. */
export function CreateCategory({dataset,initialKind,onClose,onSaved}: {
  dataset:Dataset; initialKind:'income'|'expense'; onClose:()=>void; onSaved:()=>void;
}) {
  const [name,setName]=useState(''),[kind,setKind]=useState(initialKind),[icon,setIcon]=useState<string>('receipt'),[color,setColor]=useState<string>('#f9733b'),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function save(e:React.FormEvent){e.preventDefault();if(busy)return;if(!name.trim()){setError('Enter a category name.');return;}setError('');setBusy(true);try{await txRequest('/categories',dataset,'POST',{name:name.trim(),kind,icon,color});onSaved();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  return <Dialog title="Create custom category" className="fc-category-dialog" onClose={onClose} beforeClose={()=>!busy}><form onSubmit={save} aria-busy={busy}>
    <div className="fc-category-body" inert={busy}>
      <label className="fc-category-name">Category name<input required autoFocus maxLength={80} autoComplete="off" placeholder="Enter category name" value={name} onChange={e=>{setName(e.target.value);setError('');}} aria-invalid={!!error} aria-describedby={error?'fc-category-error':'fc-category-help'}/></label>
      <div className="fc-category-kind" role="group" aria-label="Transaction type">{(['income','expense'] as const).map(k=><button key={k} type="button" aria-pressed={kind===k} className={kind===k?'selected':''} onClick={()=>{setKind(k);setError('');}}>{k==='income'?'Income':'Expense'}</button>)}</div>
      <fieldset className="fc-icon-choices"><legend>Choose an icon</legend><div>{categoryIcons.map(x=><button type="button" key={x} aria-label={x+' icon'} aria-pressed={icon===x} className={icon===x?'selected':''} onClick={()=>setIcon(x)}><Icon name={x} collection="categories" size={22}/></button>)}</div></fieldset>
      <fieldset className="fc-color-choices"><legend>Choose a color</legend><div>{categoryColors.map((x,i)=><button type="button" key={x} style={{backgroundColor:x}} aria-label={['Orange','Green','Red','Blue','Purple','Gray'][i]} aria-pressed={color===x} onClick={()=>setColor(x)}>{color===x&&<Icon name="check" collection="categories" size={22}/>}</button>)}</div></fieldset>
      <div id="fc-category-help" className="fc-category-help"><p>Names must be unique within the selected type.</p><p>Trim spaces and compare case-insensitively.</p></div>
      {error&&<p id="fc-category-error" className="error-text" role="alert">{error}</p>}
    </div>
    <footer className="fc-category-footer"><span>{dataset==='demo'?'Sample workspace · BDT':'Your categories · BDT'}</span><DialogCloseButton disabled={busy}>Cancel</DialogCloseButton><button className="ov-button orange" disabled={busy||!name.trim()}>{busy?'Creating…':'Create category'}</button></footer>
  </form></Dialog>;
}
