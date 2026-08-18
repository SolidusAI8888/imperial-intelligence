import pytest
from pydantic import ValidationError

from backend.app.models.knowledge import (
    HistoricalExperienceUnit,
    HistoricalRecord,
    Insight,
    RoleExperienceLink,
    SourceReference,
)
from backend.app.services.knowledge_runtime import build_runtime_context, render_grounded_context


def _record(record_id: str = "HER-TANG-000001") -> HistoricalRecord:
    return HistoricalRecord(
        record_id=record_id,
        research_id="R-000001",
        title="贞观十年：唐太宗与房玄龄、魏征论草创与守成",
        record_type="discussion",
        dynasty="Tang",
        time_label="贞观十年",
        participants=["tang_taizong", "fang_xuanling", "wei_zheng"],
        historical_record="唐太宗问草创与守成孰难；房玄龄言草创难，魏征言守成难，太宗表示今后当慎守成。",
        sources=[
            SourceReference(
                source_id="CN-TANG-0004",
                canonical_ids=["CN-TANG-0004-V001-P0003"],
            )
        ],
        supported_claims=["唐太宗主动提出草创与守成之问。"],
        unsupported_claims=["唐太宗此后从未在守成问题上失误。"],
        derived_from_candidate_evidence_ids=["CAND-R000001-0001"],
        status="reviewed",
    )


def _heu() -> HistoricalExperienceUnit:
    return HistoricalExperienceUnit(
        heu_id="HEU-TANG-000001",
        research_id="R-000001",
        title="从草创转入守成后重新识别风险",
        experience_owner="tang_taizong",
        record_links=["HER-TANG-000001"],
        challenge="取得阶段性成功后，如何认识新的风险与约束。",
        response_or_choice=["接受房玄龄与魏征从不同阶段提出的判断。", "明确把注意力转向守成风险。"],
        experienced_outcome=["形成了对草创与守成阶段差异的明确认识。"],
        explicit_reflection=["今草创之难既已往矣，守成之难者，当思与公等慎之。"],
        interpretation=["处境改变后，需要重新判断风险，而不能沿用创业期的成功经验。"],
        source_references=[
            SourceReference(
                source_id="CN-TANG-0004",
                canonical_ids=["CN-TANG-0004-V001-P0003"],
            )
        ],
        status="reviewed",
    )


def _insight() -> Insight:
    return Insight(
        insight_id="INS-FATE-000001",
        research_id="R-000001",
        statement="人的选择空间会随处境变化；过去有效的行动方式不能被当作永久答案。",
        derived_from_heus=["HEU-TANG-000001"],
        applies_when=["个人已经从高不确定环境进入相对稳定阶段。"],
        limits=["该洞见不能推出个人可以控制所有结构性条件。"],
        status="draft",
    )


def _role_link() -> RoleExperienceLink:
    return RoleExperienceLink(
        person_id="tang_taizong",
        heu_id="HEU-TANG-000001",
        relation="experience_owner",
        responder_eligible=True,
        personal_experience_strength="primary",
        life_course_rule="full_lifetime",
    )


def test_runtime_context_builds_complete_chain() -> None:
    context = build_runtime_context(
        problem_id="Q-FATE-AGENCY-001",
        question="面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？",
        person_id="tang_taizong",
        records=[_record()],
        experiences=[_heu()],
        insights=[_insight()],
        role_links=[_role_link()],
    )

    assert context.life_course_rule == "full_lifetime"
    rendered = render_grounded_context(context)
    assert "CN-TANG-0004-V001-P0003" in rendered
    assert "HEU-TANG-000001" in rendered
    assert "INS-FATE-000001" in rendered
    assert "Do not invent motives" in rendered


def test_runtime_rejects_missing_record_link() -> None:
    heu = _heu().model_copy(update={"record_links": ["HER-TANG-DOES-NOT-EXIST"]})

    with pytest.raises(ValidationError, match="references missing HER records"):
        build_runtime_context(
            problem_id="Q-FATE-AGENCY-001",
            question="test",
            person_id="tang_taizong",
            records=[_record()],
            experiences=[heu],
            insights=[_insight()],
            role_links=[_role_link()],
        )


def test_runtime_rejects_insight_without_present_heu() -> None:
    insight = _insight().model_copy(update={"derived_from_heus": ["HEU-TANG-MISSING"]})

    with pytest.raises(ValidationError, match="references missing HEUs"):
        build_runtime_context(
            problem_id="Q-FATE-AGENCY-001",
            question="test",
            person_id="tang_taizong",
            records=[_record()],
            experiences=[_heu()],
            insights=[insight],
            role_links=[_role_link()],
        )


def test_runtime_rejects_responder_without_eligible_personal_link() -> None:
    ineligible = _role_link().model_copy(update={"responder_eligible": False})

    with pytest.raises(ValidationError, match="Selected responder must have"):
        build_runtime_context(
            problem_id="Q-FATE-AGENCY-001",
            question="test",
            person_id="tang_taizong",
            records=[_record()],
            experiences=[_heu()],
            insights=[_insight()],
            role_links=[ineligible],
        )
