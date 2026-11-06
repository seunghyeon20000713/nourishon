"""공식 자료 확인 기록. 확인일은 서비스 검토일이며 자료 발행일과 다르다."""
CHECKED_ON = '2026-11-06'
ENERGY_SOURCE = 'https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/dietary-reference-intakes/tables/equations-estimate-energy-requirement.html'
PROTEIN_SOURCE = 'https://www.healthlinkbc.ca/healthlinkbc-files/protein-and-your-health'
DIET_SOURCE = 'https://www.who.int/news-room/fact-sheets/detail/healthy-diet'
KDRI_SOURCE = 'https://www.kns.or.kr/fileroom/fileroom_view.asp?BoardID=Kdr&idx=168'
ACTIVITY_SOURCE = 'https://www.who.int/europe/news-room/fact-sheets/item/physical-activity'
NIDDK_SOURCE = 'https://www.niddk.nih.gov/health-information/weight-management/tips-get-active/tips-keep-moving'
_METADATA = {
    ENERGY_SOURCE: ('북미 DRI Energy 2023 / 공개표 갱신 2025-11-19', '19세 이상 비임신·비수유 성인 공식 중 서비스는 19~64세만 적용', '유지 에너지 추정이며 한국인 개인 목표로 검증한 값은 아님'),
    PROTEIN_SOURCE: ('HealthLink BC / 2025-07-09', '건강한 19세 이상 일반 성인', '0.8g/kg/일 참고이며 운동선수·질환별 목표는 아님'),
    DIET_SOURCE: ('WHO Healthy diet / 2026-01-26', '성인 나트륨·10세 초과 식이섬유 기준 중 성인에 적용', '식이섬유 25g 이상·나트륨 2,000mg 미만; 총당류와 유리당 구분'),
    KDRI_SOURCE: ('2025 한국인 영양소 섭취기준 / 학회 공개 발표', '일반 성인 에너지 적정비율 참고', '탄수화물 50~65%, 단백질 10~20%, 지방 15~30%; 개인 처방 아님'),
    ACTIVITY_SOURCE: ('WHO 신체활동·좌식행동 지침 2020', 'WHO 성인 18~64세 중 서비스는 19~64세 일반 성인에 제한', '중강도 유산소 주 150~300분과 중강도 이상 근력 주 2일 이상; 가벼운 시작 계획은 충족 보장 없음'),
    NIDDK_SOURCE: ('NIDDK Tips to Keep Moving / 최종 검토 2017-05', '일반적인 활동 시작·점진적 증가 안내', '서비스의 분 단위 배분을 정한 공식이나 개인 처방 근거는 아님'),
}


def checked_sources(items: list[dict]) -> list[dict]:
    return [{**item, 'version': _METADATA[item['url']][0],
             'applies_to': _METADATA[item['url']][1], 'usage': _METADATA[item['url']][2],
             'checked_on': CHECKED_ON} for item in items]
