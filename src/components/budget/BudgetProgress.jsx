import { formatAmount } from '../../lib/utils'

export default function BudgetProgress({ label, used, total }) {
  const pct = total > 0 ? Math.min((used / total) * 100, 100) : 0
  const over = total > 0 && used > total
  return (
    <div className="bg-white rounded-2xl p-4 shadow-sm">
      <div className="flex justify-between items-center mb-2">
        <span className="font-medium text-gray-700">{label}</span>
        <span className={`text-sm font-semibold ${over ? 'text-red-500' : 'text-gray-500'}`}>
          {formatAmount(used)} / {formatAmount(total)}
        </span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full transition-all ${over ? 'bg-red-500' : 'bg-pink-400'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {over && (
        <p className="text-xs text-red-500 mt-1">예산을 {formatAmount(used - total)} 초과했어요!</p>
      )}
    </div>
  )
}
