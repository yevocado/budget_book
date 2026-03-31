import CategoryBadge from './CategoryBadge'
import { formatAmount, formatDate } from '../../lib/utils'

export default function TransactionItem({ tx, onEdit, onDelete }) {
  return (
    <div className="flex items-center gap-3 p-4 bg-white rounded-2xl shadow-sm hover:shadow-md transition">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <CategoryBadge category={tx.category} type={tx.type} />
          <span className="text-xs text-gray-400">{formatDate(tx.date)}</span>
        </div>
        {tx.memo && <p className="text-sm text-gray-600 truncate">{tx.memo}</p>}
      </div>
      <div className="flex items-center gap-2">
        <span className={`font-bold text-base ${tx.type === 'income' ? 'text-blue-500' : 'text-red-500'}`}>
          {tx.type === 'income' ? '+' : '-'}{formatAmount(tx.amount)}
        </span>
        <button onClick={() => onEdit(tx)} className="text-gray-300 hover:text-gray-500 text-sm">✏️</button>
        <button onClick={() => onDelete(tx.id)} className="text-gray-300 hover:text-red-400 text-sm">🗑️</button>
      </div>
    </div>
  )
}
