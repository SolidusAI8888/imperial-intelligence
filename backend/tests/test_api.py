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


def test_first_question_returns_evidence_grounded_answer() -> None:
    response = client.post(
        "/emperors/tang_taizong/consult",
        json={"question": "面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "evidence_grounded"
    assert data["emperor_stage_id"] == "full_lifetime"
    assert "人不能主宰全部命运" in data["imperial_advice"]
    assert len(data["reasoning"]) == 3
    assert data["modern_translation"].startswith("【现代转译】")

    evidence = {item["evidence_id"]: item["source_id"] for item in data["evidence"]}
    assert evidence["CN-TANG-0001-V002-P0004"] == "CN-TANG-0001"
    assert evidence["CN-TANG-0002-V002-P0004"] == "CN-TANG-0002"
    assert evidence["CN-TANG-0004-V001-P0003"] == "CN-TANG-0004"
