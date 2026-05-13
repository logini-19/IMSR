import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import { api } from '../lib/api'
import { DemandBadge } from '../components/ui/DemandBadge'
import { InsightCard } from '../components/ui/InsightCard'
import { StatGrid } from '../components/ui/StatGrid'
import { InfluenceBar } from '../components/ui/InfluenceBar'

const demandColor: Record<string, string> = {
  HIGH: '#EF4444', MODERATE: '#F59E0B', LOW: '#22C55E',
}

export function Overview() {
  const { data: fc, isLoading } = useQuery({
    queryKey: ['forecasts-daily-7'],
    queryFn: () => api.forecasts.daily(7),
    staleTime: 5 * 60 * 1000,
  })

  const { data: weekly } = useQuery({
    queryKey: ['forecasts-weekly-1'],
    queryFn: () => api.forecasts.weekly(1),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) return <div className="p-8 text-slate-400">Loading forecast…</div>

  const forecasts = fc?.forecasts ?? []
  const today = forecasts[0]
  const thisWeek = weekly?.weeks[0]
  const alerts = forecasts.filter(d => d.risk_flags.length > 0)

  const chartData = forecasts.map(d => ({
    day: format(new Date(d.date + 'T00:00:00'), 'EEE dd'),
    op: d.op_forecast,
    ip: d.ip_forecast,
    level: d.demand_level,
  }))

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Overview</h1>
        <p className="text-slate-400 text-sm">Department of Pulmonology · PSG IMSR</p>
      </div>

      {/* Top stat row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Today's OP Forecast", value: today?.op_forecast ?? '—', sub: 'outpatients' },
          { label: "Today's IP Forecast",  value: today?.ip_forecast ?? '—', sub: 'inpatients' },
          { label: 'Weekly Total',          value: thisWeek?.total_footfall ?? '—', sub: 'patients this week' },
          { label: "Peak Day",              value: thisWeek ? format(new Date(thisWeek.peak_day + 'T00:00:00'), 'EEE dd MMM') : '—', sub: `${thisWeek?.peak_value ?? '—'} patients` },
        ].map((s, i) => (
          <div key={i} className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
            <div className="text-xs text-slate-400 mb-1">{s.label}</div>
            <div className="text-2xl font-bold text-slate-800">{s.value}</div>
            <div className="text-xs text-slate-400">{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* 7-day chart */}
        <div className="col-span-2 bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-700">7-Day Patient Forecast</h2>
            {today && <DemandBadge level={today.demand_level} />}
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} barGap={4}>
              <XAxis dataKey="day" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} width={36} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
              />
              <Bar dataKey="op" radius={[6, 6, 0, 0]} name="op">
                {chartData.map((d, i) => (
                  <Cell key={i} fill={demandColor[d.level]} fillOpacity={0.85} />
                ))}
              </Bar>
              <Bar dataKey="ip" radius={[6, 6, 0, 0]} fill="#93C5FD" name="ip" />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 text-xs text-slate-400">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-amber-400 inline-block" /> Outpatients</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-blue-300 inline-block" /> Inpatients</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-red-400 inline-block" /> High demand</span>
          </div>
        </div>

        {/* AI Insights panel */}
        <InsightCard
          title="AI Forecast Insights"
          subtitle="Contextual factors influencing predicted load"
          footer="Model trained using Federated Learning. No patient data leaves hospital servers."
        >
          <div className="flex flex-col gap-4">
            <StatGrid stats={[
              { label: 'Avg Daily OP', value: thisWeek?.avg_daily ?? '—' },
              { label: 'Weekly IP Total', value: thisWeek?.ip_total ?? '—' },
              { label: 'Peak Value', value: thisWeek?.peak_value ?? '—' },
              { label: 'Demand Level', value: thisWeek?.demand_level ?? '—' },
            ]} />
            <div className="flex flex-col gap-2 mt-2">
              <div className="text-blue-200 text-xs font-semibold uppercase tracking-wide">AI Influence Breakdown</div>
              <InfluenceBar label="Historical Utilization" value={38} />
              <InfluenceBar label="Environmental Signals"  value={24} />
              <InfluenceBar label="Institutional Load"     value={18} />
              <InfluenceBar label="Seasonal Trends"        value={12} />
              <InfluenceBar label="Short-Term Dynamics"    value={8}  />
            </div>
          </div>
        </InsightCard>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <h2 className="font-semibold text-slate-700">Active Alerts</h2>
            <span className="bg-red-100 text-red-600 text-xs font-semibold px-2 py-0.5 rounded-full">
              {alerts.length}
            </span>
          </div>
          <div className="flex flex-col gap-2">
            {alerts.map((d, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  d.demand_level === 'HIGH' ? 'bg-red-400' : 'bg-amber-400'
                }`} />
                <span className="text-sm text-slate-600">
                  <span className="font-medium">{format(new Date(d.date + 'T00:00:00'), 'EEE, MMM dd')}</span>
                  {' — '}
                  {d.risk_flags.join(', ').replace(/_/g, ' ')}
                </span>
                <DemandBadge level={d.demand_level} size="sm" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
