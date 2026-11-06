"""일반 성인 로컬 MVP의 프로필·참고 목표 계산. 개인정보를 저장하지 않는다."""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
from backend.references import (ENERGY_SOURCE, PROTEIN_SOURCE, DIET_SOURCE,
                                KDRI_SOURCE, ACTIVITY_SOURCE, checked_sources)
COEFFICIENTS = {
    "male": {"inactive": (753.07, -10.83, 6.50, 14.10),
             "low_active": (581.47, -10.83, 8.30, 14.94),
             "active": (1004.82, -10.83, 6.52, 15.91),
             "very_active": (-517.88, -10.83, 15.61, 19.11)},
    "female": {"inactive": (584.90, -7.01, 5.72, 11.71),
               "low_active": (575.77, -7.01, 6.60, 12.14),
               "active": (710.25, -7.01, 6.54, 12.34),
               "very_active": (511.83, -7.01, 9.07, 12.56)},
}


class BodyComposition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    measured_on: date
    skeletal_muscle_kg: Annotated[Number, Field(gt=0)] | None = None
    fat_mass_kg: Annotated[Number, Field(ge=0)] | None = None
    body_fat_percent: Annotated[Number, Field(ge=0, le=100)] | None = None


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age: Annotated[int, Field(strict=True, ge=19, le=64)]
    height_cm: Annotated[Number, Field(ge=100, le=250)]
    weight_kg: Annotated[Number, Field(ge=25, le=350)]
    equation_sex: Literal["male", "female"]
    activity: Literal["inactive", "low_active", "active", "very_active"]
    goal: Literal["maintain", "lose", "gain"] = "maintain"
    scope_confirmed: Literal[True]
    body: BodyComposition | None = None
    measured_on: date | None = None

    @model_validator(mode="after")
    def check_body(self):
        today = datetime.now(timezone(timedelta(hours=9))).date()
        if self.measured_on and self.measured_on > today:
            raise ValueError("측정일은 미래일 수 없습니다.")
        if self.body:
            if self.measured_on and self.measured_on != self.body.measured_on:
                raise ValueError("체중과 체성분은 같은 측정일로 입력하세요.")
            if self.body.measured_on > today:
                raise ValueError("측정일은 미래일 수 없습니다.")
            if all(v is None for v in (self.body.skeletal_muscle_kg,
                                       self.body.fat_mass_kg, self.body.body_fat_percent)):
                raise ValueError("측정값을 하나 이상 입력하세요.")
            for value in (self.body.skeletal_muscle_kg, self.body.fat_mass_kg):
                if value is not None and value > self.weight_kg:
                    raise ValueError("체성분 값은 같은 측정의 체중을 넘을 수 없습니다.")
            if (self.body.skeletal_muscle_kg is not None and self.body.fat_mass_kg is not None
                    and self.body.skeletal_muscle_kg + self.body.fat_mass_kg > self.weight_kg):
                raise ValueError("골격근량과 체지방량의 합을 확인하세요.")
        return self


def estimate_profile(profile: ProfileInput) -> dict:
    a, b, c, d = COEFFICIENTS[profile.equation_sex][profile.activity]
    energy = a + b * profile.age + c * profile.height_cm + d * profile.weight_kg
    if energy <= 0:
        raise ValueError("입력 범위에서 유효한 에너지 추정값을 구할 수 없습니다.")
    return {
        "bmi": round(profile.weight_kg / (profile.height_cm / 100) ** 2, 2),
        "maintenance_kcal": round(energy),
        "protein_reference_g": round(profile.weight_kg * 0.8, 1),
        "fiber_reference_g": 25,
        "sodium_reference_mg": 2000,
        "macro_reference_ranges": {
            key: {"percent": [low, high], "min_g": round(energy * low / 100 / kcal_per_g, 1),
                  "max_g": round(energy * high / 100 / kcal_per_g, 1)}
            for key, low, high, kcal_per_g in (("carbohydrate", 50, 65, 4),
                                               ("protein", 10, 20, 4), ("fat", 15, 30, 9))
        },
        "macro_reference_version": "2025 한국인 영양소 섭취기준 / 일반 성인 에너지 적정비율",
        "basis": "체성분 정보 추가 등록" if profile.body else "기본 정보 기반 추정",
        "body_used_in_energy_equation": False,
        "energy_formula": {"version": "NASEM DRI Energy 2023 / Health Canada 공개표",
                           "coefficients": [a, b, c, d],
                           "expression": "상수 + 나이계수×나이 + 키계수×키(cm) + 체중계수×체중(kg)"},
        "limitations": ["유지 에너지 추정값이며 감량·증량 열량 처방이 아닙니다.",
                       "유지 에너지 공식은 북미 DRI 2023이며 한국인 개인 목표로 검증한 값은 아닙니다.",
                       "BMI는 체지방·근육·건강 상태의 단독 판정 기준이 아닙니다.",
                       "인바디는 변화 기록에 활용하며 이번 에너지 공식에는 사용하지 않습니다.",
                       "단백질은 일반 성인 참고값이며 운동선수·질환 치료 목표가 아닙니다."],
        "sources": checked_sources([{"title": "2025 한국인 기준: 에너지 적정비율", "url": KDRI_SOURCE},
                    {"title": "유지 에너지: DRI 2023", "url": ENERGY_SOURCE},
                    {"title": "일반 성인 단백질 참고", "url": PROTEIN_SOURCE},
                    {"title": "WHO 식생활 기준", "url": DIET_SOURCE},
                    {"title": "WHO 2020 신체활동 지침", "url": ACTIVITY_SOURCE}]),
    }
