"""일반 성인 활동 계획 초안. 임상 운동 처방·재활·체성분 기반 강도 산출 제외."""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from backend.profile import ProfileInput

WHO = 'https://www.who.int/europe/news-room/fact-sheets/item/physical-activity'
NIDDK = 'https://www.niddk.nih.gov/health-information/weight-management/tips-get-active/tips-keep-moving'


class ExerciseInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    experience: Literal['beginner', 'regular']
    days: Annotated[int, Field(strict=True, ge=2, le=6)]
    minutes: Annotated[int, Field(strict=True, ge=5, le=60)]
    current_weekly_minutes: Annotated[int, Field(strict=True, ge=0, le=1000)]
    preference: Literal['walking', 'cycling'] = 'walking'
    has_limitations: Annotated[bool, Field(strict=True)]
    has_symptoms: Annotated[bool, Field(strict=True)]
    scope_confirmed: Literal[True]


def plan_exercise(profile: ProfileInput, request: ExerciseInput) -> dict:
    common = {
        'version': 'adult-activity-draft-v1',
        'generated_on': datetime.now(timezone(timedelta(hours=9))).date().isoformat(),
        'medical_prescription': False,
        'sources': [{'title': 'WHO 2020 일반 성인 활동 지침', 'url': WHO},
                    {'title': 'NIDDK 안전한 활동 시작', 'url': NIDDK}],
        'reference': '일반 성인 참고는 중강도 유산소 주 150~300분과 주요 근육 강화 주 2일 이상입니다.',
        'stop_rule': '흉통·어지럼·실신감·통증·비정상적인 호흡곤란이 있으면 중단하고 진료를 받으세요.',
    }
    if request.has_limitations or request.has_symptoms:
        return {**common, 'status': 'needs_assessment', 'schedule': [],
                'message': '증상·질환·부상·운동 제한을 먼저 전문가에게 평가받으세요. 자동 운동 계획을 생성하지 않습니다.'}
    # 이용 가능 시간과 현재 활동량에 맞춘 제품 규칙이며 WHO의 개인 처방 공식이 아니다.
    beginner = request.experience == 'beginner' or request.current_weekly_minutes < 60
    duration = min(request.minutes, 10 if beginner else max(10, request.current_weekly_minutes // request.days))
    warmup, cooldown = 1, 1
    indices = [round(i * 6 / (request.days - 1)) for i in range(request.days)]
    strength_indices = {indices[0], indices[len(indices) // 2]}
    schedule = []
    for index, name in enumerate(['월', '화', '수', '목', '금', '토', '일']):
        if index not in indices:
            schedule.append({'day': name, 'rest': True, 'total_minutes': 0,
                             'message': '회복일 · 오래 앉아 있는 시간을 줄이고 편안하게 움직이세요.'})
            continue
        strength = min(4 if beginner else 8, max(1, duration - 3)) if index in strength_indices else 0
        aerobic = duration - warmup - cooldown - strength
        schedule.append({'day': name, 'rest': False, 'total_minutes': duration,
                         'warmup_minutes': warmup, 'cooldown_minutes': cooldown,
                         'aerobic_minutes': aerobic, 'strength_minutes': strength,
                         'activity': '걷기' if request.preference == 'walking' else '실내 자전거',
                         'intensity': '편하게 대화할 수 있는 낮은 강도로 시작' if beginner else '대화 가능한 범위에서, 기존에 익숙한 강도 유지',
                         'strength_note': '주요 근육을 고르게 사용하는 익숙한 동작을 편안하게 연습하세요. 무게·최대반복수는 자동 처방하지 않습니다.' if strength else None})
    return {**common, 'status': 'draft', 'schedule': schedule,
            'weekly_aerobic_minutes': sum(x.get('aerobic_minutes', 0) for x in schedule),
            'weekly_strength_days': len(strength_indices),
            'message': '현재 여건에 맞춘 시작 계획입니다. 일반 주간 권고량을 충족한다는 뜻은 아닙니다.',
            'goal_note': {'maintain': '지속 가능한 활동 습관과 회복을 우선합니다.',
                          'lose': '섭취 열량을 운동으로 상쇄하거나 빠른 감량을 약속하지 않습니다.',
                          'gain': '회복과 점진적인 근력 활동을 살펴보되 체성분만으로 중량을 정하지 않습니다.'}[profile.goal],
            'basis': {'experience': request.experience, 'available_days': request.days,
                      'available_minutes': request.minutes, 'current_weekly_minutes': request.current_weekly_minutes,
                      'body_composition_used': False},
            'progression': '첫 주 반응을 확인한 뒤 편안할 때 시간·빈도 중 한 가지만 조금씩 조정하세요. 자동 증량은 하지 않습니다.'}
