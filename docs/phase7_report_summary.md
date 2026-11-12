# Phase 7 summary: final report

Status: complete; waiting for `continue` before Phase 8.

## Deliverables
- `report/report.docx` (A4, 34 pages) and `report/report.pdf` (the same document rendered by LibreOffice).
- `report/report_source.md`: the same content as Markdown, for reading and diffing. `report/content.json`: the block list rendered by `scripts/render_report.js`.
- `docs/report_numbers.yaml`: all 579 result numbers shown in the report. Each entry records the source file, the locator, the raw value and the displayed text.
- New scripts:
  - `scripts/report_lib.py`: number readers and formatter;
  - `scripts/build_report_content.py`: report text;
  - `scripts/render_report.js`: docx rendering;
  - `scripts/toc_pages.py` and `scripts/build_report.sh`: two-pass build with the contents page;
  - `scripts/make_report_diagrams.py`: Fig. 0a and Fig. 0b.
- Verifier check V7, added to `scripts/verify_results.py`, runs 6 checks:
  - every registered value equals its source;
  - every value is formatted correctly;
  - every value appears in the .docx;
  - all 14 figures are embedded;
  - all captions are present;
  - the report is 25–40 pages long.

  The full verifier now reports **278 checks passed, 0 failed**: the previous 272 plus the 6 V7 checks.
- Updated documents: `README.md`, `docs/design_decisions.md` (D28), `docs/deviations_log.md` (N4, a note that nothing in the analysis changed), `results/manifest.json` (2,436 files).

## Report structure
- Front matter: title page, summary and contents.
- Sections 1–14 as required:
  1. RQ and hypotheses; review changes; evidence labels.
  2. Background and notation table.
  3. Formal problem (R1).
  4. Environment, with diagrams.
  5. Calibration (R3).
  6. Algorithms, with IQL pseudocode.
  7. Metrics.
  8. Protocol.
  9. Results.
  10. Attribution (R2) and what we can and cannot conclude.
  11. Generalisation.
  12. Limitations.
  13. Reproducibility.
  14. Eight success criteria.
- References: [1]–[7] from the proposal, and [8]–[14] added and marked "added, verify".
- Appendices:
  - A. Hyperparameters.
  - B. Decision log D1–D27.
  - C. Deviations log.
  - D. Glossary.
  - E. Review Response Matrix.
  - F. File map.
- Content: 14 figures (figure numbers match the result file names) and 25 tables.

## How the five points the group stressed are handled
1. **Non-convergence.**
   - The summary, Section 9.1, Section 10.7, the first limitation and Section 14 all state it.
   - Every result is described as "after 8,000 episodes".
   - Only 5/350 runs are stable (0/40 main runs), and the stable-run sensitivity analysis could not be computed.
2. **A3 is scale- and calibration-dependent.**
   - H5 is reported as significant in the opposite direction.
   - Table 15 shows all six DiD analyses with their family labels.
   - The interpretation covers floor effects, the proportional reversal (post hoc) and the own-calibration null.
   - We make no cooperation-bottleneck claim.
3. **Confirmatory, secondary, exploratory and post hoc analyses are kept apart.**
   - Section 1.5 defines the labels.
   - Each table caption and result paragraph carries its label.
   - The log-scale A3 analysis is marked post hoc wherever it appears.
4. **A8 is association only.** It is stated in the summary, in Section 10.8 (bold), in the Fig. 8 caption and in the limitations.
5. **Other limits are stated:**
   - A4 is confounded by distribution shift.
   - The greedy baseline moves in lockstep and is read as "uncoordinated identical agents"; IQL is not better than it at Critical (p = 0.0742).
   - The study uses 10 seeds; non-significant results are called inconclusive.

## Checks run
- `bash scripts/build_report.sh`: contents page numbers stable between passes.
- `python scripts/verify_results.py`: 278 passed, 0 failed.
- `pytest`: 261 passed.
- Visual inspection of every page of the PDF:
  - fixed a blank page before the contents;
  - fixed wrapped pseudocode;
  - fixed the broken step-pipeline diagram;
  - corrected four figure captions that described panels the figures do not have.
- Content corrections made while reviewing against the sources:
  - **Proposal references.** [2], [5] and [6] were corrected to the exact entries in the proposal.
  - **A1 relative drops.** The text said 20–26%; it now gives the registry values 23%, 26% and 24%.
  - **Observation features f1–f2.** The descriptions were corrected to match the spec.
  - **Feasibility definition.** It now uses the spec's exact check rather than "oracle rescues ≥ 1".
  - **Interpretive sentences.** Several were softened to "plausibly" or "most likely" where they go beyond the data.
