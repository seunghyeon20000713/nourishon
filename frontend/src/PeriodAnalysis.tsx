import { useState } from 'react'
import type { WellnessData, Nutrient } from './Wellness'
import { labels, today } from './Wellness'

const fmt = (value: number) => new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 }).format(value)
function shift(date: string, days: number) {
  const value = new Date(`${date}T12:00:00Z`)
  value.setUTCDate(value.getUTCDate() + days)
  return value.toISOString().slice(0, 10)
}
export function periodBounds(anchor: string, mode: 'week' | 'month') {
  const date = new Date(`${anchor}T12:00:00Z`)
  if (mode === 'week') {
    const start = shift(anchor, -((date.getUTCDay() + 6) % 7))
    return { start, end: shift(start, 6) }
  }
  const start = `${anchor.slice(0, 7)}-01`
  const next = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1, 12)).toISOString().slice(0, 10)
  return { start, end: shift(next, -1) }
}
function sum(records: WellnessData['records'], key: string): Nutrient {
  let total = 0, known = 0, missing = 0
  for (const record of records) {
    const nutrient = record.calculation.totals[key]
    if (nutrient?.known_total != null) { total += nutrient.known_total; known++ }
    missing += nutrient ? Math.max(nutrient.missing_count, nutrient.status === 'complete' ? 0 : 1) : 1
  }
  return { known_total: known ? total : null, missing_count: missing, status: !known ? 'missing' : missing ? 'partial' : 'complete', unit: key === 'energy' ? 'kcal' : key === 'sodium' ? 'mg' : 'g' }
}
export function PeriodAnalysis({ data, anchor, onDay }: { data: WellnessData; anchor: string; onDay: (date: string) => void }) {
  const [mode, setMode] = useState<'week' | 'month'>('week')
  const { start, end } = periodBounds(anchor, mode)
  const days: { date: string; records: WellnessData['records']; energy: Nutrient }[] = []
  for (let date = start; date <= end; date = shift(date, 1)) {
    const records = data.records.filter(record => record.date === date)
    days.push({ date, records, energy: sum(records, 'energy') })
  }
  const records = days.flatMap(day => day.date <= today() ? day.records : [])
  const recordedDays = days.filter(day => day.date <= today() && day.records.length).length
  const energyDays = days.filter(day => day.date <= today() && day.energy.known_total !== null)
  const energy = sum(records, 'energy')
  const measurements = (data.measurements ?? []).filter(row => row.measured_on >= start && row.measured_on <= end && row.measured_on <= today()).sort((a, b) => a.measured_on.localeCompare(b.measured_on))
  const maximum = Math.max(1, ...energyDays.map(day => day.energy.known_total ?? 0))
  return <section className="period-analysis" aria-labelledby="period-heading">
    <div className="period-heading"><h2 id="period-heading">주간·월간 기록 분석</h2><div role="group" aria-label="분석 기간"><button aria-pressed={mode === 'week'} onClick={() => setMode('week')}>주간</button><button aria-pressed={mode === 'month'} onClick={() => setMode('month')}>월간</button></div></div>
    <p>선택한 조회 날짜가 속한 {mode === 'week' ? '월요일~일요일' : '달력 월'} · <b>{start} ~ {end}</b></p>
    <p className="period-limitation">오늘까지 등록한 값만 집계합니다. 미기록일은 0으로 채우지 않으며, 기록량은 실제 하루 전체 섭취량과 다를 수 있습니다.</p>
    <div className="period-summary"><article><span>식사 기록</span><strong>{records.length}건 · {recordedDays}일</strong></article><article><span>확인된 열량 합계</span><strong>{energy.known_total === null ? '정보 없음' : `${fmt(energy.known_total)} kcal`}</strong><small>{energy.status === 'partial' ? '일부 정보 누락 · 확인된 값만 합산' : '등록한 식사의 합계'}</small></article><article><span>열량 정보가 있는 기록일 평균</span><strong>{energyDays.length ? `${fmt((energy.known_total ?? 0) / energyDays.length)} kcal` : '정보 없음'}</strong><small>분모 {energyDays.length}일 · 실제 일평균 섭취량이 아닙니다.</small></article></div>
    <div className="period-table"><table><caption>기간별 영양성분 · 확인된 값의 합계</caption><thead><tr><th>영양성분</th><th>기록 합계</th><th>정보 상태</th></tr></thead><tbody>{Object.entries(labels).map(([key, label]) => { const value = sum(records, key); return <tr key={key}><th>{label}</th><td>{value.known_total === null ? '정보 없음' : `${fmt(value.known_total)} ${value.unit}`}</td><td>{!records.length ? '식사 미기록' : value.status === 'complete' ? '등록 값 확인됨' : value.status === 'partial' ? '일부 정보 누락' : '영양 정보 없음'}</td></tr> })}</tbody></table></div>
    <h3>날짜별 식사 기록</h3><div className={`period-days ${mode}`}>{days.map(day => <button key={day.date} disabled={day.date > today()} onClick={() => onDay(day.date)} aria-label={`${day.date} 상세 기록 보기`} className={day.date === anchor ? 'selected' : ''}><b>{day.date.slice(5)}</b><span>{day.date > today() ? '예정' : !day.records.length ? '미기록' : day.energy.known_total === null ? '열량 정보 없음' : `${fmt(day.energy.known_total)} kcal`}</span>{day.date <= today() && day.energy.known_total !== null && <span className="period-bar" aria-hidden="true"><i style={{ width: `${100 * day.energy.known_total / maximum}%` }}/></span>}{day.records.length > 0 && day.energy.status === 'partial' && <small>일부 누락</small>}</button>)}</div>
    <h3>같은 기간의 신체 변화</h3><p>측정 {measurements.length}건. 기간 안에서 각 항목의 값이 있는 첫날과 마지막 날을 비교합니다. 측정 조건에 따른 차이가 있어 식사 기록과의 인과관계나 건강 개선을 뜻하지 않습니다.</p>
    <div className="period-table"><table><caption>기간 내 체중·체성분 변화</caption><thead><tr><th>항목</th><th>첫 측정</th><th>마지막 측정</th><th>변화</th></tr></thead><tbody>{([['weight_kg', '체중', 'kg'], ['skeletal_muscle_kg', '골격근량', 'kg'], ['fat_mass_kg', '체지방량', 'kg'], ['body_fat_percent', '체지방률', '%p']] as const).map(([key, label, unit]) => {
      const values = measurements.filter(row => row[key] != null), first = values[0], last = values[values.length - 1]
      const comparable = first && last && first.measured_on !== last.measured_on
      const difference = comparable ? last[key]! - first[key]! : null
      return <tr key={key}><th>{label}</th><td>{first ? `${first.measured_on} · ${fmt(first[key]!)}${key === 'body_fat_percent' ? '%' : ' kg'}` : '미등록'}</td><td>{last ? `${last.measured_on} · ${fmt(last[key]!)}${key === 'body_fat_percent' ? '%' : ' kg'}` : '미등록'}</td><td>{difference === null ? '다른 날짜의 측정 2회 필요' : `${difference > 0 ? '+' : ''}${fmt(difference)} ${unit}`}</td></tr>
    })}</tbody></table></div>
    <p className="period-limitation">동일 날짜의 기록만 있으면 변화량을 산출하지 않습니다. 기간 밖의 측정값을 대신 넣거나 누락된 체성분을 추정하지 않습니다.</p>
  </section>
}
