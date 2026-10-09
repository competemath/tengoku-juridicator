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
4. **The AI never reads raw untrusted text.** It sees evidence records, whitelisted fields only, with control and invisible
   characters stripped, lengths capped, anything shaped like a verdict marker neutralised and anything shaped like a secret
   redacted. The prompt is the warden's (`vendor/warden/untrusted.py`, notice v2): the notice that all of it is data comes
   first, the evidence sits inside a fence whose delimiter is random for every call, and the marker instruction comes last.
   A planted instruction is a finding to report, not something to resist quietly. **The reader is told when it did not see
   everything**: records dropped by the 200-record cap, and characters dropped by the character cap, are stated in the
   prompt, and the reader is told not to answer "none" on a partial view.
5. **A fresh marker per call; only the text after the last marker is read; the whole answer is validated.** Anything planted
   earlier, including a ready-made "approved" object, is discarded. The answer is `{verdict, summary, findings}` checked against
   the warden's closed schema (`vendor/warden/verdict.py`): unknown keys, wrong types, a boolean posing as a line number, an
   absolute path, duplicate keys and NaN are all refused, and a malformed `findings` list is "no answer", never a crash. A missing
   marker, bad JSON or a verdict outside `none/hold/escalate` means "no answer", and no answer changes nothing.
   **An `injection_attempt` finding is grounds to escalate**: if the reader reports one on a case that was about to be
   accepted, the case becomes ESCALATE whatever verdict the reader gave, because text in the evidence tried to talk to the
   reader and a person should see it. It is never grounds to accept.
6. **No tools, no network, no secrets.** A backend that exposes any tool is refused before it is called
   (`ToolsNotAllowed`). The check reads the tool set itself rather than trusting a flag, because Tau Ceti found a reviewer
   whose "read-only" flag still had a shell (see "Tool sets, not flags" below). Secrets in evidence text are redacted before
   the model sees them (`secretscan.redact`).
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

## Tool sets, not flags

The rule behind principle 6, written the way `tengoku-warden`'s `toolpolicy` writes it, because the judge's backend is one
more agent CLI that someone will wire in:

- **The restriction is a set, and it is stated as a set.** For the Claude CLI that is `--tools`, which decides which built-in
  tools exist (`--tools=""` for none). `--allowedTools` only pre-approves tools and `--disallowedTools` only denies named ones:
  neither removes a tool that nobody thought to name. A launch that passes a deny-list or `--allowedTools` without `--tools`
  is a violation, and so is `--tools default`. Tau Ceti's reviewer ran for about 79 days with `--allowedTools` alone (their
  TauCetiReview PR #123, 2026-08-21: Bash in 295 of 427 traced calls).
- **The judge's backend has the empty set.** The Python-level guard in `ai.advise` (`backend.tools` must be `()`) is the
  last line; the launcher is the first. MCP servers count as tools: use `--strict-mcp-config` so that ambient servers from the
  user's or the repository's configuration add nothing.
- **A flag in a test is a record, not a defence.** A test that pins the permissive flags documents the exposure. What
  protects is a check on the argv that is actually built (`warden toolpolicy check-argv`), a scan of the source that builds
  it (`warden toolpolicy scan-source`, which fails on any spawn site that relies on a deny-list) and an audit of what the
  agent really did (`warden toolpolicy audit-trace` on the `stream-json` trace of every run).
- **The trace audit is evidence.** A run's audit, and the escape battery that ran as the agent's identity before it started,
  become `mechanical.agent_contained` (praiser) and `mechanical.jail_selftest` (wounder) records; see `docs/CONTRACT.md`. This
  repository never runs them; it only weighs them.
- **Authority of the answer does not depend on any of this.** Even a perfectly confined reader that is fully persuaded can only
  make a case more cautious. Confinement limits what a persuaded reader can reach; the one-way valve limits what it can decide.

## What the AI may do in the other two repositories

- **Wounder:** propose near-miss variants of a formal statement and propose new planted-defect cases, as data only. The
  output is validated against a schema, never executed, and a person promotes a proposed case into the corpus.
- **Praiser:** produce a second, blind formalization of a problem from its plain-language statement. A machine then
  checks whether the two statements are equivalent. The AI proposed; the check is the evidence.

## Who owns what now

| Mechanism | Owner | Why |
| --- | --- | --- |
| The prompt notice, fences, templating, marker, answer schema | `tengoku-warden` (vendored here, pinned in `vendor/warden/PIN`) | one implementation for every reader of untrusted text in Tengoku, including this one |
| The valve (`apply_advice`), the refusal of any backend with tools, the choice of verdicts | this repository | it is the decision, and decisions are the juridicator's |
| Checking that the warden's gates hold (secret scan, scope, marker, tool policy, environment) | `tengoku-wounder` (`agent-canaries`) | a gate nobody attacks is a gate nobody knows works |
| Measuring injection resistance of a backend, running the escape battery | `tengoku-warden` code, run and recorded by the wounder (`injection-eval`, `jail-selftest`) | evidence about a backend or a jail, not a decision |
| Turning a trace audit and an escape battery into a reason to trust a run | `tengoku-praiser` (`agentrun`) | falsifiable, re-runnable, weighed here |

## What no AI is ever asked to do

Decide that a proof is valid. Decide that a statement is faithful without a machine comparison behind it. Grade its own
work or the work of the same model family at a high tier. Read credentials, run commands or browse. Choose which
evidence the judge sees.

## Cost

AI calls are the expensive, slow, least predictable part, so they sit last in the order of work and behind a spending cap
(see the wounder's `budget.py`). A case that fails a cheap deterministic check never reaches them.
