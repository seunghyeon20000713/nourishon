import { test, expect } from '@playwright/test'

// 2026-11-17 메뉴 정리: 메뉴 버튼은 화면마다 하나. 데스크톱은 왼쪽, 모바일은 상단.
test('데스크톱은 왼쪽, 모바일은 상단 메뉴 버튼 하나로 메뉴 이름 펼침과 화면 이동', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/#dashboard')
  const left = page.getByRole('button', { name: '왼쪽 메뉴 펼치기', exact: true })
  const top = page.getByRole('button', { name: '상단 메뉴 펼치기', exact: true })
  await expect(page.getByRole('heading', { name: '오늘의 나를 기록해요' })).toBeVisible()
  await expect(left).toBeVisible()
  await expect(top).toBeHidden()
  await expect(page.getByRole('button', { name: '계정 설정', exact: true })).toBeHidden()
  await expect(left).toHaveAttribute('aria-expanded', 'false')
  await left.click()
  await expect(left).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByRole('navigation', { name: '주 메뉴' }).getByText('내 정보', {exact:true})).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(left).toHaveAttribute('aria-expanded', 'false')
  await expect(left).toBeFocused()
  // 상단 바의 기록 설정 드롭다운은 메뉴의 '내 정보'(신체 정보 화면)와 이름이 겹치지 않는다.
  await expect(page.locator('details.profile-tools > summary')).toContainText('기록 설정')

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(left).toBeHidden()
  await expect(top).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  // 모바일 상단 한 줄: 서비스 이름·계정·기록 설정·메뉴가 겹치지 않는다.
  const boxes = await Promise.all(['.journal-wordmark', '#account-tools > summary', 'details.profile-tools > summary', '.top-menu-toggle'].map(s => page.locator(s).boundingBox()))
  for (let i = 1; i < boxes.length; i++) expect(boxes[i]!.x).toBeGreaterThanOrEqual(boxes[i - 1]!.x + boxes[i - 1]!.width)
  await top.click()
  await expect(top).toHaveAttribute('aria-expanded', 'true')
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('button', { name: '내 몸과 목표', exact: true }).click()
  await expect(page.getByRole('heading', { name: '내 몸과 목표', exact: true })).toBeVisible()
  await expect(top).toHaveAttribute('aria-expanded', 'false')
})
