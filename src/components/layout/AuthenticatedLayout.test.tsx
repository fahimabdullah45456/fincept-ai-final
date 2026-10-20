import {beforeEach, afterEach, expect, it, vi} from 'vitest';
import {render, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import {AuthenticatedLayout} from './AuthenticatedLayout';
import {navigationItems, SIDEBAR_PREFERENCE_KEY, readSidebarPreference} from './navigation';
vi.mock('../../features/auth/AuthProvider',()=>({useAuth:()=>({user:{full_name:'Sidebar Test',email:'sidebar@example.com'},signOut:vi.fn()})}));
function mount() {return render(<MemoryRouter initialEntries={['/overview']}><Routes><Route element={<AuthenticatedLayout/>}>{navigationItems.map(item => <Route key={item.path} path={item.path} element={<h1>{item.label} page</h1>}/>)}</Route></Routes></MemoryRouter>);}
beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());
it('starts minimized and supports keyboard toggle, tooltip and persistence', async () => {
  const user = userEvent.setup(); mount();
  const button = screen.getByRole('button', {name: 'Expand sidebar'});
  expect(button).toHaveAttribute('aria-expanded', 'false');
  await user.tab(); await user.tab();
  await user.hover(button); expect(screen.getByRole('tooltip')).toHaveTextContent('Expand sidebar');
  await user.keyboard('{Escape}'); expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  button.focus(); await user.keyboard('{Enter}');
  expect(screen.getByRole('button', {name: 'Minimize sidebar'})).toHaveAttribute('aria-expanded', 'true');
  expect(localStorage.getItem(SIDEBAR_PREFERENCE_KEY)).toBe('expanded');
  await user.keyboard(' '); expect(screen.getByRole('button', {name: 'Expand sidebar'})).toBeInTheDocument();
});
it('shares the same sidebar instance across every route and updates active selection', async () => {
  const user = userEvent.setup(); mount();
  const sidebar = screen.getByRole('complementary', {name: 'Application sidebar'});
  await user.click(screen.getByRole('button', {name: 'Expand sidebar'}));
  for (const item of navigationItems) {
    await user.click(screen.getByRole('link', {name: item.label}));
    expect(screen.getByRole('heading', {name: `${item.label} page`})).toBeVisible();
    expect(screen.getByRole('link', {name: item.label})).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('complementary')).toBe(sidebar);
    expect(screen.getByRole('button', {name: 'Minimize sidebar'})).toBeInTheDocument();
  }
});
it('reads saved preference synchronously and rejects missing or invalid values', () => {
  expect(readSidebarPreference()).toBe(false);
  for (const value of ['true', 'garbage', '{}', 'null', 'minimized']) {localStorage.setItem(SIDEBAR_PREFERENCE_KEY, value); expect(readSidebarPreference()).toBe(false);}
  localStorage.setItem(SIDEBAR_PREFERENCE_KEY, 'expanded'); mount();
  expect(screen.getByRole('button', {name: 'Minimize sidebar'})).toHaveAttribute('aria-expanded', 'true');
});
it('keeps working if storage access is blocked', async () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {throw new Error('Denied');});
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {throw new Error('Denied');});
  const user = userEvent.setup(); mount();
  await user.click(screen.getByRole('button', {name: 'Expand sidebar'}));
  expect(screen.getByRole('button', {name: 'Minimize sidebar'})).toBeInTheDocument();
  await user.click(screen.getByRole('link', {name: 'Wallets'}));
  expect(screen.getByRole('heading', {name: 'Wallets page'})).toBeInTheDocument();
});
