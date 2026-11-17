import './site-notice.css'

/** 화면 맨 위에 고정 안내 띠를 붙인다. 체험판과 테스트 서버가 같은 모양을 쓴다. */
export function showSiteNotice(label: string, text: string, ...extra: HTMLElement[]) {
 document.body.classList.add('notice-mode')
 const banner = document.createElement('aside')
 banner.className = 'site-notice'
 banner.setAttribute('aria-label', label)
 const message = document.createElement('span')
 message.textContent = text
 banner.append(message, ...extra)
 document.body.prepend(banner)
 return message
}

/** 실제 기능 테스트 서버(staging) 빌드에서만 켜진다. 실제 개인정보·건강정보 입력을 막기 위한 안내다. */
export function setupStagingNotice() {
 const message = showSiteNotice('테스트 서버 안내',
  '테스트 서버입니다 · 실제 개인정보·건강정보 대신 가상 정보만 입력하세요. 무료 서버라 첫 접속이 느릴 수 있고, 기록은 장기 보관을 보장하지 않습니다.')
 // 모바일은 한 줄 요약만 보여준다(긴 문장은 화면 읽기 프로그램용으로 남김).
 message.classList.add('notice-long')
 const short = document.createElement('span')
 short.className = 'notice-short'
 short.setAttribute('aria-hidden', 'true')
 short.textContent = '테스트 서버 · 실제 정보 대신 가상 정보만 입력하세요'
 message.after(short)
}
