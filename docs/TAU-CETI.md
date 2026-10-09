# Tau Ceti, and what this design takes, changes and does not yet match

Tau Ceti (github.com/TauCetiProject) is an AI-maintained Lean library downstream of Mathlib. Its agentic-security
practices were read from its public repositories (2026-10-09). This note is the honest accounting.

## What is taken

| Tau Ceti practice | Here |
| --- | --- |
| Reviewer prompt says all content is untrusted data, and an injection attempt is itself a finding (TauCetiReview `rubrics/_common.md`, PR #17) | the warden's notice v2 (`vendor/warden/untrusted.py`), used by `ai.build_prompt`; see [tengoku-warden `docs/TAU-CETI.md`](https://github.com/competemath/tengoku-warden/blob/main/docs/TAU-CETI.md) |
| One-time verdict marker; only text after the last one counts; fail closed (TauCetiReview `runner/verdict.py`) | the warden's `verdict` (vendored), wrapped by `marker.py`; the whole answer is schema-validated |
| Reviewers get a restricted tool set, enforced at the set level, with a regression test (their reviewer once still had a shell; TauCetiReview PR #123) | `ai.advise` refuses any tool; `tests/test_ai.py`; the argv checker, source scanner and trace audit live in the warden's `toolpolicy` (`docs/AI-USE.md`, "Tool sets, not flags") |
| Agents never merge; a bot identity merges on independent signals | the juridicator is the only writer of the decision (roadmap: GitHub App) |
| Humans own rules, workflows and infrastructure paths; bots cannot earn reviewer trust | CODEOWNERS; the praiser's track record counts only human-confirmed outcomes |
| Approvals tied to an exact commit and rubric version | evidence binds to `head_sha`; verdict records `policy_sha256` |
| A written list of what is not solved | `SECURITY.md` |
| Append-only records built from platform data, not agent say-so | ledger; evidence must carry the command that reproduces it |
| Spend caps and round caps | wounder `budget.py` |
| Test the sandbox before trusting it | the warden's escape battery (`selftest`); the wounder records a run as `mechanical.jail_selftest`, the praiser folds it into `mechanical.agent_contained` |
| Compare-and-swap wrappers for git and PR writes | roadmap |

## What the warden took over, and what each repository owns now

After the first version of this note, Tengoku gained a fourth repository, [tengoku-warden](https://github.com/competemath/tengoku-warden),
which treats every agent as an untrusted party and carries the agent-security mechanisms. Some of what this note listed as taken
from Tau Ceti or marked "roadmap" now lives there, and this repository uses it instead of keeping a private copy:

| Mechanism | Tau Ceti origin (what they did and found) | Where it lives now |
| --- | --- | --- |
| Untrusted-content notice, fences, one-pass templating | TauCetiReview PR #17 (preamble); TauCetiProgress `context.py` (fencing); TauCetiWorker PR #178 (sequential substitution bug) | warden `untrusted`, vendored here; the judge's prompt is built with it. Changes against our first version: the reader is told when records or characters were dropped (Tau Ceti cut diffs at 120,000 characters without telling reviewers: 477 of 609 truncated runs were approved), and fences are random per call |
| Verdict marker and answer validation | TauCetiReview `runner/verdict.py`; PR #122 (2026-09-02: a parser crash ended a paid round) | warden `verdict`, vendored here. Our first `marker.extract` read only `action`; now the whole answer is validated, `injection_attempt` is a category, and an injection finding escalates (`ai.apply_advice`) |
| Tool-set restriction, trace audit, spawn-source scan | TauCetiReview PR #123 (Bash reachable for ~79 days; 295 of 427 traced calls) | warden `toolpolicy`; documented for the judge's backend in `docs/AI-USE.md` |
| Secret redaction, environment allowlists, escape battery, scope guard | TauCetiWorker `review_diagnostics.py`, host mode environment inheritance, TauCeti `pr-build.yml` self-test, `scope` status | warden `secretscan`, `envscrub`, `selftest`, `scope`. Not used by this repository's code except `secretscan.redact` on what the AI reads |

Ownership, so nobody keeps two copies of a rule:

| Repository | Owns |
| --- | --- |
| tengoku-warden | the agent-security mechanisms above, their reports, and the injection payload set |
| tengoku-wounder | attacking our own gates, now including the warden's: `agent-canaries` (`mechanical.agent_canary`), `injection-eval` (`mechanical.injection_eval`), `jail-selftest` (`mechanical.jail_selftest`) |
| tengoku-praiser | the reason to trust one run: `mechanical.agent_contained` from a trace audit and an escape battery, and the tool-policy and jail-spec facts in the provenance declaration |
| tengoku-juridicator (this one) | weighing all of it with the statute; the AI valve; vendors the prompt and marker code, runs none of the audits |

## What differs, and why it may be better

1. **An adversary role that never stops.** Tau Ceti ran one nine-angle audit. Here planted-defect canaries run
   continuously and the judge refuses to accept anything while the gate's health is unproven (R11).
2. **Evidence has a ladder.** Only claims someone else can re-run carry decisive weight; opinions and attestations can
   make a case more cautious but never less. Tau Ceti's gate is largely AI reviewers' judgments of a whole change.
3. **Checkers that disagree escalate.** A disagreement between two proof checkers may be a bug in one of them, which is
   the most valuable thing the system could learn, so it is surfaced, not outvoted.
4. **No cherry-picking.** Producers pre-declare what they will report; silence holds the case.
5. **A one-way valve with a locked ladder for AI**, measured before it is widened. Tau Ceti's AI reviewers are the gate.
6. **Falsifiable reputation.** Praise for a system, prompt or team counts only when it can be checked (provenance that
   matches stored files, a rebuild that matches, a track record computed from the ledger) and only to lower scrutiny by
   one step, never to override a failure.
7. **Comparison with similar past cases** is deterministic, and history can only raise scrutiny.

## Where Tau Ceti is ahead (and this is a seed)

They run in production: real merges, a GitHub App with per-step minimal tokens, an offline sandbox that tests itself
before every run, a container isolation layer with a scoped proxy, spend caps in use, and a pipeline of human labels
used to calibrate their AI judges. Here there is a decision engine and its tests, a contract, documents and a first
cut of the other two repositories. No bot, no sandbox, no live AI backend, no signed ledger.

## Is the three-part split an improvement?

Probably, for this kind of content, and for reasons that do not depend on three AIs arguing:

- It separates *permissions*: the party that hunts for faults has no write access, the party that argues credibility
  cannot write verdicts, and only the judge's output gates anything. Separate repositories make that a real boundary.
- It makes the *evidence the product*. Every decision can be re-derived from records anyone can re-run.
- It lets the cheap, objective part (Lean makes this unusually rich) carry most of the weight, so the AI parts stay small,
  bounded and measured.

What it does not do: create independence by itself. If one model family plays all three roles, the debate adds little;
the gain is in the objective checks, the recorded labels and the refusal to let praise outweigh a failure. The honest
test of whether it is better is practical: does it catch planted defects that a single AI reviewer misses, at a cost the
project can afford? The canary corpus and the labels are how that gets measured.

Better in the future when AI-generated content outgrows what people can read, because the evidence and labels
accumulate and make each later decision cheaper and better calibrated. Not better if volume stays small enough for a
person to just read everything, or if nobody labels cases, in which case it stays at its safe defaults and adds only
overhead.
