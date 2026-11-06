import { Check, ArrowUpRight } from 'lucide-react'
import type { WellnessData } from './Wellness'

export function GettingStarted({ data, onView }: { data: WellnessData; onView: (view: string) => void }) {
  const steps = [
    { title: '내 몸과 목표 입력', done: Boolean(data.profile), view: 'profile', action: '프로필 입력하기', description: '나이·키·체중·활동 수준을 등록하세요. 인바디 값은 선택입니다.' },
    { title: '추정 목표 계산', done: Boolean(data.profile && data.estimate), view: 'profile', action: '목표와 근거 보기', description: '프로필 적용 후 계산된 유지 에너지와 참고 목표의 근거를 확인하세요.' },
    { title: '첫 식사 기록', done: data.records.length > 0, view: 'meal', action: '식사 기록하기', description: '음식을 검색하고 실제 섭취량을 입력한 뒤, 계산 결과를 기록하세요.' },
  ]
  const completed = steps.filter(step => step.done).length
  const next = steps.findIndex(step => !step.done)
  return <details className="getting-started" open={completed < steps.length}>
    <summary><span>{completed === steps.length ? '첫 이용 준비 완료' : '처음이라면 여기서 시작하세요'}</span><small>{completed} / {steps.length} 단계</small></summary>
    <p className="getting-started-context">현재 선택한 프로필 기준입니다. 로그인 없이 시작할 수 있으며, 계정별 저장은 상단 ‘로그인 / 회원가입’에서 로그인 후 사용할 수 있어요. 로컬 기록은 계정으로 자동 이동하지 않습니다.</p>
    <ol>{steps.map((step, index) => <li key={step.title} aria-current={index === next ? 'step' : undefined}>
      <span className={`getting-started-number ${step.done ? 'done' : ''}`}>{step.done ? <Check size={16} aria-label="완료"/> : `0${index + 1}`}</span>
      <h2>{step.title}</h2><p>{step.description}</p>
      <button onClick={() => onView(step.view)}>{step.done ? index === 2 ? '식사 추가하기' : step.action.replace('입력하기', '확인하기') : step.action}<ArrowUpRight size={15}/></button>
      <small>{step.done ? index === 1 ? '계산됨 · 근거를 읽어보세요' : '등록됨' : index === next ? '다음 할 일' : '미완료'}</small>
    </li>)}</ol>
  </details>
}
