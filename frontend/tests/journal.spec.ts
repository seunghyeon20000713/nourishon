import {test,expect} from '@playwright/test'

async function seedJournal(page:import('@playwright/test').Page){
 await page.goto('/')
 await page.evaluate(()=>{
  const today='2026-11-06'
  const totals=(energy:number)=>{const values={energy,carbohydrate:energy*.55/4,protein:energy*.18/4,fat:energy*.27/9,sodium:energy*1600/1500,fiber:null,sugar:0};return Object.fromEntries(Object.entries(values).map(([key,v])=>[key,{unit:key==='energy'?'kcal':key==='sodium'?'mg':'g',known_total:v,missing_count:v===null?1:0,status:v===null?'missing':'complete'}]))}
  const meal=(date:string,kind:string,energy:number)=>{const n=totals(energy);return {id:crypto.randomUUID(),date,kind,calculation:{totals:n,foods:[{food_name:'디자인 검증용 가상 식사',intake_g:100,nutrients:Object.fromEntries(Object.entries(n).map(([k,v])=>[k,{unit:v.unit,consumed:v.known_total}]))}]}}}
  localStorage.setItem('nourishon-local-mvp-v1',JSON.stringify({profile:{age:30,height_cm:170,weight_kg:70,equation_sex:'female',activity:'inactive',goal:'maintain',scope_confirmed:true},estimate:{bmi:24.22,maintenance_kcal:2000,protein_reference_g:56,limitations:[],sources:[]},records:[meal('2026-11-02','점심',1600),meal('2026-11-03','점심',1750),meal('2026-11-05','점심',1420),meal(today,'아침',520),meal(today,'점심',980)]}))
 });await page.reload()
}

test('선택 시안의 기록 대시보드·날짜·이동과 모바일',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
 await page.setViewportSize({width:1440,height:1024})
 await seedJournal(page)
 await expect(page.getByRole('heading',{name:'기록으로 보는 나의 영양'})).toBeVisible()
 await expect(page.getByRole('img',{name:'탄수화물 55%, 참고 범위 50~65%'})).toBeVisible()
 await expect(page.locator('.composition-section .recharts-line-curve')).toHaveCount(3)
 await expect(page.locator('.composition-section .recharts-reference-dot-dot')).toHaveCount(3)
 await page.evaluate(()=>document.fonts.ready)
 await page.screenshot({path:'/tmp/nourishon-journal-desktop.png',fullPage:false})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await page.getByRole('button',{name:'2026-11-04 미기록',exact:true}).click()
 await expect(page.locator('.journal-summary')).toContainText('아직 기록한 식사가 없어요')
 await expect(page.getByRole('img',{name:'탄수화물 평가 보류, 참고 범위 50~65%'})).toBeVisible()
 await page.getByRole('button',{name:'2026-11-06 2개 기록',exact:true}).click()
 await page.getByRole('button',{name:'판단 근거 보기'}).click()
 await expect(page.getByRole('heading',{name:'영양학적 근거로 식사 돌아보기'})).toBeVisible()
 await page.getByRole('button',{name:'영양 대시보드',exact:true}).click()
 await page.setViewportSize({width:390,height:844})
 await expect(page.getByRole('img',{name:'탄수화물 55%, 참고 범위 50~65%'})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await page.screenshot({path:'/tmp/nourishon-journal-mobile.png',fullPage:true})
 await page.getByRole('button',{name:'식사 기록',exact:true}).click()
 await expect(page.getByRole('textbox',{name:'음식 이름'})).toBeVisible()
 expect(errors).toEqual([])
})
