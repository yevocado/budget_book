import { useEffect } from 'react'
import { supabase } from '../lib/supabase'
import { useBudgetStore } from '../store/budgetStore'
import { getYearMonth } from '../lib/utils'

export function useBudget(roomId, yearMonth = getYearMonth()) {
  const { budgets, setBudgets } = useBudgetStore()

  useEffect(() => {
    if (!roomId) return
    fetchBudgets()
  }, [roomId, yearMonth])

  async function fetchBudgets() {
    const { data } = await supabase
      .from('budgets')
      .select('*')
      .eq('room_id', roomId)
      .eq('year_month', yearMonth)

    setBudgets(data || [])
  }

  async function setBudget(category, amount) {
    return supabase
      .from('budgets')
      .upsert({ room_id: roomId, year_month: yearMonth, category: category || null, amount },
        { onConflict: 'room_id,year_month,category' })
  }

  const totalBudget = budgets.find((b) => b.category === null)?.amount ?? 0

  return { budgets, totalBudget, setBudget, refetch: fetchBudgets }
}
