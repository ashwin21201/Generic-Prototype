import { Link, Outlet, useLocation } from 'react-router-dom'

const navItems = [
  { path: '/', label: 'Dashboard' },
  { path: '/intent-builder', label: 'Intent Builder' },
  { path: '/topologies', label: 'Projects / Topologies' },
  { path: '/legacy', label: 'Legacy Chat' },
  { path: '/intent-schema', label: 'Intent Schema' },
  { path: '/blocks', label: 'Block Registry' },
  { path: '/policy', label: 'Policy Rules' },
  { path: '/impact', label: 'Impact Analysis' },
  { path: '/audit', label: 'Audit Log' },
]

export default function Layout() {
  const location = useLocation()
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{ width: 220, padding: 16, borderRight: '1px solid #eee', background: '#fafafa' }}>
        <h2 style={{ fontSize: 18, marginBottom: 16 }}>Configurator</h2>
        <nav>
          {navItems.map(({ path, label }) => (
            <Link
              key={path}
              to={path}
              style={{
                display: 'block',
                padding: '8px 12px',
                marginBottom: 4,
                borderRadius: 6,
                textDecoration: 'none',
                color: location.pathname === path ? '#fff' : '#333',
                background: location.pathname === path ? '#2563eb' : 'transparent',
              }}
            >
              {label}
            </Link>
          ))}
        </nav>
      </aside>
      <main style={{ flex: 1, padding: 24, overflow: 'auto' }}>
        <Outlet />
      </main>
    </div>
  )
}
