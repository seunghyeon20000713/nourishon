import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { today } from './Wellness'
import type { WellnessData } from './Wellness'
export type Measurement = {
 id: string; measured_on: string; weight_kg: number;
 skeletal_muscle_kg?: number; fat_mass_kg?: number; body_fat_percent?: number;
}
function MeasurementEditor({record,onSave,onCancel}:{record:Measurement;onSave:(record:Measurement)=>void;onCancel:()=>void}) {
 const [error,setError]=useState('');const [busy,setBusy]=useState(false)
 const request=useRef<AbortController|null>(null)
 const save=useRef(onSave);save.current=onSave
 useEffect(()=>()=>request.current?.abort(),[])
 async function submit(event:FormEvent<HTMLFormElement>) {
  event.preventDefault();const form=new FormData(event.currentTarget)
  const value:Record<string,unknown>={id:record.id,measured_on:form.get('measurement_date'),weight_kg:Number(form.get('measurement_weight'))}
  for(const key of ['skeletal_muscle_kg','fat_mass_kg','body_fat_percent'])if(String(form.get(key)??'').trim())value[key]=Number(form.get(key))
  const controller=new AbortController();request.current=controller;setBusy(true);setError('')
  try {const response=await fetch('/api/measurements/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value),signal:controller.signal})
   if(!response.ok)throw Error()
   const validated:Measurement=await response.json();if(!controller.signal.aborted)save.current(validated)
  }catch{if(!controller.signal.aborted)setError('측정일·입력 범위·체중과 체성분 합계 또는 서버 연결을 확인해주세요. 원래 기록은 유지됩니다.')}finally{if(!controller.signal.aborted)setBusy(false)}
 }
 return <form className="measurement-editor meal-record-editor" aria-label="측정 기록 수정" onSubmit={submit}>
  <fieldset disabled={busy}><legend>측정 기록 수정</legend>
   <label>이력 측정일<input name="measurement_date" type="date" required max={today()} defaultValue={record.measured_on}/></label>
   <label>이력 체중 (kg)<input name="measurement_weight" type="number" required min="25" max="350" step="any" defaultValue={record.weight_kg}/></label>
   {([['skeletal_muscle_kg','이력 골격근량 (kg)'],['fat_mass_kg','이력 체지방량 (kg)'],['body_fat_percent','이력 체지방률 (%)']] as const).map(([key,label])=><label key={key}>{label}<input name={key} type="number" min={key==='skeletal_muscle_kg'?'0.001':'0'} max={key==='body_fat_percent'?100:350} step="any" defaultValue={record[key]}/></label>)}
   <p>인바디 항목을 비우면 미등록으로 저장합니다. 체지방량·체지방률의 0과 미등록은 구분합니다.</p>
   <button type="submit">{busy?'확인 중…':'측정 변경 적용'}</button>
  </fieldset>
  <button type="button" onClick={()=>{request.current?.abort();onCancel()}}>측정 수정 취소</button>
  {error&&<p role="alert">{error}</p>}
 </form>
}
export function Measurements({data,onChange}:{data:WellnessData;onChange:(data:WellnessData)=>void}) {
 const [editing,setEditing]=useState<string|null>(null)
 const current=data.measurements?.find(row=>row.id===editing)

 const rows=[...(data.measurements??[])].sort((a,b)=>a.measured_on.localeCompare(b.measured_on))
 if(!rows.length)return <section className="measurement-section"><h2>체중·인바디 측정 이력</h2><p>프로필을 적용하면 측정일과 체중이 함께 기록됩니다. 인바디 항목은 선택입니다.</p></section>
 const first=rows[0],last=rows[rows.length-1]
 const delta=Number((last.weight_kg-first.weight_kg).toFixed(2))
 const min=Math.min(...rows.map(r=>r.weight_kg)), max=Math.max(...rows.map(r=>r.weight_kg))
 return <section className="measurement-section"><h2>체중·인바디 측정 이력</h2><p>기록 {rows.length}건 · 최근 체중 <b>{last.weight_kg} kg</b>{rows.length>1&&<> · 첫 기록 대비 <b>{delta>0?'+':''}{delta} kg</b></>}</p><p>이력 수정·삭제는 아래 표와 그래프에만 반영합니다. 현재 프로필·참고 목표·운동 계획은 바꾸지 않습니다. 현재 목표도 바꾸려면 위 프로필을 수정하고 적용하세요.</p><p>변화량은 기록값의 차이입니다. 수분 상태·측정 시간·기기 차이를 고려해야 하며 건강 개선 여부로 판정하지 않습니다.</p>
 {rows.length>1&&<figure className="weight-chart"><figcaption>측정 순서에 따른 체중 변화 (kg)</figcaption><svg viewBox="0 0 640 140" role="img" aria-label={`체중 기록 ${rows.length}건, 처음 ${first.weight_kg}kg, 최근 ${last.weight_kg}kg`}><line x1="28" y1="110" x2="612" y2="110" stroke="#dce3d6"/><polyline fill="none" stroke="#347a58" strokeWidth="3" points={rows.map((r,i)=>`${28+i*584/(rows.length-1)},${100-(r.weight_kg-min)/Math.max(max-min,1)*65}`).join(' ')}/>{rows.map((r,i)=><g key={r.id}><circle cx={28+i*584/(rows.length-1)} cy={100-(r.weight_kg-min)/Math.max(max-min,1)*65} r="4" fill="#347a58"/><title>{r.measured_on}: {r.weight_kg}kg</title></g>)}</svg><small>{first.measured_on} → {last.measured_on} · 가로 간격은 측정 순서이며 시간 간격이 아닙니다.</small></figure>}
 <div className="measurement-table"><table><caption>측정값 원본 · 빈 값은 미등록</caption><thead><tr><th>측정일</th><th>체중 kg</th><th>골격근량 kg</th><th>체지방량 kg</th><th>체지방률 %</th><th>기록 관리</th></tr></thead><tbody>{[...rows].reverse().map(r=><tr key={r.id}><td>{r.measured_on}</td><td>{r.weight_kg}</td><td>{r.skeletal_muscle_kg??'미등록'}</td><td>{r.fat_mass_kg??'미등록'}</td><td>{r.body_fat_percent??'미등록'}</td><td><button type="button" onClick={()=>setEditing(r.id)}>측정 수정</button><button type="button" onClick={()=>{if(window.confirm(`${r.measured_on}의 이 측정 기록을 삭제할까요? 현재 프로필과 목표는 유지됩니다.`)){setEditing(null);onChange({...data,measurements:data.measurements?.filter(row=>row.id!==r.id)})}}}>측정 삭제</button></td></tr>)}</tbody></table></div>{current&&<MeasurementEditor key={current.id} record={current} onCancel={()=>setEditing(null)} onSave={updated=>{onChange({...data,measurements:data.measurements?.map(row=>row.id===updated.id?updated:row)});setEditing(null)}}/>}</section>
}
