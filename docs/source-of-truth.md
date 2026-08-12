# Documentation Source of Truth — Hybrid FTP

This page tells the team which file to trust for each question. It is a map,
not another copy of the requirements or results.

## Read in this order

1. [Official project requirements](../planning/reference/Project1_SocketProgramming_2026.md) define what must be delivered.
2. Current source code and its automated tests define the behavior now present in the repository.
3. [Shared API contract](api-contract.md) defines the agreed A/B/C boundary: packet, endpoint, reply, ownership, and cleanup rules.
4. [Project status](project-status.md) is the only current acceptance and blocker status.
5. [Requirement checklist](requirement-checklist.md) maps requirements to evidence.
6. Dated files in [evidence/](evidence/) are proof only for the command or demo they record.

## Supporting documents

- [Hybrid_FTP_Technical_Report.pdf](Hybrid_FTP_Technical_Report.pdf) is the
  final team submission artifact. Use it for submission/review; its technical
  claims must remain traceable to the authoritative sources above.
- [report.md](report.md) and [report-parts/](report-parts/) are submission
  narrative; they must follow the sources above.
- [code-change-history.md](code-change-history.md) and `genai-log-*.md` are
  historical records, not current requirements or status.
- [planning/](../planning/) tracks work plans. A plan does not override the
  official requirement, current contract, implementation, or acceptance state.

## When files disagree

- Requirement conflict: follow the official project requirement and update the
  contract/checklist before declaring the work complete.
- Contract or documentation conflict with code: do not guess. Run the relevant
  test, record the result, then update the stale document in the same change.
- Status claim: it is valid only when `project-status.md` links to concrete
  evidence (a command, log, hash, screenshot, or test result).

**Updated:** 12/08/2026. Keep this file short; add links and ownership rules,
not duplicated technical content.
