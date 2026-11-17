import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { randomBytes } from 'node:crypto'
import { goToView } from './ui'

// 건강 비서 화면(2026-11-17). 테스트 DB에 가상 계정을 만들고 끝나면 탈퇴시킨다. 기본 설정은 가짜 AI(외부 전송 없음).
const ORIGIN = { Origin: 'http://127.0.0.1:5173', 'X-NourishOn-Client': 'web' }

async function virtualAccount(page: Page) {
  const username = `e2e_${randomBytes(8).toString('hex')}`, password = randomBytes(12).toString('hex')
  const registered = await page.request.post('/api/auth/register', { headers: ORIGIN, data: { username, password } })
  expect(registered.status()).toBe(201)
  const csrf = (await registered.json()).csrf_token as string
  const profile = (await (await page.request.get('/api/account/profiles')).json()).profiles[0]
  const today = await page.evaluate(() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` })
  const saved = await page.request.put(`/api/account/profiles/${profile.id}/data`, { headers: { ...ORIGIN, 'X-CSRF-Token': csrf }, data: { revision: 0, data: {
    profile: { age: 34, height_cm: 165, weight_kg: 61, equation_sex: 'female', activity: 'low_active', scope_confirmed: true, measured_on: today },
    records: [{ id: crypto.randomUUID(), date: today, kind: '점심', calculation: { foods: [{ food_code: 'D101-050000000-0001', intake_g: 210 }] } }],
  } } })
  expect(saved.ok()).toBe(true)
  return async () => {
    const deleted = await page.request.post('/api/account/delete', { headers: { ...ORIGIN, 'X-CSRF-Token': csrf }, data: { password, confirm: true } })
    expect(deleted.status()).toBe(200)
  }
}

test('로그인 전에는 로그인 안내만 보인다', async ({ page }) => {
  await page.goto('/#dashboard')
  await goToView(page, '건강 비서')
  await expect(page.getByRole('heading', { name: '건강 비서', level: 1 })).toBeVisible()
  await expect(page.getByText('로그인하면 내 기록으로 질문할 수 있어요.')).toBeVisible()
  await expect(page.getByRole('textbox', { name: '질문' })).toHaveCount(0)
})

for (const width of [1440, 390]) {
  test(`가짜 AI 답변·계산 근거·전송 안내·진단 거절 (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/#dashboard')
    const cleanup = await virtualAccount(page)
    try {
      await page.reload()
      await goToView(page, '건강 비서')
      const input = page.getByRole('textbox', { name: '질문' })
      await expect(input).toBeVisible()
      await expect(page.locator('#assistant-data-notice')).toContainText('외부로 전송하지 않는')
      await expect(page.getByText('오늘 남은 질문 20 / 20')).toBeVisible()
      await page.getByRole('button', { name: '이번 주 나트륨 어때?' }).click()
      const answer = page.locator('.assistant-answer').last()
      await expect(answer).toContainText('나트륨')
      await expect(answer.locator('.assistant-provider')).toHaveText('기본 설명')
      await expect(answer.getByRole('heading')).toBeFocused()
      await answer.getByText(/계산 근거/).click()
      await expect(answer.locator('.assistant-evidence-item table')).toContainText('나트륨')
      await expect(page.getByText('오늘 남은 질문 19 / 20')).toBeVisible()
      await input.fill('당뇨인지 진단해줘')
      await page.getByRole('button', { name: '보내기' }).click()
      await expect(page.locator('.assistant-answer.refused')).toContainText('전문가와 상담')
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    } finally { await cleanup() }
  })
}

test('대시보드에서 건강 비서로 이동', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/#dashboard')
  await page.getByRole('button', { name: '건강 비서에게 물어보기' }).click()
  await expect(page.getByRole('heading', { name: '건강 비서', level: 1 })).toBeVisible()
})
