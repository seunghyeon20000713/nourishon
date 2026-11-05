import math


def calculate_nutrient(per_100g: float, intake_g: float) -> float:
    """100g당 값과 섭취량(g)을 환산한다. 결과 단위는 영양성분 입력과 같다.

    일반 int/float만 허용하며 잘못된 형식은 TypeError,
    음수·비유한 값 또는 표현 범위를 넘는 계산은 ValueError로 거부한다.
    """
    values = []
    for name, value in (("per_100g", per_100g), ("intake_g", intake_g)):
        if type(value) not in (int, float):
            raise TypeError(f"{name}: 정수 또는 실수를 입력해야 합니다.")
        try:
            number = float(value)
        except OverflowError:
            raise ValueError(f"{name}: 계산 가능한 숫자 범위를 넘었습니다.") from None
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"{name}: 0 이상의 유한한 숫자를 입력해야 합니다.")
        values.append(number)

    result = values[0] * (values[1] / 100)
    if not math.isfinite(result):
        raise ValueError("계산 결과가 표현 가능한 숫자 범위를 넘었습니다.")
    return result
