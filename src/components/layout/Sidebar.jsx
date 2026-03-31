import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/app/dashboard', icon: '🏠', label: '홈' },
  { to: '/app/transactions', icon: '📝', label: '거래 내역' },
  { to: '/app/statistics', icon: '📊', label: '통계' },
  { to: '/app/budget', icon: '💰', label: '예산 관리' },
  { to: '/app/settings', icon: '⚙️', label: '설정' },
]

export default function Sidebar() {
  return (
    <aside className="hidden sm:flex flex-col w-56 min-h-screen bg-white border-r border-gray-100 py-8 px-4">
      <div className="text-2xl font-bold text-pink-500 mb-10 px-2">💑 가계부</div>
      <nav className="flex flex-col gap-1">
        {navItems.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition ${
                isActive
                  ? 'bg-pink-50 text-pink-500'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'
              }`
            }
          >
            <span>{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
