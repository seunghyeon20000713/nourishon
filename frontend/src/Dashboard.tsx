import { DailyActions } from './DailyActions'
import { GettingStarted } from './GettingStarted'
import { useState } from 'react'
import { ArrowUpRight, ChevronLeft, ChevronRight, CalendarDays, Info } from 'lucide-react'
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList, ComposedChart, ReferenceArea, ReferenceDot, Line } from 'recharts'
import { aggregate, today } from './Wellness'
import type { WellnessData } from './Wellness'
import { useNutritionReview } from './NutritionReview'

const fmt=(n:number)=>new Intl.NumberFormat('ko-KR',{maximumFractionDigits:1}).format(n)
const dateObject=(date:string)=>new Date(`${date}T12:00:00+09:00`)
export function shiftDay(day:string,by:number){const d=dateObject(day);d.setUTCDate(d.getUTCDate()+by);return d.toISOString().slice(0,10)}
function MacroPlot({label,value,range}:{label:string;value:number|null;range:number[]}) {
 const max=value!==null&&value>100?Math.ceil(value/10)*10:100
 return <div className="macro-row"><div className="macro-number"><span>{label}</span><strong>{value===null?'—':`${fmt(value)}%`}</strong></div><div className="macro-plot" role="img" aria-label={`${label} ${value===null?'평가 보류':`${value}%`}, 참고 범위 ${range[0]}~${range[1]}%`}>
  <ResponsiveContainer width="100%" height={88}><ComposedChart data={[{x:0,y:0.5},{x:max,y:0.5}]} margin={{top:27,right:12,bottom:0,left:12}} accessibilityLayer={false}><XAxis type="number" dataKey="x" domain={[0,max]} ticks={[0,...range,max]} tickFormatter={v=>`${v}%`} tickLine={false} axisLine={false} tick={{fontSize:11,fill:'#849089'}}/><YAxis type="number" dataKey="y" domain={[0,1]} hide/><Line dataKey="y" stroke="#d6dcd8" strokeWidth={4} dot={false} isAnimationActive={false}/><ReferenceArea x1={range[0]} x2={range[1]} y1={0.2} y2={0.8} fill="#d7e7ca" fillOpacity={0.9} stroke="none"/>{value!==null&&<ReferenceDot x={value} y={0.5} r={6} fill="#19573f" stroke="white" strokeWidth={2} label={{value:`${fmt(value)}%`,position:'top',fill:'#19573f',fontSize:12,fontWeight:700}}/>}</ComposedChart></ResponsiveContainer>
 </div><div className="macro-reference"><span>참고 범위</span><strong>{range[0]}–{range[1]}%</strong></div></div>
}
export function Dashboard({data,onMeal,onView}:{data:WellnessData;onMeal:(kind:string)=>void;onView:(view:string,day?:string)=>void}) {
 const [day,setDay]=useState(today());const records=data.records.filter(r=>r.date===day)
 const totals=aggregate(records),energy=totals.energy
 const {review,error}=useNutritionReview(data,day)
 const selected=dateObject(day),monday=shiftDay(day,-((selected.getUTCDay()+6)%7))
 const week=Array.from({length:7},(_,i)=>{const date=shiftDay(monday,i),rows=data.records.filter(r=>r.date===date),e=aggregate(rows).energy;return {date,weekday:['월','화','수','목','금','토','일'][i],label:`${Number(date.slice(5,7))}/${Number(date.slice(8))}`,value:rows.length?e.known_total:null,missing:rows.length>0&&e.status!=='complete',count:rows.length}})
 const chartMax=Math.max(2500,...week.map(d=>d.value===null?0:Math.ceil(d.value/500)*500))
 const humanDate=new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'2-digit',day:'2-digit',weekday:'long',timeZone:'Asia/Seoul'}).format(selected)
 const macros=review?.macros??[]
 const fiberMissing=totals.fiber.status!=='complete'
 return <section className="journal-dashboard" aria-labelledby="journal-title">
  <div className="journal-page-heading"><h1 id="journal-title">기록으로 보는 나의 영양</h1><div className="journal-date"><button aria-label="이전 날짜" onClick={()=>setDay(shiftDay(day,-1))}><ChevronLeft size={18}/></button><label><span className="sr-only">요약 날짜</span><input aria-label="요약 날짜" type="date" value={day} max={today()} onChange={e=>{if(e.target.value)setDay(e.target.value)}}/><span>{humanDate}</span><CalendarDays size={18}/></label><button aria-label="다음 날짜" disabled={day>=today()} onClick={()=>setDay(shiftDay(day,1))}><ChevronRight size={18}/></button></div></div>
  <DailyActions data={data} day={day} onView={onView} onMeal={onMeal}/>
  <GettingStarted data={data} onView={onView}/>
  <div className="journal-columns"><div className="journal-analysis">  <div className="journal-summary"><span>기록된 열량 <strong>{energy.known_total===null?'—':fmt(energy.known_total)}</strong> {energy.known_total===null?'':'kcal'}{energy.status==='partial'&&<small> · 일부 누락</small>}</span><span>추정 유지 에너지 <strong>{data.estimate?fmt(data.estimate.maintenance_kcal):'—'}</strong> {data.estimate?'kcal':''}</span><span>{records.length?<><strong>{records.length}</strong>개 식사 기록</>:'아직 기록한 식사가 없어요'}</span></div>
