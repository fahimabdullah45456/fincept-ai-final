import {useEffect,useRef,useState,type FormEvent} from 'react';
import {Link,NavLink,Navigate,Route,Routes,useLocation,useNavigate} from 'react-router-dom';
import {UserRound,ShieldCheck,Link2,Database,CircleHelp,ArrowUpRight,LockKeyhole,Info} from 'lucide-react';
import {useAuth} from '../auth/AuthProvider';
import {usePreferences,formatMoney} from '../../components/layout/ApplicationPreferences';
import {Dialog,DialogCloseButton} from '../../components/ui/Dialog';
import {Icon} from '../../components/ui/Icon';
import {passwordRules} from '../auth/validation';
import {downloadExport,settingsRequest,updateProfile,type FinancialPreferences,type NotificationPreferences,type Security} from './api';
import {Feedback,FormControl,Notice,SettingsCard,Toggle,useAction} from './components';
import {version as applicationVersion} from '../../../package.json';
import '../../styles/settings.css';

export function initials(name:string) {return name.trim().split(/\s+/).filter(Boolean).slice(0,2).map(part=>Array.from(part)[0]).join('').toLocaleUpperCase()||'?';}
const categories=[
  {path:'profile',label:'Profile',icon:<UserRound size={19}/>},
  {path:'privacy-security',label:'Privacy & Security',icon:<ShieldCheck size={19}/>},
  {path:'notifications',label:'Notifications',icon:<Icon name="bell"/>},
  {path:'financial-preferences',label:'Financial Preferences',icon:<Icon name="wallet"/>},
  {path:'connected-services',label:'Connected Services',icon:<Link2 size={19}/>},
  {path:'data-account',label:'Data & Account',icon:<Database size={19}/>},
  {path:'help-about',label:'Help & About',icon:<CircleHelp size={19}/>}
];
export function Settings() {
  const {user}=useAuth();const {settings,settingsLoading,settingsError,reloadSettings}=usePreferences();
  const {pathname}=useLocation();const navigate=useNavigate();const selected=categories.find(c=>pathname===`/settings/${c.path}`)||categories[0];
  return <div className="settings-page">
    <header className="st-page-heading"><h1>Settings</h1><p>Manage your account, privacy, notifications, and financial preferences.</p></header>
    <section className="st-summary" aria-label="Your profile"><span className="st-avatar" aria-hidden="true">{initials(user?.full_name||'')}</span><div><h2>{user?.full_name}</h2><p>{user?.email}</p></div><Link to="/settings/profile?edit=1" className="ov-button"><Icon name="edit"/>Edit Profile</Link></section>
    <div className="st-layout"><nav className="st-navigation" aria-label="Settings categories">{categories.map(c=><NavLink key={c.path} to={`/settings/${c.path}`} className={({isActive})=>`st-nav-link${isActive?' selected':''}`}><span aria-hidden="true">{c.icon}</span>{c.label}<span className="st-nav-arrow" aria-hidden="true">›</span></NavLink>)}</nav><div className="st-mobile-category st-field"><label htmlFor="st-category">Settings category</label><select id="st-category" className="ov-input" value={selected.path} onChange={event=>navigate(`/settings/${event.target.value}`)}>{categories.map(category=><option key={category.path} value={category.path}>{category.label}</option>)}</select></div>
      <div className="st-content" aria-label={selected.label}>
        {settingsLoading?<div className="st-skeleton st-card" role="status" aria-live="polite"><p>Loading your settings…</p><i/><i/><i/></div>:settingsError?<Notice tone="error" action={<button className="ov-button" onClick={()=>void reloadSettings()}>Try again</button>}>{settingsError}{settingsError.includes('session has expired')&&<> <Link to="/sign-in">Sign in again</Link>.</>}</Notice>:settings&&<Routes>
          <Route index element={<Navigate to="profile" replace/>}/><Route path="profile" element={<Profile/>}/>
          <Route path="privacy-security" element={<PrivacySecurity/>}/><Route path="notifications" element={<Notifications/>}/>
          <Route path="financial-preferences" element={<FinancialPreferencesPanel/>}/><Route path="connected-services" element={<ConnectedServices/>}/>
          <Route path="data-account" element={<DataAccount/>}/><Route path="help-about" element={<HelpAbout/>}/>
          <Route path="*" element={<Notice>That Settings category does not exist. <Link to="/settings/profile">Open Profile</Link>.</Notice>}/>
        </Routes>}
      </div>
    </div>
  </div>;
}

