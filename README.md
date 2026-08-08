# Hybrid FTP — Đồ án Internetworking Protocol

Ứng dụng FTP lai (Hybrid FTP): control channel qua TCP, data channel qua UDP
với tầng Reliable Data Transfer (RDT) tự cài đặt.

## Chạy demo trên hai máy cùng LAN

Trên máy chạy server, thay `192.168.x.x` bằng IPv4 LAN của máy đó. `--host
0.0.0.0` cho phép nhận kết nối từ mạng; `--advertise-host` bảo đảm PASV trả về
đúng IP mà máy client có thể kết nối.

```bash
python -m server.threaded_server --host 0.0.0.0 --port 2121 --advertise-host 192.168.x.x
```

Trên máy client cùng mạng, chạy:

```bash
python -m client.demo_transfer demo.bin --remote demo-lan.bin --mode PASV --host 192.168.x.x --port 2121
```

Mở firewall cho TCP/UDP port 2121 nếu hệ điều hành hỏi. Lưu output và SHA-256
vào `docs/evidence/` sau khi demo thành công.

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
