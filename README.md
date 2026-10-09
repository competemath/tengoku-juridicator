# tengoku-juridicator

One program in three repositories, for deciding whether AI-generated content should be trusted into Tengoku:

| Repository | Role | One line |
| --- | --- | --- |
| [tengoku-wounder](https://github.com/competemath/tengoku-wounder) | challenge | tries to find how bad content would slip through; keeps the gate honest |
| [tengoku-praiser](https://github.com/competemath/tengoku-praiser) | credibility | gathers reasons to trust content that anyone can re-check |
| **tengoku-juridicator** (this one) | decision | weighs both with a fixed statute, history and a tightly leashed AI |

The three share one thing, the evidence record. Read `docs/DESIGN.md` first, then `docs/AI-USE.md` (how AI is, and is not,
used), `docs/SECURITY.md` (what is defended and what is not), `docs/TAU-CETI.md` (what was taken from Tau Ceti and how this
differs) and `docs/CONTRACT.md`.

## The rules in plain words

- A failed check that someone can re-run rejects the content, however good its reputation.
- Praise nobody can check counts for nothing. Checkable merit can lower scrutiny by one step, never buy acceptance.
- If two proof checkers disagree, a person looks. It may be a bug in a checker.
- If a producer said it would run some checks, it must report all of them. Silence is not a pass.
- If the gate itself is not proven healthy, nothing is accepted.
- AI may make a decision more cautious. It may never approve, reject or overrule.

## Use

```bash
python3 -m juridicator judge --case case.json --evidence evidence/ --standing standing.json --ledger ledger.jsonl
# exit 0 ACCEPT, 10 HOLD, 11 ESCALATE, 12 REJECT, 2 bad input
python3 -m juridicator ledger-verify --ledger ledger.jsonl
python3 -m unittest discover -s tests
```

Standard library only; no network; no AI is called unless a backend is wired in (none is).

## Status

A seed: the decision engine and its tests are real; the pipeline wiring, signing, sandbox and live AI backend are on
`docs/ROADMAP.md`. Private while it matures.
