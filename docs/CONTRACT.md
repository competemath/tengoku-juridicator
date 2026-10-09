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

## Rules added in version 2 (found by the sibling repositories while building against this one)

8. **Complete means every subject.** A manifest may list `details.expected`: a list of `{kind, subject}`. Each one must
   be reported by the same producer, or the case holds (R9). A manifest with only `checks` enforces the kind, not each subject.
   Give every canary case its own `subject`; without one, a pass and a fail on different cases look like a disagreement (R7).
9. **A manifest covers its own producer.** One manifest per producer identity. A manifest from one identity does not
   cover results from another, so each independent checker declares its own.
10. **A crash is not a pass.** An inconclusive mechanical or reproducible record that nobody passed for the same
    `(kind, subject)` holds the case (R12).
11. **Numbers somebody wrote down are not believed.** `reproducible.track_record` lowers scrutiny only when the caller
    re-derived it from the ledger (the praiser's `verify_against_ledger`) and passes its evidence id to the judge
    (`decide(..., verified=ids)`, CLI `--verified-ids`). Otherwise it is shown, not weighed.
12. **Which side is wrong?** `escalate_on_fail` (default `mechanical.restatement_match`) lists kinds whose failure
    goes to a person rather than rejecting, because either the original or the second reading may be the faulty one.
13. Records should carry only `{repo, head_sha, class}` in `case`, not the author.

## The ledger entry (not in the evidence file, so documented here)

An entry is `{seq, kind, body, prev, hash}` with `hash = "sha256:" + sha256(canonical_json({seq, kind, body, prev}))`
and `prev` of the first entry the genesis value `"sha256:" + "0" * 64`. Entry kinds: `evidence` (body is an evidence
record), `verdict` (body is a `tengoku-verdict/1`), and `label` (body `{repo, head_sha, label: "accept"|"reject", by}`),
which a person appends after the fact; track records count only labelled outcomes. The praiser re-implements this hash and
tests it against the real `Ledger`. The reference is `juridicator/ledger.py`.

## Vendoring

Each consumer keeps `vendor/juridicator_evidence.py` (a verbatim copy) and `vendor/EVIDENCE.sha256`. Its tests fail if the
copy no longer matches the pin, and `scripts/sync_contract.py --from <path to juridicator>` refreshes both.
