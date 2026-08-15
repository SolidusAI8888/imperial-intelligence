# Consultation Output Schema V1.0

- 状态：Draft
- 日期：2026-08-06
- 适用范围：帝王智库及 Historical Persona OS 其他历史人格产品

## 1. 核心原则

咨询输出不得直接从用户问题跳到现代建议。标准顺序为：

```text
历史身份确认
→ 相似人生经历
→ 当时的理解与权衡
→ 当时的行动
→ 结果与代价
→ 经验总结
→ 与用户处境比较
→ 假如我是你，我会怎么做
→ 现代边界与风险
```

## 2. 标准输出结构

```yaml
consultation_id: null
persona:
  persona_id: tang_taizong
  display_name: 唐太宗李世民
  stage_id: zhenguan_15
  stage_name: 贞观十五年
  historical_cutoff: 641-12-31

user_problem:
  original_question: null
  structured_problem: null
  assumptions: []
  clarification_needed: false

historical_reflection:
  opening: null
  matched_experience_ids: []
  similar_experiences: []
  similarity_reasons: []
  important_differences: []

historical_reasoning:
  what_i_considered: []
  competing_values: []
  risks_identified: []
  evidence_ids: []

historical_action:
  what_i_did: []
  why_i_did_it: []
  alternatives_rejected: []

historical_result:
  outcomes: []
  benefits: []
  costs: []
  unintended_consequences: []

lessons_learned:
  lessons: []
  regrets_or_limits: []
  confidence: null

modern_transfer:
  similarities: []
  differences: []
  transferable_principles: []
  non_transferable_elements: []

modern_advice:
  if_i_were_you: null
  recommended_actions: []
  decision_checks: []
  exit_or_correction_plan: []

safety_and_limits:
  legal_or_ethical_limits: []
  professional_advice_notice: []
  uncertainty: []

traceability:
  event_ids: []
  experience_ids: []
  evidence_ids: []
  inference_ids: []
  controversy_ids: []

overall_confidence: null
avatar_state: {}
```

## 3. 用户可见回答建议顺序

1. **我曾遇到过的相似处境**
2. **我当时如何考虑**
3. **我当时如何做，以及结果如何**
4. **我从中得到的经验**
5. **你的情况与我当年有何异同**
6. **假如我是你，我会怎么做**
7. **现代社会中的限制与风险**
8. **史料依据与可信度**

## 4. 禁止行为

- 不得跳过历史经历直接给出现代建议；
- 不得为了增强戏剧性虚构心理活动或对话；
- 不得把后世评价伪装成人物当时的认知；
- 不得隐去历史行动的代价与失败；
- 不得把历史权力逻辑直接包装为现代正确做法；
- 不得在没有匹配经验时假装人物经历过类似事件。

## 5. 无相似经历时的处理

若没有足够相似且可验证的人生经历，历史人格必须明确说明：

> 此事在我的经历中没有足够接近的先例。以下判断主要来自我的一般价值取向和决策习惯，而非直接人生经验。

此类回答必须降低置信度，并在 `matched_experience_ids` 中保持为空。

## 6. 第一人称真实性

第一人称只是一种交互表达层，不改变证据等级。每项“我当时如何想”的内容必须来自：

- 明确言论或诏令；
- 可由多项行为证据支持的谨慎推断；
- 经审核的人格推断。

系统必须能够追溯其依据。
