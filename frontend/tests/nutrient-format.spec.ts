import { test, expect } from '@playwright/test'
import { formatAmount, formatWithUnit } from '../src/nutrientFormat'

// 열량·영양소 표시 규칙(2026-11-17): kcal·mg 정수, g·% 소수 첫째 자리, 0이 아닌 작은 값은 '미만'.
test('표시 규칙: 단위별 반올림과 작은 값·0 구분', () => {
  expect(formatWithUnit(949.7, 'kcal')).toBe('950 kcal')
  expect(formatWithUnit(1457.1, 'mg')).toBe('1,457 mg')
  expect(formatWithUnit(41.25, 'g')).toBe('41.3 g')
  expect(formatWithUnit(19, 'g')).toBe('19 g')
  expect(formatAmount(47.33, '%')).toBe('47.3')
  expect(formatWithUnit(0, 'g')).toBe('0 g')
  expect(formatWithUnit(0.04, 'g')).toBe('0.1 미만 g')
  expect(formatWithUnit(0.4, 'mg')).toBe('1 미만 mg')
})

test('대시보드: 같은 열량은 어디서나 같은 숫자', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/#dashboard')
  await page.evaluate(() => {
    const v = (value: number, unit: string) => ({ unit, known_total: value, status: 'complete', missing_count: 0 })
    const totals = { energy: v(949.7, 'kcal'), protein: v(41.25, 'g'), fiber: v(19.7, 'g'), sodium: v(1457.1, 'mg'), carbohydrate: v(112.3, 'g'), fat: v(37.5, 'g'), sugar: v(10, 'g') }
    localStorage.setItem('nourishon-local-mvp-v1', JSON.stringify({ profile: { age: 30, height_cm: 170, weight_kg: 70, equation_sex: 'female', activity: 'inactive', goal: 'maintain', scope_confirmed: true }, records: [{ id: crypto.randomUUID(), date: '2026-11-06', kind: '점심', calculation: { totals } }] }))
  })
  await page.reload()
  await page.getByLabel('요약 날짜', { exact: true }).fill('2026-11-06')
  await expect(page.locator('.diary-energy')).toContainText('950')
  await expect(page.locator('.journal-summary')).toContainText('950')
  await expect(page.locator('.journal-summary')).not.toContainText('949.7')
  await expect(page.locator('.diary-nutrients')).toContainText('1,457')
  await expect(page.locator('.sodium-note')).toContainText('1,457')
})
