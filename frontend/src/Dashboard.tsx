import { useState } from 'react'
import { ArrowRight, CalendarDays, Flame, UserRound } from 'lucide-react'
import { aggregate, today } from './Wellness'
import type { WellnessData } from './Wellness'

export function Dashboard({data,onMeal,onView}:{data:WellnessData;onMeal:(kind:string)=>void;onView:(view:string)=>void}) {
 const [day,setDay]=useState(today())
 const records=data.records.filter(r=>r.date===day)
 const totals=aggregate(records)
 const energy=totals.energy
 const reference=data.estimate?.maintenance_kcal
 const pct=reference&&energy.known_total!==null?Math.round(energy.known_total/reference*100):null
 return <section className="daily-dashboard" aria-labelledby="daily-title">
  <div className="dashboard-heading"><div><span className="section-eyebrow">MY DAILY OVERVIEW</span><h2 id="daily-title">나의 하루 한눈에 보기</h2></div><label className="day-picker"><CalendarDays size={17}/><span className="sr-only">요약 날짜</span><input type="date" value={day} max={today()} onChange={e=>{if(e.target.value)setDay(e.target.value)}}/></label></div>
  <div className="overview-grid">
   <article className="overview-card energy-overview"><span><Flame size={17}/> 기록된 열량</span><strong>{energy.known_total===null?'—':Math.round(energy.known_total).toLocaleString('ko-KR')} <small>{energy.known_total!==null?'kcal':''}</small></strong><p>{records.length?`${records.length}개 식사 기록${energy.status!=='complete'?' · 열량 정보 누락 있음':''}`:'아직 기록된 식사가 없어요'}</p>{pct!==null?<><div className="reference-track" aria-hidden="true"><i style={{width:`${Math.min(pct,100)}%`}}/></div><small>현재 추정 유지 에너지 대비 {pct}% · 권장 잔여량이 아닙니다</small></>:<button onClick={()=>onView('profile')}>내 참고 목표 확인 <ArrowRight size={14}/></button>}</article>
   <article className="overview-card"><span>오늘을 위한 작은 실천</span><h3>한 끼씩, 꾸준히 기록해요</h3><p>기록된 양과 실제 하루 섭취량은 다를 수 있어요. 미기록은 0으로 계산하지 않습니다.</p><button onClick={()=>onView('history')}>기록과 7일 분석 보기 <ArrowRight size={14}/></button></article>
   <article className="overview-card"><span><UserRound size={17}/> 내 몸과 목표</span><h3>{data.profile?`${data.profile.weight_kg} kg · ${data.profile.goal==='lose'?'감량':data.profile.goal==='gain'?'증량':'유지'} 방향`:'나에게 맞는 기록의 시작'}</h3><p>{data.estimate?`BMI ${data.estimate.bmi} · 건강 상태를 단독 판정하지 않아요`:'프로필을 등록하면 참고 목표와 측정 이력을 볼 수 있어요.'}</p><button onClick={()=>onView('profile')}>{data.profile?'프로필과 측정 이력':'프로필 입력하기'} <ArrowRight size={14}/></button></article>
  </div>
  <div className="meal-shortcuts">{['아침','점심','저녁','간식'].map(kind=>{const rows=records.filter(r=>r.kind===kind);return <button key={kind} onClick={()=>{onMeal(kind);document.getElementById('search-title')?.scrollIntoView({behavior:'smooth',block:'center'})}}><span>{kind}</span><small>{rows.length?`${rows.length}개 기록`:'미기록'}</small><b>+ 음식 추가</b></button>})}</div>
  <p className="dashboard-note">식사별 바로가기는 오늘 날짜의 새 기록을 준비합니다. 과거 기록은 ‘기록과 분석’에서 확인하세요.</p>
 </section>
}
