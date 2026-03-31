import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import { generateInviteCode } from '../lib/utils'

export function useCouple(userId) {
  const [room, setRoom] = useState(null)
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!userId) return
    fetchRoom()
  }, [userId])

  async function fetchRoom() {
    setLoading(true)
    const { data: memberData } = await supabase
      .from('room_members')
      .select('room_id, nickname, couple_rooms(*)')
      .eq('user_id', userId)
      .single()

    if (memberData) {
      setRoom(memberData.couple_rooms)
      const { data: allMembers } = await supabase
        .from('room_members')
        .select('user_id, nickname')
        .eq('room_id', memberData.room_id)
      setMembers(allMembers || [])
    }
    setLoading(false)
  }

  async function createRoom(nickname) {
    const invite_code = generateInviteCode()
    const { data: roomData, error: roomError } = await supabase
      .from('couple_rooms')
      .insert({ invite_code })
      .select()
      .single()

    if (roomError) return { error: roomError }

    const { error: memberError } = await supabase
      .from('room_members')
      .insert({ room_id: roomData.id, user_id: userId, nickname })

    if (memberError) return { error: memberError }

    setRoom(roomData)
    setMembers([{ user_id: userId, nickname }])
    return { data: roomData }
  }

  async function joinRoom(inviteCode, nickname) {
    const { data: roomData, error: roomError } = await supabase
      .from('couple_rooms')
      .select()
      .eq('invite_code', inviteCode.toUpperCase())
      .single()

    if (roomError || !roomData) return { error: '유효하지 않은 초대 코드입니다.' }

    const { data: existing } = await supabase
      .from('room_members')
      .select()
      .eq('room_id', roomData.id)

    if (existing && existing.length >= 2) return { error: '이미 2명이 연결된 방입니다.' }

    const { error: memberError } = await supabase
      .from('room_members')
      .insert({ room_id: roomData.id, user_id: userId, nickname })

    if (memberError) return { error: memberError }

    await fetchRoom()
    return { data: roomData }
  }

  return { room, members, loading, createRoom, joinRoom, refetch: fetchRoom }
}
