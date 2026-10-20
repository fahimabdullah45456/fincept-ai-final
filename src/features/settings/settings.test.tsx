import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {render,screen,within,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {MemoryRouter,Route,Routes} from 'react-router-dom';
import {ApplicationPreferences,Money,usePreferences,formatMoney} from '../../components/layout/ApplicationPreferences';
import {Settings,initials} from './Settings';
import type {SettingsResource} from './api';
vi.mock('../auth/AuthProvider',()=>({useAuth:()=>({user:{id:'unit-user',full_name:'Real Account',email:'account@example.com'},updateUser:vi.fn()})}));
const resource:SettingsResource={version:0,preferences:{notifications:{budget_alerts:false,goal_updates:false,payment_reminders:false,product_updates:false},financial:{number_grouping:true,decimal_style:'flexible'}},notification_delivery:false,currency:'BDT',capabilities:{restore:false,delete_account:false,clear_demo:true},integrations:[{id:'google',name:'Google sign-in',status:'not_configured',description:'Not configured.'}]};
let saved:SettingsResource,failSave=false;
beforeEach(()=>{
  localStorage.clear();saved=structuredClone(resource);failSave=false;
  vi.stubGlobal('fetch',vi.fn(async(_url:string,init?:RequestInit)=>{
    if(init?.method==='PATCH'){
      if(failSave)return new Response(JSON.stringify({message:'Save was rejected.'}),{status:503});
      const payload=JSON.parse(init.body as string);saved={...saved,preferences:{notifications:payload.notifications,financial:payload.financial},version:saved.version+1};
      return new Response(JSON.stringify(saved));
    }
    if(String(_url).endsWith('/security'))return new Response(JSON.stringify({active_sessions:1,current_expires_at:null}));
    return new Response(JSON.stringify(saved));
  }));
});
afterEach(()=>vi.unstubAllGlobals());
function Probe(){const {hidden,toggle}=usePreferences();return <div data-testid="probe"><Money value={1234.5}/><button onClick={toggle} aria-pressed={hidden}>Header privacy</button></div>;}
function mount(path='/settings/profile'){render(<MemoryRouter initialEntries={[path]}><ApplicationPreferences accountId="unit-user"><Probe/><Routes><Route path="/settings/*" element={<Settings/>}/></Routes></ApplicationPreferences></MemoryRouter>);}
it('derives initials only from the actual supplied name and keeps formatting pure',()=>{
 expect(initials('  Fahim   Defalt ')).toBe('FD');expect(initials('Single')).toBe('S');expect(initials('')).toBe('?');
 expect(formatMoney(1234.5,{number_grouping:false,decimal_style:'fixed'})).toBe('৳1234.50');
});
it('loads the real profile data and provides URL-based category links',async()=>{
 mount();await screen.findByLabelText('Display name');
 expect(screen.getByLabelText('Display name')).toHaveValue('Real Account');expect(screen.getByLabelText('Email address')).toHaveValue('account@example.com');expect(screen.getByLabelText('Email address')).toHaveAttribute('readonly');
 const nav=screen.getByRole('navigation',{name:'Settings categories'});
 expect(within(nav).getAllByRole('link')).toHaveLength(7);expect(within(nav).getByRole('link',{name:'Profile'})).toHaveAttribute('aria-current','page');
 await userEvent.click(within(nav).getByRole('link',{name:'Help & About'}));expect(screen.getByRole('heading',{name:'Help & About'})).toBeVisible();
});
it('persists notification preferences only on successful save, retaining edits on failure',async()=>{
 mount('/settings/notifications');const toggle=await screen.findByRole('switch',{name:'Budget alerts'});
 await userEvent.click(toggle);expect(toggle).toHaveAttribute('aria-checked','true');
 failSave=true;await userEvent.click(screen.getByRole('button',{name:'Save Changes'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Save was rejected.');expect(saved.preferences.notifications.budget_alerts).toBe(false);
 expect(screen.queryByText('Notification preferences saved. Delivery is not configured.')).not.toBeInTheDocument();
 failSave=false;await userEvent.click(screen.getByRole('button',{name:'Save Changes'}));
 expect(await screen.findByText('Notification preferences saved. Delivery is not configured.')).toBeVisible();expect(saved.preferences.notifications.budget_alerts).toBe(true);
});
it('shares monetary privacy with header controls and preserves it after category navigation',async()=>{
 mount('/settings/privacy-security');const toggle=await screen.findByRole('switch',{name:'Hide monetary amounts'});
 await userEvent.click(toggle);expect(localStorage.getItem('fincept.money.hidden')).toBe('true');expect(screen.getByRole('button',{name:'Header privacy'})).toHaveAttribute('aria-pressed','true');
 expect(within(screen.getByTestId('probe')).getByLabelText('Amount hidden')).toBeVisible();
 await userEvent.click(screen.getByRole('link',{name:'Financial Preferences'}));expect(await screen.findByText('Formatting example')).toBeVisible();
 expect(screen.queryByText('৳1,234.5')).not.toBeInTheDocument();
 await userEvent.click(screen.getByRole('button',{name:'Header privacy'}));expect(within(screen.getByTestId('probe')).getByText('৳1,234.5')).toBeVisible();
});
it('applies persisted formatting to the shared Money component without changing its value',async()=>{
 mount('/settings/financial-preferences');await screen.findByLabelText('Decimal display');
 await userEvent.selectOptions(screen.getByLabelText('Decimal display'),'fixed');await userEvent.click(screen.getByRole('switch',{name:'Thousands separators'}));
 await userEvent.click(screen.getByRole('button',{name:'Save Changes'}));
 await waitFor(()=>expect(within(screen.getByTestId('probe')).getByText('৳1234.50')).toBeVisible());
 expect(saved.preferences.financial).toEqual({number_grouping:false,decimal_style:'fixed'});
});
it('does not offer unsupported restore or account deletion',async()=>{
 mount('/settings/data-account');expect(await screen.findByRole('button',{name:'Restore unavailable'})).toBeDisabled();expect(screen.getByRole('button',{name:'Delete unavailable'})).toBeDisabled();
});
it('shows a retryable initial fetch failure, not defaults presented as saved data',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>{throw Error('Offline');}));mount();
 expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach Settings');expect(screen.getByRole('button',{name:'Try again'})).toBeVisible();expect(screen.queryByLabelText('Display name')).not.toBeInTheDocument();
});