function Profile() {
  const {user,updateUser}=useAuth();const [name,setName]=useState(user?.full_name||'');const action=useAction();const {search}=useLocation();
  useEffect(()=>{setName(user?.full_name||'');},[user?.full_name]);
  useEffect(()=>{if(new URLSearchParams(search).get('edit'))document.getElementById('st-display-name')?.focus();},[search]);
  async function submit(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();const normalized=name.trim().replace(/\s+/g,' ');
    if(normalized.length<2||normalized.length>100){action.setFields({full_name:'Enter a display name between 2 and 100 characters.'});document.getElementById('st-display-name')?.focus();return;}
    await action.run(async()=>{const result=await updateProfile(normalized);updateUser(result.user);return 'Your profile has been updated.';});
  }
  return <form onSubmit={submit} noValidate><SettingsCard title="Profile" description="Your personal account information." footer={<><button type="button" className="ov-button" disabled={action.busy||name===user?.full_name} onClick={()=>{setName(user?.full_name||'');action.reset();}}>Cancel</button><button type="submit" className="ov-button orange" disabled={action.busy||name===user?.full_name}>{action.busy?'Saving…':'Save Changes'}</button></>}>
    <div className="st-profile-initials"><span className="st-avatar" aria-hidden="true">{initials(user?.full_name||'')}</span><div><strong>Profile initials</strong><p className="st-help">Generated from your display name. Photo uploads are not supported.</p></div></div>
    <fieldset disabled={action.busy} className="st-fields"><FormControl id="st-display-name" name="full_name" label="Display name" autoComplete="name" maxLength={100} value={name} onChange={e=>{setName(e.target.value);action.reset();}} error={action.fields.full_name} required/>
      <FormControl label="Email address" type="email" value={user?.email||''} autoComplete="email" readOnly help="Email changes require a verification workflow that is not configured. Your email cannot be edited here."/>
    </fieldset><Feedback error={action.error} success={action.success}/>
  </SettingsCard></form>;
}

