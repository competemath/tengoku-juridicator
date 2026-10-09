# Roadmap

Done in this seed: the contract, the statute, policy-as-data, precedents, ledger, marker, AI valve and calibration lock,
CLI, 70+ tests (the statute's tests were checked by deliberately breaking it).

Next, in order:
1. Wire the pipeline in shadow mode: run the juridicator on real Tengoku PRs, record verdicts, change nothing. Compare
   with what people decide. This is where labels start.
2. Planted-defect canaries running in the wounder against Tengoku's real gates; publish gate health as the standing input.
3. Signed records and a GitHub App identity for the judge's writes; publish the ledger head outside the repository.
4. Audit lottery with a committed-then-revealed salt (closes residual risk R3).
5. A live AI backend at level 1 (explanations only), then level 2, measured against labels.
6. Same shape applied to Leak submissions.
Deliberately not planned: letting any AI approve anything.
