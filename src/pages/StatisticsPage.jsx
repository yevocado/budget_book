import { useState, useMemo } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useCouple } from '../hooks/useCouple'
import { useTransactions } from '../hooks/useTransactions'
import { getYearMonth } from '../lib/utils'
import { EXPENSE_CATEGORIES } from '../lib/constants'
import MonthlyBarChart from '../components/charts/MonthlyBarChart'
import CategoryPieChart from '../components/charts/CategoryPieChart'
import TrendLineChart from '../components/charts/TrendLineChart'
import LoadingSpinner from '../components/common/LoadingSpinner'
import { Navigate } from 'react-router-dom'

export default function StatisticsPage() {
  const { user } = useAuth()
  const { room, loading: coupleLoading } = useCouple(user?.id)
  const [yearMonth, setYearMonth] = useState(getYearMonth())
  const { transactions, loading } = useTransactions(room?.id, yearMonth)

  const categoryData = useMemo(() => {
    const map = {}
    transactions.filter((t) => t.type === 'expense').forEach((t) => {
      map[t.category] = (map[t.category] || 0) + t.amount
    })
    return Object.entries(map).map(([category, amount]) => {
      const cat = EXPENSE_CATEGORIES.find((c) => c.id === category)
      return { category, label: cat?.label || category, amount }
    }).sort((a, b) => b.amount - a.amount)
  }, [transactions])

  const trendData = useMemo(() => {
    const map = {}
    transactions.filter((t) => t.type === 'expense').forEach((t) => {
      map[t.date] = (map[t.date] || 0) + t.amount
    })
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b)).map(([date, amount]) => ({ date: date.slice(5), amount }))
  }, [transactions])

  if (coupleLoading) return <LoadingSpinner className="min-h-screen" />
  if (!room) return <Navigate to="/app/settings" replace />

  const [year, month] = yearMonth.split('-')
  const monthlyData = [{ month: `${month}월`, income: transactions.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0), expense: transactions.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0) }]

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">통계</h1>
        <input
          type="month"
          value={yearMonth}
          onChange={(e) => setYearMonth(e.target.value)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-pink-400"
        />
      </div>

      {loading ? <LoadingSpinner className="py-12" /> : (
        <div className="flex flex-col gap-6">
          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <h2 className="font-bold text-gray-700 mb-4">수입 / 지출</h2>
            <MonthlyBarChart data={monthlyData} />
          </div>

          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <h2 className="font-bold text-gray-700 mb-4">카테고리별 지출</h2>
            <CategoryPieChart data={categoryData} />
          </div>

          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <h2 className="font-bold text-gray-700 mb-4">일별 지출 추이</h2>
            <TrendLineChart data={trendData} />
          </div>
        </div>
      )}
    </div>
  )
}
