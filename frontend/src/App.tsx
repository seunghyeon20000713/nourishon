import { Profile, History, Insights, emptyData, today, storageKey } from './Wellness'
import type { WellnessData, Calculation } from './Wellness'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Activity, ArrowLeft, ArrowRight, ArrowUpRight, Check, ChevronRight,
  CircleAlert, CircleHelp, Flame, Leaf, LoaderCircle, Plus, Salad, Search,
  ShieldCheck, Sprout, Trash2, UserRound, Utensils } from 'lucide-react'

type Food = { food_code: string; food_name: string; basis: string;
  source_name: string | null; updated_date: string | null }
type SearchData = { total: number; offset: number; limit: number; items: Food[] }
type Entry = { food: Food; grams: string }
const PAGE_SIZE = 8
const nutrientLabels = [ ['energy', '열량'], ['protein', '단백질'], ['fat', '지방'],
  ['carbohydrate', '탄수화물'], ['sugar', '당류'], ['fiber', '식이섬유'], ['sodium', '나트륨'] ]
const format = (n: number) => new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 3 }).format(n)

function BowlArt() {
  return <svg className="bowl-art" viewBox="0 0 220 150" fill="none" aria-hidden="true">
    <ellipse cx="110" cy="127" rx="69" ry="8" fill="#D5DECE" />
    <path d="M41 68h138c-5 39-31 61-69 61S46 107 41 68Z" fill="#F9F6EA" stroke="#387452" strokeWidth="2" />
    <path d="M44 83h132" stroke="#CDD9BC" strokeWidth="7" />
    <ellipse cx="110" cy="68" rx="70" ry="24" fill="#AEC98A" stroke="#387452" strokeWidth="2" />
    <path d="M71 61C42 28 72 9 97 44c12-46 46-32 30 3 42-21 58 7 25 23" fill="#559264" />
    <path d="M85 70c-25-21-10-37 10-13 1-27 30-32 30 0 27-18 40-2 18 19" fill="#B8D797" />
    <path d="m81 27 17 36m43-38-18 40" stroke="#E5ECD5" strokeWidth="2" strokeLinecap="round" />
    <ellipse cx="71" cy="75" rx="13" ry="9" fill="#D88D61" />
    <ellipse cx="145" cy="61" rx="12" ry="10" fill="#E7BA65" />
    <path d="m163 26 18-16m-8 31 21-4" stroke="#7DA17A" strokeWidth="2" strokeLinecap="round" />
  </svg>
}

