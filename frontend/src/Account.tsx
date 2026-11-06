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
 return <><details id="account-tools" className="account-tools"><summary aria-label={session.user?'내 계정 열기':'로그인 / 회원가입 열기'}><UserRound size={18}/><span>{session.user?"내 계정":"로그인 / 회원가입"}</span><ChevronDown size={14}/></summary><section className="account-banner" aria-label="회원 계정"><div><strong>{session.user?`${session.user.username}님의 계정`:'나의 기록을 이어서 관리하세요'}</strong><p>{session.user?'이 계정에 저장한 기록을 불러옵니다. 기기에만 보관한 기록은 자동으로 옮기지 않습니다.':'로그인하면 이 계정으로 기록을 보관할 수 있어요. 로그인 없이도 기기에서 먼저 사용해볼 수 있습니다.'}</p></div>{session.user?<button disabled={busy||pending>0} onClick={async()=>{setBusy(true);try{await accountRequest('/auth/logout',session,{method:'POST'});setSession({user:null,database_enabled:true});setMode('login');setError('')}catch(e){if((e as Error&{status?:number}).status===401){setSession({user:null,database_enabled:true});setMode('login')}else setError((e as Error).message)}finally{setBusy(false)}}}>로그아웃</button>:session.database_enabled?<div className="auth-entry"><div className="auth-mode-switch" role="group" aria-label="로그인 또는 회원가입 선택">{(['login','register'] as const).map(value=><button type="button" key={value} aria-label={value==='login'?'로그인 선택':'회원가입 선택'} aria-pressed={mode===value} disabled={busy} onClick={()=>{setMode(value);setError('')}}>{value==='login'?'로그인':'회원가입'}</button>)}</div><form key={mode} onSubmit={submit}><label>아이디<input name="username" autoComplete="username" pattern={mode==='register'?'[a-zA-Z0-9_]{4,40}':'[a-zA-Z0-9_]{3,40}'} minLength={mode==='register'?4:3} maxLength={40} required placeholder={mode==='register'?'영문·숫자·밑줄 4~40자':'영문·숫자·밑줄 3~40자'}/></label><label>비밀번호<input name="password" type="password" autoComplete={mode==='register'?'new-password':'current-password'} minLength={4} maxLength={128} required placeholder="4~128자"/></label><button disabled={busy} type="submit">{busy?'처리 중':mode==='login'?'로그인':'가입하고 시작'}</button>{mode==='register'&&<small>로컬 개발용 계정입니다. 실명·이메일은 요구하지 않으며 비밀번호 재설정 기능은 아직 없습니다.</small>}</form></div>:<small>{import.meta.env.MODE==='demo'?'체험판에서는 로그인·회원가입·서버 저장을 제공하지 않습니다. 가상 프로필로 화면을 확인해주세요.':'계정 서비스에 연결되면 가입·로그인을 사용할 수 있습니다.'}</small>}{error&&<p role="alert">{error}</p>}</section></details>{children(session,setPending)}</>
}
