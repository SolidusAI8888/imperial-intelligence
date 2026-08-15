import pytest
from pydantic import ValidationError

from runtime.contracts.consultation import (
    ConsultationOutput,
    DecisionOwnership,
    ExperienceMatch,
    HistoricalReflection,
    ModernTransfer,
    ReferenceAdvice,
)


def _valid_reflection() -> HistoricalReflection:
    return HistoricalReflection(
        has_comparable_experience=True,
        experience_matches=[
            ExperienceMatch(
                experience_id="EXP-TTZ-0001",
                title="任用旧敌并接受直谏",
                similarity_reasons=["都涉及是否继续信任一个存在风险但有能力的人"],
                important_differences=["现代私人关系与君臣政治关系不同"],
                evidence_ids=["EVD-TTZ-0001"],
                confidence=0.82,
            )
        ],
        historical_context=["人物曾面对是否重用、信任并约束有独立立场之人的问题。"],
        what_i_considered=["能力是否真实可用，以及风险是否可以通过规则和观察来控制。"],
        what_i_did=["在保留判断和约束的同时继续使用其能力。"],
        historical_results=["获得了有价值的意见，同时也证明信任需要边界和持续判断。"],
        lessons_learned=["信任不等于取消边界，能力与风险应当同时评估。"],
    )


def test_consultation_output_keeps_final_decision_with_user() -> None:
    output = ConsultationOutput(
        persona_id="tang_taizong",
        stage_id="zhenguan_15",
        user_question="我是否应该继续信任背叛过我的伴侣？",
        historical_reflection=_valid_reflection(),
        modern_transfer=ModernTransfer(
            similarities=["都涉及信任受损后的继续合作或关系维持"],
            differences=["亲密关系不是君臣关系，现代个人权利与情感边界不同"],
            transferable_principles=["重新建立信任需要证据、边界和观察期"],
            non_transferable_elements=["古代权力处置方式"],
            modern_risks=["不能用政治控制逻辑替代亲密关系中的平等与安全"],
        ),
        reference_advice=ReferenceAdvice(
            if_i_were_you="我不会只凭一次道歉恢复全部信任，而会先看事实、边界和后续行为。",
            suggested_actions=["确认事实", "明确底线", "设置观察期"],
            questions_for_self_reflection=["你真正不能接受的是什么？"],
            correction_or_exit_plan=["若再次违反核心边界，应准备结束关系"],
            confidence=0.75,
        ),
    )

    assert output.decision_ownership.final_decision_owner == "user"
    assert output.decision_ownership.purpose == "reference_and_inspiration"


def test_comparable_experience_requires_verified_match() -> None:
    with pytest.raises(ValidationError):
        HistoricalReflection(
            has_comparable_experience=True,
            experience_matches=[],
            what_i_considered=["placeholder"],
            what_i_did=["placeholder"],
            historical_results=["placeholder"],
            lessons_learned=["placeholder"],
        )


def test_reference_advice_requires_historical_reasoning_action_result_and_lesson() -> None:
    with pytest.raises(ValidationError):
        ConsultationOutput(
            persona_id="tang_taizong",
            stage_id="zhenguan_15",
            user_question="我该辞职吗？",
            historical_reflection=HistoricalReflection(
                has_comparable_experience=True,
                experience_matches=[
                    ExperienceMatch(
                        experience_id="EXP-TTZ-0002",
                        title="某可比经验",
                        confidence=0.6,
                    )
                ],
                historical_context=["有可比历史背景"],
                # intentionally missing reasoning/action/result/lesson
            ),
            modern_transfer=ModernTransfer(),
            reference_advice=ReferenceAdvice(
                if_i_were_you="我会辞职。",
                confidence=0.4,
            ),
        )


def test_no_comparable_experience_is_allowed_without_invention() -> None:
    output = ConsultationOutput(
        persona_id="tang_taizong",
        stage_id="zhenguan_15",
        user_question="我该选择哪种云计算架构？",
        historical_reflection=HistoricalReflection(
            has_comparable_experience=False,
            experience_matches=[],
            uncertainty_notes=[
                "该问题缺乏足够接近且可验证的人生经验，不能假装存在直接历史先例。"
            ],
        ),
        modern_transfer=ModernTransfer(
            differences=["这是现代专业技术问题"],
            non_transferable_elements=["具体技术选型"],
        ),
        reference_advice=ReferenceAdvice(
            if_i_were_you=(
                "我只能从一般决策习惯提醒你比较目标、风险和可逆性；"
                "具体技术选择应依赖现代专业知识。"
            ),
            confidence=0.2,
        ),
        decision_ownership=DecisionOwnership(),
    )

    assert output.historical_reflection.has_comparable_experience is False
    assert output.reference_advice.confidence == 0.2
