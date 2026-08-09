# Report Parts — Draft Workspace

> **Không phải trạng thái hiện tại hoặc bản nộp.** `docs/report.md` là report
> nộp cuối đang do Role B hoàn thiện. Xem `docs/project-status.md` cho trạng
> thái vận hành và `docs/requirement-checklist.md` cho acceptance trước nộp.

## Cấu trúc

```text
docs/report-parts/
├── README.md
├── technical/       # Nội dung kỹ thuật theo luồng kiến trúc và triển khai
│   ├── 01-introduction.md
│   ├── 02-requirement-analysis.md
│   ├── 03-system-architecture.md
│   ├── 04-control-channel.md
│   ├── 05-data-channel-rdt.md
│   ├── 06-filesystem-security.md
│   ├── 07-active-pasv.md
│   ├── 08-concurrency-integration.md
│   └── 09-client-cli-logging.md
└── submission/      # Evidence, contribution và kiểm tra trước nộp
    ├── 10-testing-results.md
    ├── 11-contribution.md
    ├── 12-limitations-future-work.md
    ├── 13-genai-usage.md
    └── 14-requirement-compliance.md
```

## Ownership và thứ tự hoàn thiện

| Nhóm | Parts | Owner chính | Review |
|---|---|---|---|
| Technical | 01, 03, 06, 08, 09 | C | A/B theo phần liên quan |
| Technical | 02, 04 | A | B/C |
| Technical | 05 | B | A/C |
| Technical | 07 | A/B | C |
| Submission | 10 | C | A/B |
| Submission | 11 | A/C | Cả nhóm |
| Submission | 12–13 | Cả nhóm | Cả nhóm |
| Submission | 14 | A | B/C |

Role B là editor của `docs/report.md`. Không sửa trực tiếp report của B từ các
draft này; owner chỉ cung cấp phần kỹ thuật đã review cùng evidence.

## Quy tắc dùng draft

- Chỉ đưa claim vào `docs/report.md` khi có evidence trong checklist/log/hash.
- Giữ `TODO` và trạng thái lịch sử trong draft cho đến khi owner cập nhật; không
  dùng chúng để kết luận tiến độ dự án.
- Dẫn test bằng lệnh, ngày chạy và artifact lưu được. Không dùng mock, sleep hay
  compile-only làm evidence end-to-end.
- Mỗi phần merge theo ownership, có reviewer, và không được mâu thuẫn với
  `docs/api-contract.md` về reply, RDT header hay cleanup.
