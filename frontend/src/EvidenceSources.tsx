export type EvidenceSource = { title: string; url: string; version?: string; applies_to?: string; usage?: string; checked_on?: string }
export function EvidenceSources({ sources }: { sources: EvidenceSource[] }) {
  return <details className="evidence-sources"><summary>출처·버전·적용 대상 확인</summary><p>자료 확인일은 서비스에서 출처를 대조한 날짜이며, 개인별 효과 검증이나 전문가 진료를 뜻하지 않습니다.</p><ul>{sources.map(source => <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a><p>{source.version ?? '이전 결과 · 버전 정보 없음'}</p>{source.applies_to && <p>적용 대상: {source.applies_to}</p>}{source.usage && <p>{source.usage}</p>}<small>확인일: {source.checked_on ?? '정보 없음 · 다시 계산하면 최신 확인 정보가 표시됩니다.'}</small></li>)}</ul></details>
}
