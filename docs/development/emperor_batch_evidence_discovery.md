# Emperor batch evidence discovery

This tool accelerates Q-FATE-AGENCY-001 knowledge production without bypassing the reviewed knowledge chain.

## What it does

`backend/report_emperor_evidence_discovery.py` scans the existing canonical Han/Tang/Song Source Corpus for each of the 69 registered emperors. It reports candidate canonical passages mentioning the ruler's personal name or imperial title.

## What it does not do

Discovery hits are not automatically accepted as HER, HEU, Insight, or Role Link data. They are candidate evidence only. A ruler remains ineligible for answer ranking until a reviewed HER -> HEU -> Insight -> Role Link chain passes RuntimeContext validation.

## Run

```bash
cd backend
PYTHONPATH=. python report_emperor_evidence_discovery.py
```

The output gives a concrete evidence-review queue for expanding the first-question eligible pool beyond the currently reviewed responders.
