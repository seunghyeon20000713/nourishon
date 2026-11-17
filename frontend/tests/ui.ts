import type {Page} from '@playwright/test'
export async function openProfiles(page:Page){const panel=page.locator('details.profile-tools');if(await panel.getAttribute('open')===null)await panel.locator(':scope > summary').click();const advanced=panel.locator('.advanced-profiles');if(await advanced.getAttribute('open')===null)await advanced.locator(':scope > summary').click()}
// 패널 바로 아래 summary만 누른다(패널 안 '회원 탈퇴' 접힘 항목의 summary와 구분).
export async function openAccount(page:Page){const panel=page.locator('#account-tools');if(await panel.getAttribute('open')===null)await panel.locator(':scope > summary').click()}
