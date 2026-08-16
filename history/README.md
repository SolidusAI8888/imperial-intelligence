# Historical Source Corpus

This directory is the archival source layer for the project.

## Scope order

Phase 1 is built strictly in dynasty order:

1. Han
2. Tang
3. Song

Within each dynasty, only first-tier authoritative historical sources are admitted initially.

## Data-layer rule

The source corpus stores the full original text and its source/version metadata. Derived knowledge is built above this layer.

Canonical flow:

`Source Corpus -> Passage -> Claim -> Event -> Historical Interpretation -> HEU -> Consultation`

The source text must not be rewritten by downstream AI processing. Corrections, edition changes, segmentation changes, or source substitutions must be documented and traceable.

## Current first source

The first registered source is 《史记》. Its corpus directory is:

`history/source_corpus/china/han/shiji/`
