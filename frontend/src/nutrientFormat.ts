// 열량·영양소 화면 표시 규칙(서비스 자체 규칙, 2026-11-17). 계산·저장·평균은 원래 값으로 하고 '보여줄 때만' 반올림한다.
// - kcal, mg: 정수 (예: 949.7 kcal → 950 kcal)
// - g, %: 소수 첫째 자리 (예: 41.25 g → 41.3 g)
// - 0이 아닌 작은 값이 0으로 반올림되면 '0.1 미만'처럼 표시한다. 기록된 0과 구분하기 위해서다.
// 이 파일만 고치면 대시보드·식사 계산·기간 분석·음식 비교·운동 기록 표시가 함께 바뀐다.
const DIGITS: Record<string, number> = { kcal: 0, mg: 0, g: 1, '%': 1 }

export function nutrientDigits(unit: string): number {
  return DIGITS[unit] ?? 1
}

export function formatAmount(value: number, unit: string): string {
  const digits = nutrientDigits(unit)
  const scale = 10 ** digits
  if (value > 0 && Math.round(value * scale) === 0) return digits === 0 ? '1 미만' : `0.${'0'.repeat(digits - 1)}1 미만`
  return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: digits }).format(value)
}

// 단위까지 붙인 표시. 예: formatWithUnit(949.7, 'kcal') → '950 kcal'
export function formatWithUnit(value: number, unit: string): string {
  return `${formatAmount(value, unit)} ${unit}`
}
