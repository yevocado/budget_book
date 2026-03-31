import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { useTransactionStore } from '../store/transactionStore'
import { getYearMonth } from '../lib/utils'

export function useTransactions(roomId, yearMonth = getYearMonth()) {
  const { transactions, setTransactions, handleRealtimeEvent } = useTransactionStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!roomId) return
    fetchTransactions()

    const channel = supabase
      .channel(`transactions-${roomId}`)
      .on('postgres_changes', {
        event: '*',
        schema: 'public',
        table: 'transactions',
        filter: `room_id=eq.${roomId}`,
      }, handleRealtimeEvent)
      .subscribe()

    return () => supabase.removeChannel(channel)
  }, [roomId, yearMonth])

  async function fetchTransactions() {
    setLoading(true)
    const { data } = await supabase
      .from('transactions')
      .select('*')
      .eq('room_id', roomId)
      .gte('date', `${yearMonth}-01`)
      .lte('date', `${yearMonth}-31`)
      .order('date', { ascending: false })

    setTransactions(data || [])
    setLoading(false)
  }

  async function addTransaction(tx) {
    return supabase.from('transactions').insert({ ...tx, room_id: roomId })
  }

  async function updateTransaction(id, tx) {
    return supabase.from('transactions').update({ ...tx, updated_at: new Date().toISOString() }).eq('id', id)
  }

  async function deleteTransaction(id) {
    return supabase.from('transactions').delete().eq('id', id)
  }

  const totalIncome = transactions.filter((t) => t.type === 'income').reduce((s, t) => s + t.amount, 0)
  const totalExpense = transactions.filter((t) => t.type === 'expense').reduce((s, t) => s + t.amount, 0)

  return { transactions, loading, totalIncome, totalExpense, addTransaction, updateTransaction, deleteTransaction }
}
