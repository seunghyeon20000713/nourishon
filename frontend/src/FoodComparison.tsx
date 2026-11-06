import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
export type FoodFocus = 'protein'|'fiber'|'sodium'
export type ComparedFood = {food_code:string;food_name:string;basis:string;source_name:string|null;reference_date:string|null;updated_date:string|null;nutrients:Record<string,{unit:string;per_100g:number|null}>}
type Results={query:string;focus:FoodFocus;total:number;offset:number;limit:number;items:ComparedFood[];sort_note:string;scope:string}
const labels={protein:'단백질 많은 순',fiber:'식이섬유 많은 순',sodium:'나트륨 적은 순'}
export function FoodComparison({focus,onFocus,onAdd}:{focus:FoodFocus;onFocus:(focus:FoodFocus)=>void;onAdd:(food:ComparedFood)=>void}) {
 const [query,setQuery]=useState(''),[result,setResult]=useState<Results|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 const controller=useRef<AbortController|null>(null)
 useEffect(()=>{controller.current?.abort();setResult(null);setError('');setBusy(false);return()=>controller.current?.abort()},[focus])
 async function search(term:string,offset=0) {
  if(!term.trim()){setError('비교할 음식 이름을 입력해주세요.');return}
  controller.current?.abort();const request=new AbortController();controller.current=request;setBusy(true);setError('');setResult(null)
  try {const response=await fetch(`/api/foods/compare?${new URLSearchParams({q:term.trim(),focus,offset:String(offset),limit:'8'})}`,{signal:request.signal});if(!response.ok)throw Error();const value:Results=await response.json();if(!request.signal.aborted)setResult(value)}
  catch{if(!request.signal.aborted)setError('비교할 식품을 불러오지 못했습니다. 서버 연결을 확인하고 다시 검색해주세요.')}
  finally{if(!request.signal.aborted)setBusy(false)}
 }
 function submit(event:FormEvent){event.preventDefault();void search(query)}
 const value=(food:ComparedFood,key:string)=>{const n=food.nutrients[key];return n?.per_100g==null?'정보 없음':`${new Intl.NumberFormat('ko-KR',{maximumFractionDigits:2}).format(n.per_100g)} ${n.unit}`}
 if(import.meta.env.MODE==='demo')return <section className="food-comparison"><h2>실제 식품 비교</h2><p>공개 화면 체험판에는 실제 식품 비교 서버가 연결되어 있지 않습니다.</p></section>
 return <section id="food-comparison" className="food-comparison" aria-labelledby="food-comparison-title"><h2 id="food-comparison-title" tabIndex={-1}>다음 식사에 담을 음식 비교</h2>
  <p>바꾸거나 추가하고 싶은 음식 이름으로 검색하세요. 같은 검색어의 결과를 <b>100g당</b> 성분으로 비교합니다. 1회 제공량이나 권장 섭취량이 아닙니다. 담은 뒤 식사 계산 화면에서 실제로 먹은 양(g)으로 바꿔주세요.</p>
  <form onSubmit={submit}><label>비교할 음식 이름<input value={query} onChange={event=>setQuery(event.target.value)} placeholder="예: 국, 두부, 현미밥" required maxLength={100}/></label><label>비교 성분<select aria-label="비교 성분" value={focus} onChange={event=>onFocus(event.target.value as FoodFocus)}>{Object.entries(labels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><button type="submit" disabled={busy}>{busy?'비교 중…':'음식 비교 검색'}</button></form>
  <p className="comparison-limit">성분 값만 비교합니다. 조리 상태·제품·출처를 확인하고, 알레르기·질환별 적합성·가격·재고는 별도로 확인하세요. 성분이 많거나 적다는 이유만으로 가장 건강한 음식으로 추천하지 않습니다.</p>
  {error&&<p role="alert">{error}</p>}{busy&&<p role="status">식품 데이터를 비교하고 있습니다…</p>}
  {result&&<><p role="status">‘{result.query}’ {result.total}개 · {labels[result.focus]}</p><p className="comparison-limit">{result.sort_note}</p>{result.items.length?<><p className="comparison-scroll-hint">표를 좌우로 움직여 성분과 담기 버튼을 확인하세요.</p><div className="comparison-table"><table><caption>모든 영양 값은 100g당 · 정보 없음과 0은 구분합니다.</caption><thead><tr><th>식품·출처</th><th>열량</th><th>단백질</th><th>식이섬유</th><th>나트륨</th><th>선택</th></tr></thead><tbody>{result.items.map(food=><tr key={food.food_code}><th scope="row"><strong>{food.food_name}</strong><small>코드 {food.food_code} · {food.source_name??'출처명 없음'}</small><small>자료 기준일 {food.reference_date??'정보 없음'} · 갱신일 {food.updated_date??'정보 없음'}</small></th>{['energy','protein','fiber','sodium'].map(key=><td key={key}>{value(food,key)}</td>)}<td><button aria-label={`${food.food_name} 식사 계산에 담기`} onClick={()=>onAdd(food)}>식사 계산에 담기</button></td></tr>)}</tbody></table></div></>:<p>일치하는 식품이 없습니다. 다른 이름으로 검색해주세요.</p>}
  {result.total>8&&<div className="comparison-pages"><button disabled={result.offset===0||busy} onClick={()=>void search(result.query,Math.max(0,result.offset-8))}>비교 이전 결과</button><span>{result.offset+1}~{Math.min(result.offset+8,result.total)} / {result.total}</span><button disabled={result.offset+8>=result.total||result.offset+8>10000||busy} onClick={()=>void search(result.query,result.offset+8)}>비교 다음 결과</button></div>}</>}
 </section>
}
