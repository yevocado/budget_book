import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useCouple } from '../hooks/useCouple'
import { useTransactions } from '../hooks/useTransactions'
import { useBudget } from '../hooks/useBudget'
import { formatAmount, getYearMonth } from '../lib/utils'
import TransactionList from '../components/transactions/TransactionList'
import Modal from '../components/common/Modal'
import TransactionForm from '../components/transactions/TransactionForm'
import Button from '../components/common/Button'
import LoadingSpinner from '../components/common/LoadingSpinner'
import { Navigate } from 'react-router-dom'

export default function DashboardPage() {
  const { user } = useAuth()
  const { room, loading: coupleLoading } = useCouple(user?.id)
  const yearMonth = getYearMonth()
  const { transactions, loading, totalIncome, totalExpense, addTransaction } = useTransactions(room?.id, yearMonth)
  const { totalBudget } = useBudget(room?.id, yearMonth)
  const [showForm, setShowForm] = useState(false)

  if (coupleLoading) return <LoadingSpinner className="min-h-screen" />
  if (!room) return <Navigate to="/app/settings" replace />

  const balance = totalIncome - totalExpense
  const budgetUsedPct = totalBudget > 0 ? Math.min((totalExpense / totalBudget) * 100, 100) : 0

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-800">{yearMonth.replace('-', '년 ')}월</h1>
          <p className="text-sm text-gray-400">우리의 가계부</p>
        </div>
        <Button onClick={() => setShowForm(true)}>+ 추가</Button>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-white rounded-2xl p-4 shadow-sm text-center">
          <p className="text-xs text-gray-400 mb-1">수입</p>
          <p className="font-bold text-blue-500 text-sm">{formatAmount(totalIncome)}</p>
        </div>
        <div className="bg-white rounded-2xl p-4 shadow-sm text-center">
          <p className="text-xs text-gray-400 mb-1">지출</p>
          <p className="font-bold text-red-500 text-sm">{formatAmount(totalExpense)}</p>
        </div>
        <div className="bg-white rounded-2xl p-4 shadow-sm text-center">
          <p className="text-xs text-gray-400 mb-1">잔액</p>
          <p className={`font-bold text-sm ${balance >= 0 ? 'text-gray-800' : 'text-red-500'}`}>{formatAmount(balance)}</p>
        </div>
      </div>

      {totalBudget > 0 && (
        <div className="bg-white rounded-2xl p-4 shadow-sm mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="font-medium text-gray-700">이번달 예산</span>
            <span className={`font-semibold ${budgetUsedPct >= 100 ? 'text-red-500' : 'text-gray-500'}`}>
              {formatAmount(totalExpense)} / {formatAmount(totalBudget)}
            </span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all ${budgetUsedPct >= 100 ? 'bg-red-500' : 'bg-pink-400'}`}
              style={{ width: `${budgetUsedPct}%` }}
            />
          </div>
        </div>
      )}

      <h2 className="font-bold text-gray-700 mb-3">최근 거래</h2>
      <TransactionList transactions={transactions.slice(0, 5)} loading={loading} />

      <Modal open={showForm} onClose={() => setShowForm(false)} title="거래 추가">
        <TransactionForm
          onSubmit={(tx) => addTransaction({ ...tx, user_id: user.id })}
          onClose={() => setShowForm(false)}
        />
      </Modal>
    </div>
  )
}
