from app.models.api import (
    AvatarDirective,
    ConsultationRequest,
    ConsultationResponse,
    EvidenceReference,
)
from app.services.answer_pipeline import FIRST_PROBLEM_ID, generate_first_question_answer
from app.services.persona_repository import PersonaRepository


class ConsultationService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    @staticmethod
    def _is_first_fate_question(question: str) -> bool:
        normalized = "".join(question.split())
        return "命运" in normalized and ("主宰" in normalized or "谁决定" in normalized)

    def consult(
        self,
        emperor_id: str,
        request: ConsultationRequest,
    ) -> ConsultationResponse:
        package = self.repository.get_persona_package(emperor_id) or {}
        manifest = package.get("manifest", {})
        default_stage = manifest.get("default_stage_id", "unknown")

        if emperor_id == "tang_taizong" and self._is_first_fate_question(request.question):
            grounded = generate_first_question_answer(request.question)
            return ConsultationResponse(
                emperor_id=emperor_id,
                emperor_stage_id="full_lifetime",
                imperial_advice=grounded.answer,
                reasoning=grounded.reasoning,
                historical_analogy=(
                    "本回答以唐太宗在贞观时期关于草创与守成、兼听与偏信、"
                    "纳谏与克终风险的已审核历史记录为经验基础。"
                ),
                modern_translation=(
                    "无法控制全部时代条件时，仍可通过持续选择、获取真实反馈、"
                    "修正错误和在成功后保持警惕来扩大自己能够影响的部分。"
                ),
                cautions=grounded.cautions,
                evidence=[
                    EvidenceReference(
                        evidence_id=canonical_id,
                        source_id="CN-TANG-0004",
                        summary=f"{FIRST_PROBLEM_ID} grounded canonical evidence",
                        confidence=0.95,
                    )
                    for canonical_id in grounded.evidence_ids
                ],
                overall_confidence=0.88,
                avatar_directive=AvatarDirective(
                    listening_state="attentive_still",
                    thinking_action="lower_gaze_review_memorial",
                    speaking_style="calm_measured_authoritative",
                    emotion="reflective_composed",
                ),
                status="evidence_grounded",
            )

        # Prototype fallback for questions not yet connected to reviewed knowledge.
        return ConsultationResponse(
            emperor_id=emperor_id,
            emperor_stage_id=request.emperor_stage_id or default_stage,
            imperial_advice=(
                "此问题尚需先辨明目标、可用之人、可承受之失，以及一旦判断错误的退路。"
                "在事实未明之前，不宜只凭一时好恶决断。"
            ),
            reasoning=[
                "先确认真正目标，而非只处理表面困扰。",
                "同时寻找支持与反对当前判断的证据。",
                "评估人才、制度与执行条件是否匹配。",
                "保留纠错和退出机制。",
            ],
            historical_analogy=(
                "当前问题尚未接入对应的审核知识链；只有通过 Source Corpus → HER → HEU → Insight"
                " 的内容才能进入 evidence-grounded 回答。"
            ),
            modern_translation=(
                "把重大选择拆成目标、信息、人员、制度、风险和复盘六个部分，"
                "不要只凭直觉做不可逆决定。"
            ),
            cautions=[
                "当前为结构验证版本，不应视为完成的历史人格结论。",
                "历史帝王的治理经验不能直接替代现代法律、伦理和专业意见。",
            ],
            evidence=[
                EvidenceReference(
                    evidence_id="EVD-TTZ-PLACEHOLDER-001",
                    source_id="SRC-PLACEHOLDER",
                    summary="该问题尚未接入审核后的知识链。",
                    confidence=0.1,
                )
            ],
            overall_confidence=0.1,
            avatar_directive=AvatarDirective(
                listening_state="attentive_still",
                thinking_action="lower_gaze_review_memorial",
                speaking_style="calm_measured_authoritative",
                emotion="composed",
            ),
            status="prototype",
        )
