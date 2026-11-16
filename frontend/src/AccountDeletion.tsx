import { useState } from 'react'
import type { FormEvent } from 'react'

/**
 * 회원 탈퇴: 비밀번호 재입력 + 영구 삭제 동의 + 마지막 확인 창.
 * 실제 삭제는 서버(/api/account/delete)가 하며, 계정과 모든 기록을 즉시 지운다.
 */
export function AccountDeletion({disabled,onDelete}:{disabled:boolean;onDelete:(password:string)=>Promise<void>}) {
 const [busy,setBusy]=useState(false)
 const [error,setError]=useState('')
 async function submit(e:FormEvent<HTMLFormElement>) {
  e.preventDefault()
  const form=e.currentTarget
  const password=String(new FormData(form).get('password')??'')
  if(!window.confirm('정말 탈퇴할까요? 이 계정과 모든 기록이 즉시 영구 삭제되며 되돌릴 수 없습니다.'))return
  setBusy(true);setError('')
  try{await onDelete(password);form.reset()}
  catch(err){setError((err as Error).message)}
  finally{setBusy(false)}
 }
 return <details className="account-delete">
  <summary>회원 탈퇴</summary>
  <p>탈퇴하면 이 계정과 <strong>모든 기록(프로필·신체 측정·식사·운동·활동 계획)</strong>이 즉시 영구 삭제됩니다. 되돌릴 수 없습니다.</p>
  <p className="account-delete-note">DB 서비스(Neon)의 장애 복구용 변경 기록에는 최대 6시간 남은 뒤 사라집니다.</p>
  <form onSubmit={submit}>
   <label>비밀번호 확인<input name="password" type="password" autoComplete="current-password" required minLength={4} maxLength={128}/></label>
   <label className="account-delete-confirm"><input name="confirm" type="checkbox" required/> 모든 기록이 즉시 영구 삭제됨을 이해했습니다</label>
   <button type="submit" disabled={disabled||busy}>{busy?'삭제 중…':'탈퇴하고 모든 기록 삭제'}</button>
  </form>
  {error&&<p role="alert">{error}</p>}
 </details>
}
