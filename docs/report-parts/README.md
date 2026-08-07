# Report Components

## Mục đích

Thư mục này chứa các section độc lập để ghép thành `docs/report.md`; không ghi
đè report hiện tại. Requirement chuẩn là [`../requirement-checklist.md`](../requirement-checklist.md),
API chuẩn là [`../api-contract.md`](../api-contract.md).

## Thứ tự merge, owner và reviewer

| Thứ tự | File | Owner | Reviewer | Dependency |
|---:|---|---|---|---|
| 1 | 01-introduction | C | A | requirement |
| 2 | 02-requirement-analysis | A | B/C | checklist |
| 3 | 03-system-architecture | C | A/B | 01–02, API |
| 4 | 04-control-channel | A | C | API, architecture |
| 5 | 05-data-channel-rdt | B | A/C | API, architecture |
| 6 | 06-filesystem-security | C | A | API |
| 7 | 07-active-pasv | A/B | C | 04–05 |
| 8 | 08-concurrency-integration | C | A/B | 04–07 |
| 9 | 09-client-cli-logging | C | A | 08 |
| 10 | 10-testing-results | C | A/B | actual tests/evidence |
| 11 | 11-contribution | A/C | all | Git/peer agreement |
| 12 | 12-limitations-future-work | all | all | audit |
| 13 | 13-genai-usage | all | all | GenAI logs |
| 14 | 14-requirement-compliance | A | all | all sections |

Merge theo số thứ tự; mỗi owner sửa section của mình, editor cuối cùng là người
được nhóm chỉ định và phải ghi tên trong commit. Không chỉnh đồng thời cùng một
section; dùng một commit cho một component.

## Quy tắc bằng chứng và định dạng

- Hình: `docs/evidence/fig-<section>-<n>.<ext>`; bảng: `Table <section>.<n>`.
- Dẫn code bằng đường dẫn tương đối + symbol/function, không paste cả file.
- Dẫn test bằng lệnh, test name, ngày chạy và output lưu được; mock/sleep/compileall
  không phải evidence end-to-end.
- Trạng thái component luôn `Chưa hoàn thành` cho tới khi owner cập nhật bằng chứng.
- Không bịa test, benchmark, screenshot, diagram đã chạy, hash, Active/PASV hoặc
  concurrency. Dữ liệu thiếu phải là TODO cụ thể.
- Trước merge: link API/checklist đúng, requirement có owner, TODO có owner, diagram
  khớp code, test/evidence tồn tại, không mâu thuẫn reply/header/cleanup.
