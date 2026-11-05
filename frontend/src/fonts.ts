import manropeCss from '@fontsource-variable/manrope/index.css?raw'
import koreanCss from '@fontsource-variable/noto-sans-kr/index.css?raw'

// 개발 서버에서도 모든 한글 하위 글꼴의 경로를 명시적인 자산 URL로 연결한다.
const assets = import.meta.glob<string>(
  '../node_modules/@fontsource-variable/*/files/*.woff2',
  { eager: true, query: '?url', import: 'default' },
)
const css = [['manrope', manropeCss], ['noto-sans-kr', koreanCss]].map(([family, content]) =>
  content.replace(/url\(\.\/files\/([^)]*)\)/g, (_, file: string) => {
    const url = assets[`../node_modules/@fontsource-variable/${family}/files/${file}`]
    if (!url) throw new Error('로컬 글꼴 자산을 찾을 수 없습니다.')
    return `url("${url}")`
  }),
).join('\n')
document.querySelector('[data-nourishon-fonts]')?.remove()
const style = document.createElement('style')
style.dataset.nourishonFonts = 'true'
style.textContent = css
document.head.append(style)
