# Source Corpus V1

## Purpose

This specification defines how authoritative historical full texts are archived before any downstream knowledge extraction.

## Mandatory rules

1. Full original text is required for an admitted source corpus.
2. Sources are built in dynasty order for Phase 1: Han, then Tang, then Song.
3. Only first-tier authoritative historical sources are admitted initially.
4. Every source must be registered before full-text ingestion.
5. The archived source layer and the derived knowledge layer are separate.
6. AI-generated summaries, interpretations, HEUs, or consultation text must never be written into the source corpus as source text.
7. The selected edition or digital witness, provider, access record, rights status, and checksum must be recorded before ingestion is marked complete.
8. Natural paragraph is the default smallest archival and citation unit. Volume and section structure must also be preserved.
9. Canonical paragraph IDs are permanent after downstream references exist.
10. Any correction, replacement of base text, segmentation change, or edition change must have a provenance record.

## Canonical ID

Source IDs use the registry ID, for example:

`CN-HAN-0001`

Paragraph IDs use:

`CN-HAN-0001-V001-P00001`

where `V001` is the canonical volume number and `P00001` is the paragraph sequence within that volume.

The ID identifies the archived unit, not an interpretation of it.

## Full-text completeness

A source is not considered fully archived until:

- all intended volumes are present;
- all source text is preserved;
- volume/section boundaries are recoverable;
- paragraph IDs have been assigned;
- source/version metadata is complete;
- rights/reuse status for the chosen digital witness has been reviewed;
- a corpus checksum or equivalent integrity record has been stored.

## Derived data

Derived objects may quote or reference corpus paragraphs, but their provenance must point back to canonical source IDs. They may be regenerated without altering the source corpus.
