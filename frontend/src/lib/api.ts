const BASE = '/api/v1'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface DailyForecast {
  date: string
  op_forecast: number
  ip_forecast: number
  total_forecast: number
  lower: number
  upper: number
  demand_level: 'HIGH' | 'MODERATE' | 'LOW'
  risk_flags: string[]
}

export interface WeeklyForecast {
  week_start: string
  week_end: string
  op_total: number
  ip_total: number
  total_footfall: number
  peak_day: string
  peak_value: number
  avg_daily: number
  demand_level: string
}

export interface ForecastRangeResponse {
  generated_at: string
  horizon_days: number
  forecasts: DailyForecast[]
}

export interface WeeklyForecastResponse {
  generated_at: string
  weeks: WeeklyForecast[]
}

export interface Doctor {
  doctor_id: string
  name: string
  specialization: string
  join_date: string
  max_patients_per_day: number
  is_active: number
}

export interface RedistributionPlan {
  doctors_on_leave: number
  remaining_doctors: number
  baseline_load_per_doctor: number
  redistributed_load_per_doctor: number
  load_increase_pct: number
  exceeds_safe_threshold: boolean
  safe_threshold: number
}

export interface DailyLeaveBreakdown {
  date: string
  day_name: string
  op_forecast: number
  ip_forecast: number
  total_forecast: number
  doctors_available: number
  load_per_doctor: number
  redistributed_load: number
  demand_level: string
  risk_flags: string[]
}

export interface LeaveSimulateResponse {
  doctor_id: string
  doctor_name: string
  leave_type: string
  start_date: string
  end_date: string
  duration_days: number
  feasibility_score: number
  feasibility_level: string
  feasibility_color: string
  recommendation: string
  avg_daily_forecast: number
  peak_day: string
  peak_forecast: number
  redistribution: RedistributionPlan
  daily_breakdown: DailyLeaveBreakdown[]
}

export interface SmartLeaveWindow {
  start_date: string
  end_date: string
  duration_days: number
  avg_daily_forecast: number
  avg_load_per_doctor: number
  window_type: string
  score: number
  reason: string
}

export interface LeaveCalendarDay {
  date: string
  day_name: string
  op_forecast: number
  load_per_doctor: number
  window_type: string
  color: string
  reason: string
  is_holiday: boolean
  is_weekend: boolean
}

export interface SmartLeaveResponse {
  doctor_id: string
  doctor_name: string
  analysis_from: string
  analysis_to: string
  top_windows: SmartLeaveWindow[]
  calendar: LeaveCalendarDay[]
  summary: string
}

export interface FLRound {
  round_number: number
  started_at: string
  completed_at: string | null
  participating_nodes: number
  status: string
  train_loss: number | null
  val_loss: number | null
}

export interface FLStatusResponse {
  model_version: string
  last_trained: string | null
  total_rounds: number
  current_round: FLRound | null
  history: FLRound[]
  node_status: string
}

// ── API calls ──────────────────────────────────────────────────────────────

export const api = {
  forecasts: {
    daily: (days = 14) => get<ForecastRangeResponse>(`/forecasts/daily?days=${days}`),
    weekly: (weeks = 4) => get<WeeklyForecastResponse>(`/forecasts/weekly?weeks=${weeks}`),
  },
  doctors: {
    list: () => get<Doctor[]>('/doctors'),
    get: (id: string) => get<Doctor>(`/doctors/${id}`),
  },
  leave: {
    simulate: (body: {
      doctor_id: string
      start_date: string
      end_date: string
      leave_type?: string
      duration?: string
    }) => post<LeaveSimulateResponse>('/leave/simulate', body),
    recommend: (doctorId: string) =>
      get<SmartLeaveResponse>(`/leave/recommend/${doctorId}`),
  },
  fl: {
    status: () => get<FLStatusResponse>('/fl/status'),
    train: (num_rounds = 3, target = 'op_count') =>
      post('/fl/train', { num_rounds, target }),
  },
}