function PrivacySecurity() {
  const {hidden,toggle,privacyStorageError}=usePreferences();const [security,setSecurity]=useState<Security|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
  const [dialog,setDialog]=useState<'password'|'sessions'|null>(null),[message,setMessage]=useState('');
  const controller=useRef<AbortController|null>(null);
  async function load() {controller.current?.abort();const c=new AbortController();controller.current=c;setLoading(true);setError('');try{const result=await settingsRequest<Security>('/security','GET',undefined,c.signal);if(!c.signal.aborted)setSecurity(result);}catch(e){if(!c.signal.aborted)setError(e instanceof Error?e.message:'Could not load security information.');}finally{if(!c.signal.aborted)setLoading(false);}}
  useEffect(()=>{void load();return()=>controller.current?.abort();},[]);
  return <><SettingsCard title="Privacy & Security" description="Keep your finances private and your account secure.">
    <Toggle label="Hide monetary amounts" description="Mask balances and monetary values throughout the app. This is the same control as the privacy button in your header." checked={hidden} onChange={toggle}/>
    <p className="st-help st-spaced">Saved on this browser, including after navigation and refresh. Downloaded exports contain original, unmasked values.</p>{privacyStorageError&&<Notice tone="error">{privacyStorageError}</Notice>}
  </SettingsCard>
  <SettingsCard title="Account security" description="Manage your password and existing sign-in sessions.">
    <div className="st-action-row"><div><h3>Password</h3><p>Update your password with your current password. Other sessions will be signed out.</p></div><button className="ov-button" onClick={()=>setDialog('password')}>Change Password</button></div>
    <div className="st-action-row"><div><h3>Active sessions</h3>{loading?<p role="status">Checking sessions…</p>:security?<><p>{security.active_sessions} active {security.active_sessions===1?'session':'sessions'}, including this one.</p>{security.current_expires_at&&<p>This session expires {new Date(security.current_expires_at).toLocaleString()}.</p>}</>:null}</div><button className="ov-button" disabled={loading||!security||security.active_sessions<2} onClick={()=>setDialog('sessions')}>Sign Out Other Sessions</button></div>
    {error&&<Notice tone="error" action={<button className="ov-button" onClick={()=>void load()}>Retry</button>}>{error}</Notice>}
    <div className="st-action-row"><div><h3>Two-factor authentication</h3><p>Not available with the current authentication service. No additional verification method is active.</p></div><span className="st-badge">Unavailable</span></div>
    {message&&<Notice tone="success">{message}</Notice>}
  </SettingsCard>
  {dialog&&<SecurityDialog mode={dialog} onClose={()=>setDialog(null)} onDone={text=>{setDialog(null);setMessage(text);void load();}}/>}</>;
}
function SecurityDialog({mode,onClose,onDone}:{mode:'password'|'sessions';onClose:()=>void;onDone:(text:string)=>void}) {
  const [current,setCurrent]=useState(''),[next,setNext]=useState(''),[confirm,setConfirm]=useState('');const action=useAction();const form=useRef<HTMLFormElement>(null);
  async function submit(e:FormEvent) {
    e.preventDefault();const fields:Record<string,string>={};if(!current)fields.current_password='Enter your current password.';
    if(mode==='password'){if(next.length>512||!passwordRules(next).every(r=>r.met))fields.new_password='Use 8+ characters, upper and lowercase letters, a number and a symbol.';if(next!==confirm)fields.confirm_password='Passwords do not match.';}
    if(Object.keys(fields).length){action.setFields(fields);return;}
    await action.run(async()=>{
      if(mode==='password'){const r=await settingsRequest<{message:string}>('/password','POST',{current_password:current,new_password:next,confirm_password:confirm});onDone(r.message);}
      else{const r=await settingsRequest<{revoked:number}>('/sessions/revoke-others','POST',{current_password:current});onDone(`${r.revoked} other ${r.revoked===1?'session was':'sessions were'} signed out.`);}
    });
  }
  useEffect(()=>{if(Object.keys(action.fields).length)form.current?.querySelector<HTMLInputElement>('[aria-invalid="true"]')?.focus();},[action.fields]);
  return <Dialog title={mode==='password'?'Change Password':'Sign Out Other Sessions'} initialFocusSelector="input" onClose={onClose} beforeClose={()=>!action.busy} className="st-dialog"><form ref={form} onSubmit={submit} noValidate aria-busy={action.busy}><p className="st-dialog-copy">{mode==='password'?'Verify your current password to update it. Your current session will be renewed; all other sessions will be revoked.':'Confirm your current password. This browser stays signed in; other active sessions will be revoked.'}</p><fieldset className="st-fields" disabled={action.busy}>
    <FormControl autoFocus label="Current password" type="password" autoComplete="current-password" value={current} onChange={e=>setCurrent(e.target.value)} maxLength={512} error={action.fields.current_password} required/>
    {mode==='password'&&<><FormControl label="New password" type="password" autoComplete="new-password" value={next} onChange={e=>setNext(e.target.value)} maxLength={512} error={action.fields.new_password} help="Use at least 8 characters, uppercase, lowercase, a number, and a symbol." required/><FormControl label="Confirm new password" type="password" autoComplete="new-password" value={confirm} onChange={e=>setConfirm(e.target.value)} maxLength={512} error={action.fields.confirm_password} required/></>}
    </fieldset><Feedback error={action.error} success=""/><footer className="st-dialog-footer"><DialogCloseButton disabled={action.busy}>Cancel</DialogCloseButton><button className="ov-button orange" type="submit" disabled={action.busy}>{action.busy?'Processing…':mode==='password'?'Update Password':'Sign Out Other Sessions'}</button></footer></form></Dialog>;
}
const notificationGroups=[
  {title:'Financial activity',description:'Choose the financial updates you would like to receive.',items:[{key:'budget_alerts',label:'Budget alerts',description:'Updates when a budget approaches or exceeds its limit.'},{key:'goal_updates',label:'Goal updates',description:'Updates about progress toward your financial goals.'},{key:'payment_reminders',label:'Payment reminders',description:'Reminders for planned payments and due dates.'}]},
  {title:'Product updates',description:'Choose whether you want to hear about FINCEPT AI.',items:[{key:'product_updates',label:'Product updates',description:'News about product improvements and new features.'}]}
] as const;
function Notifications() {
  const {settings,saveSettings,savingSettings,reloadSettings}=usePreferences();const saved=settings!.preferences;
  const [draft,setDraft]=useState<NotificationPreferences>(saved.notifications);const action=useAction();
  useEffect(()=>{setDraft(saved.notifications);},[settings!.version]);
  const dirty=JSON.stringify(draft)!==JSON.stringify(saved.notifications);
  return <><Notice>These choices are saved to your account. Email, push, and reminder delivery are not configured; changing a switch does not send or schedule notifications.</Notice>
    <form onSubmit={e=>{e.preventDefault();void action.run(async()=>{await saveSettings({...saved,notifications:draft});return 'Notification preferences saved. Delivery is not configured.';});}}>
      {notificationGroups.map(group=><SettingsCard key={group.title} title={group.title} description={group.description}>{group.items.map(item=><Toggle key={item.key} label={item.label} description={item.description} checked={draft[item.key]} disabled={savingSettings} onChange={()=>{setDraft(d=>({...d,[item.key]:!d[item.key]}));action.reset();}}/>)}</SettingsCard>)}
      <PreferenceFooter busy={savingSettings} dirty={dirty} error={action.error} success={action.success} cancel={()=>{setDraft(saved.notifications);action.reset();}} reload={()=>void reloadSettings()}/>
    </form></>;
}
function PreferenceFooter({busy,dirty,cancel,error,success,reload}:{busy:boolean;dirty:boolean;cancel:()=>void;error:string;success:string;reload:()=>void}) {
  return <><Feedback error={error} success={success}/>{error.includes('another window')&&<button type="button" className="ov-button" onClick={reload}>Reload saved settings (discard edits)</button>}<div className="st-save-bar"><span className="st-help">{busy?'Saving your preferences…':dirty?'You have unsaved changes.':'Your saved preferences are up to date.'}</span><div><button type="button" className="ov-button" disabled={busy||!dirty} onClick={cancel}>Cancel</button><button type="submit" className="ov-button orange" disabled={busy||!dirty}>{busy?'Saving…':'Save Changes'}</button></div></div></>;
}
function FinancialPreferencesPanel() {
  const {settings,saveSettings,savingSettings,hidden,reloadSettings}=usePreferences();const saved=settings!.preferences;
  const [draft,setDraft]=useState<FinancialPreferences>(saved.financial);const action=useAction();
  useEffect(()=>{setDraft(saved.financial);},[settings!.version]);
  return <form onSubmit={e=>{e.preventDefault();void action.run(async()=>{await saveSettings({...saved,financial:draft});return 'Financial display preferences saved. Your recorded amounts have not changed.';});}}>
    <SettingsCard title="Financial Preferences" description="Choose how monetary values are displayed across FINCEPT AI."><fieldset className="st-fields" disabled={savingSettings}>
      <FormControl label="Account currency" value="BDT — Bangladeshi Taka" readOnly help="The existing ledger supports BDT. Currency conversion is a separate Financial Hub tool; it never changes recorded amounts."/>
      <div className="st-field"><label htmlFor="st-decimals">Decimal display</label><select id="st-decimals" className="ov-input" value={draft.decimal_style} onChange={e=>{setDraft(d=>({...d,decimal_style:e.target.value as FinancialPreferences['decimal_style']}));action.reset();}}><option value="flexible">Up to two decimal places</option><option value="fixed">Always two decimal places</option></select><p className="st-help">Display only. Original integer minor units are preserved.</p></div>
      <Toggle label="Thousands separators" description="Group digits for easier reading, for example 1,234.50 instead of 1234.50." checked={draft.number_grouping} onChange={()=>{setDraft(d=>({...d,number_grouping:!d.number_grouping}));action.reset();}} disabled={savingSettings}/>
      <div className="st-format-preview"><span>Formatting example <small>(not an account balance)</small></span><strong>{hidden?<span aria-label="Amount hidden">••••</span>:formatMoney(1234.5,draft)}</strong></div>
    </fieldset></SettingsCard>
    <PreferenceFooter busy={savingSettings} dirty={JSON.stringify(draft)!==JSON.stringify(saved.financial)} error={action.error} success={action.success} cancel={()=>{setDraft(saved.financial);action.reset();}} reload={()=>void reloadSettings()}/>
  </form>;
}
function ConnectedServices() {
  const {settings,reloadSettings}=usePreferences();
  return <><SettingsCard title="Connected Services" description="Only verified connections appear as connected."><Notice>No third-party account connections are active. Your manually maintained wallets and records are unchanged.</Notice><div className="st-integrations">{settings!.integrations.map(integration=><article className="st-integration" key={integration.id}><div className="st-service-icon">{integration.id==='google'?<img src="/assets/google.svg" width="24" height="24" alt=""/>:<Icon collection="wallets" name="bank" size={24}/>}</div><div><h3>{integration.name}</h3><span className="st-badge">{integration.status==='not_configured'?'Not configured':'Unavailable'}</span><p>{integration.description}</p></div><button className="ov-button" disabled>Connect unavailable</button></article>)}</div></SettingsCard><button className="ov-button" onClick={()=>void reloadSettings()}>Refresh connection status</button></>;
}

