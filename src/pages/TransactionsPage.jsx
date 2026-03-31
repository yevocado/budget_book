import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useCouple } from '../hooks/useCouple'
import { useTransactions } from '../hooks/useTransactions'
import { getYearMonth } from '../lib/utils'
import TransactionList from '../components/transactions/TransactionList'
import TransactionForm from '../components/transactions/TransactionForm'
import Modal from '../components/common/Modal'
import Button from '../components/common/Button'
import { Navigate } from 'react-router-dom'
import LoadingSpinner from '../components/common/LoadingSpinner'

export default function TransactionsPage() {
  const { user } = useAuth()
  const { room, loading: coupleLoading } = useCouple(user?.id)
  const [yearMonth, setYearMonth] = useState(getYearMonth())
  const { transactions, loading, addTransaction, updateTransaction, deleteTransaction } = useTransactions(room?.id, yearMonth)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [filter, setFilter] = useState('all')

  if (coupleLoading) return <LoadingSpinner className="min-h-screen" />
  if (!room) return <Navigate to="/app/settings" replace />

  const filtered = transactions.filter((t) => filter === 'all' || t.type === filter)

  function handleEdit(tx) { setEditing(tx); setShowForm(true) }
  function handleClose() { setEditing(null); setShowForm(false) }

  async function handleDelete(id) {
    if (confirm('삭제할까요?')) await deleteTransaction(id)
  }

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">거래 내역</h1>
        <Button onClick={() => setShowForm(true)}>+ 추가</Button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <input
          type="month"
          value={yearMonth}
          onChange={(e) => setYearMonth(e.target.value)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-pink-400"
        />
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
          {[['all', '전체'], ['expense', '지출'], ['income', '수입']].map(([v, l]) => (
            <button
              key={v}
              onClick={() => setFilter(v)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition ${filter === v ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-400'}`}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      <TransactionList transactions={filtered} loading={loading} onEdit={handleEdit} onDelete={handleDelete} />

      <Modal open={showForm} onClose={handleClose} title={editing ? '거래 수정' : '거래 추가'}>
        <TransactionForm
          initial={editing}
          onSubmit={(tx) =>
            editing
              ? updateTransaction(editing.id, tx)
              : addTransaction({ ...tx, user_id: user.id })
          }
          onClose={handleClose}
        />
      </Modal>
    </div>
  )
}
