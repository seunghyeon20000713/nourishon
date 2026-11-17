import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Bike, Dumbbell, Flower2, Footprints, HeartPulse, Timer, Volleyball } from 'lucide-react'
import type { WellnessData } from './Wellness'
import { today } from './Wellness'
import { ACTIVITY_GUIDE, activityLabel, intensity } from './activityGuide'
export type ActivityRecord = { id: string; date: string; age: number; activity_code: string; weight_kg: number; minutes: number; calculation: { name: string; met: number; gross_kcal: number; above_rest_kcal: number; formula: string; version: string; checked_on: string; source_url: string; scope: string } }
type Activity = { category: string; code: string; name: string; met: number; url: string }
const CATEGORY_ICONS: Record<string, typeof Bike> = { '걷기': Footprints, '러닝': Timer, '자전거': Bike, '근력·맨몸': Dumbbell, '스트레칭·요가·필라테스': Flower2, '유산소 기구': HeartPulse, '생활 스포츠': Volleyball }
const kcal = (value: number) => `${Number(value.toFixed(2))} kcal`

export function ActivityLog({ data, onChange }: { data: WellnessData; onChange: (data: WellnessData) => void }) {
  const [activities, setActivities] = useState<Activity[]>([])
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<ActivityRecord | null>(null)
  const [day, setDay] = useState(today())
  const [category, setCategory] = useState('')
  const [code, setCode] = useState('')
  const request = useRef<AbortController | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    setError('')
    fetch('/api/activities', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw Error()
      const value = await response.json()
      if (controller.signal.aborted) return
      setActivities(value.items)
      if (value.items.length) { setCategory(value.items[0].category); setCode(value.items[0].code) }
    }).catch(() => { if (!controller.signal.aborted) setError('운동 목록을 불러오지 못했습니다. 다시 시도해주세요.') })
    return () => { controller.abort(); request.current?.abort() }
  }, [attempt])
  const records = data.activityRecords ?? []
  const selected = records.filter(record => record.date === day)
  const categories = [...new Set(activities.map(activity => activity.category))]
  function chooseCategory(name: string) {
    setCategory(name)
    setCode(activities.find(activity => activity.category === name)?.code ?? '')
  }
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
  return <section className="activity-log" aria-labelledby="activity-log-title">
    <h2 id="activity-log-title" tabIndex={-1}>오늘 한 운동 기록하기</h2>
    <p className="activity-lead">한 운동과 시간을 고르면 쓴 에너지를 추정해 드려요. 운동을 추천하거나 처방하지는 않아요.</p>
    <details className="activity-notes"><summary>계산 방법과 주의할 점</summary>
      <p>2024 Adult Compendium의 <b>19~59세 일반 성인</b> 표준 MET를 사용합니다. MET는 활동의 에너지 비용을 나타내는 값입니다. 60세 이상은 이번 계산에서 제외하며, BMI·인바디로 강도를 정하지 않습니다.</p>
      <p>걷기·러닝·근력·자전거·생활 스포츠 등을 분류별로 선택할 수 있습니다. 웨이트의 반복 수는 자료의 수행 조건이며 권장 반복 수가 아닙니다. 세트 수·중량을 자동 처방하지 않습니다.</p>
      <p>긴 휴식·대기·다른 종목을 섞은 전체 시간을 하나의 MET로 계산하면 오차가 커질 수 있습니다. 해당 조건으로 수행한 시간을 구분해 기록하세요.</p>
      <p>이미 수행한 활동의 조건을 선택하세요. 속도·출력을 모르면 비슷하다고 임의로 고르지 마세요. 계산은 필수 운동량이나 운동 강도 추천이 아닙니다.</p>
      <p>강도 표시는 MET 3 미만 가벼운 강도, 3 이상 6 미만 중간 강도, 6 이상 높은 강도로 나눈 일반적인 구분입니다(2018 Physical Activity Guidelines Advisory Committee Report).</p>
    </details>
    {activities.length > 0 ? <form className="activity-form" onSubmit={calculate} onChange={() => setResult(null)} aria-label="실제 운동 계산"><fieldset className="exercise-fields" disabled={busy}><legend className="sr-only">실제 수행한 운동</legend>
      <fieldset className="activity-step"><legend><b>1</b>어떤 운동을 했나요?</legend>
        <div className="activity-categories">{categories.map(name => { const Icon = CATEGORY_ICONS[name] ?? HeartPulse; return <label key={name} className={category === name ? 'selected' : ''}><input type="radio" name="activity-category" value={name} checked={category === name} onChange={() => chooseCategory(name)}/><Icon size={20} aria-hidden="true"/><span>{name}</span></label> })}</div>
      </fieldset>
      <fieldset className="activity-step"><legend><b>2</b>어떻게 했나요?</legend>
        <div className="activity-options">{activities.filter(activity => activity.category === category).map(activity => { const level = intensity(activity.met), guide = ACTIVITY_GUIDE[activity.code]; return <label key={activity.code} className={code === activity.code ? 'selected' : ''}><input type="radio" name="activity" value={activity.code} required checked={code === activity.code} onChange={() => setCode(activity.code)}/><span className="activity-option-text"><strong>{guide?.label ?? activity.name}</strong><small>{guide?.hint}</small></span><span className={`intensity intensity-${level.level}`}>{level.text}</span></label> })}</div>
        <p className="activity-help">속도나 출력을 모르면 비슷해 보인다고 고르지 말고, 가장 가까운 ‘내가 편한 속도’ 항목을 고르세요.</p>
      </fieldset>
      <fieldset className="activity-step"><legend><b>3</b>언제, 얼마나 했나요?</legend>
        <div className="activity-inputs">
          <label>운동 날짜<input type="date" name="date" required max={today()} defaultValue={today()}/></label>
          <label>운동 시간 (분)<input type="number" name="minutes" required min="0" max="300" step="any" defaultValue="30"/></label>
          <label>운동 당시 나이 (세)<input type="number" name="age" required min="19" max="59" step="1" defaultValue={data.profile?.age as number | undefined}/></label>
          <label>운동 당시 체중 (kg)<input type="number" name="weight" required min="25" max="350" step="any" defaultValue={data.profile?.weight_kg as number | undefined}/></label>
        </div>
        <p className="activity-help">나이·체중은 내 정보에서 가져와요. 지난 운동이면 그때 값으로 바꿔 주세요. 0분도 기록할 수 있어요.</p>
      </fieldset>
      <button className="calculate-button" type="submit">{busy ? '계산 중…' : '운동 소모량 계산'}</button>
    </fieldset></form> : <button onClick={() => setAttempt(value => value + 1)}>운동 목록 다시 불러오기</button>}
    {error && <p role="alert">{error}</p>}
    {result && <div className="activity-estimate" role="status"><h3>계산 결과 · {activityLabel(result.activity_code, result.calculation.name)} {result.minutes}분</h3>
      <div className="kcal-pair">
        <div><span>운동하는 동안 쓴 에너지</span><strong>{kcal(result.calculation.gross_kcal)}</strong><small>가만히 있어도 쓰는 에너지 포함</small></div>
        <div><span>운동으로 더 쓴 에너지</span><strong>{kcal(result.calculation.above_rest_kcal)}</strong><small>가만히 있을 때보다 늘어난 만큼</small></div>
      </div>
      <p className="activity-help">추정값이에요. 식사 열량에서 자동으로 빼거나 유지 에너지에 더하지 않아요.</p>
      <details><summary>계산 근거</summary><p>{result.calculation.name} · {result.calculation.met} MET · 체중 {result.weight_kg}kg</p><p>{result.calculation.formula}</p><p>개인 실측값이 아닙니다. 총 소모량에는 안정 시 소비도 포함됩니다. 활동량을 포함한 유지 에너지에 이 값을 자동으로 더하거나 식사 열량에서 빼지 않습니다.</p></details>
      <button className="primary-action" onClick={() => { onChange({ ...data, activityRecords: [...records, result] }); setDay(result.date); setResult(null) }}>운동 기록에 추가</button></div>}
    <div className="activity-history">
      <div className="activity-history-head"><h3>날짜별 운동 기록</h3><label>운동 조회 날짜<input type="date" max={today()} value={day} onChange={event => { if (event.target.value) setDay(event.target.value) }}/></label></div>
      {selected.length ? <><p className="activity-day-total"><span>운동 {selected.length}건</span><span>총 {selected.reduce((total, record) => total + record.minutes, 0)}분</span><span>쓴 에너지 약 {kcal(selected.reduce((total, record) => total + record.calculation.gross_kcal, 0))}</span></p>
        {selected.map(record => { const Icon = CATEGORY_ICONS[activities.find(activity => activity.code === record.activity_code)?.category ?? ''] ?? HeartPulse, level = intensity(record.calculation.met); return <article className="activity-record" key={record.id}>
          <div className="activity-record-head"><span className="activity-icon"><Icon size={20} aria-hidden="true"/></span><div><h4>{activityLabel(record.activity_code, record.calculation.name)}</h4><p>{record.minutes}분 · <span className={`intensity intensity-${level.level}`}>{level.text}</span></p></div><strong>{kcal(record.calculation.gross_kcal)}</strong></div>
          <p className="activity-help">운동으로 더 쓴 에너지 {kcal(record.calculation.above_rest_kcal)}</p>
          <details><summary>자세히</summary><p>{record.date} · 체중 {record.weight_kg}kg · 당시 {record.age}세</p><p>공식 이름: {record.calculation.name}</p><small>{record.activity_code} · {record.calculation.met} MET · {record.calculation.version} · 확인 {record.calculation.checked_on}</small><p><a href={record.calculation.source_url} target="_blank" rel="noreferrer">이 활동의 공식 MET 출처</a></p></details>
          <button className="quiet-action" onClick={() => { if (window.confirm('이 운동 기록을 삭제할까요?')) onChange({ ...data, activityRecords: records.filter(item => item.id !== record.id) }) }}>운동 기록 삭제</button>
        </article> })}</> : <p className="activity-empty">이 날짜의 운동 기록이 없어요. 기록하지 않은 날은 ‘운동 0분’으로 계산하지 않아요.</p>}
    </div>
    <p className="activity-source"><a href="https://pacompendium.com/" target="_blank" rel="noreferrer">공식 자료: 2024 Compendium of Physical Activities</a></p>
  </section>
}
