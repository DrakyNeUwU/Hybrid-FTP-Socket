# 10. Testing Results

**Trạng thái:** Hoàn thành một phần
**Mục tiêu:** Separate unit, fault-injection, integration and demo evidence.  
**Requirement:** RQ-09, RQ-10. **Owner:** C. **Reviewer:** A/B.  
**Source:** `tests/`, `../../requirement-checklist.md`.  
**Code:** all production modules.

**Diagram/table:** test matrix by command, mode, data type and fault.  
**Test/evidence:** WSL2 `python3 -m pytest -q`: **189 passed in 113.94s**;
saved as `docs/evidence/week-2.5-pytest.log`. Production E2E (Active, PASV,
three concurrent PASV clients, ABOR, disconnect): **5 passed in 18.03s**;
saved as `docs/evidence/week-2.5-e2e-transfer.log`.

**TODO(C):** Add cross-machine/LAN evidence if it is required for submission.

**DoD:** Localhost evidence-backed rows are verified; cross-machine remains
pending.
