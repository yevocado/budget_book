import { useState } from 'react'
import Button from '../common/Button'
import Input from '../common/Input'

export default function BudgetSetForm({ label, currentAmount, onSave, onClose }) {
  const [amount, setAmount] = useState(String(currentAmount || ''))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!amount || isNaN(Number(amount)) || Number(amount) <= 0) {
      setError('금액을 올바르게 입력해주세요.')
      return
    }
    setLoading(true)
    const { error } = await onSave(Number(amount))
    if (error) setError(error.message)
    else onClose()
    setLoading(false)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <p className="text-gray-600 text-sm">{label}</p>
      <Input
        label="예산 금액"
        type="number"
        placeholder="0"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        required
      />
      {error && <p className="text-sm text-red-500">{error}</p>}
      <div className="flex gap-2">
        <Button type="button" variant="secondary" onClick={onClose} className="flex-1">취소</Button>
        <Button type="submit" disabled={loading} className="flex-1">{loading ? '저장 중...' : '저장'}</Button>
      </div>
    </form>
  )
}
