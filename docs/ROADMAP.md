# Roadmap

Done: the contract, the statute (rules version 2), policy-as-data, precedents, ledger, marker, AI valve and calibration lock,
CLI, signatures and gate-health standing, the ledger-fixed audit lottery (in the wounder), and an end-to-end test of the
pipeline through the command lines. All of it checked by deliberately breaking it.

Next, in order:
1. Shadow mode on real Tengoku pull requests (`integration/trust-check.yml.example`): record verdicts, change nothing,
   compare with what people decide. This is where labels start.
2. Point the canaries at Tengoku's real gates (the corpus runs today against a reference text gate).
3. Give producers keys and turn `require_signatures` on; publish the ledger head outside the repository; a GitHub App
   identity for the judge's writes.
4. A live AI backend at level 1 (explanations only), then level 2, measured against labels.
5. Same shape applied to Leak submissions.
Deliberately not planned: letting any AI approve anything.
