"""기록된 식사 스냅샷의 영양 구성 검토. 결핍 진단·점수화·자동 식단 처방 제외."""
import math
from backend.references import checked_sources
from typing import Annotated, Literal
from pydantic import BaseModel, Field, StringConstraints, model_validator
from backend.profile import ProfileInput, KDRI_SOURCE, DIET_SOURCE, estimate_profile

UNITS={'energy':'kcal','protein':'g','fat':'g','carbohydrate':'g','sugar':'g','fiber':'g','sodium':'mg'}
Number=Annotated[float,Field(strict=True,ge=0,allow_inf_nan=False)]

class ConsumedNutrient(BaseModel):
    unit: Literal['g','mg','kcal']
    consumed: Number | None

class ReviewFood(BaseModel):
    food_name: Annotated[str,StringConstraints(min_length=1,max_length=300)]
    nutrients: dict[str,ConsumedNutrient]

    @model_validator(mode='after')
    def units(self):
        if any(key not in UNITS or n.unit!=UNITS[key] for key,n in self.nutrients.items()):
            raise ValueError('성분별 단위를 확인하세요.')
        return self

class ReviewMeal(BaseModel):
    foods: Annotated[list[ReviewFood],Field(min_length=1,max_length=100)]

class ReviewInput(BaseModel):
    meals: Annotated[list[ReviewMeal],Field(max_length=100)]
    profile: ProfileInput | None = None


def review_nutrition(request: ReviewInput) -> dict:
    foods=[f for m in request.meals for f in m.foods]
    totals={}
    for key,unit in UNITS.items():
        values=[f.nutrients[key].consumed for f in foods if key in f.nutrients and f.nutrients[key].consumed is not None]
        value=math.fsum(values) if values else None
        if value is not None and not math.isfinite(value):
            raise ValueError('합계 범위 초과')
        totals[key]={'value':value,'unit':unit,'missing':len(foods)-len(values)}
    result={'scope':'기록된 식사만 검토 · 하루 전체 섭취 평가나 결핍 진단이 아닙니다.',
            'recorded_meals':len(request.meals),'totals':totals,'macros':[],
            'macro_status':'no_records','macro_message':'식사를 기록하면 영양 구성을 확인할 수 있습니다.',
            'sodium_contributors':[], 'actions':[],
            'sources':checked_sources([{'title':'2025 한국인 기준 · 에너지 적정비율','url':KDRI_SOURCE},
                       {'title':'WHO Healthy diet · 일반 성인 참고','url':DIET_SOURCE}]),
            'sugar_note':'총당류 기록을 WHO 유리당 기준과 직접 비교하거나 혈당을 예측하지 않습니다.',
            'rules_version':'recorded-nutrition-review-v1'}
    if not foods:return result
    keys=('energy','carbohydrate','protein','fat')
    if any(totals[k]['missing'] or totals[k]['value'] is None for k in keys):
        result.update(macro_status='missing',macro_message='열량 또는 탄수화물·단백질·지방 정보가 누락되어 비율 평가를 보류합니다.')
    elif totals['energy']['value']==0:
        result.update(macro_status='zero_energy',macro_message='기록된 열량이 0kcal이므로 에너지 비율을 계산하지 않습니다.')
    else:
        energy=totals['energy']['value']
        macro_energy=sum(totals[k]['value']*factor for k,factor in [('carbohydrate',4),('protein',4),('fat',9)])
        discrepancy=abs(macro_energy-energy)/energy
        # 10%는 자료 불일치를 드러내기 위한 제품 보류 규칙이다. 영양학적 오류 판정 기준이 아니다.
        if discrepancy>0.10:
            result.update(macro_status='inconsistent',macro_message='표시 열량과 4·4·9 환산 열량의 차이가 10%를 넘어 비율 평가를 보류합니다. 식이섬유·유기산·성분 산출 방식 등도 영향을 줄 수 있습니다. 10%는 데이터 확인을 위한 서비스 규칙이며 공식 영양 판정 기준은 아닙니다.')
        else:
            result.update(macro_status='available',macro_message='등록된 식사 구성의 참고 비교입니다. 하루 적정성 판정이 아닙니다. 분모는 기록된 표시 열량이며 비율 합이 100%와 다를 수 있습니다.')
            for key,label,factor,low,high in [('carbohydrate','탄수화물',4,50,65),('protein','단백질',4,10,20),('fat','지방',9,15,30)]:
                ratio=totals[key]['value']*factor/energy*100
                result['macros'].append({'key':key,'label':label,'percent':round(ratio,1),'reference':[low,high],
                                         'comparison':'범위보다 낮음' if ratio<low else '범위보다 높음' if ratio>high else '참고 범위 안'})
    ranked=[]
    for f in foods:
        n=f.nutrients.get('sodium')
        if n and n.consumed is not None and n.consumed>0:
            ranked.append({'food_name':f.food_name,'sodium_mg':n.consumed})
    result['sodium_contributors']=sorted(ranked,key=lambda x:x['sodium_mg'],reverse=True)[:3]
    sodium=totals['sodium']['value']
    if sodium is not None and sodium>=2000:
        result['actions'].append('확인된 나트륨만으로 WHO 일반 성인 하루 참고 기준 2,000mg 미만에 도달했습니다. 다음 식사에서는 국물·소스를 따로 두고 사용량을 줄이는 방법을 고려해보세요.')
    if totals['fiber']['missing']:
        result['actions'].append('식이섬유 누락이 있어 적정 여부를 판단하지 않습니다. 다음 식사는 채소·콩류·통곡물 등 다양한 식품을 포함하는 방향으로 살펴보세요.')
    else:
        result['actions'].append('기록된 식이섬유 합계는 일반 성인 하루 참고값 25g과 함께 살펴볼 수 있지만, 일부 기록만으로 부족을 판단하지 않습니다.')
    protein=next((m for m in result['macros'] if m['key']=='protein'),None)
    if protein and protein['comparison']=='범위보다 낮음':
        result['actions'].append('등록된 식사의 단백질 에너지 비율이 참고 범위보다 낮습니다. 다음 식사에는 생선·달걀·두부·콩류 등 단백질 급원을 함께 살펴보세요. 하루 단백질 부족 판정은 아닙니다.')
    if request.profile:
        estimate=estimate_profile(request.profile)
        result['personal_reference']={'maintenance_kcal':estimate['maintenance_kcal'],'protein_reference_g':estimate['protein_reference_g'],
                                      'note':'유지 에너지 추정과 일반 성인 단백질 참고값입니다. 감량·증량 처방이나 남은 권장 섭취량이 아닙니다.'}
    return result
