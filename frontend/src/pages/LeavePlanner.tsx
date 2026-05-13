import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { format } from 'date-fns'
import { api } from '../lib/api'
import type { LeaveSimulateResponse } from '../lib/api'
import { InsightCard } from '../components/ui/InsightCard'
import { StatGrid } from '../components/ui/StatGrid'
import { InfluenceBar } from '../components/ui/InfluenceBar'

const LEAVE_TYPES = ['Casual Leave', 'Medical Leave', 'Conference Leave', 'Personal Leave']

function FeasibilityGauge({ score, level, color }: { score: number; level: string; color: string }) {
  const colorMap: Record<string, string> = {
    green: 'text-green-600 bg-green-50 border-green-200',
    amber: 'text-amber-600 bg-amber-50 border-amber-200',
    red: 'text-red-600 bg-red-50 border-red-200',
  }
  const barColor: Record<string, string> = {
    green: 'bg-green-500', amber: 'bg-amber-500', red: 'bg-red-500',
  }
  return (
    <div className={`rounded-2xl border p-4 ${colorMap[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold">Feasibility Score</span>
        <span className="text-2xl font-bold">{score}/100</span>
      </div>
      <div className="w-full bg-white rounded-full h-2 mb-2">
        <div className={`${barColor[color]} h-2 rounded-full transition-all`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-semibold uppercase tracking-wide">{level.replace(/_/g, ' ')}</span>
    </div>
  )
}


export function LeavePlanner() {
  const [doctorId, setDoctorId] = useState('DR001')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [leaveType, setLeaveType] = useState('Casual Leave')
  const [duration, setDuration] = useState<'Full Day' | 'Half Day'>('Full Day')
  const [result, setResult] = useState<LeaveSimulateResponse | null>(null)

  const { data: doctors } = useQuery({
    queryKey: ['doctors'],
    queryFn: api.doctors.list,
    staleTime: Infinity,
  })

  const mutation = useMutation({
    mutationFn: () => api.leave.simulate({ doctor_id: doctorId, start_date: startDate, end_date: endDate, leave_type: leaveType, duration }),
    onSuccess: (data) => setResult(data),
  })

  const handleSimulate = () => {
    if (!startDate || !endDate) return
    mutation.mutate()
  }

  const { data: rec } = useQuery({
    queryKey: ['recommend', doctorId],
    queryFn: () => api.leave.recommend(doctorId),
    staleTime: 5 * 60 * 1000,
    enabled: !!doctorId,
  })

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Plan Your Leave with AI Assistance</h1>
        <p className="text-slate-400 text-sm">Optimize your schedule and ensure patient care continuity using predictive analytics.</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left column */}
        <div className="col-span-2 flex flex-col gap-5">
          {/* Leave configuration card */}
          <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
            <h2 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
              <span>📅</span> Leave Configuration
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-400 font-medium mb-1 block">Doctor</label>
                <select
                  value={doctorId}
                  onChange={e => setDoctorId(e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  {doctors?.map(d => (
                    <option key={d.doctor_id} value={d.doctor_id}>{d.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 font-medium mb-1 block">Leave Type</label>
                <select
                  value={leaveType}
                  onChange={e => setLeaveType(e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  {LEAVE_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 font-medium mb-1 block">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 font-medium mb-1 block">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>
            </div>

            {/* Duration toggle */}
            <div className="mt-4">
              <label className="text-xs text-slate-400 font-medium mb-2 block">Duration</label>
              <div className="flex rounded-xl border border-slate-200 overflow-hidden w-fit">
                {(['Full Day', 'Half Day'] as const).map(d => (
                  <button
                    key={d}
                    onClick={() => setDuration(d)}
                    className={`px-5 py-2 text-sm font-medium transition-colors ${
                      duration === d ? 'bg-blue-600 text-white' : 'bg-white text-slate-500 hover:bg-slate-50'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handleSimulate}
              disabled={!startDate || !endDate || mutation.isPending}
              className="mt-4 w-full bg-blue-600 text-white py-2.5 rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {mutation.isPending ? 'Simulating…' : '⚡ Simulate Impact'}
            </button>
          </div>

          {/* Feasibility result */}
          {result && (
            <>
              <FeasibilityGauge
                score={result.feasibility_score}
                level={result.feasibility_level}
                color={result.feasibility_color}
              />

              <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
                <h2 className="font-semibold text-slate-700 mb-1">Recommendation</h2>
                <p className="text-slate-600 text-sm">{result.recommendation}</p>
              </div>

              {/* Redistribution */}
              <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
                <h2 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <span>⚖️</span> Workload Redistribution
                </h2>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  {[
                    { label: 'Baseline pts/doctor', value: result.redistribution.baseline_load_per_doctor },
                    { label: 'Redistributed pts/doctor', value: result.redistribution.redistributed_load_per_doctor },
                    { label: 'Load increase', value: `+${result.redistribution.load_increase_pct}%` },
                  ].map((s, i) => (
                    <div key={i} className="bg-slate-50 rounded-xl p-3 text-center">
                      <div className="text-slate-800 text-lg font-bold">{s.value}</div>
                      <div className="text-slate-400 text-xs">{s.label}</div>
                    </div>
                  ))}
                </div>

                {result.redistribution.exceeds_safe_threshold && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-2 text-amber-700 text-sm">
                    ⚠ Redistributed load exceeds recommended limit of {result.redistribution.safe_threshold} patients/doctor
                  </div>
                )}

                {/* Day breakdown */}
                <table className="w-full text-xs mt-4">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-100">
                      <th className="text-left pb-1.5 font-medium">Date</th>
                      <th className="text-right pb-1.5 font-medium">OP</th>
                      <th className="text-right pb-1.5 font-medium">Baseline</th>
                      <th className="text-right pb-1.5 font-medium">After Leave</th>
                      <th className="text-right pb-1.5 font-medium">Demand</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.daily_breakdown.map((d, i) => (
                      <tr key={i} className="border-b border-slate-50 last:border-0">
                        <td className="py-1.5 text-slate-600">{d.day_name.slice(0,3)} {format(new Date(d.date + 'T00:00:00'), 'dd MMM')}</td>
                        <td className="py-1.5 text-right font-medium text-slate-700">{d.op_forecast}</td>
                        <td className="py-1.5 text-right text-slate-400">{d.load_per_doctor}</td>
                        <td className="py-1.5 text-right font-semibold text-blue-600">{d.redistributed_load}</td>
                        <td className="py-1.5 text-right">
                          <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${
                            d.demand_level === 'HIGH' ? 'bg-red-100 text-red-600'
                            : d.demand_level === 'LOW' ? 'bg-green-100 text-green-600'
                            : 'bg-amber-100 text-amber-600'
                          }`}>{d.demand_level}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleSimulate}
              disabled={!startDate || !endDate || mutation.isPending}
              className="flex-1 bg-slate-800 text-white py-3 rounded-xl font-semibold text-sm hover:bg-slate-900 disabled:opacity-50 transition-colors"
            >
              ✦ Generate AI Forecast & Apply
            </button>
            <button
              onClick={() => {}}
              className="flex-1 border border-blue-300 text-blue-600 py-3 rounded-xl font-semibold text-sm hover:bg-blue-50 transition-colors"
            >
              ⊕ Check Best Leave Window
            </button>
          </div>
        </div>

        {/* Right column — Insights */}
        <div className="flex flex-col gap-4">
          <InsightCard
            title="AI Forecast Insights"
            subtitle="Contextual factors influencing predicted patient load"
            footer="Model trained using Federated Learning. No patient data leaves hospital servers."
          >
            <div className="flex flex-col gap-4">
              <div>
                <div className="text-blue-200 text-xs font-semibold uppercase tracking-wide mb-2">Demand Pattern Signals</div>
                {[
                  { label: 'Weekly Demand Pattern', val: 'Elevated' },
                  { label: 'Short-Term Volatility', val: 'Stable' },
                  { label: 'Social Activity Index', val: 'Moderate' },
                  { label: 'Seasonal Respiratory', val: 'Moderate' },
                ].map((s, i) => (
                  <div key={i} className="flex justify-between text-sm py-1 border-b border-blue-500 last:border-0">
                    <span className="text-blue-200">{s.label}</span>
                    <span className="text-white font-medium">{s.val}</span>
                  </div>
                ))}
              </div>

              {result && (
                <StatGrid stats={[
                  { label: 'Avg Forecast', value: result.avg_daily_forecast },
                  { label: 'Peak Day', value: result.peak_forecast },
                  { label: 'Duration', value: `${result.duration_days}d` },
                  { label: 'Doctors Left', value: result.redistribution.remaining_doctors },
                ]} />
              )}

              <div>
                <div className="text-blue-200 text-xs font-semibold uppercase tracking-wide mb-2">AI Influence Breakdown</div>
                <InfluenceBar label="Historical Utilization" value={38} />
                <InfluenceBar label="Environmental Signals"  value={24} />
                <InfluenceBar label="Institutional Load"     value={18} />
                <InfluenceBar label="Seasonal Trends"        value={12} />
                <InfluenceBar label="Demand Dynamics"        value={8}  />
              </div>
            </div>
          </InsightCard>

          {/* Smart leave windows */}
          {rec && (
            <div className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-slate-700 text-sm">Best Leave Windows</h3>
                <span className="bg-blue-100 text-blue-600 text-xs font-semibold px-2 py-0.5 rounded-full">
                  {rec.top_windows.length}
                </span>
              </div>
              <p className="text-slate-400 text-xs mb-3">{rec.summary}</p>
              <div className="flex flex-col gap-2">
                {rec.top_windows.slice(0, 3).map((w, i) => (
                  <div key={i} className="flex items-start gap-2 py-2 border-b border-slate-50 last:border-0">
                    <div className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${
                      w.window_type === 'OPTIMAL' ? 'bg-green-400' : 'bg-amber-400'
                    }`} />
                    <div>
                      <div className="text-sm text-slate-700 font-medium">
                        {format(new Date(w.start_date + 'T00:00:00'), 'dd MMM')} – {format(new Date(w.end_date + 'T00:00:00'), 'dd MMM')}
                        <span className="text-slate-400 font-normal"> · {w.duration_days}d</span>
                      </div>
                      <div className="text-xs text-slate-400">{w.reason.split('—')[0].trim()}</div>
                    </div>
                    <ConflictTag label={w.window_type === 'OPTIMAL' ? 'BEST' : 'OK'} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ConflictTag({ label }: { label: string }) {
  const best = label === 'BEST'
  return (
    <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0 ${
      best ? 'bg-green-100 text-green-600' : 'bg-blue-100 text-blue-600'
    }`}>{label}</span>
  )
}
