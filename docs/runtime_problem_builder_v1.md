# Runtime Problem Builder v1

`POST /consult/auto` now has two safe runtime outcomes:

1. a reviewed grounded answer for a question already supported by the registered responder path; or
2. a deterministic, non-answering research package for an unseen question.

For unseen questions the runtime creates a stable `Q-RESEARCH-<16 HEX>` identifier and recalls reviewed reusable HEUs into ranked research candidates. The research path never grants responder eligibility and never renders an answer without the existing problem-specific review gates.

This removes the old requirement that clients first know whether a question has a hand-written Problem file before using the automatic consultation entry point, while preserving the evidence boundary.

## Persona Voice Corpus boundary

When the selected responder has reviewed Persona Voice Corpus (PVC) records, the
renderer may compile their tagged voice features into conservative structural style
guidance. The selected `voice_evidence_ids` are returned as audit metadata and exposed
by the read-only runtime explanation endpoint.

PVC is optional and style-only. It does not improve candidate scores, grant responder
eligibility, override counterevidence, or replace factual HER/HEU/Insight grounding.
Candidate, rejected, untraceable, or another person's voice records cannot affect an
answer. A style change also requires at least two independently traceable passages and
a combined weighted evidence score of 1.20; one vivid passage or duplicated annotation
therefore cannot define a person's general voice. Source text is never copied into
first-person prose as a fabricated quotation.

A `reviewed` label alone is insufficient. Every runtime-eligible PVC record must carry
a human attestation that the canonical passage link, transcription, and feature tags
were checked. The review-packet endpoint verifies that candidate text is present in the
immutable archived passage and that the source file still matches the SHA-256 recorded
by its ingestion report; the decision endpoint supports a dry run and only unlocks the
record after an explicit persisted approval with all three attestations.

`GET /personas/{person_id}/voice-readiness` reports reviewed and traceable PVC coverage,
the evidence IDs and feature tags selected for runtime style, the independent-passage
and source counts, the weighted score, and any style-gate blockers. It distinguishes
selected records from evidence actually applied to wording. This endpoint is
observational: voice readiness never grants factual answer permission.
