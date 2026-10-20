export const navigationItems = [
  {label: 'Overview', path: '/overview', icon: 'overview'},
  {label: 'Transactions', path: '/transactions', icon: 'transactions'},
  {label: 'Wallets', path: '/wallets', icon: 'wallets'},
  {label: 'Budgets', path: '/budgets', icon: 'budgets'},
  {label: 'Financial Goals', path: '/financial-goals', icon: 'financial-goals'},
  {label: 'Insights', path: '/insights', icon: 'insights'},
  {label: 'AI Assistant', path: '/ai-assistant', icon: 'ai-assistant'},
  {label: 'Planner', path: '/planner', icon: 'planner'},
  {label: 'Debt & Loans', path: '/debt-loans', icon: 'debt-loans'},
  {label: 'Financial Hub', path: '/financial-hub', icon: 'financial-hub'},
  {label: 'Settings', path: '/settings', icon: 'settings'},
] as const;
export const SIDEBAR_PREFERENCE_KEY = 'fincept.sidebar.state';
export function readSidebarPreference(): boolean {
  try { return localStorage.getItem(SIDEBAR_PREFERENCE_KEY) === 'expanded'; }
  catch { return false; }
}
export function saveSidebarPreference(expanded: boolean): void {
  try { localStorage.setItem(SIDEBAR_PREFERENCE_KEY, expanded ? 'expanded' : 'minimized'); }
  catch { /* Private/restricted storage must not stop navigation or toggling. */ }
}
