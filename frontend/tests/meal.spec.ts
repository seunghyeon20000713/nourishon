import { expect, test } from '@playwright/test'

test('실제 검색 → 추가 → 150g 계산 → 변경 시 결과 초기화 → 삭제', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
  await page.setViewportSize({ width: 1440, height: 1100 })
  await page.goto('/')
  await expect(page.getByText('290,871개 식품 정보와 연결됐어요')).toBeVisible()
  await page.evaluate(() => document.fonts.load('16px "Noto Sans KR Variable"', '한글'))
  expect(await page.evaluate(() => document.fonts.check('16px "Noto Sans KR Variable"', '한글'))).toBeTruthy()
  await page.getByRole('textbox', { name: '음식 이름' }).fill('국밥_돼지머리')
  await page.getByRole('button', { name: '검색', exact: true }).click()
  await page.getByRole('button', { name: '국밥_돼지머리 추가', exact: true }).click()
  await page.getByRole('spinbutton', { name: '국밥_돼지머리 섭취량' }).fill('150')
  await page.getByRole('button', { name: '영양 합계 계산' }).click()
  await expect(page.locator('.energy-card .nutrient-value')).toHaveText('205.5 kcal')
  await page.screenshot({ path: '/tmp/nourishon-desktop.png', fullPage: true })
  await page.getByRole('spinbutton', { name: '국밥_돼지머리 섭취량' }).fill('200')
  await expect(page.locator('.energy-card .nutrient-value')).toHaveText('—')
  await page.getByRole('button', { name: '국밥_돼지머리 삭제' }).click()
  await expect(page.getByRole('button', { name: '영양 합계 계산' })).toBeDisabled()
  expect(errors).toEqual([])
})

test('전체 결측·부분 결측·숫자 0을 다르게 표시', async ({ page }) => {
  await page.route('**/api/health', route => route.fulfill({ json: { food_count: 2 } }))
  await page.route('**/api/foods?**', route => route.fulfill({ json: {
    total: 2, offset: 0, limit: 8, items: [
      { food_code: 'practice-1', food_name: '연습용 음식', basis: '100g', source_name: '가상 자료' },
      { food_code: 'practice-2', food_name: '다른 연습용 음식', basis: '100g', source_name: '가상 자료' },
    ],
  } }))
  await page.route('**/api/meals/calculate', route => {
    expect(route.request().postDataJSON()).toEqual({ entries: [
      { food_code: 'practice-1', intake_g: 100 }, { food_code: 'practice-2', intake_g: 100 },
    ] })
    const value = (n: number | null, unit: string, status = 'complete', missing_count = 0) => ({ known_total: n, unit, status, missing_count })
    return route.fulfill({ json: { totals: {
      energy: value(200, 'kcal'), protein: value(10, 'g'), fat: value(3, 'g'),
      carbohydrate: value(5, 'g', 'partial', 1), sugar: value(0, 'g'),
      fiber: value(null, 'g', 'missing', 2), sodium: value(5, 'mg'),
    } } })
  })
  await page.goto('/')
  await page.getByRole('textbox', { name: '음식 이름' }).fill('연습용')
  await page.getByRole('button', { name: '검색', exact: true }).click()
  await page.getByRole('button', { name: '연습용 음식 추가', exact: true }).click()
  await page.getByRole('button', { name: '다른 연습용 음식 추가', exact: true }).click()
  await page.getByRole('button', { name: '영양 합계 계산' }).click()
  await expect(page.getByText('정보 없음', { exact: true })).toBeVisible()
  await expect(page.getByText('확인된 값의 합계 · 누락 1개')).toBeVisible()
  const sugar = page.locator('.nutrient-card').filter({ has: page.getByText('당류', { exact: true }) })
  await expect(sugar.locator('.nutrient-value')).toHaveText('0 g')
})

test('검색 결과 없음과 연결 오류를 안내', async ({ page }) => {
  await page.route('**/api/foods?**', route => route.fulfill({ json: { total: 0, offset: 0, limit: 8, items: [] } }))
  await page.goto('/')
  await page.getByRole('textbox', { name: '음식 이름' }).fill('연습용 없는 이름')
  await page.getByRole('button', { name: '검색', exact: true }).click()
  await expect(page.getByText('검색된 음식이 없어요')).toBeVisible()
  await page.unroute('**/api/foods?**')
  await page.route('**/api/foods?**', route => route.fulfill({ status: 503, json: { detail: '연습용 실패' } }))
  await page.getByRole('button', { name: '검색', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('불러오지 못했어요')
})

test('모바일 폭에서 검색·선택·계산과 가로 넘침 확인', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('textbox', { name: '음식 이름' }).fill('국밥_돼지머리')
  await page.getByRole('button', { name: '검색', exact: true }).click()
  await page.getByRole('button', { name: '국밥_돼지머리 추가', exact: true }).click()
  await page.getByRole('button', { name: '영양 합계 계산' }).click()
  await expect(page.locator('.energy-card .nutrient-value')).toHaveText('137 kcal')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({ path: '/tmp/nourishon-mobile.png', fullPage: true })
})

test('검색 페이지 이동과 빈 섭취량 안내', async ({ page }) => {
  await page.route('**/api/foods?**', route => {
    const offset = Number(new URL(route.request().url()).searchParams.get('offset'))
    const items = Array.from({ length: 9 }, (_, index) => ({ food_code: `practice-${index}`,
      food_name: `연습용 음식 ${index + 1}`, basis: '100g', source_name: '가상 자료' }))
    return route.fulfill({ json: { total: 9, offset, limit: 8, items: items.slice(offset, offset + 8) } })
  })
  await page.goto('/')
  await page.getByRole('textbox', { name: '음식 이름' }).fill('연습용')
  await page.getByRole('button', { name: '검색', exact: true }).click()
  await page.getByRole('button', { name: '다음 페이지' }).click()
  await page.getByRole('button', { name: '연습용 음식 9 추가', exact: true }).click()
  await page.getByRole('spinbutton', { name: '연습용 음식 9 섭취량' }).fill('')
  await page.getByRole('button', { name: '영양 합계 계산' }).click()
  await expect(page.getByRole('alert')).toContainText('0 이상의 숫자')
  await page.getByRole('button', { name: '이전 페이지' }).click()
  await expect(page.getByRole('button', { name: '연습용 음식 1 추가', exact: true })).toBeVisible()
})
