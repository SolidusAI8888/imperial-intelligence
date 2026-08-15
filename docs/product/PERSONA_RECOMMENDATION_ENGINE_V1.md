# Persona Recommendation Engine V1.0

- 状态：Draft
- 日期：2026-08-15
- 适用范围：Historical Persona OS 全部人物系列

## 1. 核心问题

当用户没有明确指定人物时，系统必须回答：

> 为什么应该由这个人来回答，而不是另一个人？

推荐逻辑不得基于“谁最有名”“谁最成功”或平台运营方的主观偏好，而应基于问题与人物人生经验之间的可解释匹配。

## 2. 推荐原则

> 用户真正需要匹配的不是“一个名字”，而是“一种人生经验”。

系统应先理解问题，再选择人物。

标准流程：

```text
用户问题
→ 问题结构化
→ 核心困境识别
→ 经验主题提取
→ Experience Profile 匹配
→ 候选人物排序
→ 推荐理由生成
→ 用户选择或接受推荐
```

## 3. 用户指定优先

如果用户明确提出：

- “我想听唐太宗怎么说”
- “让巴菲特回答”

系统应尊重用户选择。

但若该人物没有足够相关经验，系统必须坦率说明匹配度与限制，不得为了满足角色期待而虚构经历。

## 4. Experience Profile

每位人物应拥有结构化 Experience Profile，用于表达其一生中经过审核的经验主题，而不是简单职业标签。

示例字段：

```yaml
persona_id: tang_taizong
experience_domains:
  talent_management:
    strength: 0.92
    experience_ids: []
  dissent_and_remonstrance:
    strength: 0.95
    experience_ids: []
  succession:
    strength: 0.78
    experience_ids: []
  romantic_relationships:
    strength: 0.15
    experience_ids: []
```

评分必须来自已审核 Experience Package，不得仅凭人物印象赋值。

## 5. 问题结构化

系统不得只按关键词匹配。

例如：

“男朋友出轨了，我要不要继续？”

可被结构化为：

- trust
- betrayal
- forgiveness
- relationship_exit
- repeated_risk
- self_respect

“工作很累、工资又少，要不要辞职？”

可被结构化为：

- stay_or_leave
- opportunity_cost
- livelihood_security
- endurance
- long_term_growth
- risk_tolerance

推荐应匹配这些底层问题结构，而不是表面时代场景。

## 6. 推荐评分建议

初步推荐分数可以考虑：

- experience_similarity
- evidence_strength
- stage_relevance
- outcome_diversity
- lesson_clarity
- transferability
- counterevidence_quality
- domain_relevance

推荐算法的具体数学权重应在真实数据与用户反馈积累后再确定。

## 7. 推荐解释

系统不能只显示“推荐唐太宗”。

必须解释：

- 推荐了谁；
- 为什么；
- 匹配的是哪些人生经验；
- 哪些方面不匹配；
- 该人物回答的置信度如何。

示例：

> 建议先听唐太宗。你的问题核心包含“是否继续信任一个重要合作者”和“如何在能力与控制风险之间权衡”。唐太宗在用人、纳谏与权力关系方面有多项可验证经历，因此匹配度较高。但你面对的是现代商业合作，制度环境与其时代差异很大。

## 8. 多人物推荐

系统长期不应只返回唯一人物。

建议输出：

- primary_persona：最适合先回答的人
- alternative_personas：2–3 位具有不同经验结构的人

目的不是制造“正确答案”，而是允许用户比较不同人生路径。

例如：

```text
先听唐太宗：偏重识人、用人、制度与权衡
再听朱元璋：偏重风险、防范与控制
未来可听巴菲特：偏重长期收益、机会成本与耐心
```

## 9. 无合适人物

如果当前智库中没有足够匹配的人物，系统必须明确说明：

> 当前人物库中没有足够相关且资料可靠的经验可以支持高质量回答。

不得为了保持交互流畅而随机推荐人物。

## 10. 推荐引擎与人物类别解耦

推荐引擎不得预设帝王优先。

未来企业家、思想家、科学家、教育家等加入后，所有人物应在统一 Experience Profile 体系下参与匹配。

类别仅用于浏览与理解，不应成为推荐排序的硬编码优先级。

## 11. 长期产品目标

Persona Recommendation Engine 最终要实现的不是“替用户选一个名人”，而是：

> 在人类高质量人生经验库中，找到最值得用户此刻先听的一段人生。
