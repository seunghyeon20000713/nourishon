import { test, expect } from '@playwright/test'

// 서버에 연결하지 못하면 빈 화면처럼 보이지 않고 모든 화면 위에 이유와 다시 연결 버튼을 보여준다.
for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`서버 연결 실패 안내 띠 (${viewport.width}px)`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await page.route('**/api/**', route => route.abort())
    await page.goto('/#dashboard')
    const banner = page.getByRole('alert').filter({ hasText: '서버에 연결하지 못했습니다' })
    await expect(banner).toBeVisible()
    await expect(banner.getByRole('button', { name: '다시 연결' })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
    // 연결되면 다시 연결 버튼으로 안내가 사라진다.
    await page.unroute('**/api/**')
    await banner.getByRole('button', { name: '다시 연결' }).click()
    await expect(page.getByText('서버에 연결하지 못했습니다')).toHaveCount(0)
  })
}
