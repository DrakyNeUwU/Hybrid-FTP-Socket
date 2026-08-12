# Screenshots — Evidence Collection Log

> Danh mục bằng chứng screenshots và vị trí nhúng trong `docs/report.md`.

## 1. Ảnh chính (nhúng trong report)

| # | File | Nội dung | Vị trí trong report.md |
|---:|---|---|---|
| 01 | `evidence/screenshots/01-full-pytest-271-passed.png` | Full WSL2 regression — **271 passed** | §7 (intro, figure full regression) |
| 02 | `evidence/screenshots/02-lan-pasv-server-lifecycle.png` | LAN PASV server lifecycle (client sessions + luồng `150 → 226`) | §7.1 |
| 03 | `evidence/screenshots/03-sha256-pasv-active.png` | So sánh SHA-256 PASV và ACTIVE (source/server/download khớp) | §7.3 |
| 04 | `evidence/screenshots/04-three-pasv-clients.png` | Ba PASV client transfer độc lập không block nhau | §7.3 |

## 2. Ảnh bổ sung (giữ nguyên, không thay thế ảnh 02–04)

| File | Nội dung | Vị trí trong report.md |
|---|---|---|
| `evidence/screenshots/final-lan-pasv.png` | PASV upload/download hai máy hoàn tất (client progress) | §7.3 |
| `evidence/screenshots/active-demo-success.png` | ACTIVE source/server/download SHA-256 khớp | §7.3 |

## 2b. Role A — 5 ảnh evidence bắt buộc (oral defense, 2026-08-11)

Chụp trên **macOS localhost** (`127.0.0.1:2121`), commit `43764fd`, ngày
**2026-08-11**. Code không có file tracked nào bị sửa so với commit release
(`git status` chỉ có 19 untracked = runtime/evidence). Mọi command trong log
dùng `python3`; hash dùng `shasum -a 256` (macOS, thay cho `sha256sum`).

| File | Nội dung | Bằng chứng chính |
|---|---|---|
| `role-a-mode-b-pasv-roundtrip.png` | MODE B PASV round-trip | `200 Mode Block`; SHA-256 source/server/client **b57b64b1…** khớp nhau |
| `role-a-mode-c-active-roundtrip.png` | MODE C ACTIVE round-trip (localhost) | `200 Mode Compressed`; SHA-256 **b57b64b1…** khớp nhau |
| `role-a-concurrent-b-c-sessions.png` | 2 client B/C đồng thời (server log) | `S000001` (MODE C) + `S000002` (MODE B) cùng `'alive': True`, cả 2 STOR `result=success bytes=256000` |
| `role-a-control-command-evidence.png` | Control-channel transcript | `220 → 331 → 530` (login sai) → `230` → `213-Status` → `214 HELP MODE` → `501 STOU extra` → `221` |
| `role-a-final-pytest.png` | Full regression | `271 passed, 357 subtests passed in 177.16s` |

Kèm theo mỗi ảnh là transcript/hash trong `docs/evidence/`:
`role-a-mode-b-pasv.{log,-sha256.txt}`, `role-a-mode-c-active.{log,-sha256.txt}`,
`role-a-concurrent-b-c-sessions.log`, `role-a-control-command-evidence.log`,
`role-a-final-pytest.log`.

## 3. Cách nhúng

Mỗi ảnh được nhúng bằng block Markdown từ `docs/report.md` (đường dẫn tương đối
`evidence/screenshots/…` resolve tới `docs/evidence/screenshots/`):

```markdown
![alt text](evidence/screenshots/<file>.png)
*Figure: caption diễn giải bằng chứng.*
```

## 4. Ghi chú chỉnh sửa

- **2026-08-11** — thêm §2b: 5 ảnh evidence Role A cho oral defense (mục "Screenshot
  evidence giao Role A" trong `planning/weekly-plans/final-code-fix-a-c.md`).
  Tất cả chụp localhost macOS, commit `43764fd`; đã nhúng vào `docs/report.md`
  §7.1 (sub-block "Role A Oral-Defense Evidence").
- Đã rename 2 file có khoảng trắng thừa đầu tên để link Markdown sạch:
  - ` 01-full-pytest-271-passed.png` → `01-full-pytest-271-passed.png`
  - ` 03-sha256-pasv-active.png` → `03-sha256-pasv-active.png`
- Caption ảnh 01 dùng **271 passed** (khớp tên file thật và §8 report: full
  **271 passed + 357 subtests in 192.88s**), không dùng 199 passed — 199 là
  baseline lịch sử pre-MODE, không phản ánh screenshot hiện tại.
- Chi tiết GenAI usage được ghi trong `docs/genai-log-a.md` mục
  "Nhúng Evidence Screenshots vào Report §7".
