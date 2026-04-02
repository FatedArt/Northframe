# Design audit

Tool untuk memeriksa kualitas dan konsistensi aset desain (saat ini: integrasi Figma).

## Isi folder

| Project | Deskripsi |
|---------|-----------|
| [DesignSystemAudit](./DesignSystemAudit/) | **Design System Health** — server Flask lokal, audit via Figma API, export ke `../Research/` (root monorepo). |

## Menjalankan DesignSystemAudit

```bash
cd DesignSystemAudit
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Buka http://127.0.0.1:5555 — detail lengkap ada di README modul tersebut.
