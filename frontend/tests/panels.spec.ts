import { test, expect, type Page } from '@playwright/test'
import { randomBytes } from 'node:crypto'

// 상단 드롭다운(계정·기록 설정)이 어떤 화면 폭에서도 화면 밖으로 잘리지 않는지 확인한다(2026-11-17).
async function inside(page: Page, selector: string) {
  const width = page.viewportSize()!.width
  const box = (await page.locator(selector).boundingBox())!
  expect(box.x, `${selector} 왼쪽`).toBeGreaterThanOrEqual(0)
  expect(box.x + box.width, `${selector} 오른쪽`).toBeLessThanOrEqual(width)
}

for (const width of [1440, 390, 360]) {
  test(`계정·기록 설정 패널이 화면 안에 있음 (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 })
    await page.goto('/#dashboard')
    const account = page.locator('#account-tools')
    await account.locator(':scope > summary').click()
    await expect(account.locator('.account-banner')).toBeVisible()
    await inside(page, '#account-tools .account-banner')
    await account.locator(':scope > summary').click()

    await page.locator('details.profile-tools > summary').click()
    await inside(page, 'details.profile-tools .profile-popup')
    // 패널이 자기 버튼을 덮지 않아 같은 버튼으로 다시 닫을 수 있다.
    await page.locator('details.profile-tools > summary').click()
    await expect(page.locator('details.profile-tools .profile-popup')).toBeHidden()

    // 로그인 후: 회원 탈퇴 항목까지 펼쳐도 화면 안
    const origin = new URL(page.url()).origin
    const headers = { Origin: origin, 'X-NourishOn-Client': 'web' }
    const username = 'panel_' + randomBytes(6).toString('hex'), password = randomBytes(12).toString('hex')
    const reg = await page.request.post('/api/auth/register', { headers, data: { username, password } })
    expect(reg.status()).toBe(201)
    const csrf = (await reg.json()).csrf_token
    await page.reload()
    await account.locator(':scope > summary').click()
    await expect(account.locator('.account-banner')).toContainText(`${username}님의 계정`)
    await account.locator('.account-delete > summary').click()
    await inside(page, '#account-tools .account-banner')
    await inside(page, '#account-tools .account-delete')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
    // 테스트가 만든 가상 계정 정리
    expect((await page.request.post('/api/account/delete', { headers: { ...headers, 'X-CSRF-Token': csrf }, data: { password, confirm: true } })).status()).toBe(200)
  })
}
