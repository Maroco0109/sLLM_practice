"""FastAPI backend app for local development.

KO: 로컬 개발을 위한 최소 FastAPI 애플리케이션입니다.
- 제공 엔드포인트: `GET /health` -> `{"status": "ok"}` 헬스체크 응답을 반환합니다.
- 개발 실행 예시: `uvicorn backend.api.app:app --reload --port 8000`
"""

from fastapi import FastAPI

app = FastAPI(title="sLLM-KR Backend")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple health payload."""
    return {"status": "ok"}
