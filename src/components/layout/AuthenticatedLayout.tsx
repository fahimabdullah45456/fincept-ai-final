import {useEffect, useState} from 'react';
import {Outlet,useLocation} from 'react-router-dom';
import {Sidebar} from './Sidebar';
import {readSidebarPreference, saveSidebarPreference} from './navigation';
import '../../styles/application.css';
import '../../styles/overview.css';
import {ApplicationPreferences} from './ApplicationPreferences';
import {ApplicationHeader} from './ApplicationHeader';
import {useAuth} from '../../features/auth/AuthProvider';

/** The persistent route parent is the sole owner of sidebar state. */
export function AuthenticatedLayout() {
  const {pathname} = useLocation();
  const {user} = useAuth();
  const [expanded, setExpanded] = useState(readSidebarPreference);
  useEffect(() => {saveSidebarPreference(expanded);}, [expanded]);
  return <ApplicationPreferences accountId={user?.id}><div className="application-shell" data-settings={pathname.startsWith('/settings')||undefined} data-assistant={pathname.startsWith('/ai-assistant')||undefined} data-sidebar={expanded ? 'expanded' : 'minimized'}>
    <a className="application-skip-link" href="#application-main">Skip to content</a>
    <Sidebar expanded={expanded} onToggle={() => setExpanded(value => !value)}/>
    <div className="application-workspace">
      <ApplicationHeader/>
      <main id="application-main" className="application-main" tabIndex={-1}><Outlet/></main>
    </div>
  </div></ApplicationPreferences>;
}
