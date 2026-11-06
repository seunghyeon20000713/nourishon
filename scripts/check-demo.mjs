import {chromium} from '../frontend/node_modules/playwright-core/index.mjs';
const browser=await chromium.launch();try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],api=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))api.push(r.url())});
 await page.goto(process.env.NOURISHON_DEMO_URL??'http://127.0.0.1:5174/');await page.getByRole('complementary',{name:'체험판 안내'}).waitFor();
 await page.getByRole('link',{name:'내 식사 관리 시작하기',exact:true}).click();await page.getByRole('heading',{name:'기록으로 보는 나의 영양'}).waitFor();
 await page.getByRole('button',{name:'식사 분석',exact:true}).click();await page.getByRole('textbox',{name:'음식 이름'}).fill('두부');await page.getByRole('button',{name:'검색',exact:true}).click();await page.getByRole('button',{name:'연습용 두부 추가',exact:true}).click();await page.getByRole('button',{name:'영양 합계 계산'}).click();await page.getByRole('button',{name:'식사 기록에 추가',exact:true}).click();
 await page.getByRole('button',{name:'기록과 분석',exact:true}).click();await page.getByRole('button',{name:'월간',exact:true}).click();
 await page.getByRole('button',{name:'운동 계획',exact:true}).click();const f=page.getByRole('form',{name:'실제 운동 계산'});await f.getByLabel('수행한 운동',{exact:true}).selectOption('12030');await f.getByRole('button',{name:'운동 소모량 계산'}).click();await page.getByRole('button',{name:'운동 기록에 추가',exact:true}).click();await page.locator('.activity-record').waitFor();
 await page.getByRole('button',{name:'영양 대시보드',exact:true}).click();await page.screenshot({path:'/tmp/nourishon-sites-demo-desktop.png'});
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'/tmp/nourishon-sites-demo-mobile.png'});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('모바일 넘침');
 if(api.length||errors.length)throw Error(JSON.stringify({api,errors}));console.log('체험판 소개·가상 식사 검색/계산/기록·기간 분석·러닝 기록·모바일 정상, API 네트워크 요청 0건');
}finally{await browser.close()}