<section className="composition-section"><div className="journal-section-heading"><h2>기록된 식사의 에너지 구성</h2><span>2025 한국인 영양소 섭취기준 참고</span></div>
   {[['carbohydrate','탄수화물',[50,65]],['protein','단백질',[10,20]],['fat','지방',[15,30]]].map(([key,label,range])=><MacroPlot key={String(key)} label={String(label)} range={range as number[]} value={macros.find(m=>m.key===key)?.percent??null}/>)}
   {!macros.length&&<p className="chart-state" role="status"><Info size={15}/>{error||review?.macro_message||'식사를 기록하면 확인 가능한 영양 비율을 표시합니다.'}</p>}
  </section>
  <section className="week-section"><div className="journal-section-heading"><h2>이번 주 기록 현황</h2><span>기록된 양이며 실제 하루 섭취량과 다를 수 있습니다.</span></div><div className="weekly-chart" role="img" aria-label="이번 주 기록 열량, 미기록일은 0으로 표시하지 않습니다."><small>열량 (kcal)</small><ResponsiveContainer width="100%" height={170}><BarChart data={week} margin={{top:20,right:12,bottom:8,left:-12}} accessibilityLayer><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e9e6"/><XAxis dataKey="label" hide/><YAxis ticks={Array.from({length:Math.floor(chartMax/500)+1},(_,i)=>i*500)} domain={[0,chartMax]} tickLine={false} axisLine={false} tick={{fontSize:11,fill:'#76817c'}} width={58}/><Tooltip formatter={v=>[`${fmt(Number(v))} kcal`,'기록된 열량']} labelFormatter={(_,payload)=>payload[0]?.payload.date??''}/><Bar dataKey="value" maxBarSize={70} isAnimationActive={false}>{week.map(w=><Cell key={w.date} fill={w.date===day?'#19573f':'#d3e2c8'}/>)}<LabelList dataKey="value" position="top" fill="#32493e" fontSize={12} formatter={v=>v==null?'':fmt(Number(v))}/></Bar></BarChart></ResponsiveContainer></div><div className="week-labels">{week.map(w=><button key={w.date} disabled={w.date>today()} onClick={()=>setDay(w.date)} className={w.date===day?'selected':''} aria-label={`${w.date} ${w.count?`${w.count}개 기록`:w.date>today()?'예정':'미기록'}`}><strong>{w.weekday}</strong><span>{w.label}</span>{w.value===null&&<small>{w.date>today()?'예정':w.count?'열량 없음':'미기록'}</small>}{w.missing&&<small>일부 누락</small>}</button>)}</div></section>
  <div className="diary-strip"><strong>식사 상세 기록</strong>{['아침','점심','저녁','간식'].map(kind=>{const rows=records.filter(r=>r.kind===kind),e=aggregate(rows).energy;return <button key={kind} onClick={()=>{if(day===today())onMeal(kind);else onView('history',day)}}><span>{kind}</span><b>{rows.length?(e.known_total===null?'열량 없음':`${fmt(e.known_total)} kcal`):'기록 없음'}</b><ChevronRight size={14}/></button>})}</div>
  </div>
  <aside className="journal-notes" aria-label="기록 해석"><h2>오늘 살펴볼 점</h2><ol><li><div><h3>기록한 식사의 영양 비율을<br className="desktop-break"/> 참고 범위와 비교해보세요.</h3><p>{macros.length?macros.map(m=>`${m.label} ${fmt(m.percent)}%`).join(', '):error||review?.macro_message||'아직 비교할 식사 기록이 없습니다. 식사를 추가하면 계산 근거와 함께 확인할 수 있어요.'}</p></div></li><li><div><h3>{!records.length?'기록이 쌓이면 더 잘 보여요.':fiberMissing?'식이섬유 일부 정보 없음.':'식이섬유 기록을 확인해보세요.'}</h3><p>{!records.length?'먹은 음식과 실제 양을 기록하면 하루의 식사를 돌아볼 수 있습니다.':fiberMissing?'누락된 성분은 0으로 채우지 않습니다. 기록된 양만으로 충분히 섭취했는지 판단하지 않습니다.':`등록된 식사의 식이섬유 합계는 ${fmt(totals.fiber.known_total??0)}g입니다. 일부 기록으로 하루 부족을 판정하지 않습니다.`}</p></div></li><li><div><h3>다음 식사를 위한 작은 실천</h3><p>{review?.actions[0]??'다양한 채소와 단백질 급원을 함께 살펴보세요. 특정 식품의 가격·알레르기 적합성을 확인한 추천은 아닙니다.'}</p></div></li></ol><div className="sodium-note">나트륨 <small>(기록된 양)</small><strong>{totals.sodium.known_total===null?'—':fmt(totals.sodium.known_total)} <small>{totals.sodium.known_total===null?'':'mg'}</small></strong>{totals.sodium.status==='partial'&&<span>일부 정보 누락</span>}</div><button className="evidence-link" onClick={()=>onView('insights')}><ArrowUpRight size={18}/> 판단 근거 보기 <ChevronRight size={16}/></button><p className="journal-limitation">일부 식사 기록만으로 하루 영양 적정성을 판단하지 않습니다.</p></aside>
  </div>
 </section>
}
