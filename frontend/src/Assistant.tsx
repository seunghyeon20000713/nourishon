import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Bot, Send } from 'lucide-react'
import { accountRequest } from './Account'
import type { Session } from './Account'
import { formatWithUnit } from './nutrientFormat'

// AI 건강 비서 화면(2026-11-17). 대화는 저장하지 않고 이 화면에만 잠시 보인다.
type ToolCall = { name: string; args: Record<string, unknown>; result: Record<string, unknown> }
type Answer = { question: string; answer: string; provider: string; refused: boolean; notice: string | null; tool_calls: ToolCall[] }
type Status = { provider: string; notice: string; daily_limit: number; remaining: number }
type Nutrient = { label: string; value: number | null; unit: string; missing_count?: number }

const EXAMPLES = ['이번 주 나트륨 어때?', '어제 단백질 충분해?', '이번 주 운동 얼마나 했어?']
const TOOL_LABELS: Record<string, string> = {
  get_period_nutrition: '기간 영양 합계', get_day_meals: '하루 식사', get_nutrition_review: '영양 구성 검토',
  get_activity_summary: '운동 기록 요약', get_my_reference: '내 참고값',
}
const PROVIDER_LABELS: Record<string, string> = { fake: '기본 설명', gemini: 'Google AI', rule: '안전 안내' }

function Evidence({ call }: { call: ToolCall }) {
  const result = call.result
  const period = result.start ? `${result.start} ~ ${result.end}` : result.date ? String(result.date) : ''
  const totals = (result.totals ?? {}) as Record<string, Nutrient>
  const facts: [string, string][] = []
  if (typeof result.days_in_period === 'number' && typeof result.recorded_days === 'number') facts.push(['기록한 날', `${result.days_in_period}일 중 ${result.recorded_days}일`])
  if (typeof result.record_count === 'number') facts.push(['운동 기록', `${result.record_count}건 · ${result.total_minutes}분`])
  if (typeof result.gross_kcal_estimate === 'number') facts.push(['소모량 추정', formatWithUnit(result.gross_kcal_estimate, 'kcal')])
  if (typeof result.protein_reference_g === 'number') facts.push(['단백질 참고값', formatWithUnit(result.protein_reference_g, 'g')])
  if (typeof result.maintenance_kcal_estimate === 'number') facts.push(['유지 에너지 추정', formatWithUnit(result.maintenance_kcal_estimate, 'kcal')])
  if (typeof result.error === 'string') facts.push(['도구 오류', result.error])
  return <div className="assistant-evidence-item">
    <strong>{TOOL_LABELS[call.name] ?? call.name}</strong>{period && <span> · {period}</span>}
    {facts.length > 0 && <dl>{facts.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>}
    {Object.keys(totals).length > 0 && <table><thead><tr><th>성분</th><th>기록된 합계</th><th>누락</th></tr></thead><tbody>
      {Object.entries(totals).map(([key, n]) => <tr key={key}><th scope="row">{n.label}</th><td>{n.value == null ? '정보 없음' : formatWithUnit(n.value, n.unit)}</td><td>{n.missing_count ? `${n.missing_count}개` : '—'}</td></tr>)}
    </tbody></table>}
    {typeof result.note === 'string' && <small>{result.note}</small>}
  </div>
}

export function Assistant({ session, profileId }: { session: Session; profileId: string }) {
  const [status, setStatus] = useState<Status | null>(null)
  const [answers, setAnswers] = useState<Answer[]>([])
  const [question, setQuestion] = useState('')
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const latest = useRef<HTMLHeadingElement | null>(null)
  const loggedIn = Boolean(session.user)
  useEffect(() => {
    if (!loggedIn) return
    let active = true
    accountRequest('/assistant/status', session).then(value => { if (active) setStatus(value) }).catch(() => { if (active) setError('건강 비서 상태를 불러오지 못했어요. 잠시 뒤 다시 시도해 주세요.') })
    return () => { active = false }
  }, [loggedIn, session])
  useEffect(() => { latest.current?.focus() }, [answers.length])

  async function ask(text: string) {
    const value = text.trim()
    if (!value || busy) return
    setBusy(true); setError('')
    try {
      const body = await accountRequest('/assistant/ask', session, { method: 'POST', body: JSON.stringify({ profile_id: profileId, question: value }) })
      setAnswers(list => [...list, { question: value, ...body }])
      setStatus(current => current ? { ...current, remaining: body.remaining } : current)
      setQuestion('')
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); void ask(question) }

  if (import.meta.env.MODE === 'demo') return <section className="panel wellness-panel assistant-page"><h1>건강 비서</h1><p>체험판에서는 건강 비서를 제공하지 않아요. 실제 기능 테스트 서버에서 로그인 후 사용할 수 있어요.</p></section>
  return <section className="panel wellness-panel assistant-page" aria-labelledby="assistant-title">
    <header className="page-head"><h1 id="assistant-title">건강 비서</h1>
      <p>내 식사·운동 기록을 계산 도구로 확인하고 쉬운 말로 설명해 드려요. 기록된 값만 설명하며, 진단이나 치료를 대신하지 않습니다.</p></header>
    {!loggedIn ? <p className="assistant-login">로그인하면 내 기록으로 질문할 수 있어요. 오른쪽 위 ‘로그인’에서 가상 계정으로 시작해 보세요.</p> : <>
      <div className="assistant-thread" aria-live="polite">
        {answers.length === 0 && <div className="assistant-empty"><Bot size={28} aria-hidden="true"/><p>이렇게 물어보세요</p>
          <div className="assistant-examples">{EXAMPLES.map(example => <button key={example} type="button" disabled={busy} onClick={() => void ask(example)}>{example}</button>)}</div></div>}
        {answers.map((item, index) => <article key={index} className={`assistant-answer${item.refused ? ' refused' : ''}`}>
          <p className="assistant-question"><span className="sr-only">내 질문: </span>{item.question}</p>
          <h2 ref={index === answers.length - 1 ? latest : undefined} tabIndex={-1}>답변 <span className="assistant-provider">{PROVIDER_LABELS[item.provider] ?? item.provider}</span></h2>
          <p>{item.answer}</p>
          {item.notice && <p className="assistant-notice" role="status">{item.notice}</p>}
          {item.tool_calls.length > 0 && <details><summary>계산 근거 ({item.tool_calls.length})</summary>{item.tool_calls.map((call, i) => <Evidence key={i} call={call}/>)}</details>}
        </article>)}
      </div>
      {error && <p role="alert" className="inline-error">{error}</p>}
      <form className="assistant-form" onSubmit={submit}>
        <label htmlFor="assistant-question">질문</label>
        <div className="assistant-input"><textarea id="assistant-question" aria-describedby="assistant-data-notice" value={question} maxLength={300} rows={2} placeholder="예: 이번 주 나트륨 어때?" onChange={event => setQuestion(event.target.value)}
          onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void ask(question) } }}/>
          <button type="submit" className="calculate-button" disabled={busy || !question.trim() || status?.remaining === 0}><Send size={17} aria-hidden="true"/>{busy ? '확인 중…' : '보내기'}</button></div>
        <p className="assistant-data-notice" id="assistant-data-notice">{status?.notice ?? '전송 방식을 확인하는 중이에요.'}</p>
        {status && <p className="assistant-remaining">오늘 남은 질문 {status.remaining} / {status.daily_limit}</p>}
      </form>
    </>}
  </section>
}
