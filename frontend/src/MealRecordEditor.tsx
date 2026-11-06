import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { Calculation, MealRecord } from './Wellness'
import { today } from './Wellness'

export function MealRecordEditor({ record, onSave, onCancel }: {
  record: MealRecord; onSave: (record: MealRecord) => void; onCancel: () => void
}) {
  const foods = record.calculation.foods ?? []
  const [date, setDate] = useState(record.date)
  const [kind, setKind] = useState(record.kind)
  const [grams, setGrams] = useState(foods.map(food => String(food.intake_g)))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  const save = useRef(onSave)
  save.current = onSave
  useEffect(() => () => controller.current?.abort(), [])
  const canRecalculate = foods.length > 0 && foods.every(food => Boolean(food.food_code))

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!date || date > today()) { setError('식사 날짜는 오늘까지 선택해주세요.'); return }
    if (grams.some(value => !value.trim() || !Number.isFinite(Number(value)) || Number(value) < 0)) {
      setError('섭취량은 0 이상의 숫자로 입력해주세요.'); return
    }
    const changed = grams.some((value, index) => Number(value) !== foods[index].intake_g)
    setBusy(true); setError('')
    const request = new AbortController()
    controller.current = request
    try {
      let calculation: Calculation = record.calculation
      if (changed) {
        if (!canRecalculate) throw Error()
        const response = await fetch('/api/meals/calculate', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: request.signal,
          body: JSON.stringify({ entries: foods.map((food, index) => ({ food_code: food.food_code, intake_g: Number(grams[index]) })) }),
        })
        if (!response.ok) throw Error()
        calculation = await response.json()
      }
      if (!request.signal.aborted) save.current({ ...record, date, kind, calculation })
    } catch {
      if (!request.signal.aborted) setError('수정하지 못했어요. 식품 데이터와 서버 연결을 확인한 뒤 다시 시도해주세요.')
    } finally { if (!request.signal.aborted) setBusy(false) }
  }

  return <form className="meal-record-editor" aria-label="식사 기록 수정" onSubmit={submit}>
    <fieldset disabled={busy}><legend>식사 기록 수정</legend>
      <div className="meal-edit-fields"><label>식사 날짜<input type="date" required max={today()} value={date} onChange={event => setDate(event.target.value)}/></label>
      <label>식사 구분<select aria-label="식사 구분" value={kind} onChange={event => setKind(event.target.value)}>{['아침', '점심', '저녁', '간식'].map(value => <option key={value}>{value}</option>)}</select></label></div>
      {foods.map((food, index) => <label key={index}>{food.food_name} 섭취량 (g)<input type="number" min="0" step="any" required disabled={!canRecalculate} value={grams[index]} onChange={event => setGrams(values => values.map((value, i) => i === index ? event.target.value : value))}/></label>)}
      <p>{canRecalculate ? '섭취량을 바꾸면 현재 식품 데이터로 이 식사의 모든 영양성분을 다시 계산합니다. 날짜·구분만 바꾸면 기존 영양 값과 출처를 유지합니다.' : '식품 코드가 없는 이전 기록은 날짜·식사 구분만 수정할 수 있습니다.'}</p>
      <button type="submit">{busy ? '계산 중…' : '변경 적용'}</button>
    </fieldset>
    <button type="button" onClick={() => { controller.current?.abort(); onCancel() }}>수정 취소</button>
    {error && <p role="alert">{error}</p>}
  </form>
}
