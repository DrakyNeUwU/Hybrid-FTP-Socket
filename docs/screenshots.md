# Screenshots — Evidence Collection Log

> Compatibility index for existing documentation and merge history. The report
> itself embeds the screenshots and is the current submission narrative; see
> [documentation source of truth](source-of-truth.md).

## Embedded in `report.md`

| File | Evidence |
|---|---|
| `evidence/screenshots/01-full-pytest-271-passed.png` | Full WSL2 regression — 271 passed |
| `evidence/screenshots/02-lan-pasv-server-lifecycle.png` | LAN PASV server lifecycle and `150 → 226` |
| `evidence/screenshots/03-sha256-pasv-active.png` | PASV/ACTIVE SHA-256 comparison |
| `evidence/screenshots/04-three-pasv-clients.png` | Three independent PASV clients |
| `evidence/screenshots/final-lan-pasv.png` | Two-machine PASV transfer |
| `evidence/screenshots/active-demo-success.png` | ACTIVE SHA-256 comparison |

## Role A oral-defense evidence

| File | Evidence |
|---|---|
| `role-a-mode-b-pasv-roundtrip.png` | MODE B PASV round-trip |
| `role-a-mode-c-active-roundtrip.png` | MODE C ACTIVE round-trip |
| `role-a-concurrent-b-c-sessions.png` | Concurrent B/C sessions |
| `role-a-control-command-evidence.png` | Control-channel transcript |
| `role-a-final-pytest.png` | Full regression output |

The supporting logs and SHA-256 files are in `docs/evidence/`. Do not treat
screenshots as newer than their dated logs or current automated tests.
