# Hybrid FTP — Đồ án Internetworking Protocol

Ứng dụng FTP lai (Hybrid FTP): control channel qua TCP, data channel qua UDP
với tầng Reliable Data Transfer (RDT) tự cài đặt.

## Thành viên & Vai trò

| Role | Người | Phụ trách |
|---|---|---|
| A | ___________ | TCP Control Channel & Session |
| B | ___________ | UDP Data Channel & RDT |
| C | Khánh | File/Concurrency & Integration (Leader) |

## Cấu trúc thư mục

```
.
├── client/         # Code phía client
├── server/         # Code phía server
├── common/         # Code dùng chung: RDTHeader, reply codes, protocol constants
├── docs/           # Technical report, protocol spec, diagrams
│   ├── protocol-spec.md
│   ├── report.md
│   └── genai-log-<role>.md
├── tests/          # Unit test cho từng module
└── phan-chia-cong-viec.md
```

## Môi trường

- **Ngôn ngữ:** Python 3.x
- **Hệ điều hành:** Linux (native hoặc WSL2)
- **Chạy thử:**
  ```bash
  python3 server/server.py
  python3 client/client.py
  ```

## Quy ước Git

- `main` — code ổn định, chỉ merge qua Pull Request đã review
- `dev` — nhánh tích hợp chung
- `feature/role-a`, `feature/role-b`, `feature/role-c` — nhánh làm việc riêng từng role

**Commit message:** `[role][module] mô tả ngắn`, ví dụ: `[A][auth] implement USER/PASS command`

**Trước khi merge vào `dev`/`main`:** cần ít nhất 1 người khác review PR.

## Tài liệu liên quan

- Spec giao thức dùng chung: [`docs/protocol-spec.md`](docs/protocol-spec.md)
- Kế hoạch phân chia công việc: [`phan-chia-cong-viec.md`](phan-chia-cong-viec.md)
- Báo cáo kỹ thuật: [`docs/report.md`](docs/report.md)
