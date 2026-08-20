# Runtime Problem Builder v1

`POST /consult/auto` now has two safe runtime outcomes:

1. a reviewed grounded answer for a question already supported by the registered responder path; or
2. a deterministic, non-answering research package for an unseen question.

For unseen questions the runtime creates a stable `Q-RESEARCH-<16 HEX>` identifier and recalls reviewed reusable HEUs into ranked research candidates. The research path never grants responder eligibility and never renders an answer without the existing problem-specific review gates.

This removes the old requirement that clients first know whether a question has a hand-written Problem file before using the automatic consultation entry point, while preserving the evidence boundary.
