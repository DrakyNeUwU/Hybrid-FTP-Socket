# Hybrid FTP

Hybrid FTP dùng TCP cho control channel và UDP qua custom Reliable Data Transfer
(RDT) cho payload file. Dự án chạy bằng Python 3 trên Linux hoặc WSL2.

## Chạy và kiểm tra

Từ repository root:

```bash
python -m pip install pytest
python -m pytest -v
python -m server.threaded_server
```

Server mặc định lắng nghe tại `127.0.0.1:2121`. Dừng bằng `Ctrl+C`.

### Demo hai máy LAN

Trên máy server, thay `192.168.x.x` bằng IPv4 LAN thật:

```bash
python -m server.threaded_server --host 0.0.0.0 --port 2121 --advertise-host 192.168.x.x
```

Trên máy client cùng mạng:

```bash
python -m client.demo_transfer demo.bin --remote demo-lan.bin --mode PASV --host 192.168.x.x --port 2121
```

Mở firewall cho TCP/UDP port 2121 khi cần, rồi lưu terminal output, SHA-256 và
screenshot vào `docs/evidence/`. LAN hai máy chỉ được đánh dấu hoàn thành khi
có artifact thật; localhost E2E và LAN là các scope evidence khác nhau.

## Cấu trúc thư mục

```text
.
├── client/                     # Client FTP và CLI demo
├── server/                     # TCP server, command/session/transfer handling
├── common/                     # RDT, protocol và filesystem helpers dùng chung
├── tests/                      # Pytest unit, fault-injection và E2E
├── docs/                       # Contract, evidence, status, checklist và report
│   ├── project-status.md       # Source of truth trạng thái hiện tại
│   ├── requirement-checklist.md# Acceptance gate trước nộp
│   ├── api-contract.md         # Shared A/B/C contract
│   ├── report.md               # Report nộp cuối — Role B hoàn thiện
│   ├── report-parts/           # Draft: technical/ và submission/
│   └── evidence/               # Logs, hashes và screenshots đã xác minh
└── planning/                   # Requirement, ownership và kế hoạch tuần
    ├── Project1_SocketProgramming_2026.md  # Requirement gốc, chỉ đọc
    ├── Socket Role.md                       # Ownership gốc
    ├── status/                              # Điều hướng tới project status
    └── weekly-plans/                        # Kế hoạch/snapshot tuần 1, 2, 2.5, final
```

## Quy tắc tài liệu

- `planning/Project1_SocketProgramming_2026.md`: requirement gốc, không cập nhật tiến độ ở đây.
- `docs/project-status.md`: nguồn trạng thái duy nhất (`Done`, `In progress`, `Deferred`).
- `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md`: dashboard họp hằng ngày, owner, deadline, blocker và evidence.
- `docs/requirement-checklist.md`: kiểm tra đủ điều kiện trước nộp; mọi claim `Done` phải có evidence.
- `docs/report.md`: bản report nộp cuối, do Role B tổng hợp; Role A/C sign-off phần kỹ thuật của mình.
- `docs/report-parts/`: nội dung nháp/lịch sử, không dùng để kết luận trạng thái hiện tại.

## Quy ước Git

- `main`: code ổn định; merge qua Pull Request đã review.
- `dev`: nhánh tích hợp chung.
- `feature/role-a`, `feature/role-b`, `feature/role-c`: nhánh theo role.
- Commit message: `[role][module] mô tả ngắn`, ví dụ `[A][auth] implement USER/PASS command`.

Trước khi commit cấu trúc tài liệu đã di chuyển, chạy:

```bash
git add -A
git status --short --branch --untracked-files=all
git diff --check
```

`git add -A` giúp Git nhận diện các file được rename giữa `filephanchiacv/`,
`planning/` và `docs/report-parts/`.
