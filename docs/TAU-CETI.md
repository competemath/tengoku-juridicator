# Tau Ceti, and what this design takes, changes and does not yet match

Tau Ceti (github.com/TauCetiProject) is an AI-maintained Lean library downstream of Mathlib. Its agentic-security
practices were read from its public repositories (2026-10-09). This note is the honest accounting.

## What is taken

| Tau Ceti practice | Here |
| --- | --- |
| Reviewer prompt says all content is untrusted data, and an injection attempt is itself a finding | `ai.NOTICE` |
| One-time verdict marker; only text after the last one counts; fail closed | `marker.py` |
| Reviewers get a restricted tool set, enforced at the set level, with a regression test (their reviewer once still had a shell) | `ai.advise` refuses any tool; `tests/test_ai.py` |
| Agents never merge; a bot identity merges on independent signals | the juridicator is the only writer of the decision (roadmap: GitHub App) |
| Humans own rules, workflows and infrastructure paths; bots cannot earn reviewer trust | CODEOWNERS; the praiser's track record counts only human-confirmed outcomes |
| Approvals tied to an exact commit and rubric version | evidence binds to `head_sha`; verdict records `policy_sha256` |
| A written list of what is not solved | `SECURITY.md` |
| Append-only records built from platform data, not agent say-so | ledger; evidence must carry the command that reproduces it |
| Spend caps and round caps | wounder `budget.py` |
| Test the sandbox before trusting it | roadmap (needs the sandbox) |
| Compare-and-swap wrappers for git and PR writes | roadmap |

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
