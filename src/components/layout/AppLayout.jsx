import { Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import Sidebar from './Sidebar'
import BottomNav from './BottomNav'
import LoadingSpinner from '../common/LoadingSpinner'

export default function AppLayout() {
  const { user, loading } = useAuth()

  if (loading) return <LoadingSpinner className="min-h-screen" />
  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 pb-20 sm:pb-0 overflow-auto">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
