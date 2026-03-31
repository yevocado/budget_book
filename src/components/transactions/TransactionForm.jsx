import { useState } from 'react'
import { EXPENSE_CATEGORIES, INCOME_CATEGORIES } from '../../lib/constants'
import Button from '../common/Button'
import Input from '../common/Input'

const defaultForm = { type: 'expense', amount: '', category: 'food', date: new Date().toISOString().slice(0, 10), memo: '' }

export default function TransactionForm({ onSubmit, onClose, initial = null }) {
  const [form, setForm] = useState(initial ? { ...initial, amount: String(initial.amount) } : defaultForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const categories = form.type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.amount || isNaN(Number(form.amount)) || Number(form.amount) <= 0) {
      setError('금액을 올바르게 입력해주세요.')
      return
    }
    setLoading(true)
    const { error } = await onSubmit({ ...form, amount: Number(form.amount) })
    if (error) setError(error.message)
    else onClose()
    setLoading(false)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex gap-2">
        {['expense', 'income'].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => { set('type', t); set('category', t === 'income' ? 'salary' : 'food') }}
            className={`flex-1 py-2 rounded-xl font-semibold transition ${
              form.type === t
                ? t === 'expense' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'
                : 'bg-gray-100 text-gray-400'
            }`}
          >
            {t === 'expense' ? '지출' : '수입'}
          </button>
        ))}
      </div>

      <Input
        label="금액"
        type="number"
        placeholder="0"
        value={form.amount}
        onChange={(e) => set('amount', e.target.value)}
        required
      />

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">카테고리</label>
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => set('category', cat.id)}
              className={`px-3 py-1.5 rounded-full text-sm transition ${
                form.category === cat.id ? 'text-white' : 'bg-gray-100 text-gray-600'
              }`}
              style={form.category === cat.id ? { backgroundColor: cat.color } : {}}
            >
              {cat.icon} {cat.label}
            </button>
          ))}
        </div>
      </div>

      <Input label="날짜" type="date" value={form.date} onChange={(e) => set('date', e.target.value)} required />
      <Input label="메모 (선택)" value={form.memo} onChange={(e) => set('memo', e.target.value)} placeholder="간단한 메모" />

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="flex gap-2 mt-2">
        <Button type="button" variant="secondary" onClick={onClose} className="flex-1">취소</Button>
        <Button type="submit" disabled={loading} className="flex-1">{loading ? '저장 중...' : '저장'}</Button>
      </div>
    </form>
  )
}
