# How AI is used in this program, and where it is not

The whole program exists because AI wrote content that people now have to trust. So the rule for using AI inside the
program is stricter than the rule for the content it checks. Ten principles, each one enforced by code or a test, not
by a promise.

1. **AI proposes, machines dispose.** Anything that can be checked by a deterministic tool (a proof checker, a linter,
   a rebuild, a hash) is checked by that tool. An AI's statement that "this is correct" is never evidence of
   correctness. An AI may *produce* something a machine then checks: a second formalization of a problem, a variant of a
   statement, a new test case. The machine's verdict is the evidence; the AI is only labeled as the proposer.
2. **The judge's AI is a one-way valve.** Inside the juridicator an AI may be asked one question: should a careful person
   look at this before it is accepted? It can make a case more cautious (ACCEPT becomes HOLD or ESCALATE). It cannot
   approve, cannot reject, and cannot undo what another rule decided. `ai.apply_advice` is the only place this happens;
   `tests/test_ai.py` tries every action against every decision.
3. **Deterministic first, AI after.** The statute runs first. AI is consulted only on cases it already accepted, so a
   mechanical failure never costs an AI call and an AI outage never blocks a rejection.
4. **The AI never reads raw untrusted text.** It sees evidence records, whitelisted fields only, control characters
   stripped, lengths capped, anything shaped like a verdict marker removed, and a notice that all of it is data, never
   instructions. A planted instruction is a finding to report, not something to resist quietly.
5. **A fresh marker per call; only the text after the last marker is read.** Anything planted earlier, including a
   ready-made "approved" object, is discarded. A missing marker, bad JSON or an action outside `none/hold/escalate`
   means "no answer", and no answer changes nothing.
6. **No tools, no network, no secrets.** A backend that exposes any tool is refused before it is called
   (`ToolsNotAllowed`). The check reads the tool set itself rather than trusting a flag, because Tau Ceti found a reviewer
   whose "read-only" flag still had a shell.
7. **Everything AI-made is labeled.** Every evidence record says whether AI was used, in which role, which model, which
   prompt hash and which model family. That is what makes it possible to measure an AI later and to refuse a reviewer
   that shares the author's model family at higher scrutiny tiers.
8. **Staged trust, measured.** Level 0: AI ignored. Level 1: AI writes an explanation, no effect. Level 2: AI may make a
   case more cautious. Level 3, where AI could move a non-failing case between scrutiny tiers, is locked and cannot be
   switched on by configuration. It opens only in code (`calibration.level3_allowed`) after hundreds of human-labeled
   cases show zero missed bad cases and a high agreement rate with the small-sample doubt counted against it.
9. **Fail toward caution, not toward nothing.** An unreadable or missing AI answer is "no advice", not a default. A policy
   may mark AI review required; then its absence holds acceptance. By default an outage costs nothing.
10. **AI cannot write the rules.** The policy, the statute, the canary corpus and the rubrics are human-owned files. An
    AI may suggest a change in a pull request like anyone else; it cannot merge it (see SECURITY.md, code owners).

## What the AI may do in the other two repositories

- **Wounder:** propose near-miss variants of a formal statement and propose new planted-defect cases, as data only. The
  output is validated against a schema, never executed, and a person promotes a proposed case into the corpus.
- **Praiser:** produce a second, blind formalization of a problem from its plain-language statement. A machine then
  checks whether the two statements are equivalent. The AI proposed; the check is the evidence.

## What no AI is ever asked to do

Decide that a proof is valid. Decide that a statement is faithful without a machine comparison behind it. Grade its own
work or the work of the same model family at a high tier. Read credentials, run commands or browse. Choose which
evidence the judge sees.

## Cost

AI calls are the expensive, slow, least predictable part, so they sit last in the order of work and behind a spending cap
(see the wounder's `budget.py`). A case that fails a cheap deterministic check never reaches them.
