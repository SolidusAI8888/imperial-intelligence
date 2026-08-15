# Experience Package Schema V1.0

- 状态：Draft
- 日期：2026-08-06
- 适用范围：Historical Persona OS 全部历史人格

## 1. 目标

Experience Package 用于把“发生过什么”转换为“历史人物从中形成了什么可复用经验”。它位于史实事件与现代咨询建议之间。

系统回答必须遵循：

```text
史料 → 历史事件 → 当时思考 → 当时行动 → 结果 → 经验 → 现代迁移 → 建议
```

不得脱离可验证的人生经历，直接生成符合人物性格的现代观点。

## 2. Experience 与 Event 的区别

### Event

回答“发生过什么”，属于事实层。

### Experience

回答“人物如何理解这件事、如何行动、结果如何、后来可提炼出什么经验”，属于经审核的解释与推断层。

一个 Experience 可以关联一个或多个 Event；同一 Event 也可以产生多个不同主题的 Experience。

## 3. 必填字段

```yaml
experience_id: EXP-TTZ-0001
persona_id: tang_taizong
stage_id: zhenguan_15
title: 任用旧敌魏征并持续纳谏
status: draft

summary: >
  对该人生经验的简要概括。

related_event_ids:
  - EVT-TTZ-0001

problem_patterns:
  - 是否重用曾经反对自己的人
  - 是否允许下属公开反对自己

reusable_patterns:
  - talent_management
  - dissent
  - trust
  - power_balance

historical_context:
  facts: []
  evidence_ids: []

historical_reasoning:
  conclusion: null
  basis: []
  evidence_ids: []
  confidence: null

historical_action:
  actions: []
  evidence_ids: []

historical_result:
  outcomes: []
  positive_results: []
  negative_results: []
  unintended_consequences: []
  evidence_ids: []

lessons_learned:
  lessons: []
  limitations: []
  counterevidence_ids: []
  confidence: null

modern_transfer:
  applicable_scenarios: []
  transfer_conditions: []
  non_transferable_elements: []
  modern_risks: []

source_attribution:
  primary_evidence_ids: []
  secondary_evidence_ids: []
  inference_ids: []
  controversy_ids: []

review:
  reviewer: null
  reviewed_at: null
  review_status: pending

version: 0.1.0
```

## 4. 第一人称表达规则

系统可以用第一人称讲述经审核的事实与推断，但必须区分：

- **可直接陈述的史实**：史料明确支持。
- **谨慎表达的推断**：使用“我当时更可能考虑的是”等表述。
- **禁止内容**：虚构具体心理独白、私人对话、未见于史料的细节。

## 5. 反证要求

每项 Experience 必须主动记录：

- 支持证据；
- 反证；
- 条件性证据；
- 学术争议；
- 经验适用边界。

不得只收集支持既定人物形象的材料。

## 6. 阶段边界

Experience 只能由当前人生阶段已经发生的事件构成。运行时不得让人物引用其知识截止日期之后的经历。

## 7. 现代迁移规则

现代建议必须明确建立在历史经验之上，并依次回答：

1. 我曾遇到什么相似问题；
2. 我当时如何理解；
3. 我当时采取了什么行动；
4. 结果与代价是什么；
5. 我由此得到什么经验；
6. 你的情况与当年有哪些相似和不同；
7. 假如我是你，我会怎么做；
8. 哪些历史做法不适用于现代社会。

## 8. 质量门槛

正式上线的 Experience 至少应满足：

- 关联一个经审核 Event；
- 至少一个证据来源；
- 明确标记事实与推断；
- 有反证或说明未发现反证；
- 有现代迁移条件；
- 有置信度；
- 通过人工审核。
