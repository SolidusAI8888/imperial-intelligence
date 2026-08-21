# Qing persona voice source acquisition

The Qing persona source plan now has a dedicated machine-readable registry at
`history/source_registry/qing_persona_voice_sources.yaml`.

The first acquisition order is:

1. `CN-QING-VOICE-0001` — 上諭檔
2. `CN-QING-VOICE-0002` — 朱批奏摺
3. `CN-QING-VOICE-0003` — 起居注
4. `CN-QING-VOICE-0004` — 軍機處檔

Initial official-source discovery verified catalog/access scopes for the first three
families at the First Historical Archives of China. Access reviews for 上諭檔 and
朱批奏摺、起居注 are complete and all three are now `blocked_with_reason` pending written
permission and a permitted export path. The broad 軍機處檔 scope is now catalog-verified
and remains `catalog_verified_access_review_required`. The project must not invent a host, volume range, reuse
permission, or machine-access claim merely to make ingestion appear ready.

Verified findings:

- the on-site Manchu 上諭檔 full-text database contains 613 volumes, spanning 1730–1911;
- the on-site Manchu 起居注 full-text database contains 700 volumes, spanning 1674–1909;
- the official online catalog exposes the Grand Council Manchu edict-register node and
  the Grand Secretariat 朱批奏折 hierarchy;
- the archive announced 425,780 open Chinese 朱批奏折 catalog entries and a separate
  Manchu full-text database.

These are discovery facts, not corpus-ingestion results. The archive's current online
resource page identifies only 《清实录》 and 《清会典》 as freely available website
full-text databases; the archival databases require a separate access and reuse review.

Access reviews are now recorded for `CN-QING-VOICE-0001`,
`CN-QING-VOICE-0002`, and `CN-QING-VOICE-0003`. Official appointment
rules allow registered on-site consultation, but prohibit laptops and cameras in the
reading room, prohibit recording digital archives, and require written permission
before excerpts or copies are publicly disseminated. The source therefore remains
fail-closed: catalog verification is recorded, while automated ingestion and PVC
creation are both explicitly unauthorized.

This state is non-terminal. A provenance-backed block remains pending and does not count
as collected or unavailable; it simply lets the acquisition queue advance to the next
reviewable source instead of repeatedly selecting an already-reviewed access question.

Official collection descriptions now also verify that the First Historical Archives has
opened about 814,000 Grand Council archival items and exposes catalog series for Chinese
and Manchu copies of memorials, Manchu deliberation files, special files, and edict/message
registers. `CN-QING-VOICE-0004` deliberately remains an umbrella discovery scope: it must
be partitioned by series and deduplicated against `CN-QING-VOICE-0001` before any manifest
can be designed.

Before a source can move to `catalog_verified_ready_for_manifest`, discovery must record:

- the exact collection scope and, where needed, emperor/reign partition;
- an authoritative holding institution or edition identity;
- stable item, page, or catalog locators;
- reuse-rights information;
- the known completeness of the available digitization.

Only then may a source-specific ingestion manifest map archived items to canonical
passage IDs. Persona Voice Corpus records remain downstream artifacts: a PVC record may
become `reviewed` only after its `passage_id` resolves to that archived evidence.

Run the current status selector with:

```bash
python history/tools/select_next_qing_persona_voice_source.py --json
python history/tools/build_qing_persona_voice_access_review.py \
  --source-id CN-QING-VOICE-0001 --json
```

Registration and catalog discovery are not collection completion. Only an ingestion
report backed by canonical archived passages, or a provenance-backed
`documented_unavailable` decision, counts as terminal.
