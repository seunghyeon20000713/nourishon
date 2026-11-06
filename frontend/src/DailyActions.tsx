import { Activity, ArrowUpRight, Scale, Utensils } from 'lucide-react'
import type { WellnessData } from './Wellness'
import { today } from './Wellness'
export function DailyActions({data,day,onView,onMeal}:{data:WellnessData;day:string;onView:(view:string,day?:string)=>void;onMeal:(kind:string)=>void}) {
 const meals=data.records.filter(record=>record.date===day)
 const activities=(data.activityRecords??[]).filter(record=>record.date===day)
 const measurement=[...(data.measurements??[])].filter(row=>row.measured_on<=day).sort((a,b)=>b.measured_on.localeCompare(a.measured_on))[0]
 return <section className="daily-actions" aria-label="하루 기록 바로가기">
  <article><div className="daily-action-icon"><Utensils size={21}/><span>식사</span></div><strong>{meals.length?`${meals.length}건 기록`:'첫 식사를 남겨보세요'}</strong><p>{day===today()?'먹은 음식과 실제 양을 기록해요.':'선택한 날짜의 식사를 확인해요.'}</p><button onClick={()=>day===today()?onMeal('아침'):onView('history',day)}>{day===today()?'식사 추가':'식사 기록 보기'}<ArrowUpRight size={16}/></button></article>
  <article><div className="daily-action-icon"><Activity size={21}/><span>운동</span></div><strong>{activities.length?`${activities.reduce((sum,record)=>sum+record.minutes,0)}분 기록`:'운동 기록을 남겨보세요'}</strong><p>{activities.length?`${activities.length}건 · 기록한 활동 시간`:'미기록은 실제 운동 0분을 뜻하지 않아요.'}</p><button onClick={()=>onView('activity')} aria-label="운동 기록하기">운동 기록<ArrowUpRight size={16}/></button></article>
  <article><div className="daily-action-icon"><Scale size={21}/><span>내 몸</span></div><strong>{measurement?`${measurement.weight_kg} kg`:'몸의 변화를 기록해요'}</strong><p>{measurement?`${measurement.measured_on} 측정 · 선택일까지 최근 기록`:'체중과 선택 인바디 값을 관리해요.'}</p><button onClick={()=>onView('profile')} aria-label="신체 정보 관리">내 정보<ArrowUpRight size={16}/></button></article>
 </section>
}
