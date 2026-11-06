"""로컬 음식 계산·회원·개인 기록 API. 외부 공개용 설정은 별도 단계."""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
import psycopg
from backend.accounts import router as account_router
from backend.database import database_url as read_database_url
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from backend.food_search import _normalize_name
from backend.meal import calculate_meal
from backend.profile import ProfileInput, estimate_profile


DEFAULT_DATA = (Path(__file__).resolve().parents[1] / "data/processed"
                / "mfds-api-full-normalized-20261105/foods.json")
FoodCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class MealEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    food_code: FoodCode
    intake_g: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]


class MealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entries: Annotated[list[MealEntry], Field(min_length=1, max_length=100)]


class FoodSummary(BaseModel):
    food_code: str
    food_name: str
    basis: str
    source_name: str | None
    reference_date: str | None
    updated_date: str | None


class SearchResult(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[FoodSummary]


class FoodCatalog:
    def __init__(self, rows: list[dict]):
        if not isinstance(rows, list) or not rows:
            raise ValueError("비어 있지 않은 식품 목록이 필요합니다.")
        self.rows = rows
        self.by_code = {}
        self.names = []
        for index, row in enumerate(rows, 1):
            code = row["FOOD_CD"]
            if not code or code in self.by_code or row["NUT_CON_SRTR_QUA"] != "100g":
                raise ValueError("식품코드 또는 기준량이 잘못됐습니다.")
            self.by_code[code] = (index, row)
            self.names.append(_normalize_name(row["FOOD_NM"]))

    def search(self, query: str, offset: int, limit: int) -> dict:
        keyword = _normalize_name(query)
        if not keyword:
            raise ValueError("검색어를 입력해주세요.")
        items, total = [], 0
        for row, name in zip(self.rows, self.names):
            if keyword not in name:
                continue
            if offset <= total < offset + limit:
                items.append({"food_code": row["FOOD_CD"], "food_name": row["FOOD_NM"],
                              "basis": "100g", "source_name": row["SRC_NM"],
                              "reference_date": row["CRTR_YMD"],
                              "updated_date": row.get("UPDATE_DATE")})
            total += 1
        return {"total": total, "offset": offset, "limit": limit, "items": items}

    def meal(self, entries: list[dict]) -> dict:
        selected = {}
        for entry in entries:
            code = entry["food_code"]
            if code not in self.by_code:
                raise LookupError("해당 식품코드가 없습니다.")
            selected[code] = self.by_code[code][1]
        result = calculate_meal(list(selected.values()), entries)
        for food in result["foods"]:
            food["source_row_number"] = self.by_code[food["food_code"]][0]
        return result


def create_app(data_path: Path = DEFAULT_DATA, rows: list[dict] | None = None, database_url: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            if rows is None:
                report = json.loads(data_path.with_name("report.json").read_text(encoding="utf-8"))
                if report.get("status") != "completed":
                    raise ValueError
                loaded = json.loads(data_path.read_text(encoding="utf-8"))
                if len(loaded) != report["output_count"]:
                    raise ValueError
            else:
                loaded = rows
            app.state.catalog = FoodCatalog(loaded)
        except (OSError, ValueError, TypeError, LookupError):
            raise RuntimeError("완료된 로컬 정제 데이터가 필요합니다. 전체 정제를 먼저 실행하세요.") from None
        yield
        del app.state.catalog

    app = FastAPI(title="NourishOn 로컬 API", version="0.1.0", lifespan=lifespan,
                  description="로컬 개발용입니다. 로그인 후 개인 기록을 PostgreSQL에 저장합니다.")

    app.state.database_url = database_url if database_url is not None else (read_database_url() if rows is None else None)
    app.include_router(account_router)

    @app.middleware("http")
    async def private_response(request, call_next):
        private = request.url.path.startswith(("/auth/", "/account/"))
        if private and request.method in {"POST", "PUT", "PATCH"}:
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 2_000_000:
                    return JSONResponse(status_code=413, content={"detail": "한 번에 저장할 기록이 너무 많습니다."}, headers={"Cache-Control":"no-store"})
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        if private:
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(psycopg.Error)
    async def database_error(request, error):
        return JSONResponse(status_code=503, content={"detail": "DB 연결·저장 상태를 확인하세요. 입력 내용은 오류 응답에 포함하지 않습니다."}, headers={"Cache-Control":"no-store"})

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, error):
        # 기본 검증 오류에 포함될 수 있는 입력 본문을 응답에 복사하지 않는다.
        return JSONResponse(status_code=422, content={"detail": "입력 형식·범위·필수 항목을 확인하세요."})

    @app.get("/health", summary="서버와 로컬 데이터 상태 확인")
    def health():
        return {"status": "ok", "food_count": len(app.state.catalog.rows), "mode": "local_authenticated" if app.state.database_url else "local_single_user"}

    @app.get("/foods", response_model=SearchResult, summary="음식명 부분 검색")
    def foods(q: Annotated[str, Query(min_length=1, max_length=100)],
              offset: Annotated[int, Query(ge=0)] = 0,
              limit: Annotated[int, Query(ge=1, le=100)] = 20):
        try:
            return app.state.catalog.search(q, offset, limit)
        except ValueError:
            raise HTTPException(422, "검색어를 입력해주세요.") from None

    @app.post("/meals/calculate", summary="음식별 섭취량으로 한 끼 영양 합계 계산")
    def meal(payload: MealRequest):
        try:
            return app.state.catalog.meal([entry.model_dump() for entry in payload.entries])
        except LookupError:
            raise HTTPException(404, "해당 식품코드가 없습니다.") from None
        except (ValueError, TypeError, OverflowError):
            raise HTTPException(422, "계산할 수 없는 입력입니다.") from None

    @app.post("/profile/estimate", summary="일반 성인 프로필의 BMI·추정 유지 에너지·참고 기준")
    def profile(payload: ProfileInput):
        try:
            return estimate_profile(payload)
        except ValueError:
            raise HTTPException(422, "프로필 값과 적용 범위를 확인하세요.") from None

    return app


app = create_app()
