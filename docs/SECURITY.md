# Threat model and residual risks

Written the way Tau Ceti writes theirs: what is defended, how, and, just as important, what is *not* solved.
Nothing here has been through an outside audit. It is a seed.

## What is protected

The decision to accept AI-generated content into Tengoku; the evidence behind it; the ledger that records both; the
policy and statute that turn one into the other.

## Who is assumed hostile or unreliable

| Party | Why it is not trusted |
| --- | --- |
| The agent that wrote the content | may lie about its work, claim checks it did not run, plant text aimed at a reviewer |
| Any AI reviewer, including this program's own | can be prompt-injected, can share the author's blind spots |
| The wounder and the praiser | can be wrong, can cherry-pick what they report, can be compromised |
| Content under review (diffs, docstrings, comments) | untrusted data, never instructions |
| The people running it | can make mistakes; the design records what happened so mistakes are visible |

## Defences

| Threat | Defence | Where |
| --- | --- | --- |
| Author vouches for own work | author evidence may only attest; attestations carry no weight | `statute.py` R0 |
| Praise outweighs a failed check | failed mechanical check rejects regardless of merit; attested praise has weight zero | R1, tests |
| Checker bug accepts a bad proof | checkers that disagree escalate to a person instead of voting | R7 |
| Selective reporting | declared manifests must be reported in full; silence holds the case | R9 |
| Stale or misfiled evidence | evidence binds to the exact commit; anything else is ignored | R0 |
| Gate quietly stops working | planted-defect canaries must keep failing; unproven gate health holds everything | R11 |
| Prompt injection into an AI reader | whitelisted sanitized input, the warden's notice with per-call random fences, truncation told to the reader, one-time marker with a validated answer schema, no tools, one-way valve, an injection report escalates | `ai.py`, `marker.py`, `vendor/warden/` |
| Drift in the vendored warden code | hash pin with the warden commit; a test fails on any difference | `vendor/warden/PIN`, `tests/test_warden_vendor.py` |
| AI reviewer shares author's blind spots | model family recorded; same family is not independent at higher tiers | R10 |
| Tampering with history | hash-chained ledger; publish the head where authors cannot edit | `ledger.py` |
| Author grinds commits to dodge audits | audit sampling uses a salt the author cannot see until later (see R3 below) | wounder `sampler.py` |
| Policy drift | policy hashed into every verdict; policy files are owned by people only | `policy.py`, CODEOWNERS |

## Residual risks (not solved)

- **R1 Prompt injection cannot be eliminated.** No wording makes a model immune. The design contains it: the AI has no
  tools, sees sanitized records, and can only make a case more cautious. A fully injected judge-AI can at worst waste a
  person's time.
- **R2 Independence is partly a fiction while one model family does most of the work.** Authoring, wounding and
  praising may all be the same family. The design's value comes from objective checks and recorded labels, not from the
  roles disagreeing. Tau Ceti states the same limit for their two reviewers.
- **R3 Sampling-seed grinding, and the withheld reveal.** The audit lottery's salt is committed (as a hash) in the ledger
  before a batch and revealed after, and the wounder's `lottery plan` fixes batches by ledger order, flagging any verdict
  written outside a batch for audit. What remains: whoever holds the salt can withhold the reveal. A batch left open is
  listed as pending, so it is visible, but not prevented.
- **R4 The ledger is tamper-evident, not signed.** Someone with write access to the repository who also rewrites the
  published head defeats it. Publish `head()` somewhere the author cannot edit; a GitHub App identity for writes is on the roadmap.
- **R5 Producer identity needs a key.** Records can be signed (`signing.py`, SSH signatures checked against the
  maintainers' `allowed_signers`), and with `require_signatures` unsigned mechanical, reproducible and judgment records are
  ignored. Off by default until producers have keys. A stolen key signs anything; signing proves who, not that their tool was honest.
- **R6 The canary corpus only covers defects we thought of.** It guards against regressions and known tricks, not
  unknown ones. The sensitivity probes and the red-team loop are meant to widen it; neither is a guarantee.
- **R7 Human labels are scarce.** Calibration, the precedent signal and any move past AI level 2 all depend on people
  labeling cases. Without labels the system stays at its cautious defaults, which is the safe failure.
- **R8 Reputation can be gamed.** A track record can be built with easy cases. It is therefore ledger-derived, counts
  only human-confirmed outcomes, penalizes a confirmed bad acceptance heavily, decays, and can lower scrutiny by one
  step at most, only together with independent checkers, a matching rebuild and consistent provenance.
- **R9 Evidence flooding.** An adversary can submit enormous amounts of harmless evidence to bury the one record that
  matters or run up cost. Records are size-capped, the judge reads structured fields, AI sees a bounded subset, and spend
  is capped; a flood is not yet rate-limited at the source.
- **R10 Complexity is itself a risk.** More parts, more places to be wrong. The statute is small on purpose, has no
  clock, randomness or network, and is attacked by its own tests (a mutation run in development broke the rules one by
  one to confirm the tests notice).

## What is not claimed

That accepted content is correct. The program lowers the chance that a bad submission is accepted and makes the reasons
for each decision reviewable; it does not prove correctness, and the proof checkers remain the ground truth for proofs.