function DataAccount() {
  const {settings}=usePreferences();const [format,setFormat]=useState<'csv'|'json'>('csv'),[scope,setScope]=useState('all');const [dialog,setDialog]=useState<'export'|'demo'|null>(null),[confirmation,setConfirmation]=useState('');const action=useAction();
  function open(which:'export'|'demo'){action.reset();setConfirmation('');setDialog(which);}
  async function execute(e:FormEvent) {e.preventDefault();await action.run(async()=>{
    if(dialog==='export'){await downloadExport(format,scope);setDialog(null);return 'Export generated. Your browser received the download.';}
    if(confirmation!=='CLEAR DEMO DATA')throw Error('Type CLEAR DEMO DATA to confirm.');
    const result=await settingsRequest<{message:string;deleted:Record<string,number>}>('/demo/clear','POST',{confirmation});setDialog(null);return result.message;
  });}
  return <><SettingsCard title="Export Your Data" description="Download your own live financial records. Sample data is never mixed into these exports.">
    <div className="st-two-fields"><div className="st-field"><label htmlFor="st-export-scope">Export scope</label><select id="st-export-scope" className="ov-input" value={scope} onChange={e=>setScope(e.target.value)}><option value="all">All supported financial records</option><option value="transactions">Transactions</option><option value="wallets">Wallets and balance events</option><option value="budgets">Budgets</option><option value="goals">Financial goals and contributions</option></select></div><div className="st-field"><label htmlFor="st-export-format">File format</label><select id="st-export-format" className="ov-input" value={format} onChange={e=>setFormat(e.target.value as 'csv'|'json')}><option value="csv">CSV files in a ZIP archive</option><option value="json">JSON financial snapshot</option></select></div></div>
    <p className="st-help st-spaced">Exports include original amounts in integer minor units and a manifest of scope, counts, and generation time. CSV text is escaped and protected against spreadsheet formulas. Empty datasets include column headers.</p><button className="ov-button" onClick={()=>open('export')}><Icon collection="wallets" name="dl"/>Export Your Data</button>
  </SettingsCard>
  <SettingsCard title="Backup & Restore" description="Keep a portable copy of your financial data."><div className="st-action-row"><div><h3>Financial snapshot</h3><p>Use the JSON export above for a real, scoped data snapshot. It excludes credentials, account preferences, and AI conversations; it is not a full database backup.</p></div></div><div className="st-action-row"><div><h3>Restore from a file</h3><p>Unavailable. A validated, transactional import pipeline with duplicate and conflict handling has not been implemented. Export files cannot be restored in this version.</p></div><button className="ov-button" disabled>Restore unavailable</button></div></SettingsCard>
  <SettingsCard title="Data & Account" description="Review the scope carefully before taking an irreversible action."><div className="st-action-row st-danger-row"><div><h3>Clear Demo Data</h3><p>Permanently remove only your explicitly marked sample workspace, including sample finance, planner, and AI history. Your live records remain untouched.</p>{!settings!.capabilities.clear_demo&&<p>Sample workspaces are disabled in production.</p>}</div><button className="ov-button st-danger-button" disabled={!settings!.capabilities.clear_demo} onClick={()=>open('demo')}>Clear Demo Data</button></div><div className="st-action-row st-danger-row"><div><h3>Delete Account</h3><p>Unavailable. A reviewed deletion and retention policy and a secure account-deletion workflow are not configured. No data or account will be deleted by this control.</p></div><button className="ov-button st-danger-button" disabled>Delete unavailable</button></div></SettingsCard>
  {!dialog&&<Feedback error={action.error} success={action.success}/>}
  {dialog&&<Dialog title={dialog==='export'?'Confirm Data Export':'Clear Demo Data'} initialFocusSelector={dialog==='demo'?'input':undefined} onClose={()=>setDialog(null)} beforeClose={()=>!action.busy} className="st-dialog"><form onSubmit={execute} aria-busy={action.busy}><div className="st-dialog-copy">{dialog==='export'?<><p>Your selected live records will be downloaded as {format==='csv'?'CSV files in a ZIP archive':'a JSON snapshot'}.</p><Notice>Exports contain unmasked monetary values, even when monetary privacy is enabled. They exclude passwords, session tokens, and other authentication credentials. Keep downloaded files private.</Notice></>:<><p>This permanently clears only this account’s sample workspace, including sample financial records, tasks, and AI history. Live records and other accounts are not affected. There is no undo.</p><FormControl autoFocus label="Type CLEAR DEMO DATA to confirm" value={confirmation} onChange={e=>setConfirmation(e.target.value)} disabled={action.busy} autoComplete="off"/></>}</div><Feedback error={action.error} success=""/><footer className="st-dialog-footer"><DialogCloseButton disabled={action.busy}>Cancel</DialogCloseButton><button type="submit" className={`ov-button ${dialog==='demo'?'st-danger-confirm':'orange'}`} disabled={action.busy||(dialog==='demo'&&confirmation!=='CLEAR DEMO DATA')}>{action.busy?'Processing…':dialog==='export'?'Download Export':'Permanently Clear Demo Data'}</button></footer></form></Dialog>}
  </>;
}
const faqs=[
  ['Are my bank accounts connected?', 'No bank-linking provider is configured in this version. Wallets and their recorded activity are managed manually. Connected Services reports only real integration status.'],
  ['Does changing display formatting change my money?', 'No. Thousands separators and decimal display only change presentation. Records retain their original integer minor-unit amounts. The ledger supports BDT; the Financial Hub converter is separate.'],
  ['How does monetary privacy work?', 'The header and Settings use one browser-local privacy preference. Monetary displays remain masked as you navigate and refresh. Other browsers have their own preference. Data exports contain original values and require an explicit review.'],
  ['Will notification switches send reminders?', 'Not yet. Preferences are saved to your account, but email, push, and reminder delivery are not configured. Budget observations remain available in the application.'],
  ['Can I restore a downloaded snapshot?', 'Not in this version. Exports are real user-owned financial records, not a promise of a restorable database backup. A safe import and conflict-resolution pipeline is required before restore can be enabled.']
];
function HelpAbout() {
  const [dialog,setDialog]=useState<'help'|'about'|null>(null);
  return <><SettingsCard title="Help & About" description="Find answers and learn about FINCEPT AI."><div className="st-help-grid">
    <button className="st-help-card" onClick={()=>setDialog('help')}><CircleHelp size={23}/><strong>Help Center</strong><p>Read the in-app guide to settings and data.</p><ArrowUpRight size={17}/></button>
    <a className="st-help-card" href="#st-faq"><Info size={23}/><strong>Frequently Asked Questions</strong><p>Answers to common account and finance questions.</p><ArrowUpRight size={17}/></a>
    <div className="st-help-card unavailable"><UserRound size={23}/><strong>Contact Support</strong><p>No support address or destination has been configured.</p><span className="st-badge">Not configured</span></div>
    <div className="st-help-card unavailable"><ShieldCheck size={23}/><strong>Privacy Policy</strong><p>The existing document is an unpublished development placeholder.</p><span className="st-badge">Not published</span></div>
    <div className="st-help-card unavailable"><LockKeyhole size={23}/><strong>Terms of Service</strong><p>Approved legal terms must be supplied before public launch.</p><span className="st-badge">Not published</span></div>
    <button className="st-help-card" onClick={()=>setDialog('about')}><img src="/assets/sidebar/logo-mark.svg" width="25" height="25" alt=""/><strong>About FINCEPT AI</strong><p>Product information and application version.</p><ArrowUpRight size={17}/></button>
  </div></SettingsCard><section id="st-faq" className="st-faq"><SettingsCard title="Frequently Asked Questions">{faqs.map(([question,answer])=><details key={question}><summary>{question}</summary><p>{answer}</p></details>)}</SettingsCard></section>
  {dialog&&<Dialog title={dialog==='about'?'About FINCEPT AI':'Help Center'} onClose={()=>setDialog(null)} className="st-dialog"><div className="st-dialog-copy">{dialog==='about'?<><div className="st-about-brand"><img src="/assets/sidebar/logo-mark.svg" width="44" height="44" alt=""/><h3>FINCEPT AI</h3></div><p>A personal finance application for managing wallets, transactions, budgets, goals, and financial planning.</p><p>Application version <strong>{applicationVersion}</strong> (from the project package).</p><p>AI responses require a server-configured provider. No bank connections or automatic reminder delivery are configured.</p></>:<><p>Your profile and account preferences are stored by the application’s authenticated backend. Monetary privacy is saved on this browser.</p><p>Use Save Changes to commit profile and preference edits. Cancel resets unsaved fields. Security actions require your current password.</p><p>Export only your own records from Data & Account. Check the export notice: files contain original unmasked values. Restore and account deletion are unavailable in this version.</p></>}</div><footer className="st-dialog-footer"><DialogCloseButton>Close</DialogCloseButton></footer></Dialog>}</>;
}
