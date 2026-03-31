import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/app/dashboard', icon: '🏠', label: '홈' },
  { to: '/app/transactions', icon: '📝', label: '내역' },
  { to: '/app/statistics', icon: '📊', label: '통계' },
  { to: '/app/budget', icon: '💰', label: '예산' },
  { to: '/app/settings', icon: '⚙️', label: '설정' },
]

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 flex justify-around py-2 z-40 sm:hidden">
      {navItems.map(({ to, icon, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition ${
              isActive ? 'text-pink-500' : 'text-gray-400'
            }`
          }
        >
          <span className="text-xl">{icon}</span>
          <span className="text-xs font-medium">{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
