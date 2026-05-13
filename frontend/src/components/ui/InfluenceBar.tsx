interface Props { label: string; value: number; color?: string }

export function InfluenceBar({ label, value, color = 'bg-blue-300' }: Props) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-blue-200 flex-1 truncate">{label}</span>
      <div className="w-24 bg-blue-800 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-white text-xs w-8 text-right">{value}%</span>
    </div>
  )
}
