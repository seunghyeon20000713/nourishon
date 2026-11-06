import {test,expect} from '@playwright/test'

test('영양 구성·기여 식품과 불일치 보류를 실제 API로 확인',async({page})=>{
 await page.goto('/')
 async function fixture(energy:number){await page.evaluate(energy=>{
  const date=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())
  const values:Record<string,number|null>={energy,carbohydrate:30,protein:10,fat:5,sodium:800,fiber:null,sugar:0}
  const unit=(k:string)=>k==='energy'?'kcal':k==='sodium'?'mg':'g'
  const nutrients=Object.fromEntries(Object.entries(values).map(([k,n])=>[k,{unit:unit(k),consumed:n}]))
  const totals=Object.fromEntries(Object.entries(values).map(([k,n])=>[k,{unit:unit(k),known_total:n,missing_count:n===null?1:0,status:n===null?'missing':'complete'}]))
  localStorage.setItem('nourishon-local-mvp-v1',JSON.stringify({profile:null,estimate:null,records:[{id:'practice-review',date,kind:'점심',calculation:{foods:[{food_name:'연습용 식사',intake_g:100,nutrients}],totals}}]}))
 },energy);await page.reload();await page.getByRole('button',{name:'생활 개선',exact:true}).click()}
 await fixture(200)
 await expect(page.getByRole('cell',{name:'60%',exact:true})).toBeVisible()
 await expect(page.getByText('연습용 식사: 800 mg',{exact:true})).toBeVisible()
 await expect(page.getByText('기록된 식사만 검토 · 하루 전체 섭취 평가나 결핍 진단이 아닙니다.')).toBeVisible()
 await page.setViewportSize({width:390,height:844})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await fixture(1000)
 await expect(page.getByText(/표시 열량과 4·4·9 환산 열량의 차이가 10%를 넘어/)).toBeVisible()
 await expect(page.getByRole('cell',{name:'60%',exact:true})).toHaveCount(0)
})
