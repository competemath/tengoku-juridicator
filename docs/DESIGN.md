# Design

## Three roles, one evidence format

- **tengoku-wounder** looks for ways the pipeline would wrongly accept bad content: planted-defect canaries, statement
  sensitivity probes, audit sampling. It *challenges*. It has no write access to anything that gates.
- **tengoku-praiser** collects falsifiable reasons to trust content: provenance that checks out, an independent rebuild,
  independent checkers agreeing, a track record computed from the ledger, a plain-language trust card. It *vouches*, but
  only with evidence a stranger could re-run. Praise that cannot be checked is recorded and ignored.
- **tengoku-juridicator** (this repo) *decides*. A deterministic statute turns evidence into ACCEPT, HOLD, ESCALATE or
  REJECT; AI is a bounded advisor after it, never a judge of facts.

## The decisions

| Decision | Meaning | Who can get out of it |
| --- | --- | --- |
| ACCEPT | required evidence present, nothing failed, nothing disputed | n/a (sampled for later audit by tier) |
| HOLD | something required is missing or needs a re-run | produce the missing evidence |
| ESCALATE | checkers disagree, or a reviewer raised a concern | a person |
| REJECT | a mechanical check failed, or a person rejected it | fix the content, new commit |

## Scrutiny tiers

Every case also gets a tier (0 to 3) that sets how likely it is to be audited later (5%, 20%, 50%, 100%). The class sets
the starting tier; history and doubt raise it; falsifiable merit can lower it by one step, all conditions together.
Reputation therefore buys *less scrutiny*, never *acceptance*.

## Evidence ladder

mechanical (re-run by the judge's own tools) > reproducible (re-run at cost or with a seed) > attested (a party's word,
shown but not weighed) > judgment (an opinion, can only add caution). See `evidence.py` for how the format enforces it.

## What lives where

`evidence.py` contract · `policy.py` + `policy/default.json` rules as data · `statute.py` the decision · `precedent.py`
similar past cases · `ledger.py` hash-chained history · `marker.py` + `ai.py` AI containment and the valve ·
`calibration.py` when AI may be given more.
