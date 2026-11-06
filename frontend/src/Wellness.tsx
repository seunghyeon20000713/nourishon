import { MealRecordEditor } from './MealRecordEditor'
import { NutritionReview } from './NutritionReview'
import type { ExerciseInput, ExercisePlan } from './Exercise'
import { Measurements } from './Measurements'
import type { Measurement } from './Measurements'
import { useState } from 'react'
import type { FormEvent } from 'react'
export type Nutrient = { unit: string; known_total: number | null; missing_count: number; status: 'complete'|'partial'|'missing' }
export type Calculation = { foods?: {food_code?:string; food_name:string; intake_g:number}[]; totals: Record<string,Nutrient> }
export type MealRecord = { id:string; date:string; kind:string; calculation:Calculation }
type Estimate = { bmi:number; maintenance_kcal:number; protein_reference_g:number; limitations:string[]; sources:{title:string;url:string}[]; macro_reference_ranges?: Record<string,{min_g:number;max_g:number;percent:number[]}> }
export type WellnessData = { profile: Record<string,unknown>|null; estimate:Estimate|null; records:MealRecord[]; measurements?:Measurement[]; exerciseInput?:ExerciseInput|null; exercisePlan?:ExercisePlan|null }
export const today = () => new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())
export const emptyData = ():WellnessData => ({profile:null,estimate:null,records:[]})
export const storageKey = 'nourishon-local-mvp-v1'
export const labels:Record<string,string> = {energy:'열량',protein:'단백질',fat:'지방',carbohydrate:'탄수화물',sugar:'당류',fiber:'식이섬유',sodium:'나트륨'}
export function aggregate(records:MealRecord[]) {
 const totals:Record<string,Nutrient>={}
 for(const key of Object.keys(labels)) {
  const values=records.map(r=>r.calculation.totals[key]).filter(Boolean)
  const known=values.filter(n=>n.known_total!==null)
  const missing=values.reduce((sum,n)=>sum+n.missing_count,0)
  totals[key]={unit:values[0]?.unit??(key==='energy'?'kcal':key==='sodium'?'mg':'g'),known_total:known.length?known.reduce((sum,n)=>sum+n.known_total!,0):null,missing_count:missing,status:!known.length?'missing':missing?'partial':'complete'}
 }
 return totals
}
export function Totals({records}:{records:MealRecord[]}) {
 const totals=aggregate(records)
 return <div className="nutrient-grid">{Object.entries(totals).map(([key,n])=><article className="nutrient-card" key={key}><div>{labels[key]}</div><strong>{n.known_total===null?'정보 없음':`${Number(n.known_total.toFixed(2))} ${n.unit}`}</strong><small>{n.status==='complete'?'기록된 값의 합계':`누락 ${n.missing_count}개 · 확인된 값만 합산`}</small></article>)}</div>
}
export function Profile({data,onChange}:{data:WellnessData;onChange:(d:WellnessData)=>void}) {
 const [error,setError]=useState('');const [busy,setBusy]=useState(false)
 const p=data.profile??{}
 const body=(p.body??{}) as Record<string,number|string>
 async function submit(e:FormEvent<HTMLFormElement>) {
  e.preventDefault();const f=new FormData(e.currentTarget)
  const profile:Record<string,unknown>={measured_on:f.get('measured_on'),age:Number(f.get('age')),height_cm:Number(f.get('height_cm')),weight_kg:Number(f.get('weight_kg')),equation_sex:f.get('equation_sex'),activity:f.get('activity'),goal:f.get('goal'),scope_confirmed:true}
  const body:Record<string,unknown>={measured_on:f.get('measured_on')}
  for(const key of ['skeletal_muscle_kg','fat_mass_kg','body_fat_percent']) if(f.get(key))body[key]=Number(f.get(key))
  if(Object.keys(body).length>1)profile.body=body
  setBusy(true);setError('')
  try{const r=await fetch('/api/profile/estimate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(profile)});if(!r.ok)throw Error();const estimate:Estimate=await r.json();
   const measurement:Measurement={id:crypto.randomUUID(),measured_on:String(f.get('measured_on')),weight_kg:Number(profile.weight_kg)}
   for(const key of ['skeletal_muscle_kg','fat_mass_kg','body_fat_percent'] as const) if(body[key]!==undefined)measurement[key]=Number(body[key])
   const history=[...(data.measurements??[])]
   // 이전 버전에서 보관한 체성분 값도 첫 갱신 때 이력으로 남긴다.
   const oldBody=data.profile?.body as Record<string,number|string>|undefined
   if(!history.length&&oldBody?.measured_on&&data.profile){history.push({id:crypto.randomUUID(),measured_on:String(oldBody.measured_on),weight_kg:Number(data.profile.weight_kg),...Object.fromEntries(['skeletal_muscle_kg','fat_mass_kg','body_fat_percent'].filter(k=>oldBody[k]!==undefined).map(k=>[k,Number(oldBody[k])]))})}
   const same=history.some(m=>m.measured_on===measurement.measured_on&&m.weight_kg===measurement.weight_kg&&m.skeletal_muscle_kg===measurement.skeletal_muscle_kg&&m.fat_mass_kg===measurement.fat_mass_kg&&m.body_fat_percent===measurement.body_fat_percent)
   onChange({...data,profile,estimate,exerciseInput:null,exercisePlan:null,measurements:same?history:[...history,measurement]})}catch{setError('입력 범위·체성분 측정일과 서버 연결을 확인해주세요.')}finally{setBusy(false)}
 }
 return <section className="panel wellness-panel"><h1>내 몸과 목표</h1><p>19~64세 일반 성인용 참고 계산입니다. 인바디 입력은 선택이며, 유지 에너지 공식에는 사용하지 않습니다.</p><form onSubmit={submit} className="profile-form">
 {([['age','나이 (세)',19,64],['height_cm','키 (cm)',100,250],['weight_kg','체중 (kg)',25,350]] as const).map(([key,label,min,max])=><label key={key}>{label}<input name={key} type="number" step={key==='age'?'1':'any'} min={min} max={max} required defaultValue={p[key] as number|undefined}/></label>)}
 <label>공식 적용 성별<select name="equation_sex" defaultValue={p.equation_sex as string??'female'}><option value="female">여성 공식</option><option value="male">남성 공식</option></select></label>
 <label>활동 수준<select name="activity" defaultValue={p.activity as string??'inactive'}><option value="inactive">비활동적: 일상생활 중심</option><option value="low_active">낮은 활동</option><option value="active">활동적</option><option value="very_active">매우 활동적</option></select></label>
 <label>관리 방향<select name="goal" defaultValue={p.goal as string??'maintain'}><option value="maintain">유지</option><option value="lose">감량</option><option value="gain">증량</option></select></label>
 <p className="wide">활동 분류 선택에 따라 추정값이 달라집니다. 공식의 활동 수준 설명은 아래 출처를 확인하세요. 감량·증량을 선택해도 열량을 자동으로 더하거나 빼지 않습니다.</p>
 <fieldset className="wide"><legend>체중·인바디 측정 · 체중과 같은 측정 기준으로 입력</legend><label>측정일<input name="measured_on" type="date" required max={today()} defaultValue={(p.measured_on as string)??body.measured_on??today()}/></label>{[['skeletal_muscle_kg','골격근량 (kg)'],['fat_mass_kg','체지방량 (kg)'],['body_fat_percent','체지방률 (%)']].map(([key,label])=><label key={key}>{label}<input name={key} type="number" min="0" max={key==='body_fat_percent'?100:350} step="any" defaultValue={body[key]}/></label>)}</fieldset>
 <label className="wide"><input type="checkbox" required/> 임신·수유 중이 아니며 질환 치료식·재활·전문 운동선수 관리가 아닌 일반 성인 참고용임을 확인했습니다.</label>
 <button className="calculate-button wide" disabled={busy}>{busy?'계산 중':'프로필 적용 및 참고 목표 계산'}</button></form>{error&&<p role="alert">{error}</p>}
 {data.estimate&&<div className="estimate"><h2>참고 목표</h2><p>BMI <b>{data.estimate.bmi}</b> · 추정 유지 에너지 <b>{data.estimate.maintenance_kcal} kcal/일</b> · 단백질 일반 참고 <b>{data.estimate.protein_reference_g} g/일</b></p><p>WHO 일반 성인 참고: 식이섬유 하루 25g 이상 · 나트륨 하루 2,000mg 미만.</p><ul>{data.estimate.limitations.map(t=><li key={t}>{t}</li>)}</ul><p>인바디 값은 현재 프로필에 보관됩니다. 측정 조건에 따라 달라지므로 정확도 향상을 보장하지 않습니다.</p>{data.estimate.macro_reference_ranges&&<div><h3>2025 한국인 기준 · 에너지 적정비율 참고</h3><p>현재 추정 유지 에너지를 비율로 환산한 참고 범위이며 개인 처방이 아닙니다. 단백질 체중당 참고값과는 기준이 다릅니다.</p>{Object.entries(data.estimate.macro_reference_ranges).map(([key,r])=><p key={key}>{labels[key]}: {r.percent[0]}~{r.percent[1]}% · {r.min_g}~{r.max_g} g/일</p>)}</div>}{data.estimate.sources.map(s=><p key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a></p>)}</div>}
 <Measurements data={data}/>
 </section>
}
export function History({data,onChange,initialDay}:{data:WellnessData;onChange:(d:WellnessData)=>void;initialDay?:string}) {
 const [day,setDay]=useState(initialDay??today());const records=data.records.filter(r=>r.date===day)
 const [editing,setEditing]=useState<string|null>(null)
 return <section className="panel wellness-panel"><h1>식사 기록과 기간 분석</h1><label>조회 날짜<input type="date" value={day} onChange={e=>{if(e.target.value)setDay(e.target.value)}}/></label><p>등록한 식사만 집계합니다. 미기록은 섭취량 0 또는 결핍을 뜻하지 않습니다.</p>{records.length?<><Totals records={records}/>{records.map(r=><article className="record" key={r.id}><h3>{r.date} · {r.kind}</h3><p>{r.calculation.foods?.map(f=>`${f.food_name} ${f.intake_g}g`).join(', ')}</p><button onClick={()=>setEditing(r.id)}>기록 수정</button>{editing===r.id&&<MealRecordEditor key={r.id} record={r} onCancel={()=>setEditing(null)} onSave={updated=>{onChange({...data,records:data.records.map(row=>row.id===updated.id?updated:row)});setEditing(null);setDay(updated.date)}}/>}<button onClick={()=>{if(window.confirm('이 식사 기록을 삭제할까요?'))onChange({...data,records:data.records.filter(x=>x.id!==r.id)})}}>기록 삭제</button></article>)}</>:<p>이 날짜에 등록된 식사가 없습니다.</p>}<h2>선택 날짜까지 최근 7일</h2><p>하루 전체 섭취를 확인한 결과가 아닌 기록 현황입니다.</p><div className="week-grid">{Array.from({length:7},(_,i)=>{const date=new Date(`${day}T12:00:00+09:00`);date.setUTCDate(date.getUTCDate()-6+i);const key=date.toISOString().slice(0,10);const rows=data.records.filter(r=>r.date===key);const energy=aggregate(rows).energy;return <button key={key} onClick={()=>setDay(key)}>{key.slice(5)}<br/>{rows.length?`${rows.length}끼 · ${energy.known_total===null?'열량 정보 없음':`${Math.round(energy.known_total)} kcal`}`:'미기록'}{rows.length>0&&energy.status!=='complete'?' (열량 누락 있음)':''}</button>})}</div></section>
}
export function Insights({data}:{data:WellnessData}) {
 const records=data.records.filter(r=>r.date===today());const n=aggregate(records)
 return <section className="panel wellness-panel"><h1>다음 한 끼와 활동</h1><p>공식 자료와 등록된 값으로 만든 규칙 기반 안내입니다. AI 챗봇은 아직 연결하지 않았습니다. 일반 성인 활동 초안은 ‘운동 계획’에서 확인할 수 있습니다.</p><NutritionReview data={data}/><h2>오늘 기록 돌아보기</h2>{!records.length?<p>오늘 식사를 등록하면 확인된 영양 합계를 함께 보여드립니다.</p>:<><Totals records={records}/>{n.sodium.known_total!==null&&n.sodium.known_total>=2000&&<p>확인된 나트륨만으로 WHO 일반 성인 하루 참고 상한에 도달했습니다. 다음 식사에서 국물·소스 양을 줄이는 방법을 고려해보세요.</p>}{n.fiber.status!=='complete'&&<p>식이섬유 정보가 누락되어 적정 여부를 판단할 수 없습니다.</p>}<p>일부 식사 기록만으로 열량·단백질 부족이나 영양 결핍을 판단하지 않습니다. 당류는 총당류이며 WHO의 유리당 기준과 직접 비교하지 않습니다.</p></>}<h2>다음 식사에서 시도할 것</h2><p>채소·통곡물·콩류 등 다양한 식품을 식사에 포함하고, 단백질 급원도 함께 살펴보세요. 특정 음식의 가격·재고·알레르기 적합성은 확인하지 않았습니다.</p><a href="https://www.who.int/news-room/fact-sheets/detail/healthy-diet" target="_blank" rel="noreferrer">출처: WHO Healthy diet</a><h2>활동은 무리 없이 늘리기</h2><p>WHO 일반 성인 참고: 주당 중강도 유산소 150~300분, 주요 근육 강화 활동 주 2일 이상. 현재 활동이 적다면 짧은 걷기부터 점진적으로 늘려보세요. BMI나 인바디만으로 운동 강도를 처방하지 않습니다.</p><a href="https://www.who.int/europe/news-room/fact-sheets/item/physical-activity" target="_blank" rel="noreferrer">출처: WHO 2020 신체활동 지침</a><p>통증이나 운동 제한이 있다면 개인 평가를 받은 뒤 활동 계획을 정하세요.</p></section>
}
