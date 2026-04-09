# Design audit

Tool untuk memeriksa kualitas dan konsistensi aset desain (saat ini: integrasi Figma).

## Isi folder

| Project | Deskripsi |
|---------|-----------|
| [design-system-audit](./design-system-audit/) | **Design System Health** — server Flask lokal, audit via Figma API, export ke `../Research/` (root monorepo). |

## Menjalankan design-system-audit

```bash
cd design-system-audit
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Buka http://127.0.0.1:5555 — detail lengkap ada di README modul tersebut.
