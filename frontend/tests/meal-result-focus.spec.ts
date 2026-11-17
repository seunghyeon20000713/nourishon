import { test, expect } from '@playwright/test'

// 계산 후 결과가 화면 아래에 있어 안 보이던 문제(지인 피드백, 2026-11-17)
for (const reducedMotion of ['no-preference', 'reduce'] as const) {
  test(`모바일 390px: 계산하면 결과 제목으로 이동·포커스 (동작 줄이기 ${reducedMotion})`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion })
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/#dashboard')
    await page.locator('.mobile-bottom-nav').getByRole('button', { name: '식사 분석', exact: true }).click()
    await page.getByRole('textbox', { name: '음식 이름' }).fill('국밥_돼지머리')
    await page.getByRole('button', { name: '검색', exact: true }).click()
    await page.getByRole('button', { name: '국밥_돼지머리 추가', exact: true }).click()
    const heading = page.getByRole('heading', { name: '한 끼에 담긴 영양' })
    await expect(heading).not.toBeInViewport()
    await page.getByRole('button', { name: '영양 합계 계산' }).click()
    await expect(page.locator('.energy-card .nutrient-value')).toHaveText('137 kcal')
    await expect(heading).toBeFocused()
    if (reducedMotion === 'reduce') {
      // 부드러운 스크롤 없이 바로 이동했는지: 기다리지 않고 곧바로 화면 안에 있어야 한다.
      expect(await heading.evaluate(el => { const r = el.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight })).toBe(true)
    }
    await expect(heading).toBeInViewport()
    // 고정 상단 바가 제목을 가리지 않는다.
    await expect.poll(async () => {
      const bar = await page.locator('.journal-topbar').boundingBox()
      const box = await heading.boundingBox()
      return !!bar && !!box && box.y >= bar.y + bar.height
    }).toBe(true)
  })
}
