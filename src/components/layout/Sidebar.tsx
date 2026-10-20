import {useEffect, useId, useRef, useState, type ReactElement} from 'react';
import {createPortal} from 'react-dom';
import {NavLink} from 'react-router-dom';
import {PanelLeftClose, PanelLeftOpen} from 'lucide-react';
import {navigationItems} from './navigation';

/** Tooltips live outside the navigation scroll container, so they cannot be clipped. */
function Tooltip({label, enabled = true, children}: {
  label: string; enabled?: boolean; children: (tooltipId: string | undefined) => ReactElement;
}) {
  const id = useId();
  const target = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{left: number; top: number} | null>(null);
  const show = () => {
    const rect = target.current?.getBoundingClientRect();
    if (enabled && rect) setPosition({left: rect.right + 8, top: rect.top + rect.height / 2});
  };
  const hide = () => setPosition(null);
  const visible = enabled && position !== null;
  useEffect(() => {
    if (!visible) return;
    const dismiss = () => setPosition(null);
    const escape = (event: KeyboardEvent) => {if (event.key === 'Escape') dismiss();};
    document.addEventListener('keydown', escape);
    window.addEventListener('resize', dismiss);
    window.addEventListener('scroll', dismiss, true);
    return () => {
      document.removeEventListener('keydown', escape);
      window.removeEventListener('resize', dismiss);
      window.removeEventListener('scroll', dismiss, true);
    };
  }, [visible]);
  return <div className="sidebar-tooltip-anchor" ref={target} onMouseEnter={show} onMouseLeave={hide}
    onFocus={show} onBlur={hide} onClick={hide} onKeyDown={event => {if (event.key === 'Escape') hide();}}>
    {children(visible ? id : undefined)}
    {visible && createPortal(<span className="sidebar-tooltip" id={id} role="tooltip"
      style={{left: position.left, top: position.top}}>{label}</span>, document.body)}
  </div>;
}

export function Sidebar({expanded, onToggle}: {expanded: boolean; onToggle: () => void}) {
  const action = expanded ? 'Minimize sidebar' : 'Expand sidebar';
  const renderItem = (item: typeof navigationItems[number]) =>
    <Tooltip key={item.path} label={item.label} enabled={!expanded}>{tooltipId =>
      <NavLink to={item.path} aria-label={item.label} aria-describedby={tooltipId}
        className={({isActive}) => `sidebar-link${isActive ? ' is-active' : ''}`}>
        <span className="sidebar-icon" aria-hidden="true"
          style={{maskImage: `url(/assets/sidebar/${item.icon}.svg)`, WebkitMaskImage: `url(/assets/sidebar/${item.icon}.svg)`}}/>
        <span className="sidebar-label" aria-hidden="true">{item.label}</span>
      </NavLink>}
    </Tooltip>;
  return <aside className="app-sidebar" aria-label="Application sidebar">
    <NavLink to="/overview" className="sidebar-brand" aria-label="FINCEPT home">
      <img src="/assets/sidebar/logo-mark.svg" width="38" height="38" alt=""/>
      <span className="sidebar-wordmark" aria-hidden="true">FINCEPT</span>
    </NavLink>
    <nav id="application-navigation" className="sidebar-navigation" aria-label="Main navigation">
      {navigationItems.slice(0, -1).map(renderItem)}
    </nav>
    <div className="sidebar-footer">
      <Tooltip label={action}>{tooltipId =>
        <button type="button" className="sidebar-toggle" onClick={onToggle} aria-label={action}
          aria-expanded={expanded} aria-controls="application-navigation" aria-describedby={tooltipId}>
          {expanded ? <PanelLeftClose size={22} aria-hidden="true"/> : <PanelLeftOpen size={22} aria-hidden="true"/>}
          <span className="sidebar-label" aria-hidden="true">Minimize sidebar</span>
        </button>}
      </Tooltip>
      <nav aria-label="Settings navigation">{renderItem(navigationItems[10])}</nav>
    </div>
  </aside>;
}
