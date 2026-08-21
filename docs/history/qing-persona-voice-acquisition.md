# Qing persona voice source acquisition

The Qing persona source plan now has a dedicated machine-readable registry at
`history/source_registry/qing_persona_voice_sources.yaml`.

The first acquisition order is:

1. `CN-QING-VOICE-0001` — 上諭檔
2. `CN-QING-VOICE-0002` — 朱批奏摺
3. `CN-QING-VOICE-0003` — 起居注
4. `CN-QING-VOICE-0004` — 軍機處檔

Initial official-source discovery verified catalog/access scopes for the first three
families at the First Historical Archives of China. They now remain
`catalog_verified_access_review_required`, while 軍機處檔 remains
`pending_source_discovery`. The project must not invent a host, volume range, reuse
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
```

Registration and catalog discovery are not collection completion. Only an ingestion
report backed by canonical archived passages, or a provenance-backed
`documented_unavailable` decision, counts as terminal.
