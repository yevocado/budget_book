import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useCouple } from '../hooks/useCouple'
import InviteCodeBox from '../components/couple/InviteCodeBox'
import PartnerStatus from '../components/couple/PartnerStatus'
import Button from '../components/common/Button'
import Input from '../components/common/Input'
import LoadingSpinner from '../components/common/LoadingSpinner'

export default function SettingsPage() {
  const { user, signOut } = useAuth()
  const { room, members, loading, createRoom, joinRoom, refetch } = useCouple(user?.id)
  const [nickname, setNickname] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [error, setError] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  if (loading) return <LoadingSpinner className="min-h-screen" />

  async function handleCreate() {
    if (!nickname.trim()) { setError('닉네임을 입력해주세요.'); return }
    setActionLoading(true)
    const { error } = await createRoom(nickname.trim())
    if (error) setError(typeof error === 'string' ? error : error.message)
    setActionLoading(false)
  }

  async function handleJoin() {
    if (!nickname.trim()) { setError('닉네임을 입력해주세요.'); return }
    if (!inviteCode.trim()) { setError('초대 코드를 입력해주세요.'); return }
    setActionLoading(true)
    const { error } = await joinRoom(inviteCode.trim(), nickname.trim())
    if (error) setError(typeof error === 'string' ? error : error.message)
    setActionLoading(false)
  }

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-6">
      <h1 className="text-xl font-bold text-gray-800 mb-6">설정</h1>

      {room ? (
        <div className="flex flex-col gap-4">
          <PartnerStatus members={members} currentUserId={user.id} />
          <InviteCodeBox code={room.invite_code} />
          <div className="text-xs text-gray-400 text-center">
            파트너에게 초대 코드를 공유해서 연결하세요
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-6 shadow-sm flex flex-col gap-4">
          <h2 className="font-bold text-gray-700">커플 연결하기</h2>
          <Input
            label="닉네임"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="상대방에게 표시될 이름"
          />
          {error && <p className="text-sm text-red-500">{error}</p>}
          <Button onClick={handleCreate} disabled={actionLoading} className="w-full">
            {actionLoading ? '처리 중...' : '새 방 만들기'}
          </Button>

          <div className="flex items-center gap-3 my-2">
            <div className="flex-1 h-px bg-gray-200" />
            <span className="text-xs text-gray-400">또는</span>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          <Input
            label="초대 코드"
            value={inviteCode}
            onChange={(e) => setInviteCode(e.target.value)}
            placeholder="8자리 초대 코드 입력"
            maxLength={8}
          />
          <Button variant="outline" onClick={handleJoin} disabled={actionLoading} className="w-full">
            {actionLoading ? '처리 중...' : '코드로 참여하기'}
          </Button>
        </div>
      )}

      <div className="mt-8">
        <p className="text-sm text-gray-400 mb-2">로그인된 계정: {user?.email}</p>
        <Button variant="secondary" onClick={signOut} className="w-full">로그아웃</Button>
      </div>
    </div>
  )
}
