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
a human attestation that the canonical passage link, attributed person/speaker, transcription, and feature tags
were checked. The review-packet endpoint verifies that candidate text is present in the
immutable archived passage and that the source file still matches the SHA-256 recorded
by its ingestion report; the decision endpoint supports a dry run and only unlocks the
record after an explicit persisted approval with all four attestations.

`POST /persona-voice/candidates` creates a deterministic candidate only when the supplied
excerpt is present in a checksum-verified archived passage. Persisted artifacts always
start as `candidate`, remain runtime-ineligible, and require the separate review flow;
candidate creation cannot directly write `reviewed` evidence.

`GET /persona-voice/review-queue` turns those records into a read-only human work queue.
It checks each candidate against the archived passage and ingestion hash, blocks duplicate
candidates for the same person and passage, and surfaces old `reviewed` labels that lack a
complete attestation. It never approves or edits a record. The repository now includes three
checksum-verified 唐太宗 candidates from 《贞观政要》 as the first real queue fixtures; all
three remain excluded from runtime style until an explicit human decision records every
required attestation.

The queue accepts `queue_state=ready|blocked|attestation_repair`, plus bounded `offset` and
`limit` parameters. Its response separates corpus-wide status counts from the filtered and
returned record counts, so an operator can page through a stable view without mistaking a
partial page for total coverage. Filtering and paging remain observational operations.
Each queue item also carries the candidate text, a bounded exact-match archive context,
proposed voice/decision/rhetoric tags, confidence, archive-integrity and text-match signals,
the four required attestations, and a deterministic next action. This makes one item sufficient
for an operator to understand the review task while preserving the separate explicit decision
endpoint.

`GET /personas/{person_id}/voice-readiness` reports reviewed and traceable PVC coverage,
the evidence IDs and feature tags selected for runtime style, the independent-passage
and source counts, the weighted score, and any style-gate blockers. It distinguishes
selected records from evidence actually applied to wording. This endpoint is
observational: voice readiness never grants factual answer permission.
