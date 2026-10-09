# The contract between the three repositories

The only thing they share is the evidence record (`juridicator/evidence.py`, schema `tengoku-evidence/1`). It is a single
standard-library file with no imports from the rest of this package, so the wounder and the praiser **vendor it byte for
byte** and pin its hash, the way Tau Ceti pins reusable workflows to an exact commit. A change to the contract is a change
here first, then a refresh of both copies.

```
tengoku-wounder  ──┐                          ┌── verdicts, ledger
                   ├──► evidence records ──►  tengoku-juridicator
tengoku-praiser  ──┘                          └── standing "gate health", precedents (read back by the praiser for track records)
```

## Who may write what

| Repo | Role value | May emit |
| --- | --- | --- |
| wounder | `wounder` | `mechanical.canary`, `mechanical.sensitivity`, `reproducible.fuzz`, `manifest.declared` |
| praiser | `praiser` | `mechanical.provenance_consistent`, `mechanical.restatement_match`, `reproducible.rebuild_match`, `reproducible.track_record`, `attested.*`, `manifest.declared` |
| existing tooling (CI, Jinshi, checkers) | `tooling` | `mechanical.kernel_check` (one identity per checker), `mechanical.axiom_closure`, `mechanical.no_sorry`, `mechanical.ci`, `mechanical.jinshi.<check>` |
| reviewers | `judge-ai`, `human` | `judgment.review`, `judgment.human_review` |
| the author's agent | `author-system` | `attested.*` only (anything stronger is ignored) |

## Rules every producer follows

1. A `mechanical` or `reproducible` record carries the command that reproduces it. No command, no record.
2. The first part of `kind` equals `verifiability` (`manifest.*` is the one exception and is always attested).
3. Declare a `manifest.declared` listing the kinds you will report **before** running, then report every one; silence is
   not a pass. `not_run` is a legitimate outcome and counts as missing.
4. Never drop a failing result. A producer that reports only passes is, by R9, a producer that holds the case.
5. Claims are plain sentences of at most 300 characters; anything long goes in `details` (8 KiB) and is for people, never
   for decisions.
6. Bind every record to the exact `head_sha` it was produced for.
7. Say whether AI was used, in which role, which model and which model family.

## Vendoring

Each consumer keeps `vendor/juridicator_evidence.py` (a verbatim copy) and `vendor/EVIDENCE.sha256`. Its tests fail if the
copy no longer matches the pin, and `scripts/sync_contract.py --from <path to juridicator>` refreshes both.
