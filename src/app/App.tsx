import {useEffect,useState,type ReactNode} from 'react';
import {Link,Navigate,Route,Routes,useLocation} from 'react-router-dom';
import {AuthProvider,useAuth} from '../features/auth/AuthProvider';
import {SignIn,SignUp} from '../features/auth/AuthForms';
import {AuthCard,AuthLayout} from '../features/auth/components/AuthLayout';
import {AuthBrand} from '../features/auth/components/AuthBrand';
import {AuthenticatedLayout} from '../components/layout/AuthenticatedLayout';
import {Transactions} from '../features/transactions/Transactions';
import {Goals} from '../features/goals/Goals';
import {Budgets} from '../features/budgets/Budgets';
import {Wallets} from '../features/wallets/Wallets';
import {Debts} from '../features/debt/Debts';
import {Hub} from '../features/hub/Hub';
import {Planner} from '../features/planner/Planner';
import {Assistant} from '../features/assistant/Assistant';
import {Insights} from '../features/insights/Insights';
import {Settings} from '../features/settings/Settings';
import {Overview} from '../features/overview/Overview';
import {navigationItems} from '../components/layout/navigation';
import {FormError,PrimaryButton} from '../features/auth/components/FormControls';
function ProtectedRoute({children}:{children:ReactNode}){const a=useAuth();if(a.loading)return <main className="session-screen" role="status">Checking your session…</main>;if(a.sessionError)return <main className="session-screen"><h1>Could not check your session</h1><FormError message={a.sessionError}/><PrimaryButton onClick={()=>void a.refresh()}>Try again</PrimaryButton></main>;return a.user?children:<Navigate to="/sign-in" replace/>;}
function Complete(){const {user,signOut}=useAuth();const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);return <main className="completion-page"><AuthBrand/><AuthCard><span className="completion-label">Authentication complete · Step 02 of 02</span><h1>You’re signed in, {user?.full_name}.</h1><p>Your account and secure session are ready. Open Overview to see your financial snapshot.</p><Link className="ov-button orange" to="/overview">Open Overview</Link><FormError message={message}/><PrimaryButton loading={busy} onClick={async()=>{setBusy(true);try{await signOut();}catch(e){setMessage(e instanceof Error?e.message:'Sign out failed.');}finally{setBusy(false);}}}>Sign out</PrimaryButton></AuthCard></main>;}
function Info({kind}:{kind:'reset'|'terms'|'privacy'}){return <AuthLayout mode="sign-in"><AuthCard><header className="form-heading"><h2>{kind==='reset'?'Password recovery':kind==='terms'?'Terms of Service':'Privacy Policy'}</h2></header><p className="info-copy">{kind==='reset'?'Password recovery is not configured yet. No reset email will be sent. This feature requires an email delivery provider and a secure, expiring reset-token flow.':kind==='terms'?'Development placeholder — not published legal terms. Final Terms of Service must be supplied and approved before public registration is enabled.':'Development placeholder — not a published privacy policy. Final privacy disclosures, retention periods and contact details must be supplied before public launch.'}</p><Link className="text-link" to={kind==='reset'?'/sign-in':'/sign-up'}>Back to {kind==='reset'?'Sign in':'Sign up'}</Link></AuthCard></AuthLayout>;}
function PageTitle(){const {pathname}=useLocation();useEffect(()=>{document.title=`${pathname==='/sign-up'?'Create your account':pathname==='/sign-in'?'Welcome back':navigationItems.find(item=>pathname===item.path||pathname.startsWith(item.path+'/'))?.label??'Authentication'} — FINCEPT`;},[pathname]);return null;}
export function App(){return <AuthProvider><PageTitle/><Routes><Route path="/sign-in" element={<SignIn/>}/><Route path="/sign-up" element={<SignUp/>}/><Route path="/forgot-password" element={<Info kind="reset"/>}/><Route path="/terms" element={<Info kind="terms"/>}/><Route path="/privacy" element={<Info kind="privacy"/>}/><Route element={<ProtectedRoute><AuthenticatedLayout/></ProtectedRoute>}><Route path="/auth/complete" element={<Complete/>}/><Route path="/debt-loans/*" element={<Debts/>}/><Route path="/financial-hub/*" element={<Hub/>}/><Route path="/planner/*" element={<Planner/>}/><Route path="/ai-assistant/*" element={<Assistant/>}/><Route path="/insights/*" element={<Insights/>}/><Route path="/settings/*" element={<Settings/>}/><Route path="/overview" element={<Overview/>}/><Route path="/transactions/*" element={<Transactions/>}/><Route path="/wallets/*" element={<Wallets/>}/><Route path="/budgets/*" element={<Budgets/>}/><Route path="/financial-goals/*" element={<Goals/>}/></Route><Route path="*" element={<Navigate to="/sign-in" replace/>}/></Routes></AuthProvider>;}
