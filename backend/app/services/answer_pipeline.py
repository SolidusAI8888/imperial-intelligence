from __future__ import annotations

from dataclasses import dataclass

from app.models.knowledge import RuntimeContext
from app.services.knowledge_repository import (
    load_first_question_experiences,
    load_first_question_insights,
    load_first_question_records,
    load_first_question_role_links,
)
from app.services.knowledge_runtime import build_runtime_context, render_grounded_context


FIRST_PROBLEM_ID = "Q-FATE-AGENCY-001"
FIRST_QUESTION = "面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？"
FIRST_RESPONDER = "tang_taizong"


@dataclass(frozen=True)
class GroundedAnswer:
    problem_id: str
    person_id: str
    answer: str
    reasoning: list[str]
    cautions: list[str]
    evidence_ids: list[str]
    grounded_context: str


def build_first_question_context(question: str = FIRST_QUESTION) -> RuntimeContext:
    return build_runtime_context(
        problem_id=FIRST_PROBLEM_ID,
        question=question,
        person_id=FIRST_RESPONDER,
        records=load_first_question_records(),
        experiences=load_first_question_experiences(),
        insights=load_first_question_insights(),
        role_links=load_first_question_role_links(),
    )


def generate_first_question_answer(question: str = FIRST_QUESTION) -> GroundedAnswer:
    """Generate the first evidence-grounded Tang Taizong answer.

    The knowledge order is fixed:
    Source Corpus -> HER -> HEU -> Insight -> Role Link -> Answer.

    MVP-1 keeps a deterministic renderer so the vertical slice is fully
    reproducible without an external model provider. The renderer may express
    only what is already present in the reviewed context; broader modern
    generalization belongs in the API's modern_translation field instead.

    Persona voice must also obey historical perspective: the emperor may speak
    from the complete life course, but may not claim awareness of posthumous
    compilations such as the Old Book of Tang or New Book of Tang. Source names
    belong in metadata/evidence fields, not in first-person imperial speech.
    """

    context = build_first_question_context(question)
    heu_by_id = {heu.heu_id: heu for heu in context.experiences}

    heu_stage = heu_by_id["HEU-TANG-000001"]
    heu_feedback = heu_by_id["HEU-TANG-000002"]
    heu_success = heu_by_id["HEU-TANG-000003"]

    insight_stage = next(i for i in context.insights if i.insight_id == "INS-TANG-000001")
    insight_feedback = next(i for i in context.insights if i.insight_id == "INS-TANG-000002")

    answer = (
        "若问命运由谁主宰，朕不敢以一句天命，便把一生的成败都推给苍天；"
        "也不敢说只凭一己之力，便可尽制世事。朕少年逢隋末乱世，随军起兵。"
        "霍邑进军之前，久雨粮乏，高祖一度欲还太原。朕力争不可退：既以义举起兵，"
        "若因眼前之难便退，众心先散，敌军随后而至，成败便在顷刻之间。"
        "那时摆在朕面前的，不是什么玄远之论，只是进与退、聚与散、成与败。\n\n"
        "后来天下渐定，难处却并未随胜利而消失。贞观十年，朕问房玄龄、魏征："
        "草创与守成，孰难？玄龄言草创难，魏征言守成难。朕听罢说，草创之难已经过去，"
        "守成之难，当与诸公共同慎之。到了守成之时，外面的强敌未必是最可怕的；"
        "更须防的是居安之后渐生骄逸，自以为是，终于听不进逆耳之言。"
        "所以朕这一生所见，并不是‘成功一次，命运便定了’，而是所处之势一变，"
        "人便要重新认清眼前真正的难处。\n\n"
        "朕尤其不敢把自己的判断当成不可更改的定论。魏征劝朕兼听，不可偏信；"
        "又以‘善始者实繁，能克终者盖寡’相戒。朕答他说‘朕闻过矣’，并令其此后仍可‘犯而无隐’。"
        "这不是因为朕从此便不会犯错，而是因为一个居于高位的人若只听顺耳之言，"
        "连自己的错误都无从知道。能有人指出错误，自己又肯改，至少还能改变随后的一步。\n\n"
        "因此，若以朕一生的经历答你：时代与处境能把许多事情推到人面前，"
        "也能限制人当时可走的路；但人在这些限制之中，仍要一次次决定进退、听谁之言、"
        "是否改过，以及得意之后还能不能自持。朕不认为其中任何一项单独便能称为命运的主人。"
        "真正能由自己承担的，是每逢一事，如何回应。\n\n"
        "所以朕愿把话说得更谨慎些：人不能主宰全部命运，但可以对自己在命运中的每一次回应负责。"
        "处境变了，便重新察势；判断错了，便容人指出；一时得志，更须防自己先失其明。"
        "能做到这些，未必使人事事如愿，却能使自己不至于把本可挽回的路，亲手走绝。"
    )

    evidence_ids = sorted(
        {
            cid
            for record in context.records
            for source in record.sources
            for cid in source.canonical_ids
        }
    )

    reasoning = [
        (
            "阶段变化：早年创业记录与贞观时期的草创—守成讨论共同支持，"
            "唐太宗本人面对的风险会随处境变化，不能把过去有效的应对方式当作永久答案。"
        ),
        (
            "纠错机制：兼听、纳谏以及‘朕闻过矣’‘犯而无隐’的记录共同支持，"
            "个人判断并非天然可靠，持续获得真实反馈会改变后续选择。"
        ),
        (
            f"综合边界：{insight_stage.statement} {insight_feedback.statement} "
            "因此本回答只把‘持续选择与修正’视为个人能够影响命运的一部分，而不宣称个人可以控制全部外部条件。"
        ),
    ]

    cautions = [
        "本回答已使用《旧唐书》《新唐书》《贞观政要》的审核证据；《资治通鉴》相关交叉验证尚未纳入本题正式 HER。",
        "唐太宗的帝王治理经验不能直接等同于普通人的现代处境；回答正文只保留人物经历可支持的部分，现代迁移另行表达。",
    ]

    return GroundedAnswer(
        problem_id=context.problem_id,
        person_id=context.person_id,
        answer=answer,
        reasoning=reasoning,
        cautions=cautions,
        evidence_ids=evidence_ids,
        grounded_context=render_grounded_context(context),
    )
