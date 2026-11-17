// 운동 목록을 일반 사용자가 읽기 쉬운 말로 보여주기 위한 화면용 번역표.
// 계산·저장·출처 표시는 서버의 공식 Compendium 이름과 MET 값을 그대로 쓴다(backend/activity_log.py).
// 여기의 문장은 공식 조건을 쉬운 말로 옮긴 것이며 새로운 기준을 만들지 않는다.
export const ACTIVITY_GUIDE: Record<string, { label: string; hint: string }> = {
  '17152': { label: '천천히 걷기', hint: '평지, 시속 약 3.2~3.9km' },
  '17190': { label: '보통 속도로 걷기', hint: '평지, 시속 약 4.5~5.5km' },
  '17200': { label: '빠르게 걷기', hint: '평지, 시속 약 5.6~6.3km' },
  '12020': { label: '조깅', hint: '내가 평소 편하게 뛰는 속도' },
  '12028': { label: '천천히 달리기', hint: '시속 약 6.4~6.8km' },
  '12030': { label: '보통 속도로 달리기', hint: '시속 약 8.0~8.4km' },
  '12050': { label: '빠르게 달리기', hint: '시속 약 9.7~10.1km' },
  '01210': { label: '실내 자전거 · 아주 가볍게', hint: '기구 화면의 출력 25~30W' },
  '01214': { label: '실내 자전거 · 가볍게', hint: '기구 화면의 출력 50W' },
  '01010': { label: '야외 자전거 · 여유롭게', hint: '시속 16km 미만, 산책·출퇴근' },
  '01015': { label: '야외 자전거 · 편한 속도', hint: '내가 편하게 고른 속도' },
  '02024': { label: '가벼운 코어 운동', hint: '크런치·플랭크 등' },
  '02056': { label: '맨몸 운동', hint: '스쿼트·런지·푸시업 등을 보통으로' },
  '02022': { label: '맨몸 운동 · 조금 힘들게', hint: '푸시업·윗몸일으키기·턱걸이 등' },
  '02054': { label: '웨이트 · 보통', hint: '여러 종목을 8~15회씩 반복' },
  '02050': { label: '웨이트 · 힘들게', hint: '프리웨이트·기구를 높은 노력으로' },
  '02052': { label: '웨이트 · 스쿼트·데드리프트', hint: '느리게 또는 폭발적으로' },
  '02101': { label: '스트레칭', hint: '가볍게' },
  '02150': { label: '요가', hint: '하타 요가' },
  '02105': { label: '필라테스', hint: '일반적인 수업·동작' },
  '02048': { label: '일립티컬(크로스 트레이너)', hint: '중간 정도 노력' },
  '15030': { label: '배드민턴', hint: '친선 단식·복식' },
  '15660': { label: '탁구', hint: '일반적인 경기' },
  '15610': { label: '축구', hint: '시합이 아닌 친선 경기' },
  '15070': { label: '농구', hint: '슛 연습' },
  '17081': { label: '천천히 등산·하이킹', hint: '들판·언덕을 천천히, 짐 없이' },
  '17082': { label: '보통 속도 등산·하이킹', hint: '들판·언덕을 평소 속도로, 짐 없이' },
  '17012': { label: '배낭 메고 등산', hint: '당일 배낭(데이팩)을 메고 산행' },
}

// MET 강도 구분: 3 미만 가벼운 강도, 3 이상 6 미만 중간 강도, 6 이상 높은 강도
// (2018 Physical Activity Guidelines Advisory Committee Report의 일반적인 구분).
export function intensity(met: number): { level: 'light' | 'moderate' | 'vigorous'; text: string } {
  if (met < 3) return { level: 'light', text: '가벼운 강도' }
  if (met < 6) return { level: 'moderate', text: '중간 강도' }
  return { level: 'vigorous', text: '높은 강도' }
}

export function activityLabel(code: string, fallback: string) {
  return ACTIVITY_GUIDE[code]?.label ?? fallback
}
