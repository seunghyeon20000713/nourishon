"""2024 Adult Compendium 일부 활동의 표준 MET 참고 계산. 개인 처방 아님."""
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

SOURCE = 'https://pacompendium.com/'
VERSION = '2024 Adult Compendium / standard MET'
ACTIVITIES = {
    '17152': {'name': '평지 느린 걷기 · 2.0~2.4mph (약 3.2~3.9km/h)', 'met': 2.8, 'url': 'https://pacompendium.com/walking/'},
    '17190': {'name': '평지 보통 걷기 · 2.8~3.4mph (약 4.5~5.5km/h)', 'met': 3.8, 'url': 'https://pacompendium.com/walking/'},
    '17200': {'name': '평지 빠른 걷기 · 3.5~3.9mph (약 5.6~6.3km/h)', 'met': 4.8, 'url': 'https://pacompendium.com/walking/'},
    '01210': {'name': '실내 자전거 · 25~30W', 'met': 3.5, 'url': 'https://pacompendium.com/bicycling/'},
    '01214': {'name': '실내 자전거 · 50W', 'met': 4.0, 'url': 'https://pacompendium.com/bicycling/'},
}


class ActivityRecord(BaseModel):
    # 이전 계산 결과는 입력에서 버리고 서버가 다시 계산한다.
    model_config = ConfigDict(extra='ignore')
    id: UUID
    date: date
    age: Annotated[int, Field(strict=True, ge=19, le=59)]
    activity_code: Literal['17152', '17190', '17200', '01210', '01214']
    weight_kg: Annotated[float, Field(strict=True, ge=25, le=350, allow_inf_nan=False)]
    minutes: Annotated[float, Field(strict=True, ge=0, le=300, allow_inf_nan=False)]

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
