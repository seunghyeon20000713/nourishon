import type { WellnessData } from './Wellness'
export type Measurement = {
 id: string; measured_on: string; weight_kg: number;
 skeletal_muscle_kg?: number; fat_mass_kg?: number; body_fat_percent?: number;
}
export function Measurements({data}:{data:WellnessData}) {
 const rows=[...(data.measurements??[])].sort((a,b)=>a.measured_on.localeCompare(b.measured_on))
 if(!rows.length)return <section className="measurement-section"><h2>체중·인바디 측정 이력</h2><p>프로필을 적용하면 측정일과 체중이 함께 기록됩니다. 인바디 항목은 선택입니다.</p></section>
 const first=rows[0],last=rows[rows.length-1]
 const delta=Number((last.weight_kg-first.weight_kg).toFixed(2))
 const min=Math.min(...rows.map(r=>r.weight_kg)), max=Math.max(...rows.map(r=>r.weight_kg))
 return <section className="measurement-section"><h2>체중·인바디 측정 이력</h2><p>기록 {rows.length}건 · 최근 체중 <b>{last.weight_kg} kg</b>{rows.length>1&&<> · 첫 기록 대비 <b>{delta>0?'+':''}{delta} kg</b></>}</p><p>변화량은 기록값의 차이입니다. 수분 상태·측정 시간·기기 차이를 고려해야 하며 건강 개선 여부로 판정하지 않습니다.</p>
 {rows.length>1&&<figure className="weight-chart"><figcaption>측정 순서에 따른 체중 변화 (kg)</figcaption><svg viewBox="0 0 640 140" role="img" aria-label={`체중 기록 ${rows.length}건, 처음 ${first.weight_kg}kg, 최근 ${last.weight_kg}kg`}><line x1="28" y1="110" x2="612" y2="110" stroke="#dce3d6"/><polyline fill="none" stroke="#347a58" strokeWidth="3" points={rows.map((r,i)=>`${28+i*584/(rows.length-1)},${100-(r.weight_kg-min)/Math.max(max-min,1)*65}`).join(' ')}/>{rows.map((r,i)=><g key={r.id}><circle cx={28+i*584/(rows.length-1)} cy={100-(r.weight_kg-min)/Math.max(max-min,1)*65} r="4" fill="#347a58"/><title>{r.measured_on}: {r.weight_kg}kg</title></g>)}</svg><small>{first.measured_on} → {last.measured_on} · 가로 간격은 측정 순서이며 시간 간격이 아닙니다.</small></figure>}
 <div className="measurement-table"><table><caption>측정값 원본 · 빈 값은 미등록</caption><thead><tr><th>측정일</th><th>체중 kg</th><th>골격근량 kg</th><th>체지방량 kg</th><th>체지방률 %</th></tr></thead><tbody>{[...rows].reverse().map(r=><tr key={r.id}><td>{r.measured_on}</td><td>{r.weight_kg}</td><td>{r.skeletal_muscle_kg??'미등록'}</td><td>{r.fat_mass_kg??'미등록'}</td><td>{r.body_fat_percent??'미등록'}</td></tr>)}</tbody></table></div></section>
}
