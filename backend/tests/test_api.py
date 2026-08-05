from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_emperors() -> None:
    response = client.get("/emperors")
    assert response.status_code == 200
    data = response.json()
    assert any(item["emperor_id"] == "tang_taizong" for item in data)


def test_consultation_prototype() -> None:
    response = client.post(
        "/emperors/tang_taizong/consult",
        json={"question": "我是否应该与别人合伙创业？"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["emperor_id"] == "tang_taizong"
    assert data["status"] == "prototype"
    assert "avatar_directive" in data
