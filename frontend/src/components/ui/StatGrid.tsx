interface Stat { label: string; value: string | number }
interface Props { stats: [Stat, Stat, Stat?, Stat?] }

export function StatGrid({ stats }: Props) {
  const items = stats.filter(Boolean) as Stat[]
  return (
    <div className={`grid ${items.length === 4 ? 'grid-cols-2' : 'grid-cols-2'} gap-2`}>
      {items.map((s, i) => (
        <div key={i} className="bg-blue-700 rounded-xl p-3">
          <div className="text-white text-xl font-bold">{s.value}</div>
          <div className="text-blue-300 text-xs">{s.label}</div>
        </div>
      ))}
    </div>
  )
}
