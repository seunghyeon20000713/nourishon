import { ArrowUpRight, ChevronRight, Activity, UserRound, Utensils } from 'lucide-react'
import { CartesianGrid, LabelList, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { aggregate, today } from './Wellness'
import type { WellnessData } from './Wellness'
import type { Measurement } from './Measurements'
const number = (value:number) => new Intl.NumberFormat('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1}).format(value)
const shortDate = (value:string) => value.replaceAll('-','.')
const fields = [['skeletal_muscle_kg','골격근량','kg'],['fat_mass_kg','체지방량','kg'],['body_fat_percent','체지방률','%']] as const

export function BodyOverview({data,day,onView,onMeal}:{data:WellnessData;day:string;onView:(view:string,day?:string)=>void;onMeal:(kind:string)=>void}) {
 // 같은 날 여러 측정이 있으면 마지막으로 보관한 값을 사용한다. 누락 항목을 과거 값으로 채우지 않는다.
 const byDate = new Map<string,Measurement>()
 for(const row of data.measurements??[])if(row.measured_on<=day)byDate.set(row.measured_on,row)
 const rows=[...byDate.values()].sort((a,b)=>a.measured_on.localeCompare(b.measured_on))
 const latest=rows.at(-1),previous=rows.at(-2)
 const difference=latest&&previous?latest.weight_kg-previous.weight_kg:null
 const chartRows=rows.slice(-12).map(row=>({...row,time:new Date(`${row.measured_on}T12:00:00+09:00`).getTime()}))
 const meals=data.records.filter(row=>row.date===day),totals=aggregate(meals)
 const mealAction=()=>day===today()?onMeal('아침'):onView('history',day)
 const profileWeight=typeof data.profile?.weight_kg==='number'?data.profile.weight_kg:null
 const height=typeof data.profile?.height_cm==='number'?data.profile.height_cm:null
 return <>
 <div className="body-diary-grid">
  <section className="body-overview" aria-labelledby="body-overview-title">
   <div className="record-section-heading"><h2 id="body-overview-title">내 몸의 기록</h2><div><small>{latest?`최근 측정일 ${shortDate(latest.measured_on)}`:'아직 측정 기록이 없어요'}</small><button onClick={()=>onView('profile')}>측정 기록 보기 <ArrowUpRight size={15}/></button></div></div>
   <div className="body-weight"><strong>{latest?number(latest.weight_kg):'—'}</strong><span>kg</span>{difference!==null&&<div className="weight-difference"><b>{difference>0?'+':''}{number(difference)} kg</b><span>({shortDate(previous!.measured_on)} 대비)</span></div>}</div>
   {!latest?<div className="body-empty"><h3>몸의 변화를 한눈에</h3><p>체중과 측정일을 등록하면 기록이 쌓일 때마다 변화를 볼 수 있어요. 인바디 항목은 선택입니다.</p><button onClick={()=>onView('profile')}>내 몸 정보 입력 <ArrowUpRight size={16}/></button></div>:chartRows.length<2?<div className="body-empty"><h3>첫 측정이 기록됐어요</h3><p>다른 날짜의 측정값을 추가하면 변화 추이를 표시합니다.</p><button onClick={()=>onView('profile')}>측정값 추가 <ArrowUpRight size={16}/></button></div>:<figure className="body-trend" aria-label="측정일에 따른 체중 변화"><figcaption>체중 (kg) · 최근 {chartRows.length}개 측정일</figcaption><ResponsiveContainer width="100%" height={195}><LineChart data={chartRows} margin={{top:30,right:28,left:-15,bottom:8}}><CartesianGrid vertical={false} stroke="#d5d9d0" strokeDasharray="3 3"/><XAxis dataKey="time" type="number" scale="time" domain={['dataMin','dataMax']} ticks={chartRows.map(row=>row.time)} minTickGap={30} tickFormatter={value=>new Intl.DateTimeFormat('ko-KR',{month:'2-digit',day:'2-digit',timeZone:'Asia/Seoul'}).format(new Date(value))} tick={{fill:'#626963',fontSize:12}} axisLine={{stroke:'#adb4aa'}} tickLine={false}/><YAxis domain={['dataMin - 1','dataMax + 1']} tickFormatter={value=>number(value)} tick={{fill:'#626963',fontSize:12}} axisLine={false} tickLine={false} width={60}/><Tooltip labelFormatter={value=>new Intl.DateTimeFormat('ko-KR',{dateStyle:'medium',timeZone:'Asia/Seoul'}).format(new Date(Number(value)))} formatter={value=>[`${number(Number(value))} kg`,'체중']}/><Line dataKey="weight_kg" stroke="#1d5139" strokeWidth={2} dot={{r:4,fill:'#f7f6f0',strokeWidth:2}} activeDot={{r:6}} isAnimationActive={false}><LabelList dataKey="weight_kg" position="top" offset={12} fill="#234b36" fontSize={12} formatter={value=>number(Number(value))}/></Line></LineChart></ResponsiveContainer></figure>}
   <dl className="body-metrics">{fields.map(([key,label,unit])=><div key={key}><dt>{label}</dt><dd>{latest?.[key]===undefined?<span className="unregistered">미등록</span>:<><strong>{number(latest[key])}</strong> <span>{unit}</span></>}</dd></div>)}</dl>
   <p className="measurement-context">선택일까지 최근 측정 기준 · 변화량은 기록값의 차이이며 건강 개선 여부를 뜻하지 않습니다.</p>
  </section>
  <aside className="daily-diary" aria-label="하루 기록 바로가기"><img className="journal-sprig" src="/decoration/journal-sprig.png" alt=""/><h2>{day===today()?'오늘의 일기':'선택한 날의 기록'}</h2><div className="diary-food-label"><Utensils size={19}/> {day===today()?'오늘의 식사':'기록한 식사'}</div><div className="diary-energy"><strong>{totals.energy.known_total===null?'—':new Intl.NumberFormat('ko-KR',{maximumFractionDigits:0}).format(totals.energy.known_total)}</strong><span>kcal</span></div><p>{meals.length?`${meals.length}건 · 기록된 식사 기준`:'식사 기록이 없어요'}{totals.energy.status==='partial'?' · 일부 누락':''}</p>
   <dl className="diary-nutrients">{(['protein','fiber','sodium'] as const).map((key,i)=><div key={key}><dt>{['단백질','식이섬유','나트륨'][i]}</dt><dd>{totals[key].known_total===null?'—':new Intl.NumberFormat('ko-KR',{maximumFractionDigits:1}).format(totals[key].known_total)} <small>{totals[key].unit}</small></dd>{totals[key].status==='partial'&&<small>일부 누락</small>}</div>)}</dl>
   <button className="diary-add" onClick={mealAction}>{day===today()?'식사 기록하기':'식사 기록 보기'}<ArrowUpRight size={17}/></button><button className="diary-shortcut" aria-label="운동 기록하기" onClick={()=>onView('activity')}><Activity size={21}/>운동 기록<ChevronRight size={18}/></button><button className="diary-shortcut" onClick={()=>onView('profile')}><UserRound size={21}/>내 정보 수정<ChevronRight size={18}/></button><small className="diary-footnote">미기록은 0이 아닙니다. 기록된 양은 하루 전체 섭취량과 다를 수 있어요.</small>
  </aside>
 </div>
 <div className="measurement-bottom"><section className="body-recent" aria-labelledby="recent-body-title"><div className="record-section-heading"><h2 id="recent-body-title">측정 기록</h2><button onClick={()=>onView('profile')}>전체 기록 <ArrowUpRight size={15}/></button></div>{rows.length?<div className="body-table-scroll" tabIndex={0} role="region" aria-label="최근 측정값 표"><table><caption className="sr-only">최근 5개 측정일 · 빈 값은 미등록</caption><thead><tr><th>측정일</th><th>체중 (kg)</th><th>골격근량 (kg)</th><th>체지방량 (kg)</th><th>체지방률 (%)</th></tr></thead><tbody>{rows.slice(-5).reverse().map(row=><tr key={row.id}><th scope="row">{shortDate(row.measured_on)}</th><td>{number(row.weight_kg)}</td>{fields.map(([key])=><td key={key}>{row[key]===undefined?'미등록':number(row[key])}</td>)}</tr>)}</tbody></table></div>:<p className="body-no-record">등록된 측정값이 없습니다.</p>}</section><section className="body-bmi"><h2>BMI</h2><div><strong>{data.estimate?number(data.estimate.bmi):'—'}</strong><span>키·체중 기반 참고값</span></div><p>{height!==null&&profileWeight!==null?`계산 기준 · 현재 프로필 키 ${height} cm / 체중 ${profileWeight} kg`:'프로필을 적용하면 계산됩니다.'}</p><small>현재 프로필 기준입니다. 체성분·건강 상태를 판단하는 지표는 아닙니다.</small></section></div>
 </>
}
