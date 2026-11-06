import { UserRound, ChevronDown } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
export type Session = {user:{id:string;username:string}|null;csrf_token?:string;database_enabled:boolean}
export async function accountRequest(path:string,session:Session,options:RequestInit={}) {
 const response=await fetch(`/api${path}`,{...options,headers:{'Content-Type':'application/json','X-NourishOn-Client':'web',...(session.csrf_token?{'X-CSRF-Token':session.csrf_token}:{}),...options.headers}})
 const data=await response.json()
 if(!response.ok)throw Object.assign(new Error(data.detail??'요청을 완료하지 못했습니다.'),{status:response.status})
 return data
}
export function Account({children}:{children:(session:Session,onPending:(n:number)=>void)=>ReactNode}) {
 const [session,setSession]=useState<Session|null>(null)
 const [pending,setPending]=useState(0)
 const [error,setError]=useState('');const [busy,setBusy]=useState(false)
 const [mode,setMode]=useState<'login'|'register'>('login')
 useEffect(()=>{let active=true;fetch('/api/auth/me').then(async r=>{if(r.status===401)return {user:null,database_enabled:true};if(!r.ok)throw Error();return r.json()}).then(s=>{if(active)setSession(s)}).catch(()=>{if(active){setError('계정 서버 연결을 확인하세요. 로컬 임시 모드를 사용할 수 있습니다.');setSession({user:null,database_enabled:false})}});return()=>{active=false}},[])
 async function submit(e:FormEvent<HTMLFormElement>) {
  e.preventDefault();const form=e.currentTarget;const f=new FormData(form);setBusy(true);setError('')
  try{const next=await accountRequest(`/auth/${mode}`,session!,{method:'POST',body:JSON.stringify({username:f.get('username'),password:f.get('password')})});form.reset();setSession(next);const panel=document.getElementById('account-tools') as HTMLDetailsElement|null;if(panel)panel.open=false}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 if(!session)return <div className="account-loading" role="status">로그인 상태 확인 중…</div>
 return <><details id="account-tools" className="account-tools"><summary aria-label="회원 계정 열기"><UserRound size={18}/><span>{session.user?session.user.username:"내 계정"}</span><ChevronDown size={14}/></summary><section className="account-banner" aria-label="회원 계정"><div><strong>{session.user?`${session.user.username}님의 계정`:'내 계정으로 기록 관리하기'}</strong><p>{session.user?'로그인 계정의 PostgreSQL 기록을 사용합니다. 기존 로컬 기록은 자동 업로드하지 않습니다.':'현재는 로컬 임시 모드입니다. 가입·로그인하면 계정별로 DB에 기록합니다.'}</p></div>{session.user?<button disabled={busy||pending>0} onClick={async()=>{setBusy(true);try{await accountRequest('/auth/logout',session,{method:'POST'});setSession({user:null,database_enabled:true});setMode('login');setError('')}catch(e){if((e as Error&{status?:number}).status===401){setSession({user:null,database_enabled:true});setMode('login')}else setError((e as Error).message)}finally{setBusy(false)}}}>로그아웃</button>:session.database_enabled?<form onSubmit={submit}><label>아이디<input name="username" autoComplete="username" pattern="[a-zA-Z0-9_]{3,40}" minLength={3} maxLength={40} required placeholder="영문·숫자·밑줄 3~40자"/></label><label>비밀번호<input name="password" type="password" autoComplete={mode==='register'?'new-password':'current-password'} minLength={15} maxLength={128} required placeholder="15~128자"/></label><button disabled={busy} type="submit">{busy?'처리 중':mode==='login'?'로그인':'가입하고 시작'}</button><button type="button" onClick={()=>{setMode(mode==='login'?'register':'login');setError('')}}>{mode==='login'?'회원가입으로 전환':'로그인으로 전환'}</button>{mode==='register'&&<small>로컬 개발용 계정입니다. 실명·이메일은 요구하지 않으며 비밀번호 재설정 기능은 아직 없습니다.</small>}</form>:<small>DB가 연결되면 가입·로그인을 사용할 수 있습니다.</small>}{error&&<p role="alert">{error}</p>}</section></details>{children(session,setPending)}</>
}
