interface Props { level: string; size?: 'sm' | 'md' }

const styles: Record<string, string> = {
  HIGH:     'bg-red-100 text-red-700 border border-red-200',
  MODERATE: 'bg-amber-100 text-amber-700 border border-amber-200',
  LOW:      'bg-green-100 text-green-700 border border-green-200',
}

export function DemandBadge({ level, size = 'md' }: Props) {
  const base = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
  return (
    <span className={`${base} font-semibold rounded-full ${styles[level] ?? styles.MODERATE}`}>
      {level}
    </span>
  )
}
