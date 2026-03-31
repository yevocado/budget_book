export default function PartnerStatus({ members, currentUserId }) {
  const me = members.find((m) => m.user_id === currentUserId)
  const partner = members.find((m) => m.user_id !== currentUserId)

  return (
    <div className="flex items-center gap-6 bg-white rounded-2xl p-4 shadow-sm">
      <div className="flex flex-col items-center gap-1">
        <div className="w-12 h-12 rounded-full bg-pink-100 flex items-center justify-center text-xl">👤</div>
        <span className="text-sm font-medium text-gray-700">{me?.nickname || '나'}</span>
        <span className="text-xs text-pink-400">나</span>
      </div>
      <div className="text-2xl flex-1 text-center">💑</div>
      <div className="flex flex-col items-center gap-1">
        <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-xl">👤</div>
        <span className="text-sm font-medium text-gray-700">{partner?.nickname || '?'}</span>
        <span className="text-xs text-blue-400">{partner ? '파트너' : '대기 중'}</span>
      </div>
    </div>
  )
}
