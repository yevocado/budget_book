import TransactionItem from './TransactionItem'
import LoadingSpinner from '../common/LoadingSpinner'

export default function TransactionList({ transactions, loading, onEdit, onDelete }) {
  if (loading) return <LoadingSpinner className="py-12" />
  if (transactions.length === 0) {
    return <div className="text-center py-12 text-gray-400">거래 내역이 없어요 🥲</div>
  }
  return (
    <div className="flex flex-col gap-3">
      {transactions.map((tx) => (
        <TransactionItem key={tx.id} tx={tx} onEdit={onEdit} onDelete={onDelete} />
      ))}
    </div>
  )
}
