import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { WellnessData } from './Wellness'
import { today } from './Wellness'
export type ActivityRecord = { id: string; date: string; age: number; activity_code: string; weight_kg: number; minutes: number; calculation: { name: string; met: number; gross_kcal: number; above_rest_kcal: number; formula: string; version: string; checked_on: string; source_url: string; scope: string } }
type Activity = { category: string; code: string; name: string; met: number; url: string }
export function ActivityLog({ data, onChange }: { data: WellnessData; onChange: (data: WellnessData) => void }) {
  const [activities, setActivities] = useState<Activity[]>([])
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<ActivityRecord | null>(null)
  const [day, setDay] = useState(today())
  const request = useRef<AbortController | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    setError('')
    fetch('/api/activities', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw Error()
      const value = await response.json()
      if (!controller.signal.aborted) setActivities(value.items)
    }).catch(() => { if (!controller.signal.aborted) setError('운동 목록을 불러오지 못했습니다. 다시 시도해주세요.') })
    return () => { controller.abort(); request.current?.abort() }
  }, [attempt])
  const records = data.activityRecords ?? []
  const selected = records.filter(record => record.date === day)
  async function calculate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget), controller = new AbortController()
    request.current = controller
    setBusy(true); setError(''); setResult(null)
    try {
      const response = await fetch('/api/activities/calculate', { method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: crypto.randomUUID(), date: form.get('date'), age: Number(form.get('age')), activity_code: form.get('activity'), weight_kg: Number(form.get('weight')), minutes: Number(form.get('minutes')) }) })
      if (!response.ok) throw Error()
      const value: ActivityRecord = await response.json()
      if (!controller.signal.aborted) setResult(value)
    } catch { if (!controller.signal.aborted) setError('연령·날짜·체중·시간과 서버 연결을 확인해주세요. 기록은 추가되지 않았습니다.') }
    finally { if (!controller.signal.aborted) setBusy(false) }
  }
  return <section className="activity-log" aria-labelledby="activity-log-title"><h2 id="activity-log-title">실제 운동 기록과 소모량 추정</h2>
    <p>2024 Adult Compendium의 <b>19~59세 일반 성인</b> 표준 MET를 사용합니다. MET는 활동의 에너지 비용을 나타내는 값입니다. 60세 이상은 이번 계산에서 제외하며, BMI·인바디로 강도를 정하지 않습니다.</p>
    <p>걷기·러닝·근력·자전거·생활 스포츠 등을 분류별로 선택할 수 있습니다. 웨이트의 반복 수는 자료의 수행 조건이며 권장 반복 수가 아닙니다. 세트 수·중량을 자동 처방하지 않습니다.</p>
    <p>긴 휴식·대기·다른 종목을 섞은 전체 시간을 하나의 MET로 계산하면 오차가 커질 수 있습니다. 해당 조건으로 수행한 시간을 구분해 기록하세요.</p>
    <p>이미 수행한 활동의 조건을 선택하세요. 속도·출력을 모르면 비슷하다고 임의로 고르지 마세요. 계산은 필수 운동량이나 운동 강도 추천이 아닙니다.</p>
    {activities.length > 0 ? <form onSubmit={calculate} onChange={() => setResult(null)} aria-label="실제 운동 계산"><fieldset className="profile-form exercise-fields" disabled={busy}><legend className="sr-only">실제 수행한 운동</legend>
      <label>운동 날짜<input type="date" name="date" required max={today()} defaultValue={today()}/></label>
      <label>운동 당시 나이 (세)<input type="number" name="age" required min="19" max="59" step="1" defaultValue={data.profile?.age as number | undefined}/></label>
      <label className="wide">수행한 운동<select name="activity" aria-label="수행한 운동" required>{[...new Set(activities.map(activity => activity.category))].map(category => <optgroup key={category} label={category}>{activities.filter(activity => activity.category === category).map(activity => <option key={activity.code} value={activity.code}>{activity.name} · {activity.met} MET</option>)}</optgroup>)}</select></label>
      <label>운동 당시 체중 (kg)<input type="number" name="weight" required min="25" max="350" step="any" defaultValue={data.profile?.weight_kg as number | undefined}/></label>
      <label>운동 시간 (분)<input type="number" name="minutes" required min="0" max="300" step="any" defaultValue="30"/></label>
      <p className="wide">기본 체중·나이는 현재 프로필에서 가져옵니다. 과거 기록은 당시 값으로 바꾸세요. 0분은 0kcal로 기록할 수 있습니다.</p>
      <button className="calculate-button wide" type="submit">{busy ? '계산 중…' : '운동 소모량 계산'}</button>
    </fieldset></form> : <button onClick={() => setAttempt(value => value + 1)}>운동 목록 다시 불러오기</button>}
    {error && <p role="alert">{error}</p>}
    {result && <div className="activity-estimate" role="status"><h3>운동 소모량 참고 결과</h3><p>{result.calculation.name} · {result.minutes}분 · {result.weight_kg}kg</p><p>운동 중 총 소모량 <b>{result.calculation.gross_kcal} kcal</b> · 안정 시 소모량 제외 <b>{result.calculation.above_rest_kcal} kcal</b></p><p>{result.calculation.formula}</p><p>개인 실측값이 아닙니다. 총 소모량에는 안정 시 소비도 포함됩니다. 활동량을 포함한 유지 에너지에 이 값을 자동으로 더하거나 식사 열량에서 빼지 않습니다.</p><button onClick={() => { onChange({ ...data, activityRecords: [...records, result] }); setDay(result.date); setResult(null) }}>운동 기록에 추가</button></div>}
    <h3>날짜별 운동 기록</h3><label>운동 조회 날짜<input type="date" max={today()} value={day} onChange={event => { if (event.target.value) setDay(event.target.value) }}/></label>
    {selected.length ? <><p>등록 {selected.length}건 · {selected.reduce((total, record) => total + record.minutes, 0)}분 · 총 소모량 추정 합계 {Number(selected.reduce((total, record) => total + record.calculation.gross_kcal, 0).toFixed(2))} kcal</p>{selected.map(record => <article className="activity-record" key={record.id}><h4>{record.calculation.name}</h4><p>{record.date} · {record.minutes}분 · {record.weight_kg}kg · 당시 {record.age}세</p><p>총 {record.calculation.gross_kcal} kcal · 안정 시 제외 {record.calculation.above_rest_kcal} kcal</p><small>{record.activity_code} · {record.calculation.met} MET · {record.calculation.version} · 확인 {record.calculation.checked_on}</small><p><a href={record.calculation.source_url} target="_blank" rel="noreferrer">이 활동의 공식 MET 출처</a></p><button onClick={() => { if (window.confirm('이 운동 기록을 삭제할까요?')) onChange({ ...data, activityRecords: records.filter(item => item.id !== record.id) }) }}>운동 기록 삭제</button></article>)}</> : <p>이 날짜의 운동 기록이 없습니다. 미기록은 실제 운동 0분을 뜻하지 않습니다.</p>}
    <p><a href="https://pacompendium.com/" target="_blank" rel="noreferrer">공식 자료: 2024 Compendium of Physical Activities</a></p>
  </section>
}
