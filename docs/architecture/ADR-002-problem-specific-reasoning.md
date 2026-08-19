# ADR-002: Reusable historical experience and problem-specific reasoning

## Status
Accepted for incremental implementation.

## Decision
Historical Records (HER) and Historical Experience Units (HEU) are reusable person-owned knowledge. A new user question may recall these reviewed experiences across people before any responder is selected.

Problem-specific reasoning begins only after recall. Insight selection, candidate scoring, and responder eligibility remain scoped to a concrete problem. Recall or research shortlisting must never grant responder eligibility.

## Runtime boundary

Source Corpus -> HER -> HEU -> research recall/shortlist -> problem-specific Insight selection -> candidate scoring -> responder eligibility -> persona answer.

## Consequences
- Existing first-question work remains valid and reusable.
- New questions do not rebuild every biography from scratch.
- A recalled emperor is only a research candidate, not yet an authorized responder.
- Unknown/unregistered questions cannot inherit another problem's eligibility.
