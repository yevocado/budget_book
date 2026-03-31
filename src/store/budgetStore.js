import { create } from 'zustand'

export const useBudgetStore = create((set) => ({
  budgets: [],
  setBudgets: (budgets) => set({ budgets }),
}))
