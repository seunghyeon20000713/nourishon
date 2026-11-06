import { EvidenceSources } from './EvidenceSources'
import type { EvidenceSource } from './EvidenceSources'
import { useEffect, useState } from 'react'
import type { WellnessData } from './Wellness'
import { today } from './Wellness'
export type Review={scope:string;macro_status:string;macro_message:string;macros:{key:string;label:string;percent:number;reference:number[];comparison:string}[];sodium_contributors:{food_name:string;sodium_mg:number}[];actions:string[];sources:EvidenceSource[];sugar_note:string;personal_reference?:{maintenance_kcal:number;protein_reference_g:number;note:string}}
export function useNutritionReview(data:WellnessData,day=today()) {
 const [review,setReview]=useState<Review|null>(null),[error,setError]=useState('')
 useEffect(()=>{const controller=new AbortController();setReview(null);setError('')
  const meals=data.records.filter(r=>r.date===day).map(r=>r.calculation)
  if(!meals.length)return()=>controller.abort()
  if(meals.some(m=>!m.foods?.length)){setError('이전 기록에 식품별 스냅샷이 없어 상세 영양 검토를 할 수 없습니다. 기존 합계는 아래에서 확인하세요.');return()=>controller.abort()}
  fetch('/api/nutrition/review',{method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,body:JSON.stringify({meals,profile:data.profile})}).then(async r=>{if(!r.ok)throw Error();return r.json()}).then(result=>{if(!controller.signal.aborted)setReview(result)}).catch(()=>{if(!controller.signal.aborted)setError('영양 구성을 검토하지 못했습니다. 식품 정보와 서버 연결을 확인하세요.')})
  return()=>controller.abort()
 },[data.records,data.profile,day])
 return {review,error}
}
export function NutritionReview({data}:{data:WellnessData}) {
 const {review,error}=useNutritionReview(data)
 return <section aria-labelledby="nutrition-review-title"><h2 id="nutrition-review-title">영양학적 근거로 식사 돌아보기</h2>{error&&<p role="alert">{error}</p>}{!review&&!error&&<p>오늘 기록한 식사의 영양 구성을 확인합니다.</p>}{review&&<><p>{review.scope}</p><h3>탄수화물·단백질·지방 에너지 비율</h3><p>{review.macro_message}</p>{review.macros.length>0&&<div className="measurement-table"><table><thead><tr><th>성분</th><th>기록 비율</th><th>2025 한국인 참고</th><th>기록 구성 비교</th></tr></thead><tbody>{review.macros.map(m=><tr key={m.key}><td>{m.label}</td><td>{m.percent}%</td><td>{m.reference[0]}~{m.reference[1]}%</td><td>{m.comparison}</td></tr>)}</tbody></table></div>}<h3>기록된 나트륨 기여 식품</h3>{review.sodium_contributors.length?<ol>{review.sodium_contributors.map((f,i)=><li key={i}>{f.food_name}: {Number(f.sodium_mg.toFixed(1))} mg</li>)}</ol>:<p>기여 식품을 표시할 양수 값이 없습니다. 누락과 0은 기존 합계에서 구분합니다.</p>}<h3>다음 한 끼에 적용하기</h3><ul>{review.actions.map(t=><li key={t}>{t}</li>)}</ul>{review.personal_reference&&<p>현재 프로필 참고: 유지 에너지 {review.personal_reference.maintenance_kcal}kcal/일, 단백질 {review.personal_reference.protein_reference_g}g/일. {review.personal_reference.note}</p>}<p>{review.sugar_note}</p><EvidenceSources sources={review.sources}/></>}</section>
}
