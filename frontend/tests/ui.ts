import type {Page} from '@playwright/test'
export async function openProfiles(page:Page){const panel=page.locator('details.profile-tools');if(await panel.getAttribute('open')===null)await panel.locator(':scope > summary').click();const advanced=panel.locator('.advanced-profiles');if(await advanced.getAttribute('open')===null)await advanced.locator(':scope > summary').click()}
// 패널 바로 아래 summary만 누른다(패널 안 '회원 탈퇴' 접힘 항목의 summary와 구분).
export async function openAccount(page:Page){const panel=page.locator('#account-tools');if(await panel.getAttribute('open')===null)await panel.locator(':scope > summary').click()}

// 주 메뉴로 화면 이동. 데스크톱은 왼쪽 메뉴, 모바일은 상단 메뉴 버튼 하나만 있다(2026-11-17 메뉴 정리).
// 화면이 다 그려질 때까지 메뉴 항목이나 메뉴 버튼 중 하나가 나타나기를 기다린 뒤 판단한다.
export async function goToView(page:Page,name:string){
 const target=page.getByRole('button',{name,exact:true})
 const left=page.getByRole('button',{name:'왼쪽 메뉴 펼치기',exact:true})
 const top=page.getByRole('button',{name:'상단 메뉴 펼치기',exact:true})
 await target.or(left).or(top).first().waitFor({state:'visible'})
 if(!await target.isVisible())await (await top.isVisible()?top:left).click()
 await target.click()
}
