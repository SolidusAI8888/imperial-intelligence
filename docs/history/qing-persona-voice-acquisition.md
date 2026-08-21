# Qing persona voice source acquisition

The Qing persona source plan now has a dedicated machine-readable registry at
`history/source_registry/qing_persona_voice_sources.yaml`.

The first acquisition order is:

1. `CN-QING-VOICE-0001` — 上諭檔
2. `CN-QING-VOICE-0002` — 朱批奏摺
3. `CN-QING-VOICE-0003` — 起居注
4. `CN-QING-VOICE-0004` — 軍機處檔

All four initially remain `pending_source_discovery`. This is deliberate: these names
describe archival source families rather than a verified single online edition. The
project must not invent a host, volume range, stable catalog, reuse permission, or
digitization-completeness claim merely to make ingestion appear ready.

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
