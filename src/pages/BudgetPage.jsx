import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useCouple } from '../hooks/useCouple'
import { useTransactions } from '../hooks/useTransactions'
import { useBudget } from '../hooks/useBudget'
import { getYearMonth } from '../lib/utils'
import { EXPENSE_CATEGORIES } from '../lib/constants'
import BudgetProgress from '../components/budget/BudgetProgress'
import BudgetSetForm from '../components/budget/BudgetSetForm'
import Modal from '../components/common/Modal'
import Button from '../components/common/Button'
import LoadingSpinner from '../components/common/LoadingSpinner'
import { Navigate } from 'react-router-dom'

export default function BudgetPage() {
  const { user } = useAuth()
  const { room, loading: coupleLoading } = useCouple(user?.id)
  const yearMonth = getYearMonth()
  const { transactions } = useTransactions(room?.id, yearMonth)
  const { budgets, totalBudget, setBudget, refetch } = useBudget(room?.id, yearMonth)
  const [editingCategory, setEditingCategory] = useState(undefined)
  const [showModal, setShowModal] = useState(false)

  if (coupleLoading) return <LoadingSpinner className="min-h-screen" />
  if (!room) return <Navigate to="/app/settings" replace />

  const totalExpense = transactions.filter((t) => t.type === 'expense').reduce((s, t) => s + t.amount, 0)

  function getExpenseByCategory(catId) {
    return transactions.filter((t) => t.type === 'expense' && t.category === catId).reduce((s, t) => s + t.amount, 0)
  }

  function getBudgetByCategory(catId) {
    return budgets.find((b) => b.category === catId)?.amount ?? 0
  }

  function openEdit(category) {
    setEditingCategory(category)
    setShowModal(true)
  }

  async function handleSave(amount) {
    const { error } = await setBudget(editingCategory ?? null, amount)
    if (!error) { refetch(); setShowModal(false) }
    return { error }
  }

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">예산 관리</h1>
        <span className="text-sm text-gray-400">{yearMonth.replace('-', '년 ')}월</span>
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-700">전체 예산</h2>
          <Button variant="outline" onClick={() => openEdit(null)} className="text-sm py-1.5">설정</Button>
        </div>
        {totalBudget > 0
          ? <BudgetProgress label="전체" used={totalExpense} total={totalBudget} />
          : <div className="text-sm text-gray-400 bg-gray-50 rounded-2xl p-4">예산을 설정해보세요</div>
        }

        <h2 className="font-semibold text-gray-700 mt-2">카테고리별 예산</h2>
        {EXPENSE_CATEGORIES.map((cat) => {
          const catBudget = getBudgetByCategory(cat.id)
          const catExpense = getExpenseByCategory(cat.id)
          return (
            <div key={cat.id} className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{cat.icon} {cat.label}</span>
                <Button variant="secondary" onClick={() => openEdit(cat.id)} className="text-xs py-1 px-3">설정</Button>
              </div>
              {catBudget > 0 && <BudgetProgress label={cat.label} used={catExpense} total={catBudget} />}
            </div>
          )
        })}
      </div>

      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title={editingCategory === null ? '전체 예산 설정' : `${EXPENSE_CATEGORIES.find((c) => c.id === editingCategory)?.label} 예산 설정`}
      >
        <BudgetSetForm
          label="이번 달 예산 금액을 입력해주세요"
          currentAmount={editingCategory === null ? totalBudget : getBudgetByCategory(editingCategory)}
          onSave={handleSave}
          onClose={() => setShowModal(false)}
        />
      </Modal>
    </div>
  )
}
