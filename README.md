# northframe

Modular UI/UX productivity toolkit: design audits, research workflows, and repeatable design ops.

## Struktur repositori

```
northframe/
├── design-audit/              # Tooling audit & konsistensi design system
│   └── design-system-audit/   # Dashboard Flask + Figma REST API
├── design-research/           # Template & panduan alur riset / UX
│   ├── persona-creation/
│   ├── problem-statement/
│   ├── research-summary/
│   └── prd-ux-heuristic-evaluation/
├── prd/                       # Export PRD PDF lokal (di-gitignore; tidak di-push)
├── Research/                  # Output export audit (dibuat otomatis saat Export di dashboard)
├── LICENSE
└── README.md
```

## Modul

| Area | Path | Deskripsi |
|------|------|-----------|
| **Design system audit** | [design-audit/design-system-audit](./design-audit/design-system-audit/) | Dashboard lokal: audit file Figma (scope frame `Folder:`), skor kategori, export dokumentasi Markdown ke `Research/`. |
| **Persona** | [design-research/persona-creation](./design-research/persona-creation/) | Instruksi + sandbox untuk menyusun persona. |
| **Problem statement** | [design-research/problem-statement](./design-research/problem-statement/) | Template problem statement. |
| **Ringkasan riset** | [design-research/research-summary](./design-research/research-summary/) | Template ringkasan temuan riset. |

## Persyaratan

- Python 3.10+ untuk **design-system-audit**
- [Figma Personal Access Token](https://www.figma.com/developers/api#access-tokens) untuk audit

## Figma MCP Self-Host (Quickstart)

Untuk workflow AI-assisted design via MCP self-host (Cloudflare + Cursor + Figma Bridge), gunakan panduan berikut:

- Runbook lengkap: [design-research/figma-mcp-selfhost-runbook.md](./design-research/figma-mcp-selfhost-runbook.md)

Alur cepat:

1. Deploy `figma-console-mcp` ke Cloudflare Workers.
2. Set secret `FIGMA_ACCESS_TOKEN` via `wrangler secret`.
3. Konfigurasi Cursor `mcp.json` ke endpoint self-host `/mcp` dengan header `Authorization`.
4. Patch Figma Desktop Bridge agar `CLOUD_RELAY_HOST` mengarah ke domain self-host.
5. Pair Cloud Mode dengan `figma_pair_plugin`, lalu validasi tool call.

Catatan:

- Gunakan interpolasi env Cursor: `${env:FIGMA_ACCESS_TOKEN}`.
- Jangan hardcode token di repo.
- Revoke & rotate token jika pernah terekspos.

## Kontribusi

Tambahkan tool baru di `design-audit/` atau `design-research/` dengan README masing-masing. Hindari meng-commit `venv/` (sudah di `.gitignore`).

## Lisensi

Lihat [LICENSE](./LICENSE).
