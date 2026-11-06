import sample from './demoData.json'
import './demo.css'

const DEMO_KEY = 'nourishon-demo-v1'
const day = () => new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())
const foods = [
  {code:'demo-1',name:'연습용 현미밥',energy:200,protein:5,fat:2,carbohydrate:40,sugar:0,fiber:3,sodium:5},
  {code:'demo-2',name:'연습용 두부',energy:100,protein:10,fat:4,carbohydrate:6,sugar:1,fiber:1,sodium:10},
  {code:'demo-3',name:'연습용 닭가슴살',energy:150,protein:25,fat:5,carbohydrate:1,sugar:0,fiber:0,sodium:80},
  {code:'demo-4',name:'연습용 사과',energy:60,protein:0.5,fat:0.2,carbohydrate:14,sugar:10,fiber:2,sodium:1},
  {code:'demo-5',name:'연습용 채소',energy:30,protein:2,fat:0.5,carbohydrate:4,sugar:2,fiber:2,sodium:20},
  {code:'demo-6',name:'연습용 국',energy:80,protein:4,fat:3,carbohydrate:9,sugar:1,fiber:null,sodium:700},
]
const keys = ['energy','protein','fat','carbohydrate','sugar','fiber','sodium'] as const
type Key = typeof keys[number]
const unit = (key:Key) => key==='energy'?'kcal':key==='sodium'?'mg':'g'
function meal(entries:{food_code:string;intake_g:number}[]) {
 const items=entries.map(entry=>{
  const food=foods.find(food=>food.code===entry.food_code)
  if(!food||!Number.isFinite(entry.intake_g)||entry.intake_g<0)throw Error('식품과 양을 확인해주세요.')
  return {food_code:food.code,food_name:food.name,intake_g:entry.intake_g,basis:'100g',source_name:'화면 체험용 가상 자료',nutrients:Object.fromEntries(keys.map(key=>[key,{unit:unit(key),per_100g:food[key],consumed:food[key]===null?null:food[key]*entry.intake_g/100}]))}
 })
 const totals=Object.fromEntries(keys.map(key=>{
  const values=items.map(food=>food.nutrients[key].consumed as number|null),known=values.filter((value):value is number=>value!==null),missing=values.length-known.length
  return [key,{unit:unit(key),known_total:known.length?known.reduce((sum,n)=>sum+n,0):null,missing_count:missing,status:!known.length?'missing':missing?'partial':'complete'}]
 }))
 return {foods:items,totals}
}
function seed() {
 if(localStorage.getItem(DEMO_KEY))return
 localStorage.setItem(DEMO_KEY,JSON.stringify({version:2,activeId:'demo-person',profiles:[{id:'demo-person',nickname:'연습용 프로필',data:{profile:{age:30,height_cm:170,weight_kg:70,equation_sex:'female',activity:'inactive',goal:'maintain',scope_confirmed:true,measured_on:day()},estimate:sample.estimate,records:[{id:'demo-meal',date:day(),kind:'점심',calculation:meal([{food_code:'demo-1',intake_g:150},{food_code:'demo-2',intake_g:100},{food_code:'demo-5',intake_g:100}])}],measurements:[{id:'demo-body',measured_on:day(),weight_kg:70,fat_mass_kg:20,body_fat_percent:28.6}],exerciseInput:null,exercisePlan:sample.plan,activityRecords:[]}}]}))
}
function estimate(profile:Record<string,unknown>) {
 const sex=profile.equation_sex as keyof typeof sample.coefficients,activity=profile.activity as keyof typeof sample.coefficients.female
 const c=sample.coefficients[sex]?.[activity]
 if(!c)throw Error()
 const weight=Number(profile.weight_kg),height=Number(profile.height_cm),age=Number(profile.age)
 if(!Number.isFinite(weight+height+age)||weight<25||weight>350||height<100||height>250||age<19||age>64)throw Error()
 const energy=c[0]+c[1]*age+c[2]*height+c[3]*weight
 return {...sample.estimate,bmi:Number((weight/(height/100)**2).toFixed(2)),maintenance_kcal:Math.round(energy),protein_reference_g:Math.round(weight*.8*10)/10,macro_reference_ranges:Object.fromEntries([['carbohydrate',50,65,4],['protein',10,20,4],['fat',15,30,9]].map(([key,lo,hi,kcal])=>[key,{percent:[lo,hi],min_g:Math.round(energy*Number(lo)/100/Number(kcal)*10)/10,max_g:Math.round(energy*Number(hi)/100/Number(kcal)*10)/10}]))}
}
export function setupDemo() {
 seed()
 document.body.classList.add('demo-mode')
 const banner=document.createElement('aside');banner.className='demo-notice';banner.setAttribute('aria-label','체험판 안내')
 const text=document.createElement('span');text.textContent='화면 체험판 · 식품·프로필은 가상 데이터입니다. 로그인·서버 저장 없음. 실제 개인정보는 입력하지 마세요.'
 const reset=document.createElement('button');reset.textContent='체험 초기화';reset.onclick=()=>{if(window.confirm('이 브라우저의 체험 기록을 초기화할까요?')){localStorage.removeItem(DEMO_KEY);location.reload()}}
 banner.append(text,reset);document.body.prepend(banner)
 const original=window.fetch.bind(window)
 window.fetch=async(input,init)=>{
  const url=new URL(input instanceof Request?input.url:String(input),location.href)
  if(!url.pathname.startsWith('/api/'))return original(input,init)
  const json=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}})
  try {
   const path=url.pathname.slice(4),body=typeof init?.body==='string'?JSON.parse(init.body):{}
   if(path==='/auth/me')return json({user:null,database_enabled:false})
   if(path.startsWith('/auth/')||path.startsWith('/account/'))return json({detail:'체험판은 로그인·회원가입·서버 저장을 제공하지 않습니다.'},403)
   if(path==='/health')return json({status:'ok',food_count:foods.length})
   if(path==='/foods') {
    const q=(url.searchParams.get('q')??'').trim().normalize('NFKC').toLowerCase()
    const found=foods.filter(food=>food.name.includes(q)||food.code===q),offset=Number(url.searchParams.get('offset')??0),limit=Number(url.searchParams.get('limit')??8)
    return json({total:found.length,offset,limit,items:found.slice(offset,offset+limit).map(food=>({food_code:food.code,food_name:food.name,basis:'100g',source_name:'연습용 가상 자료 · 실제 식품 아님',updated_date:null}))})
   }
   if(path==='/meals/calculate')return json(meal(body.entries))
   if(path==='/profile/estimate')return json(estimate(body))
   if(path==='/measurements/validate') {
    if(!body.measured_on||body.measured_on>day()||body.weight_kg<25||body.weight_kg>350||(body.fat_mass_kg??0)+(body.skeletal_muscle_kg??0)>body.weight_kg||body.body_fat_percent<0||body.body_fat_percent>100)throw Error()
    return json(body)
   }
   if(path==='/activities')return json({items:sample.activities})
   if(path==='/activities/calculate') {
    const activity=sample.activities.find(item=>item.code===body.activity_code)
    if(!activity||body.date>day()||body.age<19||body.age>59||body.minutes<0||body.minutes>300||body.weight_kg<25||body.weight_kg>350)throw Error()
    const factor=body.weight_kg*body.minutes/60
    return json({...body,calculation:{name:activity.name,met:activity.met,gross_kcal:Math.round(activity.met*factor*100)/100,above_rest_kcal:Math.round((activity.met-1)*factor*100)/100,formula:'MET × kg × 분 ÷ 60',version:'2024 Adult Compendium · 브라우저 체험 계산',checked_on:'2026-11-06',source_url:activity.url,scope:'화면 체험용'}})
   }
   if(path==='/nutrition/review') {
    const items=(body.meals??[]).flatMap((item:{foods:unknown[]})=>item.foods??[])
    const totals=Object.fromEntries(keys.map(key=>{const values=items.map((food:{nutrients:Record<string,{consumed:number|null}>})=>food.nutrients?.[key]?.consumed??null),known=values.filter((value:number|null)=>value!==null);return[key,{value:known.length?known.reduce((sum:number,n:number)=>sum+n,0):null,unit:unit(key),missing:values.length-known.length}]}))
    const macros=[] as {key:string;label:string;percent:number;reference:number[];comparison:string}[]
    const complete=['energy','carbohydrate','protein','fat'].every(key=>totals[key].value!==null&&!totals[key].missing)
    const energy=totals.energy.value
    const converted=(totals.carbohydrate.value??0)*4+(totals.protein.value??0)*4+(totals.fat.value??0)*9
    const usable=complete&&energy>0&&Math.abs(converted-energy)/energy<=.1
    if(usable)for(const [key,label,factor,lo,hi] of [['carbohydrate','탄수화물',4,50,65],['protein','단백질',4,10,20],['fat','지방',9,15,30]] as const){const percent=totals[key].value*factor/energy*100;macros.push({key,label,percent:Math.round(percent*10)/10,reference:[lo,hi],comparison:percent<lo?'범위보다 낮음':percent>hi?'범위보다 높음':'참고 범위 안'})}
    return json({scope:'가상 식사로 화면을 시연합니다. 실제 개인 영양 평가가 아닙니다.',macro_status:usable?'available':'missing',macro_message:usable?'연습용 식사의 영양 비율입니다.':'체험 자료의 누락·열량 차이로 비율 표시를 보류합니다.',macros,totals,sodium_contributors:[],actions:['가상 자료로 식사 기록과 분석 화면의 사용 흐름을 확인해보세요. 실제 식품 정보와 개인별 추천은 로컬 개발 버전에서 별도로 검증합니다.'],sources:sample.estimate.sources,sugar_note:'총당류와 유리당은 구분하며 혈당 예측을 제공하지 않습니다.'})
   }
   return json({detail:'체험판에서 지원하지 않는 동작입니다.'},404)
  } catch {return json({detail:'체험 입력 범위와 기록을 확인해주세요.'},422)}
 }
}
