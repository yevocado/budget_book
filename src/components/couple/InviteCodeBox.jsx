import { useState } from 'react'
import Button from '../common/Button'

export default function InviteCodeBox({ code }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-pink-50 border border-pink-200 rounded-2xl p-4 flex items-center justify-between gap-4">
      <div>
        <p className="text-xs text-pink-400 mb-1">초대 코드</p>
        <p className="text-2xl font-bold tracking-widest text-pink-600">{code}</p>
      </div>
      <Button variant="outline" onClick={copy} className="shrink-0">
        {copied ? '✅ 복사됨' : '복사'}
      </Button>
    </div>
  )
}
