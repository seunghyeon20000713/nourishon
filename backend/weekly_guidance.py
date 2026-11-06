"""최근 7일 기록을 묶은 일반 성인 실천 안내. 진단·보상 운동량 산출 제외."""
from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.accounts import Measurement
from backend.activity_log import ActivityRecord, ACTIVITIES, calculate_activity
from backend.exercise import ExerciseInput, plan_exercise
from backend.nutrition_review import ReviewFood, ReviewInput, ReviewMeal, review_nutrition
from backend.profile import ProfileInput
from backend.references import DIET_SOURCE, ACTIVITY_SOURCE, KDRI_SOURCE, checked_sources


def today():
    return datetime.now(timezone(timedelta(hours=9))).date()


class DatedMeal(BaseModel):
    id: Annotated[str, Field(min_length=1, max_length=100)]
    date: date
    foods: Annotated[list[ReviewFood], Field(max_length=100)] | None = None


class WeeklyInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    end: date = Field(default_factory=today)
    profile: ProfileInput | None = None
    meals: Annotated[list[DatedMeal], Field(max_length=700)] = Field(default_factory=list)
    measurements: Annotated[list[Measurement], Field(max_length=1000)] = Field(default_factory=list)
    activities: Annotated[list[ActivityRecord], Field(max_length=2000)] = Field(default_factory=list)
    exercise_input: ExerciseInput | None = None

    @model_validator(mode='after')
    def check_window(self):
        if self.end > today() or self.end < date(1900, 1, 7):
            raise ValueError('조회 날짜를 확인하세요.')
        for rows in (self.meals, self.measurements, self.activities):
            if len({row.id for row in rows}) != len(rows):
                raise ValueError('중복 기록')
        return self


