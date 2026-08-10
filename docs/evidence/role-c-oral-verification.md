# Role C Oral Guide Verification — 10/08/2026

## Source audit

The guide follows this evidence order: official requirement/rubric, current
source code, current tests/evidence, API/technical docs, then planning. Stale
claims are not turned into oral answers.

Current implementation gaps intentionally left blank in the guide:

- functional MODE B/C data transformation;
- `STAT <path>` metadata flow;
- persistent buffered TCP reply framing;
- final contribution percentage;
- clean release commit/hash and team sign-off.

## Fresh Role C regression

```bash
wsl python3 -m pytest tests/test_filesystem_service.py \
  tests/test_transfer_manager.py tests/test_threaded_server.py \
  tests/test_e2e_transfer.py -q
```

```text
........................                                                 [100%]
24 passed in 31.37s
```

## Document QA

- Deliverable: `docs/Role-C-Oral-Guide.docx`.
- Builder: `docs/build_role_c_oral.py`.
- LibreOffice renderer was unavailable on the host.
- The document was exported to PDF with Microsoft Word, then rasterized with
  PyMuPDF.
- Final page count: 19.
- Visual inspection: 19/19 pages at original rendered resolution.
- Result: no clipped or overlapping text, no split table rows, consistent
  odd/even headers and footers, and explicit blank fields preserved.
