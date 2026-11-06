import type { FoodFocus } from './FoodComparison'
import { useEffect, useState } from 'react'
import { EvidenceSources } from './EvidenceSources'
import type { EvidenceSource } from './EvidenceSources'
import { today } from './Wellness'
import type { WellnessData } from './Wellness'
type Guidance = {
 start:string;end:string;scope:string;goal:string;rules_version:string;
 coverage:{meal_records:number;meal_days:number;reviewed_days:number;legacy_meals:number;measurement_records:number;activity_records:number};
 body_changes:{key:string;label:string;unit:string;difference:number|null;first_date:string|null;last_date:string|null}[];
 activity:{recorded_minutes:number;aerobic_activity_minutes:number;strength_recorded_days:number;gross_kcal:number;plan_status:string};
 recommendations:{id:string;title:string;action:string;reason:string}[];limitations:string[];sources:EvidenceSource[];
}
export function WeeklyGuidance({data,onView,onCompare}:{data:WellnessData;onView:(view:string)=>void;onCompare:(focus:FoodFocus)=>void}) {
 const [result,setResult]=useState<Guidance|null>(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0)
 useEffect(()=>{
  if(import.meta.env.MODE==='demo')return
  const controller=new AbortController();setResult(null);setError('')
  const end=today(),start=new Date(`${end}T12:00:00Z`);start.setUTCDate(start.getUTCDate()-6);const first=start.toISOString().slice(0,10)
  const inWindow=(date:string)=>date>=first&&date<=end
  const meals=data.records.filter(row=>inWindow(row.date)).map(row=>({id:row.id,date:row.date,foods:row.calculation.foods?.length&&row.calculation.foods.every(food=>'nutrients' in food)?row.calculation.foods:null}))
  fetch('/api/nutrition/weekly-guidance',{method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,body:JSON.stringify({end,profile:data.profile,meals,measurements:(data.measurements??[]).filter(row=>inWindow(row.measured_on)),activities:(data.activityRecords??[]).filter(row=>inWindow(row.date)),exercise_input:data.exerciseInput??null})})
   .then(async response=>{if(!response.ok)throw Error();return response.json()}).then(value=>{if(!controller.signal.aborted)setResult(value)}).catch(()=>{if(!controller.signal.aborted)setError('최근 기록을 연결하지 못했습니다. 입력 범위와 서버 연결을 확인해주세요. 기존 기록은 바꾸지 않았습니다.')})
  return()=>controller.abort()
 },[data,attempt])
 if(import.meta.env.MODE==='demo')return <section className="weekly-guidance"><h2>최근 7일 연결 안내</h2><p>이 공개 체험판에는 실제 통합 추천 서버가 연결되어 있지 않습니다. 로컬 개발 버전에서 검증 중인 기능입니다.</p></section>
 return <section className="weekly-guidance" aria-labelledby="weekly-guidance-title"><h2 id="weekly-guidance-title">최근 7일, 다음 실천 정하기</h2>
 {error?<div role="alert"><p>{error}</p><button onClick={()=>setAttempt(value=>value+1)}>연결 안내 다시 확인</button></div>:!result?<p role="status">식사·신체·운동 기록을 연결하고 있어요…</p>:<>
 <p>{result.start} ~ {result.end} · 현재 관리 방향: {result.goal}</p><p>{result.scope}</p>
 <div className="period-summary"><article><span>식사 기록</span><strong>{result.coverage.meal_records}건 · {result.coverage.meal_days}일</strong><small>상세 검토 {result.coverage.reviewed_days}일 · 식품 정보 없는 기록 {result.coverage.legacy_meals}건</small></article><article><span>신체 측정</span><strong>{result.coverage.measurement_records}건</strong><small>이번 기간의 같은 항목끼리 비교</small></article><article><span>실제 운동 기록</span><strong>{result.coverage.activity_records?`${result.activity.recorded_minutes}분 · ${result.coverage.activity_records}건`:'미기록'}</strong><small>근력 기록 포함 {result.activity.strength_recorded_days}일 · 권고 충족 판정 아님</small></article></div>
 <div className="guidance-actions">{result.recommendations.map(item=><article key={item.id} data-guidance={item.id}><h3>{item.title}</h3><p>{item.action}</p><button onClick={()=>onView(['assessment','activity','activity_input'].includes(item.id)?'exercise':item.id==='body_records'?'profile':'meal')}>{['assessment','activity','activity_input'].includes(item.id)?'운동 조건 확인':item.id==='body_records'?'신체 정보 열기':'식사 기록 열기'}</button>{['sodium','protein','variety','food_records'].includes(item.id)&&<button onClick={()=>onCompare(item.id==='sodium'?'sodium':item.id==='protein'?'protein':'fiber')}>관련 음식 비교</button>}<details><summary>이 안내가 나온 이유</summary><p>{item.reason}</p></details></article>)}</div>
 <details className="guidance-body"><summary>같은 기간의 신체 변화 확인</summary><ul>{result.body_changes.map(item=><li key={item.key}>{item.label}: {item.difference===null?'서로 다른 날짜의 비교 가능한 측정이 부족합니다.':`${item.difference>0?'+':''}${item.difference} ${item.unit} (${item.first_date} → ${item.last_date})`}</li>)}</ul><p>측정 조건의 영향을 받습니다. 식사·운동의 효과로 단정하지 않습니다.</p></details>
 <details><summary>판단 범위와 한계</summary><ul>{result.limitations.map(text=><li key={text}>{text}</li>)}</ul><small>안내 규칙: {result.rules_version}</small></details>
 <EvidenceSources sources={result.sources}/>
 </>}
 </section>
}
