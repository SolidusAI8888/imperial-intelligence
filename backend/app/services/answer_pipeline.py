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

    MVP-1 intentionally uses a deterministic renderer so the end-to-end chain
    remains runnable without an external model provider. The knowledge order is
    never reversed: Source Corpus -> HER -> HEU -> Insight -> Role Link -> Answer.
    A later LLM renderer may replace only this final rendering step.
    """

    context = build_first_question_context(question)

    record_by_id = {record.record_id: record for record in context.records}
    heu_by_id = {heu.heu_id: heu for heu in context.experiences}

    heu_stage = heu_by_id["HEU-TANG-000001"]
    heu_feedback = heu_by_id["HEU-TANG-000002"]
    heu_success = heu_by_id["HEU-TANG-000003"]

    insight_stage = next(i for i in context.insights if i.insight_id == "INS-TANG-000001")
    insight_feedback = next(i for i in context.insights if i.insight_id == "INS-TANG-000002")

    answer = (
        "若以我一生所历来答，我不会说命运只由天、只由时代，或只由自己主宰。"
        "我亲历草创，也亲历守成。贞观十年，我问房玄龄、魏征草创与守成孰难；"
        "我后来承认，草创之难虽已过去，守成之难却必须与群臣共同谨慎面对。"
        "这使我明白：处境一变，人的难题也会变。乱世时，外部竞争逼人决断；"
        "安定之后，真正危险的反而可能是自己的骄逸、懈怠和听不进逆耳之言。\n\n"
        "所以，时代确实给每个人划出边界。你不能选择自己出生在盛世还是乱世，"
        "也不能控制所有制度、资源和偶然。但边界之内仍有选择。"
        "我之所以一再谈守成，并不是因为一次成功就能决定后来的一切；恰恰相反，"
        "成功以后仍要继续作选择，而新的选择又会改写后面的路。\n\n"
        "我还有一个很深的体会：不要把自己的判断当成命运。魏征曾以‘兼听则明，偏信则暗’劝我；"
        "后来又以善始难克终相戒。我在答诏中说‘朕闻过矣’，并要求他继续‘犯而无隐’。"
        "我所能做的，不是保证自己永远正确，而是尽量让错误有机会被指出，让判断有机会被修正。"
        "一个人若把自己封闭起来，即使一时得势，也可能亲手缩小自己的未来。\n\n"
        "因此，你问个体的命运究竟由谁主宰，我的回答是：没有任何单一力量能够完全主宰。"
        "时代决定许多起点和边界，偶然改变某些节点，他人会影响你的判断；"
        "而你自己的连续选择，尤其是能否在得意时仍保持清醒、在犯错时仍允许自己被纠正，"
        "会持续塑造你能走到哪里。\n\n"
        "若一定要给一句结论，我会说：人不能主宰全部命运，但可以对自己在命运中的每一次回应负责。"
        "真正值得经营的，不是幻想控制一切，而是在看清时代边界之后，仍保有选择、修正和自持的能力。"
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
        heu_stage.interpretation[0],
        heu_feedback.interpretation[0],
        heu_success.interpretation[0],
        insight_stage.statement,
        insight_feedback.statement,
    ]

    cautions = [
        "本回答只使用当前 R-000001 已审核的唐代知识链；尚未完成汉、宋反例与跨人物比较。",
        "唐太宗的帝王治理经验不能直接等同于普通人的现代处境；回答仅抽取有证据边界的可迁移部分。",
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
