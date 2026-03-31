import { EXPENSE_CATEGORIES, INCOME_CATEGORIES } from '../../lib/constants'

export default function CategoryBadge({ category, type }) {
  const list = type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES
  const cat = list.find((c) => c.id === category) || { label: category, icon: '📦', color: '#C0C0C0' }

  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium text-white"
      style={{ backgroundColor: cat.color }}
    >
      {cat.icon} {cat.label}
    </span>
  )
}
