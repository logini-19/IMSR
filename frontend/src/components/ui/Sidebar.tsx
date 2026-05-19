import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, TrendingUp, CalendarDays,
} from 'lucide-react'

const links = [
  { to: '/',        icon: LayoutDashboard, label: 'Overview' },
  { to: '/forecast', icon: TrendingUp,      label: 'Forecast' },
  { to: '/leave',    icon: CalendarDays,    label: 'Leave Planner' },
]

export function Sidebar() {
  return (
    <aside className="w-60 bg-white border-r border-slate-200 min-h-screen flex flex-col">
      <div className="px-6 py-5 border-b border-slate-100">
        <div className="text-blue-600 font-bold text-lg leading-tight">PSG IMSR</div>
        <div className="text-slate-400 text-xs">Pulmonology · AI Forecast</div>
      </div>
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-600'
                  : 'text-slate-600 hover:bg-slate-50'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-6 py-4 border-t border-slate-100">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-400" />
          <span className="text-xs text-slate-400">Node Online · FL v5.0</span>
        </div>
      </div>
    </aside>
  )
}
