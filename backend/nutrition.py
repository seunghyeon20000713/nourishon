def calculate_nutrient(per_100g: float, intake_g: float) -> float:
    """100g당 영양성분과 섭취량(g)으로 실제 섭취한 양을 계산한다."""
    if per_100g < 0 or intake_g < 0:
        raise ValueError("100g당 영양성분과 섭취량은 0 이상이어야 합니다.")
    return per_100g * (intake_g / 100)
