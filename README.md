# Northframe

Modular UI/UX productivity toolkit: design audits, research workflows, and repeatable design ops.

## Struktur repositori

```
Northframe/
├── design-audit/           # Tooling audit & konsistensi design system
│   └── DesignSystemAudit/  # Dashboard Flask + Figma REST API
├── design-research/        # Template & panduan alur riset / UX
│   ├── PersonaCreation/
│   ├── ProblemStatement/
│   └── ResearchSummary/
├── Research/               # Output export audit (dibuat otomatis saat Export di dashboard)
├── LICENSE
└── README.md
```

## Modul

| Area | Path | Deskripsi |
|------|------|-----------|
| **Design system audit** | [design-audit/DesignSystemAudit](./design-audit/DesignSystemAudit/) | Dashboard lokal: audit file Figma (scope frame `Folder:`), skor kategori, export dokumentasi Markdown ke `Research/`. |
| **Persona** | [design-research/PersonaCreation](./design-research/PersonaCreation/) | Instruksi + sandbox untuk menyusun persona. |
| **Problem statement** | [design-research/ProblemStatement](./design-research/ProblemStatement/) | Template problem statement. |
| **Ringkasan riset** | [design-research/ResearchSummary](./design-research/ResearchSummary/) | Template ringkasan temuan riset. |

## Persyaratan

- Python 3.10+ untuk **DesignSystemAudit**
- [Figma Personal Access Token](https://www.figma.com/developers/api#access-tokens) untuk audit

## Kontribusi

Tambahkan tool baru di `design-audit/` atau `design-research/` dengan README masing-masing. Hindari meng-commit `venv/` (sudah di `.gitignore`).

## Lisensi

Lihat [LICENSE](./LICENSE).
