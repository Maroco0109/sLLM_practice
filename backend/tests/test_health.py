"""Backend health endpoint test.

KO: FastAPI 앱의 `/health` 엔드포인트가 200 OK와 `{ "status": "ok" }`
페이로드를 반환하는지 검증합니다. 테스트 클라이언트는 `TestClient`를 사용합니다.
"""

from fastapi.testclient import TestClient

from backend.api.app import app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
