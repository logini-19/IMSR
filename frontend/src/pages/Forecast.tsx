import { useQuery } from '@tanstack/react-query'
import { format, addDays } from 'date-fns'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine, Legend,
} from 'recharts'
import { api } from '../lib/api'
import { DemandBadge } from '../components/ui/DemandBadge'
import { InsightCard } from '../components/ui/InsightCard'
import { InfluenceBar } from '../components/ui/InfluenceBar'


export function Forecast() {
  const { data: fc, isLoading } = useQuery({
    queryKey: ['forecasts-daily-28'],
    queryFn: () => api.forecasts.daily(28),
    staleTime: 5 * 60 * 1000,
  })

  const { data: weekly } = useQuery({
    queryKey: ['forecasts-weekly-4'],
    queryFn: () => api.forecasts.weekly(4),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) return <div className="p-8 text-slate-400">Loading forecast…</div>

  const forecasts = fc?.forecasts ?? []
  const avgForecast = forecasts.length
    ? Math.round(forecasts.reduce((s, d) => s + d.op_forecast, 0) / forecasts.length)
    : 0

  const chartData = forecasts.map(d => ({
    day: format(new Date(d.date + 'T00:00:00'), 'dd MMM'),
    op: d.op_forecast,
    ip: d.ip_forecast,
    lower: d.lower,
    upper: d.upper,
    level: d.demand_level,
  }))

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">28-Day Forecast</h1>
        <p className="text-slate-400 text-sm">
          {format(new Date(), 'dd MMM yyyy')} → {format(addDays(new Date(), 28), 'dd MMM yyyy')}
        </p>
      </div>

      <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-700">OP + IP Forecast with Confidence Band</h2>
            <span className="text-sm text-slate-400">Avg {avgForecast} pts/day</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} interval={3} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={36} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}
              />
              <Legend />
              <ReferenceLine y={150} stroke="#EF4444" strokeDasharray="4 4" label={{ value: 'High demand', fill: '#EF4444', fontSize: 11 }} />
              <ReferenceLine y={avgForecast} stroke="#94A3B8" strokeDasharray="3 3" />
              <Line dataKey="upper" stroke="#BFDBFE" strokeWidth={1} dot={false} name="Upper CI" />
              <Line dataKey="lower" stroke="#BFDBFE" strokeWidth={1} dot={false} name="Lower CI" />
              <Line dataKey="op" stroke="#2563EB" strokeWidth={2.5} dot={false} name="OP Forecast" />
              <Line dataKey="ip" stroke="#93C5FD" strokeWidth={1.5} dot={false} name="IP Forecast" strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>

      {/* Calendar heatmap */}
      <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
        <h2 className="font-semibold text-slate-700 mb-4">Demand Calendar</h2>
        <div className="grid grid-cols-7 gap-1.5">
          {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(d => (
            <div key={d} className="text-xs text-slate-400 text-center font-medium pb-1">{d}</div>
          ))}
          {forecasts.map((d, i) => {
            const col = d.demand_level === 'HIGH' ? 'bg-red-100 border-red-200 text-red-700'
              : d.demand_level === 'LOW' ? 'bg-green-100 border-green-200 text-green-700'
              : 'bg-amber-100 border-amber-200 text-amber-700'
            return (
              <div
                key={i}
                title={`${d.date}: ${d.op_forecast} OP + ${d.ip_forecast} IP | ${d.demand_level}`}
                className={`${col} border rounded-xl p-2 text-center cursor-default`}
              >
                <div className="text-xs font-semibold">{format(new Date(d.date + 'T00:00:00'), 'dd')}</div>
                <div className="text-xs">{d.op_forecast}</div>
              </div>
            )
          })}
        </div>
        <div className="flex gap-4 mt-3 text-xs text-slate-400">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-200 inline-block" /> Low (&lt;100)</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-200 inline-block" /> Moderate (100–150)</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-200 inline-block" /> High (&gt;150)</span>
        </div>
      </div>

      {/* Weekly table */}
      <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
        <h2 className="font-semibold text-slate-700 mb-4">Weekly Summary</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 text-xs border-b border-slate-100">
              <th className="text-left pb-2 font-medium">Week</th>
              <th className="text-right pb-2 font-medium">OP Total</th>
              <th className="text-right pb-2 font-medium">IP Total</th>
              <th className="text-right pb-2 font-medium">Avg/Day</th>
              <th className="text-right pb-2 font-medium">Peak Day</th>
              <th className="text-right pb-2 font-medium">Demand</th>
            </tr>
          </thead>
          <tbody>
            {weekly?.weeks.map((w, i) => (
              <tr key={i} className="border-b border-slate-50 last:border-0">
                <td className="py-2 text-slate-600">
                  {format(new Date(w.week_start + 'T00:00:00'), 'dd MMM')} –{' '}
                  {format(new Date(w.week_end + 'T00:00:00'), 'dd MMM')}
                </td>
                <td className="py-2 text-right font-semibold text-slate-700">{w.op_total}</td>
                <td className="py-2 text-right text-slate-500">{w.ip_total}</td>
                <td className="py-2 text-right text-slate-500">{w.avg_daily}</td>
                <td className="py-2 text-right text-slate-500">
                  {format(new Date(w.peak_day + 'T00:00:00'), 'EEE dd')} ({w.peak_value})
                </td>
                <td className="py-2 text-right">
                  <DemandBadge level={w.demand_level} size="sm" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
