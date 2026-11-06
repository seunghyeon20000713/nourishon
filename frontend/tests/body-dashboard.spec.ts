import { test, expect } from '@playwright/test'

async function seed(page:import('@playwright/test').Page) {
 await page.goto('/#dashboard')
 await page.evaluate(()=>{
  const rows=[['2026-10-09',72.1,26.3,21.8,30.2],['2026-10-16',71.6,26.5,21.3,29.8],['2026-10-23',71.2,26.6,21,29.5],['2026-10-30',70.8,26.8,20.6,29.1],['2026-11-06',70,27,20,28.6]].map(([date,weight,muscle,fat,percent])=>({id:crypto.randomUUID(),measured_on:date,weight_kg:weight,skeletal_muscle_kg:muscle,fat_mass_kg:fat,body_fat_percent:percent}))
  const values={energy:1450,protein:62,fiber:18,sodium:1420,carbohydrate:200,fat:45,sugar:20}
  const totals=Object.fromEntries(Object.entries(values).map(([key,value])=>[key,{unit:key==='energy'?'kcal':key==='sodium'?'mg':'g',known_total:value,status:'complete',missing_count:0}]))
  localStorage.setItem('nourishon-local-mvp-v1',JSON.stringify({profile:{age:30,height_cm:170,weight_kg:70,equation_sex:'female',activity:'inactive',goal:'maintain',scope_confirmed:true},estimate:{bmi:24.22,maintenance_kcal:2167,protein_reference_g:56,limitations:[],sources:[]},measurements:rows,records:[{id:crypto.randomUUID(),date:'2026-11-06',kind:'점심',calculation:{totals}}]}))
 });await page.reload()
 await page.getByLabel('요약 날짜',{exact:true}).fill('2026-11-06')
}

test('개인 기록장: 실제 측정·날짜 비교·요약·이동·반응형',async({page})=>{
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message))
 await page.setViewportSize({width:1440,height:1024});await seed(page)
 await expect(page.locator('.body-weight')).toContainText('70.0')
 await expect(page.locator('.weight-difference')).toContainText('-0.8 kg')
 await expect(page.locator('.weight-difference')).toContainText('2026.10.30')
 await expect(page.locator('.body-metrics')).toContainText('27.0')
 await expect(page.locator('.body-bmi')).toContainText('현재 프로필')
 await expect(page.locator('.diary-energy')).toContainText('1,450')
 await expect(page.locator('.body-recent tbody tr')).toHaveCount(5)
 await page.getByRole('button',{name:'왼쪽 메뉴 펼치기',exact:true}).click()
 await page.evaluate(()=>document.fonts.ready)
 await page.screenshot({path:'/tmp/nourishon-journal-v2-desktop.png'})
 await page.getByLabel('요약 날짜',{exact:true}).fill('2026-10-23')
 await expect(page.locator('.body-weight')).toContainText('71.2')
 await expect(page.locator('.weight-difference')).toContainText('-0.4 kg')
 await expect(page.locator('.body-recent tbody tr')).toHaveCount(3)
 await expect(page.locator('.diary-energy')).toContainText('—')
 await page.getByLabel('요약 날짜',{exact:true}).fill('2026-11-06')
 await page.getByRole('button',{name:'왼쪽 메뉴 펼치기',exact:true}).click()
 await page.setViewportSize({width:390,height:844})
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.screenshot({path:'/tmp/nourishon-journal-v2-mobile.png',fullPage:true})
 await page.locator('.daily-diary').getByRole('button',{name:'식사 기록하기',exact:true}).click()
 await expect(page.getByRole('textbox',{name:'음식 이름'})).toBeVisible()
 expect(errors).toEqual([])
})

test('몸 기록: 없는 값과 0 구분, 같은 날짜 마지막 값, 미래 기록 제외',async({page})=>{
 await seed(page)
 await page.evaluate(()=>{
  const key='nourishon-local-mvp-v1',store=JSON.parse(localStorage.getItem(key)!);const data=store.profiles.find((p:{id:string})=>p.id===store.activeId).data
  data.measurements=[{id:crypto.randomUUID(),measured_on:'2026-11-06',weight_kg:70,fat_mass_kg:10},{id:crypto.randomUUID(),measured_on:'2026-11-06',weight_kg:69.9,fat_mass_kg:0,body_fat_percent:0},{id:crypto.randomUUID(),measured_on:'2099-01-01',weight_kg:80}]
  localStorage.setItem(key,JSON.stringify(store))
 });await page.reload();await page.getByLabel('요약 날짜',{exact:true}).fill('2026-11-06')
 await expect(page.locator('.body-weight')).toContainText('69.9')
 await expect(page.locator('.weight-difference')).toHaveCount(0)
 await expect(page.locator('.body-metrics>div').nth(0)).toContainText('미등록')
 await expect(page.locator('.body-metrics>div').nth(1)).toContainText('0.0')
 await expect(page.locator('.body-metrics>div').nth(2)).toContainText('0.0')
 await expect(page.getByText('첫 측정이 기록됐어요')).toBeVisible()
 await page.getByLabel('요약 날짜',{exact:true}).fill('2026-11-05')
 await expect(page.locator('.body-weight')).toContainText('—')
 await expect(page.getByRole('button',{name:'내 몸 정보 입력',exact:true})).toBeVisible()
 await expect(page.locator('.body-recent')).toContainText('등록된 측정값이 없습니다.')
})
