# ADR-002: Second Problem end-to-end acceptance

## Decision

The first non-fate benchmark Problem is `Q-CAREER-PIVOT-001`:

> 一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？

This benchmark reuses only existing reviewed HER/HEU/Insight knowledge and performs a new problem-specific candidate ranking. It deliberately does not inherit the ranking from `Q-FATE-AGENCY-001`.

The current reviewed candidate set is Tang Gaozu, Tang Taizong, and Liu Bang. The selector is expected to choose Tang Gaozu because the already-reviewed `INS-TANG-000003` most directly covers path invalidation, path switching, and revision after new information.

## Acceptance path

CI must verify the complete executable path:

1. load a second registered Problem;
2. validate each candidate's reviewed HER -> HEU -> Insight -> Role Link chain;
3. rank multiple candidates using the existing selector;
4. render a grounded answer from the winning responder;
5. continue a related follow-up with the same responder;
6. detect a materially different follow-up;
7. start a fresh recall-only Problem research package for that drifted question.

No new historical event, quotation, or review status is introduced by this benchmark. It only reuses existing reviewed knowledge and records a new problem-specific relevance judgment.
