# Phase 3 — 清實錄 catalog-aware acquisition

`CN-QING-0001` is not a simple numbered-volume root. The verified zh.wikisource.org root catalog exposes thirteen child works, from `滿洲實錄` through `宣統政紀`. The host page also explicitly says that only part of the original work has been entered and describes the historical corpus as 4,326 volumes.

The ingestion contract therefore separates two states:

- `archive_scope_complete`: every page currently discoverable from the registered host catalog has been archived with revision provenance and canonical passage IDs.
- `source_complete`: the historical source itself is demonstrably complete against an independent extent check.

For the current Wikisource host, `source_complete` MUST remain false even when `archive_scope_complete` is true. This prevents a successful scraper run from being misreported as a complete Qing Shilu corpus.

The next acquisition step after host-catalog archival is source-gap analysis against a stable edition/catalog and, where legally and technically available, acquisition of missing reign/volume material from another provenance-bearing source.
