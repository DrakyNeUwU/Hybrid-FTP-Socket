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

## 3. Cách nhúng

Mỗi ảnh được nhúng bằng block Markdown từ `docs/report.md` (đường dẫn tương đối
`evidence/screenshots/…` resolve tới `docs/evidence/screenshots/`):

```markdown
![alt text](evidence/screenshots/<file>.png)
*Figure: caption diễn giải bằng chứng.*
```

## 4. Ghi chú chỉnh sửa

- Đã rename 2 file có khoảng trắng thừa đầu tên để link Markdown sạch:
  - ` 01-full-pytest-271-passed.png` → `01-full-pytest-271-passed.png`
  - ` 03-sha256-pasv-active.png` → `03-sha256-pasv-active.png`
- Caption ảnh 01 dùng **271 passed** (khớp tên file thật và §8 report: full
  **271 passed + 357 subtests in 192.88s**), không dùng 199 passed — 199 là
  baseline lịch sử pre-MODE, không phản ánh screenshot hiện tại.
- Chi tiết GenAI usage được ghi trong `docs/genai-log-a.md` mục
  "Nhúng Evidence Screenshots vào Report §7".