export default function App() {
  const [view,setView] = useState('meal')
  const [data,setData] = useState<WellnessData>(() => { try { const raw=localStorage.getItem(storageKey); if(raw){ const parsed=JSON.parse(raw); if(Array.isArray(parsed.records))return parsed } } catch {} return emptyData() })
  const [persist,setPersist] = useState(() => {try{return !!localStorage.getItem(storageKey)}catch{return false}})
  const [storageError,setStorageError] = useState('')
  const [mealDate,setMealDate] = useState(today())
  const [mealKind,setMealKind] = useState('아침')
  const [saved,setSaved] = useState(false)
  useEffect(()=>{try{if(persist)localStorage.setItem(storageKey,JSON.stringify(data));else localStorage.removeItem(storageKey);setStorageError('')}catch{setStorageError('브라우저 보관에 실패했습니다. 현재 실행 중인 기록만 유지됩니다.')}},[data,persist])
  const [health, setHealth] = useState<{ status: 'loading' | 'ok' | 'error'; count?: number }>({ status: 'loading' })
  const [connectionAttempt, setConnectionAttempt] = useState(0)
  const [query, setQuery] = useState('')
  const [searchedQuery, setSearchedQuery] = useState('')
  const [results, setResults] = useState<SearchData | null>(null)
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [entries, setEntries] = useState<Entry[]>([])
  const [calculation, setCalculation] = useState<Calculation | null>(null)
  const [calculating, setCalculating] = useState(false)
  const [calculationError, setCalculationError] = useState('')
  const searchController = useRef<AbortController | null>(null)
  const calculationController = useRef<AbortController | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setHealth({ status: 'loading' })
    fetch('/api/health', { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(data => setHealth({ status: 'ok', count: data.food_count }))
      .catch(() => { if (!controller.signal.aborted) setHealth({ status: 'error' }) })
    return () => controller.abort()
  }, [connectionAttempt])

  useEffect(() => () => { searchController.current?.abort(); calculationController.current?.abort() }, [])

  async function search(term: string, offset = 0) {
    const keyword = term.trim()
    if (!keyword) { setSearchError('음식 이름을 입력해주세요.'); setResults(null); return }
    searchController.current?.abort()
    const controller = new AbortController()
    searchController.current = controller
    setSearching(true); setSearchError(''); setSearchedQuery(keyword); setResults(null)
    try {
      const response = await fetch(`/api/foods?${new URLSearchParams({ q: keyword, offset: String(offset), limit: String(PAGE_SIZE) })}`, { signal: controller.signal })
      if (!response.ok) throw new Error()
      const data: SearchData = await response.json()
      if (!controller.signal.aborted) setResults(data)
    } catch {
      if (!controller.signal.aborted) setSearchError('식품 정보를 불러오지 못했어요. 연결 상태를 확인하고 다시 검색해주세요.')
    } finally {
      if (!controller.signal.aborted) setSearching(false)
    }
  }

  function changeEntries(next: Entry[]) {
    calculationController.current?.abort()
    setSaved(false); setEntries(next); setCalculation(null); setCalculationError(''); setCalculating(false)
  }

  function addFood(food: Food) {
    if (entries.some(e => e.food.food_code === food.food_code)) return
    if (entries.length >= 100) { setCalculationError('한 번에 100개 음식까지 담을 수 있어요.'); return }
    changeEntries([...entries, { food, grams: '100' }])
  }

  async function calculate() {
    if (!entries.length) return
    if (entries.some(e => !e.grams.trim() || !Number.isFinite(Number(e.grams)) || Number(e.grams) < 0)) {
      setCalculationError('섭취량은 0 이상의 숫자로 입력해주세요.'); return
    }
    calculationController.current?.abort()
    const controller = new AbortController()
    calculationController.current = controller
    setCalculating(true); setCalculationError(''); setCalculation(null)
    try {
      const response = await fetch('/api/meals/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ entries: entries.map(e => ({ food_code: e.food.food_code, intake_g: Number(e.grams) })) }),
      })
      if (!response.ok) throw new Error()
      const data: Calculation = await response.json()
      if (!controller.signal.aborted) setCalculation(data)
    } catch {
      if (!controller.signal.aborted) setCalculationError('계산을 완료하지 못했어요. 입력과 연결 상태를 확인한 뒤 다시 시도해주세요.')
    } finally {
      if (!controller.signal.aborted) setCalculating(false)
    }
  }

  function submit(event: FormEvent) { event.preventDefault(); void search(query) }
  const hasMissing = calculation && Object.values(calculation.totals).some(n => n.status !== 'complete')
  const date = new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric', weekday: 'long', timeZone: 'Asia/Seoul' }).format(new Date())

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#main" aria-label="NourishOn 홈"><span className="brand-icon"><Sprout size={25} /></span>Nourish<span>On</span></a>
      <div className="sidebar-caption">MY WELLNESS SPACE</div>
      <nav aria-label="주 메뉴">
        {([['meal','식사 분석'],['profile','내 몸과 목표'],['history','기록과 분석'],['insights','생활 개선']] as const).map(([key,label])=><button key={key} className={`nav-item ${view===key?'active':''}`} onClick={()=>setView(key)}>{key==='meal'?<Utensils size={19}/>:key==='profile'?<UserRound size={19}/>:<Activity size={19}/>} {label}</button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="small-leaf"><Leaf size={24} /></div>
        <strong>작은 한 끼가 만드는 변화</strong>
        <p>나에게 맞는 식생활을<br />하나씩 찾아가요.</p>
        <div className="local-note"><span /> 로컬 개발 버전</div>
      </div>
    </aside>

    <main id="main">
      <header className="topbar"><div>나의 공간 <ChevronRight size={14} /> <strong>{{meal:"식사 분석",profile:"내 몸과 목표",history:"기록과 분석",insights:"생활 개선"}[view]}</strong></div><span>{date}</span></header>
      <div className="storage-panel"><label><input type="checkbox" checked={persist} onChange={e=>setPersist(e.target.checked)}/> 이 브라우저에 프로필·식사 기록 보관</label><p>기본은 실행 중에만 유지됩니다. 보관을 선택하면 암호화되지 않은 브라우저 저장소에 남으므로 공용 기기에서는 사용하지 마세요. 서버·GitHub에는 저장하지 않습니다.</p>{storageError&&<p role="alert">{storageError}</p>}</div>
      {view==='profile'&&<Profile data={data} onChange={setData}/>}
      {view==='history'&&<History data={data} onChange={setData}/>}
      {view==='insights'&&<Insights data={data}/>}
      {view==='meal'&&<><section className="hero" aria-labelledby="page-title">
        <div><div className="eyebrow"><Leaf size={15} /> EVERY MEAL, A LITTLE BETTER</div>
          <h1 id="page-title">오늘의 식사,<br className="mobile-break" /> 가볍게 돌아봐요.</h1>
          <p>먹은 음식과 양을 더하고, 한 끼에 담긴 영양을 살펴보세요.</p>
          <div className={`connection ${health.status}`} role="status">
            <span className="status-dot" />{health.status === 'ok' ? `${format(health.count!)}개 식품 정보와 연결됐어요` : health.status === 'loading' ? '식품 정보를 연결하고 있어요' : '식품 정보 연결을 확인해주세요'}
            {health.status === 'error' && <button onClick={() => setConnectionAttempt(n => n + 1)}>다시 연결</button>}
          </div>
        </div>
        <div className="hero-art"><span>잘 먹는 일,<br /><b>나를 돌보는 시작.</b></span><BowlArt /><span className="art-dot one" /><span className="art-dot two" /></div>
      </section>

      <div className="steps" aria-label="분석 순서"><span><b>01</b> 음식 찾기</span><ChevronRight size={15} /><span><b>02</b> 섭취량 입력</span><ChevronRight size={15} /><span><b>03</b> 영양 확인</span></div>

      <div className="workspace">
        <section className="panel search-panel" aria-labelledby="search-title">
          <div className="panel-title"><div className="section-icon"><Search size={19} /></div><h2 id="search-title">어떤 음식을 드셨나요?</h2></div>
          <form className="search-form" onSubmit={submit}>
            <Search size={20} aria-hidden="true" /><input aria-label="음식 이름" placeholder="음식 이름을 검색해보세요" value={query} onChange={e => setQuery(e.target.value)} maxLength={100} />
            <button type="submit" disabled={searching}>{searching ? <LoaderCircle className="spin" size={18} /> : '검색'}</button>
          </form>
          <div className="suggestions"><span>이런 음식은 어때요?</span>{['두부', '현미밥', '닭가슴살', '사과'].map(term => <button key={term} onClick={() => { setQuery(term); void search(term) }}>{term}<ArrowUpRight size={12} /></button>)}</div>
          <div className="results-area" aria-live="polite" aria-busy={searching}>
            {searchError && <div className="error-box" role="alert"><CircleAlert size={18} /><span>{searchError}</span></div>}
            {searching ? <div className="empty-state"><LoaderCircle className="spin" size={30} /><h3>음식을 찾고 있어요</h3><p>잠시만 기다려주세요.</p></div>
              : results ? <>
                <div className="results-heading"><span><strong>‘{searchedQuery}’</strong> 검색 결과 <b>{format(results.total)}</b></span><span>영양성분 기준량</span></div>
                {results.items.length ? <ul className="food-list">{results.items.map(food => {
                  const added = entries.some(e => e.food.food_code === food.food_code)
                  return <li key={food.food_code} className="food-row"><div className="food-symbol"><Salad size={21} /></div>
                    <div className="food-info"><strong>{food.food_name}</strong><span>{food.source_name || '출처 정보 없음'}<span className="source-divider">·</span><span title={food.food_code}>{food.food_code}</span></span></div>
                    <span className="basis">{food.basis}</span><button className={`add-button ${added ? 'added' : ''}`} disabled={added} onClick={() => addFood(food)} aria-label={`${food.food_name} ${added ? '담김' : '추가'}`}>{added ? <Check size={16} /> : <Plus size={17} />}<span>{added ? '담김' : '추가'}</span></button></li>
                })}</ul> : <div className="empty-state"><Search size={30} /><h3>검색된 음식이 없어요</h3><p>다른 이름이나 더 짧은 검색어로 찾아보세요.</p></div>}
                {results.total > PAGE_SIZE && <div className="pagination"><button aria-label="이전 페이지" disabled={!results.offset} onClick={() => void search(searchedQuery, Math.max(0, results.offset - PAGE_SIZE))}><ArrowLeft size={16} /></button><span>{Math.floor(results.offset / PAGE_SIZE) + 1} <i>/</i> {Math.ceil(results.total / PAGE_SIZE)}</span><button aria-label="다음 페이지" disabled={results.offset + PAGE_SIZE >= results.total} onClick={() => void search(searchedQuery, results.offset + PAGE_SIZE)}><ArrowRight size={16} /></button></div>}
              </> : !searchError && <div className="empty-state initial"><div className="empty-icon"><Salad size={34} strokeWidth={1.4} /></div><h3>오늘 먹은 음식을 찾아보세요</h3><p>음식을 검색하고 <b>추가</b>를 누르면<br />오른쪽에서 섭취량을 입력할 수 있어요.</p><span className="empty-caption">한 끼를 알아가는 작은 시작</span></div>}
          </div>
          <div className="panel-footnote"><ShieldCheck size={15} /> 공공 식품 데이터 기반 · 100g 기준 식품 제공</div>
        </section>

        <section className="panel meal-panel" aria-labelledby="meal-title">
          <div className="meal-header"><div><span className="meal-label">MY MEAL</span><h2 id="meal-title">나의 한 끼 <span>{entries.length}</span></h2></div><span className="meal-header-icon"><Utensils size={22} /></span></div>
          <p className="meal-description">실제로 먹은 양을 g 단위로 입력해주세요.</p>
          {entries.length ? <ul className="entries">{entries.map(entry => <li key={entry.food.food_code}>
            <div className="entry-title"><strong>{entry.food.food_name}</strong><button className="remove-button" aria-label={`${entry.food.food_name} 삭제`} onClick={() => changeEntries(entries.filter(e => e.food.food_code !== entry.food.food_code))}><Trash2 size={16} /></button></div>
            <label className="amount-label"><span>섭취량</span><span className="amount-input"><input type="number" min="0" step="any" inputMode="decimal" aria-label={`${entry.food.food_name} 섭취량`} value={entry.grams} onChange={event => changeEntries(entries.map(e => e.food.food_code === entry.food.food_code ? { ...e, grams: event.target.value } : e))} /><span>g</span></span></label>
          </li>)}</ul> : <div className="empty-meal"><span><Plus size={24} /></span><strong>아직 담은 음식이 없어요</strong><p>검색 결과에서 음식을 추가해주세요.</p></div>}
          {calculationError && <p className="inline-error" role="alert">{calculationError}</p>}
          <button className="calculate-button" disabled={!entries.length || calculating} onClick={() => void calculate()}>{calculating ? <><LoaderCircle size={18} className="spin" /> 계산 중</> : <>영양 합계 계산 <ArrowRight size={18} /></>}</button>
          <div className="privacy-note"><ShieldCheck size={14} /> ‘식사 기록에 추가’를 눌러야 기록됩니다.</div>
        </section>
      </div>

      <section className="analysis-section" aria-labelledby="analysis-title" aria-live="polite">
        <div className="analysis-heading"><div><span className="section-eyebrow">A CLOSER LOOK AT YOUR MEAL</span><h2 id="analysis-title">한 끼에 담긴 영양</h2></div><span><CircleHelp size={15} /> 목표량 대비 평가가 아닌 섭취량 계산이에요.</span></div>
        {!calculation && <p className="analysis-placeholder">음식을 담고 ‘영양 합계 계산’을 누르면 아래에 결과가 나타나요.</p>}
        {hasMissing && <div className="missing-banner"><CircleAlert size={17} /><span>일부 성분 정보가 없어요. 누락된 값은 0으로 채우지 않고, 확인된 값만 합산했어요.</span></div>}
        <div className="nutrient-grid">{nutrientLabels.map(([key, label]) => {
          const nutrient = calculation?.totals[key]
          return <article key={key} className={`nutrient-card ${key === 'energy' ? 'energy-card' : ''}`}>
            <div className="nutrient-label">{key === 'energy' && <Flame size={15} />}{label}</div>
            <div className={`nutrient-value ${nutrient?.known_total === null ? 'unknown' : ''}`}>{!nutrient ? '—' : nutrient.known_total === null ? '정보 없음' : <>{format(nutrient.known_total)} <small>{nutrient.unit}</small></>}</div>
            <span className="nutrient-note">{!nutrient ? '계산 전' : nutrient.status === 'missing' ? `누락 ${nutrient.missing_count}개` : nutrient.status === 'partial' ? `확인된 값의 합계 · 누락 ${nutrient.missing_count}개` : '입력한 섭취량 기준'}</span>
          </article>
        })}</div>
      </section>

      {calculation&&<section className="panel wellness-panel"><h2>이 한 끼를 기록하기</h2><label>식사 날짜<input type="date" max={today()} value={mealDate} onChange={e=>{setMealDate(e.target.value);setSaved(false)}}/></label><label>식사 구분<select value={mealKind} onChange={e=>{setMealKind(e.target.value);setSaved(false)}}>{['아침','점심','저녁','간식'].map(x=><option key={x}>{x}</option>)}</select></label><button className="calculate-button" disabled={saved||!mealDate||mealDate>today()} onClick={()=>{setData({...data,records:[...data.records,{id:crypto.randomUUID(),date:mealDate,kind:mealKind,calculation}]});setSaved(true)}}>{saved?'기록에 추가했어요':'식사 기록에 추가'}</button><p>계산 당시 음식·섭취량·출처 정보와 영양 합계를 보관합니다.</p></section>}
      </>}
      <footer className="page-footer"><span><Leaf size={15} /> NourishOn · 나를 위한 식생활의 시작</span><span>일반 성인 로컬 MVP · 진단이나 치료 목적이 아닙니다.</span></footer>
    </main>
  </div>
}
