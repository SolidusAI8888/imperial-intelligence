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

    @staticmethod
    def _source_id_from_canonical(canonical_id: str) -> str:
        return canonical_id.split("-V", 1)[0]

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
                    "本回答以《旧唐书》《新唐书》所载隋末至武德初经历，"
                    "以及《贞观政要》所载草创与守成、兼听与偏信、纳谏与克终风险等"
                    "已审核记录共同构成人物经验基础。"
                ),
                modern_translation=(
                    "【现代转译】外部环境会限制可选路径，但个人仍可管理其中一部分："
                    "重新判断处境、主动获取反对意见、在发现错误后调整，并在成功后继续防止信息失真。"
                    "这是从唐太宗经验中抽取的现代可迁移表达，不是史料原话。"
                ),
                cautions=grounded.cautions,
                evidence=[
                    EvidenceReference(
                        evidence_id=canonical_id,
                        source_id=self._source_id_from_canonical(canonical_id),
                        summary=f"{FIRST_PROBLEM_ID} grounded canonical evidence",
                        confidence=0.95,
                    )
                    for canonical_id in grounded.evidence_ids
                ],
                overall_confidence=0.9,
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
