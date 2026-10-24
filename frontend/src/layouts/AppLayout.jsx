import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { ClipboardCheck, GraduationCap, LayoutDashboard, Menu, Settings, Users, X } from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/students', label: 'Students', icon: Users },
  { to: '/attendance', label: 'Attendance', icon: ClipboardCheck },
  { to: '/settings', label: 'Settings', icon: Settings },
];

function Brand() {
  return (
    <div className="flex items-center gap-3 px-2">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white">
        <GraduationCap className="h-5 w-5" aria-hidden="true" />
      </span>
      <div className="leading-tight">
        <p className="text-sm font-semibold text-ink">Attendance System</p>
        <p className="text-xs text-secondary">Student Management</p>
      </div>
    </div>
  );
}

function NavItems({ onNavigate }) {
  return (
    <ul className="space-y-1">
      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-primary ${
                isActive ? 'bg-primary-soft text-primary' : 'text-secondary hover:bg-slate-100 hover:text-ink'
              }`
            }
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
            {label}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

export default function AppLayout() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setDrawerOpen(false), [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return undefined;
    const onKey = (e) => e.key === 'Escape' && setDrawerOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [drawerOpen]);

  return (
    <div className="min-h-screen bg-white">
      <a
        href="#main"
        className="sr-only z-50 rounded-lg bg-primary px-4 py-2 text-white focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-line bg-white px-4 py-6 lg:flex">
        <Brand />
        <nav aria-label="Main" className="mt-8 flex-1">
          <NavItems />
        </nav>
        <p className="px-2 text-xs text-slate-400">v1.0 · Student module</p>
      </aside>

      {/* Mobile top bar */}
      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
        <Brand />
        <button
          type="button"
          className="icon-btn h-10 w-10"
          onClick={() => setDrawerOpen(true)}
          aria-label="Open navigation"
          aria-expanded={drawerOpen}
          aria-controls="mobile-nav"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setDrawerOpen(false)} aria-hidden="true" />
          <nav id="mobile-nav" aria-label="Main" className="absolute inset-y-0 left-0 flex w-72 flex-col bg-white px-4 py-6 shadow-xl">
            <div className="flex items-center justify-between">
              <Brand />
              <button
                type="button"
                className="icon-btn"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close navigation"
                autoFocus
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-8">
              <NavItems onNavigate={() => setDrawerOpen(false)} />
            </div>
          </nav>
        </div>
      )}

      <main id="main" className="lg:pl-64">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
