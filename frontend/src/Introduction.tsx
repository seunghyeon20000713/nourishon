import { useEffect, useRef, useState } from 'react'
import { ArrowDown, ArrowUpRight, Activity, Utensils, ChartNoAxesCombined } from 'lucide-react'
import App from './App'
import './introduction.css'

export default function Introduction() {
  const [intro, setIntro] = useState(() => location.hash !== '#dashboard')
  const [visited, setVisited] = useState(() => location.hash === '#dashboard')
  const root = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const navigate = () => {
      const next = location.hash !== '#dashboard'
      setIntro(next)
      if (!next) setVisited(true)
      window.scrollTo(0, 0)
      requestAnimationFrame(() => document.querySelector<HTMLElement>(next ? '#intro-title' : '.journal-wordmark')?.focus({ preventScroll: true }))
    }
    window.addEventListener('hashchange', navigate)
    return () => window.removeEventListener('hashchange', navigate)
  }, [])
  useEffect(() => {
    if (!intro || !root.current || !('IntersectionObserver' in window)) return
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target) }
    }), { threshold: 0.12 })
    const elements = root.current.querySelectorAll('.intro-reveal')
    elements.forEach(element => observer.observe(element))
    root.current.classList.add('intro-animated')
    return () => { observer.disconnect(); root.current?.classList.remove('intro-animated') }
  }, [intro])
  return <>
    <div ref={root} className="intro-page" hidden={!intro}>
      <a className="intro-skip" href="#intro-process">서비스 소개로 건너뛰기</a>
      <header className="intro-header"><div className="intro-brand"><a href="#intro" aria-label="N 로고 소개 화면으로 이동"><img src="/brand/nourishon-mark.png" alt=""/></a><a href="#dashboard" aria-label="NourishOn 대시보드로 이동">NourishOn</a></div><a className="intro-start" href="#dashboard">관리 시작하기 <ArrowUpRight size={17}/></a></header>
      <main>
        <section className="intro-hero" aria-labelledby="intro-title">
          <div className="intro-hero-copy"><p className="intro-kicker">NUTRITION, WITH CONTEXT</p><h1 id="intro-title" tabIndex={-1}>내 몸을 이해하고,<br/>다음 한 끼를<br/><em>더 나답게.</em></h1><p className="intro-lead">숫자를 모으는 데서 한 걸음 더.<br/>몸의 변화와 식사 기록을 함께 살펴보세요.</p><a className="intro-primary" href="#dashboard">내 식사 관리 시작하기 <ArrowUpRight size={20}/></a><p className="intro-local">현재는 로컬 개발용 서비스입니다.</p></div>
          <div className="intro-preview" aria-label="섭취량 환산 연습용 예시"><div className="intro-preview-top"><span>ONE MEAL, IN CONTEXT</span><Utensils size={22}/></div><p>얼마나 먹었는지부터,<br/><strong>정확하게.</strong></p><div className="intro-plate"><span>150<small>g 섭취</small></span></div><div className="intro-example"><span>100g당 200 kcal</span><ArrowDown size={18}/><strong>섭취 열량 300 <small>kcal</small></strong></div><p className="intro-example-note">연습용 수치 · 실제 식품·개인 기록이 아닙니다.</p></div>
          <a className="intro-scroll" href="#intro-process"><ArrowDown size={18}/> 아래로 내려 살펴보세요</a>
        </section>
        <section className="intro-process" id="intro-process" aria-labelledby="process-title">
          <div className="intro-sticky"><p className="intro-kicker">YOUR DAILY PRACTICE</p><h2 id="process-title">기록은 간단하게.<br/>해석은 근거 있게.</h2><p>내 몸, 오늘의 식사, 다음 선택.<br/>세 가지를 하나의 흐름으로 연결합니다.</p><span className="intro-side-note">01 — 03 / 일상의 영양 관리</span></div>
          <div className="intro-story">
            <article className="intro-step intro-reveal"><span className="intro-step-number">01 / UNDERSTAND</span><Activity size={32}/><h3>내 몸에서 출발해요.</h3><p>나이·키·체중·활동 수준을 입력하고, 인바디 측정값이 있다면 함께 기록하세요.</p><div className="intro-mini"><span>기본 신체 정보</span><span>선택 입력 · 체성분 측정값</span><span>계산 근거를 표시한 추정 목표</span></div><p className="intro-footnote">BMI 하나로 건강이나 근육 상태를 판단하지 않아요. 체성분은 측정 조건의 영향을 받으며 목표의 정확도를 보장하지 않습니다.</p></article>
            <article className="intro-step intro-reveal"><span className="intro-step-number">02 / RECORD</span><Utensils size={32}/><h3>먹은 만큼 기록해요.</h3><p>공공 식품 데이터에서 음식을 찾고, 실제 먹은 양을 g으로 입력해 영양성분을 계산하세요.</p><div className="intro-formula"><span>100g당 영양성분</span><b>×</b><span>섭취량(g) ÷ 100</span></div><p className="intro-footnote">100g 기준과 1회 제공량을 구분하고, 없는 영양 값은 0으로 채우지 않아요.</p></article>
            <article className="intro-step intro-reveal"><span className="intro-step-number">03 / REFLECT</span><ChartNoAxesCombined size={32}/><h3>다음 한 끼를 생각해요.</h3><p>기록된 영양 비율과 나트륨·식이섬유 정보를 살펴보고, 적용 가능한 식생활 개선 방향을 확인하세요.</p><div className="intro-mini"><span>일별·주간 기록 확인</span><span>수치와 함께 보는 판단 근거</span><span>일반 성인을 위한 생활·운동 제안</span></div><p className="intro-footnote">기록이 부족하면 판단을 보류해요. 하루 기록으로 영양 결핍을 진단하거나 질환 치료식을 처방하지 않습니다.</p></article>
          </div>
        </section>
        <section className="intro-finish intro-reveal"><p className="intro-kicker">A SMALL STEP, TODAY</p><h2>완벽한 식단보다,<br/>이해할 수 있는 한 끼부터.</h2><p>오늘 먹은 음식 하나를 기록하며 시작해보세요.</p><a className="intro-primary" href="#dashboard">대시보드 열기 <ArrowUpRight size={20}/></a></section>
      </main>
      <footer className="intro-footer"><strong>NourishOn</strong><p>일반 성인 대상 · 질환 치료식, 임신·수유, 미성년자 관리는 현재 범위에서 제외합니다.</p><span>LOCAL DEVELOPMENT / 영양 관리 포트폴리오</span></footer>
    </div>
    {visited && <div hidden={intro}><App/></div>}
  </>
}
