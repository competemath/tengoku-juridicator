# The pipeline, step by step

This is `tests/test_pipeline_e2e.py` in prose. Every command here is run by that test when the sibling repositories are
checked out next to this one.

```
 wounder                         juridicator                          praiser / tooling
 -------                         -----------                          -----------------
 1 manifest + run-canaries  -->  2 standing (gate health)
                                                                     3 manifest, then evidence:
                                                                       checkers, axioms, sorry, Jinshi,
                                                                       provenance, rebuild, track record
                                 4 sign (each producer, its own key)
                                 5 lottery_commit appended
                                 6 judge (statute) --> verdict + ledger
                                 7 lottery_reveal appended
 8 lottery plan  <------------------ ledger
                                 9 a person labels accepted cases later --> label entries --> track records
```

1. **Test the gate first.** `python3 -m wounder run-canaries --corpus corpus --gate-cmd "<our gate>" --repo R --head SHA --class gate --out gate-evidence`.
   Planted defects the gate accepts, and known-good cases it rejects, are failures. The reference text gate fails 5 of 15
   on purpose: it cannot see an axiom added by a metaprogram, a vacuous theorem, type drift, a shadowed name or a duplicate.
2. **Publish gate health.** `python3 -m juridicator standing --case gate-case.json --evidence gate-evidence --out standing.json`.
   Exit 0 means the gate is proven healthy; anything else and no content case can be accepted (rule R11).
3. **Gather evidence for a content case.** Each producer first declares a manifest listing what it will report (and, for
   many-part runs, `expected` subjects), then reports every result, failures included. Tools that already exist emit
   `mechanical.*` records; the praiser adds provenance, restatement, pre-registration, rebuild and track-record records.
4. **Sign.** `python3 -m juridicator sign --evidence ev --key KEY --principal NAME --out sigs.jsonl`. The maintainers keep an
   `allowed_signers` file (`NAME namespaces="tengoku-evidence/1" ssh-ed25519 ...`).
5. **Open an audit batch.** `python3 -m wounder lottery commit-body --salt-file salt | ...` then
   `python3 -m juridicator append --ledger L --kind lottery_commit --body body.json`.
6. **Judge.** `python3 -m juridicator judge --case case.json --evidence ev --policy policy.json --standing standing.json
   --signatures sigs.jsonl --allowed-signers allowed_signers --verified-ids verified.json --ledger L`.
   `verified.json` lists track-record ids that `python3 -m praiser track-record --ledger L --verify record.json` re-derived
   (it prints `verified_id`).
7. **Reveal.** Append `lottery_reveal` the same way.
8. **Plan the audits.** `python3 -m wounder lottery plan --ledger L` lists the accepted cases a person must look at.
9. **Label later.** `python3 -m juridicator label --ledger L --repo R --head SHA --label accept|reject --by NAME`. Track
   records and precedents are built only from these.

## Shadow mode first

For the first weeks run steps 1 to 8 on real pull requests but let nothing depend on the verdict. Compare verdicts with
what people decide, and label every case. `integration/trust-check.yml.example` is a workflow template for that; it is
read-only and advisory by construction (no token that can write, no effect on merging).
