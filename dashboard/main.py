"""
WKF Finance Dashboard
공시 및 LLM 분석 결과 대시보드
"""
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, date, timedelta
from typing import Optional
import logging

from config import settings
from database import DatabaseManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(title="WKF Finance Dashboard", version="1.0.0")

# Static 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 데이터베이스 매니저
db = DatabaseManager()


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
):
    """메인 대시보드 페이지"""
    try:
        # 날짜 파싱
        start_date_obj = None
        end_date_obj = None

        if start_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            # 기본: 오늘
            start_date_obj = date.today()
            start_date = start_date_obj.strftime("%Y-%m-%d")

        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            # 기본: 오늘
            end_date_obj = date.today()
            end_date = end_date_obj.strftime("%Y-%m-%d")

        # 데이터 조회
        disclosures = db.get_disclosures_by_date(start_date_obj, end_date_obj)

        # 각 공시별 분석 결과 조회
        for disclosure in disclosures:
            disclosure["analyses"] = db.get_analysis_results(disclosure["id"])
            disclosure["recommendations"] = db.get_stock_recommendations(
                disclosure["id"]
            )

            # 각 분석 결과별 거래 정보 조회
            for analysis in disclosure["analyses"]:
                analysis["holding"] = db.get_holdings_by_analysis(analysis["id"])

        # 통계 정보
        stats = db.get_recent_stats()
        performance = db.get_llm_performance_summary()

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "disclosures": disclosures,
                "stats": stats,
                "performance": performance,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

    except Exception as e:
        logger.error(f"Error in index route: {e}", exc_info=True)
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": str(e)},
            status_code=500,
        )


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    logger.info(
        f"Starting dashboard on {settings.DASHBOARD_HOST}:{settings.DASHBOARD_PORT}"
    )
    uvicorn.run(
        "main:app",
        host=settings.DASHBOARD_HOST,
        port=settings.DASHBOARD_PORT,
        reload=True,
    )
