"""2024 Adult Compendium 일부 활동의 표준 MET 참고 계산. 개인 처방 아님."""
from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SOURCE = 'https://pacompendium.com/'
VERSION = '2024 Adult Compendium / standard MET'
ACTIVITIES = {
    '17152': {'category': '걷기', 'name': '평지 느린 걷기 · 2.0~2.4mph (약 3.2~3.9km/h)', 'met': 2.8, 'url': 'https://pacompendium.com/walking/'},
    '17190': {'category': '걷기', 'name': '평지 보통 걷기 · 2.8~3.4mph (약 4.5~5.5km/h)', 'met': 3.8, 'url': 'https://pacompendium.com/walking/'},
    '17200': {'category': '걷기', 'name': '평지 빠른 걷기 · 3.5~3.9mph (약 5.6~6.3km/h)', 'met': 4.8, 'url': 'https://pacompendium.com/walking/'},
    '01210': {'category': '자전거', 'name': '실내 자전거 · 25~30W', 'met': 3.5, 'url': 'https://pacompendium.com/bicycling/'},
    '01214': {'category': '자전거', 'name': '실내 자전거 · 50W', 'met': 4.0, 'url': 'https://pacompendium.com/bicycling/'},
    '12020': {'category': '러닝', 'name': '조깅 · 본인이 선택한 일반적인 페이스', 'met': 7.5, 'url': 'https://pacompendium.com/running/'},
    '12028': {'category': '러닝', 'name': '러닝 · 4.0~4.2mph (약 6.4~6.8km/h)', 'met': 6.5, 'url': 'https://pacompendium.com/running/'},
    '12030': {'category': '러닝', 'name': '러닝 · 5.0~5.2mph (약 8.0~8.4km/h)', 'met': 8.5, 'url': 'https://pacompendium.com/running/'},
    '12050': {'category': '러닝', 'name': '러닝 · 6.0~6.3mph (약 9.7~10.1km/h)', 'met': 9.3, 'url': 'https://pacompendium.com/running/'},
    '02024': {'category': '근력·맨몸', 'name': '가벼운 맨몸 코어 운동 · 크런치·플랭크 등', 'met': 2.8, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '02056': {'category': '근력·맨몸', 'name': '맨몸 저항 운동 · 스쿼트·런지·푸시업 등 일반적 수행', 'met': 3.0, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '02022': {'category': '근력·맨몸', 'name': '맨몸 체조 · 푸시업·윗몸일으키기·턱걸이·런지 등 중간 노력', 'met': 3.8, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '02054': {'category': '근력·맨몸', 'name': '웨이트 트레이닝 · 여러 종목, 다양한 저항으로 8~15회 반복', 'met': 3.5, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '02050': {'category': '근력·맨몸', 'name': '웨이트 트레이닝 · 프리웨이트·기구·파워리프팅 등 높은 노력', 'met': 6.0, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '02052': {'category': '근력·맨몸', 'name': '웨이트 트레이닝 · 스쿼트·데드리프트, 느리거나 폭발적 수행', 'met': 5.0, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '01010': {'category': '자전거', 'name': '야외 자전거 · 10mph 미만 (약 16.1km/h 미만), 여가·통근', 'met': 4.0, 'url': 'https://pacompendium.com/bicycling/'},
    '01015': {'category': '자전거', 'name': '야외 자전거 · 본인이 선택한 편안한 페이스', 'met': 4.3, 'url': 'https://pacompendium.com/bicycling/'},
    '02101': {'category': '스트레칭·요가·필라테스', 'name': '스트레칭 · 가볍게 수행', 'met': 2.3, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '02150': {'category': '스트레칭·요가·필라테스', 'name': '하타 요가', 'met': 2.3, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '02105': {'category': '스트레칭·요가·필라테스', 'name': '필라테스 · 일반적 수행', 'met': 2.8, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '02048': {'category': '유산소 기구', 'name': '일립티컬 · 중간 노력', 'met': 5.0, 'url': 'https://pacompendium.com/conditioning-exercise/'},
    '15030': {'category': '생활 스포츠', 'name': '배드민턴 · 친선 단식·복식, 일반적 수행', 'met': 5.5, 'url': 'https://pacompendium.com/sports/'},
    '15660': {'category': '생활 스포츠', 'name': '탁구 · 일반적 수행', 'met': 4.0, 'url': 'https://pacompendium.com/sports/'},
    '15610': {'category': '생활 스포츠', 'name': '축구 · 비경쟁적, 일반적 수행', 'met': 7.0, 'url': 'https://pacompendium.com/sports/'},
    '15070': {'category': '생활 스포츠', 'name': '농구 · 슛 연습', 'met': 5.0, 'url': 'https://pacompendium.com/sports/'},
}


class ActivityRecord(BaseModel):
    # 이전 계산 결과는 입력에서 버리고 서버가 다시 계산한다.
    model_config = ConfigDict(extra='ignore')
    id: UUID
    date: date
    age: Annotated[int, Field(strict=True, ge=19, le=59)]
    activity_code: str
    weight_kg: Annotated[float, Field(strict=True, ge=25, le=350, allow_inf_nan=False)]
    minutes: Annotated[float, Field(strict=True, ge=0, le=300, allow_inf_nan=False)]

    @field_validator('activity_code')
    @classmethod
    def supported_activity(cls, value):
        if value not in ACTIVITIES:
            raise ValueError('지원하는 운동 코드를 선택하세요.')
        return value

    @model_validator(mode='after')
    def date_not_future(self):
        if self.date > datetime.now(timezone(timedelta(hours=9))).date():
            raise ValueError('미래 운동 기록은 허용하지 않습니다.')
        return self


def calculate_activity(record: ActivityRecord) -> dict:
    activity = ACTIVITIES[record.activity_code]
    # Compendium의 1 MET ≈ 1 kcal/kg/hour 정의를 택한 근사식이다.
    factor = record.weight_kg * record.minutes / 60
    return {**record.model_dump(mode='json'), 'calculation': {
        'name': activity['name'], 'met': activity['met'],
        'gross_kcal': round(activity['met'] * factor, 2),
        'above_rest_kcal': round((activity['met'] - 1) * factor, 2),
        'formula': '총 소모량 ≈ MET × 체중(kg) × 시간(분) ÷ 60; 안정 시 제외 ≈ (MET−1) × 체중 × 시간 ÷ 60',
        'version': VERSION, 'checked_on': '2026-11-06', 'source_url': activity['url'],
        'scope': '19~59세 일반 성인 표준 MET 참고값. 개인 실측·감량 보장·필수 운동량이 아닙니다.',
    }}
