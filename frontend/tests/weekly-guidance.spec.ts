import { test, expect } from '@playwright/test'

test('최근 기록 연결과 근거·신체 변화·운동 제한·통신 오류', async ({ page }) => {
  await page.goto('/#dashboard')
  await page.evaluate(() => {
    const end = new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())
    const earlier = new Date(`${end}T12:00:00Z`);earlier.setUTCDate(earlier.getUTCDate()-6)
    const start=earlier.toISOString().slice(0,10)
    const values={energy:200,carbohydrate:30,protein:10,fat:4.444444,sodium:2100,fiber:null,sugar:0}
    const unit=(key:string)=>key==='energy'?'kcal':key==='sodium'?'mg':'g'
    const totals=Object.fromEntries(Object.entries(values).map(([key,value])=>[key,{unit:unit(key),known_total:value,missing_count:value===null?1:0,status:value===null?'missing':'complete'}]))
    const nutrients=Object.fromEntries(Object.entries(values).map(([key,value])=>[key,{unit:unit(key),consumed:value}]))
    localStorage.setItem('nourishon-local-mvp-v1',JSON.stringify({profile:{age:30,height_cm:170,weight_kg:70,equation_sex:'female',activity:'inactive',goal:'lose',scope_confirmed:true},estimate:null,
      records:[{id:'practice-connected',date:end,kind:'점심',calculation:{foods:[{food_name:'연결 검증용 가상 식사',intake_g:100,nutrients}],totals}}],
      measurements:[{id:crypto.randomUUID(),measured_on:start,weight_kg:70,body_fat_percent:20},{id:crypto.randomUUID(),measured_on:end,weight_kg:69,body_fat_percent:18}],
      activityRecords:[{id:crypto.randomUUID(),date:end,age:30,activity_code:'12030',weight_kg:70,minutes:30,calculation:{name:'러닝 연습 기록',met:8.5,gross_kcal:297.5,above_rest_kcal:262.5,formula:'MET × kg × 분 / 60',version:'2024 Adult Compendium',checked_on:'2026-11-06',source_url:'https://pacompendium.com/running/',scope:'가상 검증'}}],
      exerciseInput:{experience:'beginner',days:3,minutes:15,current_weekly_minutes:0,preference:'walking',has_limitations:false,has_symptoms:false,scope_confirmed:true},exercisePlan:null}))
  })
  await page.reload()
  await page.getByRole('button',{name:'생활 개선',exact:true}).click()
  const section=page.locator('.weekly-guidance')
  await expect(section.locator('[data-guidance=sodium]')).toContainText('국물·소스')
  await expect(section.locator('[data-guidance=activity]')).toContainText('주 3일, 활동일마다 10분')
  await section.locator('[data-guidance=activity] summary').click()
  await expect(section.locator('[data-guidance=activity]')).toContainText('최근 기록은 총 30분')
  await section.locator('.guidance-body > summary').click()
  await expect(section.locator('.guidance-body')).toContainText('-1 kg')
  await expect(section.locator('.guidance-body')).toContainText('-2 %p')
  await section.locator('[data-guidance=activity]').getByRole('button',{name:'운동 조건 확인'}).click()
  await expect(page.getByRole('heading',{name:'나에게 맞는 주간 활동 계획'})).toBeVisible()
  await page.getByRole('button',{name:'생활 개선',exact:true}).click()
  await expect(section.locator('[data-guidance=activity]')).toBeVisible()
  await page.setViewportSize({width:390,height:844})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.screenshot({path:'/tmp/nourishon-weekly-guidance-mobile.png',fullPage:true})
  await page.evaluate(()=>{const key='nourishon-local-mvp-v1',saved=JSON.parse(localStorage.getItem(key)!);saved.profiles[0].data.exerciseInput.has_symptoms=true;localStorage.setItem(key,JSON.stringify(saved))})
  await page.reload()
  await page.getByRole('button',{name:'상단 메뉴 펼치기',exact:true}).click()
  await page.getByRole('button',{name:'생활 개선',exact:true}).click()
  await expect(section.locator('[data-guidance=assessment]')).toBeVisible()
  await expect(section.locator('[data-guidance=activity]')).toHaveCount(0)
  await page.route('**/api/nutrition/weekly-guidance',route=>route.fulfill({status:503,json:{}}))
  await page.reload()
  await page.getByRole('button',{name:'상단 메뉴 펼치기',exact:true}).click()
  await page.getByRole('button',{name:'생활 개선',exact:true}).click()
  await expect(section.getByRole('alert')).toContainText('기존 기록은 바꾸지 않았습니다.')
})
