import type { ReactNode } from 'react'

interface Props {
  title: string
  subtitle?: string
  children: ReactNode
  footer?: string
}

export function InsightCard({ title, subtitle, children, footer }: Props) {
  return (
    <div className="bg-blue-600 rounded-2xl p-5 text-white flex flex-col gap-4 h-full">
      <div>
        <div className="flex items-center gap-2 text-blue-200 text-xs font-medium uppercase tracking-wider mb-1">
          <span>⚡</span> {title}
        </div>
        {subtitle && <p className="text-blue-200 text-xs">{subtitle}</p>}
      </div>
      <div className="flex-1">{children}</div>
      {footer && (
        <p className="text-blue-300 text-xs border-t border-blue-500 pt-3">{footer}</p>
      )}
    </div>
  )
}
