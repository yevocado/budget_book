import { create } from 'zustand'

export const useTransactionStore = create((set, get) => ({
  transactions: [],
  setTransactions: (transactions) => set({ transactions }),
  handleRealtimeEvent: (payload) => {
    const { eventType, new: newRow, old: oldRow } = payload
    set((state) => {
      if (eventType === 'INSERT') {
        return { transactions: [newRow, ...state.transactions] }
      }
      if (eventType === 'UPDATE') {
        return {
          transactions: state.transactions.map((t) =>
            t.id === newRow.id ? newRow : t
          ),
        }
      }
      if (eventType === 'DELETE') {
        return {
          transactions: state.transactions.filter((t) => t.id !== oldRow.id),
        }
      }
      return state
    })
  },
}))
