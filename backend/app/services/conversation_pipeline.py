from __future__ import annotations

from app.models.api import ConversationMessage
from app.services.answer_pipeline import GroundedAnswer, build_first_question_context
from app.services.knowledge_runtime import render_grounded_context


def _evidence_ids() -> list[str]:
    context = build_first_question_context()
    return sorted(
        {
            cid
            for record in context.records
            for source in record.sources
            for cid in source.canonical_ids
        }
    )


def is_first_question_followup(question: str, history: list[ConversationMessage]) -> bool:
    if not history:
        return False
    prior = "".join(item.content for item in history)
    normalized = "".join(question.split())
    return "命运" in prior or any(
        token in normalized
        for token in ("草创", "守成", "普通人", "工作", "找不到", "资格", "开国皇帝")
    )


def generate_first_question_followup(
    question: str,
    history: list[ConversationMessage],
) -> GroundedAnswer:
    """Answer a follow-up within Q-FATE-AGENCY-001 using the reviewed chain.

    Follow-ups may challenge relevance or historical standing. The answer must
    concede valid objections, distinguish facts from transfer, and remain within
    the same reviewed HER -> HEU -> Insight evidence boundary.
    """

    context = build_first_question_context(question)
    normalized = "".join(question.split())

    if "开国皇帝" in normalized or ("资格" in normalized and "草创" in normalized):
        answer = (
            "你这句质疑有道理。唐朝开国皇帝是高祖，不是朕。若把‘草创’说成朕一人开创唐朝，"
            "那便是把史实说过了。朕能谈的，是自己亲身参与的草创阶段，而不是冒认开国之名。\n\n"
            "隋末起兵之后，朕随军征战；霍邑久雨粮乏、高祖欲还太原时，朕曾力争继续进兵。"
            "其后薛举、宋金刚、王世充、窦建德诸役，朕也长期处在唐初由乱而定的军事与政治进程中。"
            "所以，当贞观十年朕与房玄龄、魏征谈‘草创与守成孰难’时，朕并非以开国皇帝的名义说话，"
            "而是在回看自己确实经历过的创业战争，再比较即位以后守成的困难。\n\n"
            "你的追问反而提醒了一条重要边界：一个人只能从自己真正经历过的部分提炼经验。"
            "朕可以谈参与草创、领兵定乱，也可以谈即位后的守成；但若说‘大唐皆由朕所创’，朕不该这样说。"
        )
        reasoning = [
            "身份边界：高祖是唐朝开国皇帝，唐太宗不能占用这一身份。",
            "经历边界：唐太宗在隋末、武德年间实际参与起兵与统一战争，因此具有草创阶段的亲历经验。",
            "结论边界：本题使用的是‘参与草创与后来守成的阶段比较’，不是‘唐太宗独自开国’这一错误命题。",
        ]
    elif any(token in normalized for token in ("普通人", "找不到工作", "没工作", "失业", "工作都找不到")):
        answer = (
            "那朕便不该再拿‘成功之后如何守成’压在你眼前。你现在连立足之处都在寻找，"
            "若朕只讲功成之后如何自警，确实答非所问。\n\n"
            "朕前面真正想说的，并不是人人都要先成功再守成，而是处境不同，眼前真正的难题就不同。"
            "朕早年在乱军之中时，所想的是军心会不会散、这一步该进还是该退；到天下渐定以后，"
            "才需要防骄逸、偏听。若把后一阶段的办法硬塞给前一阶段，本身就是没有察势。\n\n"
            "你现在若是连工作都找不到，先不要拿‘守成’要求自己。先问更近的三件事："
            "你眼下能够进入哪些门槛较低而真实存在的机会；别人为什么没有选择你；"
            "你能否从每一次拒绝里得到真实反馈，再改下一次的投递、表达或能力准备。"
            "这不是说你只要努力就一定能找到工作。时势、行业和机会都不是你能控制的。"
            "但在不能控制的部分之外，至少要让每一次受挫都给下一步多留一点路，而不是只留下自责。\n\n"
            "所以对你此刻而言，本题的重点不是‘守住成功’，而是‘在受限的处境里，怎样不断扩大下一步仍可选择的路’。"
        )
        reasoning = [
            "相关性修正：用户当前处在求职与立足阶段，守成经验不能作为主要类比。",
            "阶段原则：唐太宗自己的经历支持‘不同处境需要重新识别主要困难’，而不是把同一经验套用到所有阶段。",
            "现代转移边界：求职建议是现代转译，只保留‘真实反馈、修正下一步、承认外部限制’这些可迁移部分。",
        ]
    else:
        answer = (
            "你可以继续追问。朕前面的回答若有哪一处与你的处境不合，便应把那一处拆开重看，"
            "而不是因为已经说过一次，就强迫你接受。朕所能坚持的只有证据允许朕坚持的部分："
            "处境会变，人的判断会错，真实的反对意见有价值，而人在外部限制之中仍要为下一步如何回应作选择。"
            "除此之外，若你的具体处境与朕的经历并不相似，就应明确说出差异，再决定哪些经验可以迁移，哪些不可以。"
        )
        reasoning = [
            "连续对话必须允许用户挑战前一轮回答，而不是重复原结论。",
            "角色只能坚持现有审核证据支持的判断；具体类比不成立时必须承认差异。",
            "现代迁移必须根据用户的新信息重新收窄。",
        ]

    return GroundedAnswer(
        problem_id=context.problem_id,
        person_id=context.person_id,
        answer=answer,
        reasoning=reasoning,
        cautions=[
            "本轮是第一问知识链内的追问回答；不会因为连续对话而扩大到未经审核的新史实。",
            "现代处境与帝王经历存在结构差异；具体建议属于受限转译，不等同于历史事实。",
        ],
        evidence_ids=_evidence_ids(),
        grounded_context=render_grounded_context(context),
    )
