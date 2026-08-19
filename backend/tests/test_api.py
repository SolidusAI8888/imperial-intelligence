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


def _history() -> list[dict[str, str]]:
    return [
        {"role": "user", "content": "面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？"},
        {"role": "assistant", "content": "人不能主宰全部命运，但可以对自己在命运中的每一次回应负责。"},
    ]


def _followup(question: str) -> dict:
    response = client.post(
        "/emperors/tang_taizong/consult",
        json={"question": question, "conversation_history": _history()},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "evidence_grounded"
    assert data["modern_translation"].startswith("【连续对话现代转译】")
    return data


def test_followup_challenges_tang_founder_claim_without_losing_grounding() -> None:
    data = _followup("你并不是唐朝开国皇帝，你有什么资格谈草创阶段？")
    assert "唐朝开国皇帝是高祖，不是朕" in data["imperial_advice"]
    assert "亲身参与的草创阶段" in data["imperial_advice"]
    assert "大唐开国之功说成一己所有" in data["imperial_advice"]


def test_followup_reframes_for_ordinary_job_seeker() -> None:
    data = _followup("我只是个普通人，我现在连工作都找不到，你跟我谈成功之后的守成有什么意义？")
    assert "确实答非所问" in data["imperial_advice"]
    assert "先不要拿成功者的标准要求自己" in data["imperial_advice"]
    assert "一次受挫自动变成对自己的终局判决" in data["imperial_advice"]


def test_followup_can_challenge_evidence_without_persona_anachronism() -> None:
    data = _followup("你说这些有什么史料依据？我怎么知道不是你编的？")
    assert "朕不该靠一句‘朕以为’便要你相信" in data["imperial_advice"]
    assert "不能证明‘只要肯选择就能控制命运’" in data["imperial_advice"]
    assert "《旧唐书》" not in data["imperial_advice"]
    assert "《新唐书》" not in data["imperial_advice"]
    assert data["evidence"]


def test_followup_accepts_challenge_that_tang_taizong_also_made_mistakes() -> None:
    data = _followup("你自己不也会犯错吗？你真的一直都能做到兼听？")
    assert "朕当然不能说自己从此无过" in data["imperial_advice"]
    assert "能修正错误，不等于不会再错" in data["imperial_advice"]


def test_followup_can_turn_first_question_into_small_next_step() -> None:
    data = _followup("道理我懂了，那我现在具体怎么办？下一步怎么做？")
    assert "先做小而可改的下一步" in data["imperial_advice"]
    assert "愿意说真话的人" in data["imperial_advice"]
    assert "不能替你决定人生" in data["imperial_advice"]


def test_followup_can_clarify_core_term_without_restarting_answer() -> None:
    data = _followup("你说的‘回应’到底是什么意思？我没听懂。")
    assert "‘回应’，不是说你能决定发生什么" in data["imperial_advice"]
    assert "它不是‘我想怎样，世界就怎样’" in data["imperial_advice"]


def test_auto_consult_screens_all_emperors_and_selects_best_grounded_role() -> None:
    response = client.post(
        "/consult/auto",
        json={"question": "面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["selected_emperor_id"] == "tang_taizong"
    assert len(data["screened_emperors"]) == 69
    assert sum(1 for item in data["screened_emperors"] if item["eligible"]) == 3
    assert any(item["emperor_id"] == "han_wudi" for item in data["screened_emperors"])
    assert any(item["emperor_id"] == "tang_xuanzong" for item in data["screened_emperors"])
    assert any(item["emperor_id"] == "song_renzong" for item in data["screened_emperors"])
    assert [item["dynasty"] for item in data["rankings"]] == ["tang", "han", "song"]
    assert data["rankings"][0]["score"] > data["rankings"][1]["score"]
    assert data["rankings"][1]["score"] > data["rankings"][2]["score"]
    assert all(item["rationale"] for item in data["rankings"])
    assert data["consultation"]["status"] == "evidence_grounded"
    assert data["consultation"]["emperor_id"] == "tang_taizong"


def test_auto_consult_rejects_question_without_reviewed_cross_dynasty_chain() -> None:
    response = client.post(
        "/consult/auto",
        json={"question": "我是否应该与别人合伙创业？"},
    )
    assert response.status_code == 422
