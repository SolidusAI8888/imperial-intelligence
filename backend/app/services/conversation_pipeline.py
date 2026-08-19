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


def _has_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def is_first_question_followup(question: str, history: list[ConversationMessage]) -> bool:
    if not history:
        return False
    prior = "".join(item.content for item in history)
    normalized = "".join(question.split())
    return "命运" in prior or _has_any(
        normalized,
        ("草创", "守成", "普通人", "工作", "找不到", "资格", "开国皇帝", "魏征", "兼听"),
    )


def generate_first_question_followup(
    question: str,
    history: list[ConversationMessage],
) -> GroundedAnswer:
    """Answer a follow-up inside the reviewed Q-FATE-AGENCY-001 evidence boundary."""

    context = build_first_question_context(question)
    normalized = "".join(question.split())

    if "开国皇帝" in normalized or ("资格" in normalized and "草创" in normalized):
        answer = (
            "你这句质疑有道理。唐朝开国皇帝是高祖，不是朕。若把‘草创’说成朕一人开创唐朝，"
            "那便是把史实说过了。朕能谈的，是自己亲身参与的草创阶段，而不是冒认开国之名。\n\n"
            "隋末起兵之后，朕确实参与军旅与进退决断。霍邑久雨粮乏、高祖欲还太原时，"
            "朕曾力争继续进兵，并说明退兵可能使众心离散、反受敌乘。后来即位，朕再与房玄龄、魏征"
            "讨论草创与守成，是把自己经历过的两个阶段放在一起比较。\n\n"
            "所以边界应说清：朕有参与草创的亲历，却没有资格把大唐开国之功说成一己所有。"
        )
        reasoning = [
            "身份边界：高祖是唐朝开国皇帝，唐太宗不能占用这一身份。",
            "经历边界：现有审核记录支持唐太宗亲历隋末唐初进退决断，并在即位后反思草创与守成。",
            "结论边界：回答只能使用亲历阶段比较，不能把‘参与草创’夸大成‘独自开国’。",
        ]
    elif _has_any(normalized, ("普通人", "找不到工作", "没工作", "失业", "工作都找不到")):
        answer = (
            "那朕便不该再拿‘成功之后如何守成’压在你眼前。你现在连立足之处都在寻找，"
            "若朕只讲功成之后如何自警，确实答非所问。\n\n"
            "朕前面真正能迁移给你的，不是‘守成’二字，而是处境一变，就要重辨眼前真正的难处。"
            "你此刻先不要拿成功者的标准要求自己。先看三件近事：眼下有哪些真实可进入的机会；"
            "每次被拒绝究竟给了什么信息；下一次投递、表达或能力准备能改哪一处。\n\n"
            "这并不保证你一定找到工作。行业、时势与他人的选择都不由你控制。"
            "能由你承担的，只是别让一次受挫自动变成对自己的终局判决。"
        )
        reasoning = [
            "相关性修正：用户处在求职与立足阶段，守成经验不能作为主要类比。",
            "阶段原则：现有经历支持‘不同处境要重新识别主要困难’，而不是把同一办法套给所有人。",
            "迁移边界：求职行动属于现代转译，只保留反馈、修正与承认外部限制。",
        ]
    elif _has_any(normalized, ("证据", "史料", "依据", "凭什么知道", "怎么知道", "真的假的")):
        answer = (
            "若你问朕凭什么这样说，这个追问应当保留。朕不该靠一句‘朕以为’便要你相信。"
            "本题能站住的，只是几段已经核对过的经历：早年霍邑进退的判断；即位后与房玄龄、魏征"
            "讨论草创与守成；以及魏征劝朕兼听、克终，朕答以‘朕闻过矣’并令其‘犯而无隐’。\n\n"
            "这些材料能支持朕说：处境会变，判断会错，保留纠错通道有价值。"
            "它们不能证明‘只要肯选择就能控制命运’，也不能证明朕一生从未犯错。"
        )
        reasoning = [
            "证据追问：只复述当前 HER/HEU 链已经覆盖的历史记录。",
            "支持边界：材料支持阶段变化、纳谏与纠错，不支持个人全能论。",
            "可审计性：具体 canonical evidence IDs 继续由 API evidence 字段返回，而不让历史角色知晓后世编纂信息。",
        ]
    elif _has_any(normalized, ("你也会错", "你不也错", "你犯错", "你自己呢", "你真的做到", "一直做到")):
        answer = (
            "朕当然不能说自己从此无过。若真能保证自己永远正确，又何必让魏征继续‘犯而无隐’？"
            "‘朕闻过矣’真正有分量之处，不在于从此不再犯错，而在于承认自己的判断需要别人来校正。\n\n"
            "所以你若拿朕自己的局限来反驳前面的结论，这并不推翻它，反而提醒朕把话说窄："
            "能修正错误，不等于不会再错；能保留谏言，也不等于每次都会听。"
            "个人能做的是提高发现和修正错误的机会，而不是把自己变成永不犯错的人。"
        )
        reasoning = [
            "不把纳谏经验夸大为人格完美或永久正确。",
            "‘闻过’与‘犯而无隐’支持的是纠错机制存在，而不是错误被彻底消灭。",
            "因此结论收窄为提高修正概率，而非保证结果。",
        ]
    elif _has_any(normalized, ("具体怎么办", "那我怎么办", "我该怎么办", "下一步", "怎么做", "如何做")):
        answer = (
            "若只从本题这组经验给你一个可执行的办法，朕会让你先做小而可改的下一步，而不是先求一个终身答案。"
            "先写清哪些条件你改不了，哪些还能动；再找一个愿意说真话的人，让他指出你判断里最可能错的一处；"
            "然后只改下一步能验证的行动。\n\n"
            "做完再看结果。若处境变了，就重察势；若判断被事实否定，就改。"
            "这套办法不能替你决定人生，却能避免你把一次判断误当成不可更改的命运。"
        )
        reasoning = [
            "行动建议只迁移当前知识链中‘察势、兼听、修正’三个已审核要点。",
            "使用小步可验证行动，避免把帝王级重大决断直接映射为现代个人决策。",
            "最终决定仍属于用户，历史经验只提供参考。",
        ]
    elif _has_any(normalized, ("什么意思", "没听懂", "解释一下", "为什么这么说", "什么叫回应")):
        answer = (
            "朕所说的‘回应’，不是说你能决定发生什么，而是事情发生以后，你仍要决定下一步怎么做。"
            "霍邑久雨粮乏不是朕能决定的，高祖一度欲退也不是朕一人造成的；朕能做的是在那个节点提出判断。"
            "即位以后，别人是否直言也不能只靠朕一人，但朕可以选择是否给直言留下位置。\n\n"
            "所以‘回应’只是个人能够影响的那一小段：看清处境、作出选择、听取反对意见、发现错误后修正。"
            "它不是‘我想怎样，世界就怎样’。"
        )
        reasoning = [
            "澄清‘回应’与‘控制结果’的区别。",
            "用当前已审核的霍邑与纳谏记录解释个人可控范围。",
            "明确拒绝把有限能动性扩大为个人全能。",
        ]
    else:
        answer = (
            "这个追问已经比原来的大问题更具体了。朕不愿因为前面说过一次，就把同一句结论重新压给你。"
            "在目前已经核对的经历范围内，朕能继续坚持的只有几件事：处境改变时要重辨主要困难；"
            "自己的判断可能有盲处；真实反对意见有价值；发现错误后仍可调整下一步。\n\n"
            "若你追问的具体事实超出这些经历，朕宁可承认这组史料暂时不足，也不借朕的身份补出一个没有根据的答案。"
        )
        reasoning = [
            "连续对话不重复首轮答案，而是根据追问收窄论证。",
            "角色只坚持当前审核知识链支持的判断。",
            "超出证据范围时明确不足，不用人格设定填补史料空白。",
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
