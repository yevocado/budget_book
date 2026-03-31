import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { EXPENSE_CATEGORIES } from '../../lib/constants'

export default function CategoryPieChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-48 text-gray-400">데이터가 없어요</div>
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={data} dataKey="amount" nameKey="label" cx="50%" cy="50%" outerRadius={90} label={({ label, percent }) => `${label} ${(percent * 100).toFixed(0)}%`}>
          {data.map((entry, index) => {
            const cat = EXPENSE_CATEGORIES.find((c) => c.id === entry.category)
            return <Cell key={index} fill={cat?.color || '#C0C0C0'} />
          })}
        </Pie>
        <Tooltip formatter={(v) => `${v.toLocaleString()}원`} />
      </PieChart>
    </ResponsiveContainer>
  )
}