def weekly_guidance(request: WeeklyInput):
    start = request.end - timedelta(days=6)
    meals = [row for row in request.meals if start <= row.date <= request.end]
    measurements = sorted([row for row in request.measurements if start <= row.measured_on <= request.end], key=lambda row: row.measured_on)
    activities = [row for row in request.activities if start <= row.date <= request.end]
    days = sorted({row.date for row in meals})
    reports = []
    legacy = sum(not row.foods for row in meals)
    for day in days:
        entries = [ReviewMeal(foods=row.foods) for row in meals if row.date == day and row.foods]
        if entries:
            # 하루 100끼를 넘는 자료는 명시적으로 보류한다.
            if len(entries) > 100:
                raise ValueError('하루 기록 범위 초과')
            reports.append((day, review_nutrition(ReviewInput(meals=entries))))
    sodium_days = [day.isoformat() for day, report in reports if report['totals']['sodium']['value'] is not None and report['totals']['sodium']['value'] >= 2000]
    protein_days = [day.isoformat() for day, report in reports if not any(row.date == day and not row.foods for row in meals) and any(item['key'] == 'protein' and item['comparison'] == '범위보다 낮음' for item in report['macros'])]
    changes = []
    for key, label, unit in [('weight_kg', '체중', 'kg'), ('skeletal_muscle_kg', '골격근량', 'kg'), ('fat_mass_kg', '체지방량', 'kg'), ('body_fat_percent', '체지방률', '%p')]:
        values = [row for row in measurements if getattr(row, key) is not None]
        first, last = (values[0], values[-1]) if values else (None, None)
        comparable = first is not None and first.measured_on != last.measured_on
        changes.append({'key': key, 'label': label, 'unit': unit,
                        'first_date': first.measured_on.isoformat() if first else None,
                        'last_date': last.measured_on.isoformat() if last else None,
                        'first': getattr(first, key) if first else None, 'last': getattr(last, key) if last else None,
                        'difference': round(getattr(last, key)-getattr(first, key), 2) if comparable else None})
    minutes = sum(row.minutes for row in activities)
    aerobic = [row for row in activities if ACTIVITIES[row.activity_code]['category'] in {'걷기', '러닝', '자전거', '유산소 기구'}]
    strength_days = {row.date for row in activities if ACTIVITIES[row.activity_code]['category'] == '근력·맨몸' and row.minutes > 0}
    recommendations = []
    def add(key, title, action, reason):
        recommendations.append({'id': key, 'title': title, 'action': action, 'reason': reason})
    plan = None
    if request.profile and request.exercise_input:
        plan = plan_exercise(request.profile, request.exercise_input)
    if plan and plan['status'] == 'needs_assessment':
        add('assessment', '운동 제한부터 확인하세요', plan['message'], '현재 입력에 증상·부상·운동 제한이 포함되어 있어 자동 운동 시간 제안을 보류합니다.')
    if not meals or legacy:
        add('food_records', '식사 기록부터 확인해요', '최근 7일의 먹은 음식과 실제 섭취량을 기록하고, 식품별 정보가 없는 이전 기록은 확인해주세요.', f'식사 {len(meals)}건·기록일 {len(days)}일, 상세 검토할 식품 정보가 없는 기록 {legacy}건입니다. 미기록을 0 또는 부족으로 판단하지 않습니다.')
    if sodium_days:
        add('sodium', '다음 한 끼의 국물·소스를 살펴보세요', '국물·소스는 따로 두고 사용량을 조절하거나, 영양표시의 나트륨을 비교해보세요.', f'기록 중 {len(sodium_days)}일은 확인된 나트륨만으로 성인 하루 참고 기준인 2,000mg 이상입니다. 누락값을 0으로 채우지 않았습니다.')
    elif meals:
        add('variety', '다음 한 끼에 식품 구성을 점검해요', '채소·통곡물·콩류와 다양한 단백질 급원을 함께 살펴보세요.', '최근 식사 기록을 바탕으로 일반적인 식품 다양성 실천을 안내합니다. 결핍 여부·알레르기·가격·재고를 확인한 개별 음식 추천은 아닙니다.')
    if len(protein_days) >= 2:
        add('protein', '단백질 급원을 함께 살펴보세요', '다음 식사에 생선·달걀·두부·콩류 등 단백질 급원을 포함할지 살펴보세요.', f'비교 가능한 기록 중 {len(protein_days)}일의 단백질 에너지 비율이 참고 범위보다 낮았습니다. 이는 하루 단백질 부족 진단이 아닙니다.')
    if plan and plan['status'] == 'draft':
        active = [row for row in plan['schedule'] if not row['rest']]
        add('activity', '현재 여건에 맞춰 활동을 이어가세요', f'입력 조건으로 만든 시작 초안은 주 {len(active)}일, 활동일마다 {active[0]["total_minutes"]}분입니다. 운동 계획에서 준비·정리·근력 배분을 확인하세요.', f'최근 기록은 총 {minutes:g}분, 그중 걷기·러닝·자전거·기구 {sum(row.minutes for row in aerobic):g}분입니다. 시간 초안은 본인이 입력한 현재 주간 유산소 {request.exercise_input.current_weekly_minutes}분과 가능 시간·경험으로 산출합니다. 미기록 활동을 추정하거나 기록 때문에 자동 증량하지 않습니다.')
    elif not plan:
        add('activity_input', '운동 가능 조건을 먼저 알려주세요', '내 정보와 운동 계획에서 현재 활동량·가능 일수·시간·운동 제한을 확인해주세요.', f'최근 실제 운동 기록은 {len(activities)}건입니다. BMI·인바디·섭취 열량만으로 필요한 운동 시간을 계산하지 않습니다.')
    if not any(row['difference'] is not None for row in changes):
        add('body_records', '같은 조건에서 신체 변화를 기록해요', '체중·선택 체성분을 서로 다른 날짜에 비슷한 조건으로 기록해보세요.', '이 7일 안에 같은 항목을 비교할 서로 다른 날짜의 측정이 충분하지 않습니다. 기록을 위해 잦은 측정을 요구하는 것은 아닙니다.')
    goal = {'maintain':'유지', 'lose':'감량', 'gain':'증량'}.get(request.profile.goal if request.profile else None, '미등록')
    return {'rules_version':'combined-weekly-guidance-v1', 'start':start.isoformat(), 'end':request.end.isoformat(),
            'scope':'최근 7일의 등록 기록과 현재 입력 조건을 연결한 일반 성인 실천 안내입니다. 개인 치료·운동 처방이 아닙니다.',
            'goal':goal, 'coverage':{'meal_records':len(meals), 'meal_days':len(days), 'reviewed_days':len(reports), 'legacy_meals':legacy, 'measurement_records':len(measurements), 'activity_records':len(activities)},
            'nutrition':{'sodium_reference_days':sodium_days,'low_protein_ratio_days':protein_days},
            'body_changes':changes, 'activity':{'recorded_minutes':minutes, 'aerobic_activity_minutes':sum(row.minutes for row in aerobic), 'strength_recorded_days':len(strength_days), 'gross_kcal':round(sum(calculate_activity(row)['calculation']['gross_kcal'] for row in activities),2), 'plan_status':plan['status'] if plan else 'needs_input'},
            'recommendations':recommendations,
            'limitations':['일부 기록으로 실제 하루 섭취·소모량이나 영양 결핍을 판단하지 않습니다.', '기록된 활동 시간·근력 포함일 수는 WHO 권고 충족 판정이 아닙니다.', '체중·체성분의 차이를 식사·운동의 효과로 단정하거나 이 차이로 운동량을 자동 조정하지 않습니다.', '총당류로 혈당을 예측하지 않고 음식 열량을 상쇄할 필수 운동 시간·남은 권장 열량을 산출하지 않습니다.'],
            'sources':checked_sources([{'title':'2025 한국인 기준 · 에너지 적정비율','url':KDRI_SOURCE},{'title':'WHO Healthy diet','url':DIET_SOURCE},{'title':'WHO 2020 신체활동 지침','url':ACTIVITY_SOURCE}])}
