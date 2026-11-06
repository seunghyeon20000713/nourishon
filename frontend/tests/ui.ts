import type {Page} from '@playwright/test'
export async function openProfiles(page:Page){const panel=page.locator('details.profile-tools');if(await panel.getAttribute('open')===null)await panel.locator(':scope > summary').click();const advanced=panel.locator('.advanced-profiles');if(await advanced.getAttribute('open')===null)await advanced.locator(':scope > summary').click()}
export async function openAccount(page:Page){const panel=page.locator('#account-tools');if(await panel.getAttribute('open')===null)await panel.locator('summary').click()}
