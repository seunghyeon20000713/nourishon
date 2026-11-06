import { useCallback, useEffect, useRef, useState } from 'react'
import { emptyData } from './Wellness'
import type { WellnessData } from './Wellness'
import { accountRequest } from './Account'
import type { Session } from './Account'

type ServerProfile={id:string;nickname:string;revision:number;data:WellnessData}
export function useServerProfiles(session:Session) {
 const [profiles,setProfiles]=useState<ServerProfile[]>([])
 const [activeId,setActiveId]=useState('')
 const [error,setError]=useState('');const [saving,setSaving]=useState(0)
 const revision=useRef<Record<string,number>>({})
 const queue=useRef<Promise<unknown>>(Promise.resolve())
 const alive=useRef(true)
 const blocked=useRef(false)
 useEffect(()=>{alive.current=true;return()=>{alive.current=false}},[])
 const reload=useCallback(async()=>{
  if(!session.user)return
  try{const result=await accountRequest('/account/profiles',session);if(!alive.current)return
   setProfiles(result.profiles);setActiveId(id=>result.profiles.some((p:ServerProfile)=>p.id===id)?id:result.profiles[0]?.id??'');setError('');blocked.current=false;revision.current=Object.fromEntries(result.profiles.map((p:ServerProfile)=>[p.id,p.revision]))
  }catch(e){if(alive.current)setError((e as Error).message)}
 },[session])
 useEffect(()=>{void reload()},[reload])
 const setData=useCallback((data:WellnessData)=>{
  const id=activeId;if(!id)return
  setProfiles(s=>s.map(p=>p.id===id?{...p,data}:p));setSaving(n=>n+1)
  queue.current=queue.current.then(async()=>{
   if(blocked.current)throw new Error('먼저 DB 기록을 다시 불러온 뒤 수정하세요.')
   const saved:ServerProfile=await accountRequest(`/account/profiles/${id}/data`,session,{method:'PUT',body:JSON.stringify({revision:revision.current[id],data})})
   revision.current[id]=saved.revision
   // 응답 이후 새로 입력한 값은 유지하고, 마지막 저장은 서버의 검증된 계산값을 반영한다.
   if(alive.current){setProfiles(s=>s.map(p=>p.id===id&&p.data===data?saved:p));setError('')}
  }).catch(e=>{blocked.current=true;if(alive.current)setError(`기록 저장 실패: ${(e as Error).message} 현재 입력은 화면에만 남아 있습니다.`)}).finally(()=>{if(alive.current)setSaving(n=>n-1)})
 },[activeId,session])
 async function register(nickname:string){if(!nickname.trim())return;try{const p:ServerProfile=await accountRequest('/account/profiles',session,{method:'POST',body:JSON.stringify({nickname:nickname.trim()})});if(alive.current){revision.current[p.id]=p.revision;setProfiles(s=>[...s,p]);setActiveId(p.id)}}catch(e){if(alive.current)setError((e as Error).message)}}
 return {data:profiles.find(p=>p.id===activeId)?.data??emptyData(),setData,profiles,activeId,register,
  select:setActiveId,storageError:error,persist:false,setPersist:()=>{},saving,reload,loading:profiles.length===0&&!error}
}
